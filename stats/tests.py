# graph_app/stats/tests.py
"""
R-backed statistical tests wrappers.

Funcionalidade:
- tukey_test_r(df, group_col, value_col, alpha=0.05, timeout=60)
- dunnett_test_r(df, group_col, value_col, control_label, alpha=0.05, timeout=60)
- pairwise_ttests_vs_control_r(df, group_col, value_col, control_label, alpha=0.05, p_adjust_method='holm', timeout=60)

Cada função tenta usar Rscript (escreve um R temporário e o executa).
Se Rscript não for encontrado, as funções levantam RuntimeError (ou podem
ser estendidas para rodar versões em Python).
"""

import os
import re
import shutil
import subprocess
import tempfile
import pandas as pd
import textwrap

def _find_rscript():
    """Retorna path para Rscript se disponível, senão None."""
    return shutil.which("Rscript")

def _run_r_script(r_code: str, args: list, timeout: int = 60):
    """
    Escreve r_code em um arquivo temporário e executa com Rscript, passando args.
    Retorna path para out CSVs que o script gerou (ou pandas DataFrame read) conforme convenção.
    Lança RuntimeError em caso de falha, com stderr incluído.
    """
    rscript = _find_rscript()
    if not rscript:
        raise RuntimeError("Rscript não encontrado no PATH. Instale R e adicione Rscript ao PATH.")

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "run_r_script.R")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(r_code)

        cmd = [rscript, script_path] + args
        try:
            completed = subprocess.run(cmd, check=True, capture_output=True, timeout=timeout, text=True)
            # sucesso: stdout/stderr disponíveis se precisar
            return completed.stdout, completed.stderr, tmpdir
        except subprocess.CalledProcessError as e:
            msg = f"Rscript retornou código de erro {e.returncode}.\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
            raise RuntimeError(msg)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Rscript timeout depois de {timeout}s. stdout: {e.stdout} stderr: {e.stderr}")


def tukey_test_r(df: pd.DataFrame, group_col: str, value_col: str, alpha: float =0.05, timeout: int = 60) -> pd.DataFrame:
    """
    Executa Tukey HSD usando R (aov + TukeyHSD).
    Retorna um DataFrame com as colunas padrão (group1, group2, meandiff, p adj, lower, upper).
    """
    rscript = _find_rscript()
    if not rscript:
        raise RuntimeError("Rscript não encontrado. Instale R para usar tukey_test_r().")

    with tempfile.TemporaryDirectory() as tmpdir:
        in_csv = os.path.join(tmpdir, "input.csv")
        out_csv = os.path.join(tmpdir, "tukey_out.csv")
        df[[group_col, value_col]].to_csv(in_csv, index=False)

        r_code = textwrap.dedent(f"""
        args <- commandArgs(trailingOnly=TRUE)
        in_csv <- args[1]
        group_col <- args[2]
        value_col <- args[3]
        out_csv <- args[4]
        alpha <- as.numeric(args[5])

        d <- read.csv(in_csv, stringsAsFactors=FALSE)
        # garantir tipos
        d[[group_col]] <- as.factor(d[[group_col]])
        d[[value_col]] <- as.numeric(d[[value_col]])

        # aov + TukeyHSD
        formula <- as.formula(paste(value_col, "~", group_col))
        fit <- aov(formula, data=d)
        tuk <- TukeyHSD(fit, conf.level = 1 - alpha)
        # TukeyHSD retorna uma lista por term; pegamos o primeiro
        termname <- names(tuk)[1]
        dfres <- as.data.frame(tuk[[termname]])
        # dfres tem rownames como "A-B", convertemos em duas colunas
        dfres$comparison <- rownames(dfres)
        # organizar colunas: comparison, diff, lwr, upr, p adj (padj)
        # nomes variam dependendo da versão R; padj chama-se 'p adj'
        names(dfres) <- make.names(names(dfres))
        # salvar em csv
        write.csv(dfres, out_csv, row.names=FALSE)
        """).strip()

        args = [in_csv, group_col, value_col, out_csv, str(alpha)]
        stdout, stderr, _ = _run_r_script(r_code, args, timeout=timeout)

        if not os.path.exists(out_csv):
            raise RuntimeError(f"R não gerou saída esperada. stdout: {stdout}\\nstderr: {stderr}")

        res = pd.read_csv(out_csv)
        # tentar extrair group1/group2 se comparison tem ' - ' or ' - ' or ' vs ' or '-'
        if 'comparison' in res.columns:
            comps = res['comparison'].astype(str).str.replace(r'\\.', ' ', regex=True)
            g1, g2 = [], []
            for c in comps:
                m = re.match(r"^(.*-\d+)-(.*)$", c)
                if m:
                    g1.append(m.group(1).strip())
                    g2.append(m.group(2).strip())
                else:
                    sep = None
                    for s in [' - ', '-', ' vs ', ' vs. ', ' ']:
                        if s in c:
                            sep=s; break
                    if sep:
                        parts = [p.strip() for p in c.split(sep) if p.strip()]
                        if len(parts)>=2:
                            g1.append(parts[0]); g2.append(parts[1])
                        else:
                            g1.append(parts[0]); g2.append('')
                    else:
                        g1.append(c); g2.append('')
            res.insert(0, 'group1', g1)
            res.insert(1, 'group2', g2)
        return res


def dunnett_test_r(df: pd.DataFrame, group_col: str, value_col: str, control_label: str, alpha: float = 0.05, timeout: int = 120) -> pd.DataFrame:
    """
    Executa Dunnett test exato via DescTools::DunnettTest em R.
    Retorna DataFrame com resultados (colunas dependem da DescTools, geralmente includes 'p-value').
    """
    rscript = _find_rscript()
    if not rscript:
        raise RuntimeError("Rscript não encontrado. Instale R para usar dunnett_test_r().")

    with tempfile.TemporaryDirectory() as tmpdir:
        in_csv = os.path.join(tmpdir, "input.csv")
        out_csv = os.path.join(tmpdir, "dunnett_out.csv")
        df[[group_col, value_col]].to_csv(in_csv, index=False)

        # R script: instala DescTools se não tiver, roda DunnettTest e salva CSV com 'comparison' col
        r_code = textwrap.dedent(f"""
        args <- commandArgs(trailingOnly=TRUE)
        in_csv <- args[1]
        group_col <- args[2]
        value_col <- args[3]
        control <- args[4]
        out_csv <- args[5]

        if (!requireNamespace("DescTools", quietly=TRUE)) {{
          install.packages("DescTools", repos="https://cloud.r-project.org")
        }}
        library(DescTools)
        d <- read.csv(in_csv, stringsAsFactors=FALSE)
        d[[group_col]] <- as.factor(d[[group_col]])
        res <- DunnettTest(d[[value_col]], d[[group_col]], control = control)
        # res pode ser a matriz direta; vamos transformar em data.frame
        if (is.list(res)) {{
          tmp <- res[[1]]
        }} else {{
          tmp <- res
        }}
        dfres <- as.data.frame(tmp)
        dfres$comparison <- rownames(dfres)
        # reorganizar: comparison first
        dfres <- dfres[, c("comparison", setdiff(names(dfres), "comparison"))]
        write.csv(dfres, out_csv, row.names=FALSE)
        """).strip()

        args = [in_csv, group_col, value_col, str(control_label), out_csv]
        stdout, stderr, _ = _run_r_script(r_code, args, timeout=timeout)

        if not os.path.exists(out_csv):
            raise RuntimeError(f"R não gerou saída esperada. stdout: {stdout}\\nstderr: {stderr}")

        res = pd.read_csv(out_csv)
        return res


def pairwise_ttests_vs_control_r(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    control_label: str,
    alpha: float = 0.05,
    p_adjust_method: str = "holm",
    timeout: int = 60,
    **kwargs 
) -> pd.DataFrame:
    """
    Para cada grupo != control, executa t.test(control, group) em R (Welch),
    calcula p-values e aplica p.adjust(method = p_adjust_method).
    Retorna DataFrame com columns: comparison, statistic, p_raw, p_adj, reject (logical).
    """
    rscript = _find_rscript()
    if not rscript:
        raise RuntimeError("Rscript não encontrado. Instale R para usar pairwise_ttests_vs_control_r().")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        in_csv = os.path.join(tmpdir, "input.csv")
        out_csv = os.path.join(tmpdir, "ttest_out.csv")
        
        try:
            r_code = textwrap.dedent(f"""
                args <- commandArgs(trailingOnly = TRUE)

                in_csv     <- args[1]
                group_col   <- args[2]
                fator_col   <- args[3]
                value_col  <- args[4]
                padj_method <- args[5]
                out_csv    <- args[6]
                alpha <- as.numeric(args[7])

                # instalar pacotes ausentes automaticamente (opcional)
                needed <- c("dplyr", "rlang")
                for (p in needed) {{
                    if (!requireNamespace(p, quietly = TRUE)) {{
                        install.packages(p, repos = "https://cloud.r-project.org")
                    }}
                }}
                library(dplyr)
                library(rlang)


                names <- c()
                stats <- c()

                # Ler os dados
                data <- read.csv(in_csv, stringsAsFactors=FALSE)

                # t-test por grupo (group_col) — agora também captura a estatística t e a string de comparação
                t_test_results <- data %>%
                group_by(!!sym(group_col)) %>%
                group_modify(~{{
                    df <- .
                    lv <- unique(df[[fator_col]])
                    if (length(lv) == 2) {{
                    g1 <- df[[value_col]][df[[fator_col]] == lv[1]]
                    g2 <- df[[value_col]][df[[fator_col]] == lv[2]]
                    res <- tryCatch(t.test(g1, g2, var.equal = FALSE), error = function(e) NULL)
                    pval <- if (is.null(res)) NA_real_ else res$p.value
                    stat <- if (is.null(res)) NA_real_ else as.numeric(res$statistic)
                    comp <- paste0(unique(df[[group_col]]), " : ", lv[1], " vs ", lv[2])
                    tibble(p_value = pval, statistic = stat, comparison = comp)
                    }} else {{
                    tibble(p_value = NA_real_, statistic = NA_real_, comparison = NA_character_)
                    }}
                }}) %>% ungroup()

                # extrai vetores para gerar a saída no mesmo formato do teste-t.r
                pvals <- t_test_results$p_value
                stats <- t_test_results$statistic
                first_col <- names(t_test_results)[1]
                last_col  <- names(t_test_results)[ncol(t_test_results)]
                names <- paste0(as.character(t_test_results[[first_col]]), as.character(t_test_results[[last_col]]))

                p_adj <- p.adjust(pvals, method = padj_method)
                reject <- ifelse(!is.na(p_adj) & p_adj < alpha, TRUE, FALSE)


                out_df <- data.frame(comparison = names, statistic = stats, p_raw = pvals, p_adj = p_adj, reject = reject, stringsAsFactors=FALSE)
                # Salvar em CSV
                write.csv(out_df, out_csv, row.names = FALSE)
            """).strip()
            
            fator_col = kwargs.get('fator_col')
            df[[fator_col, group_col, value_col]].to_csv(in_csv, index=False)
            if not fator_col:
                raise ValueError

            args = [in_csv, group_col, fator_col, value_col, p_adjust_method, out_csv, str(alpha)]
        
        except:
            df[[group_col, value_col]].to_csv(in_csv, index=False)
            r_code = textwrap.dedent(f"""
                args <- commandArgs(trailingOnly=TRUE)
                in_csv <- args[1]
                group_col <- args[2]
                value_col <- args[3]
                control <- args[4]
                out_csv <- args[5]
                padj_method <- args[6]
                alpha <- as.numeric(args[7])

                d <- read.csv(in_csv, stringsAsFactors=FALSE)
                d[[group_col]] <- as.character(d[[group_col]])
                groups <- unique(d[[group_col]])
                others <- setdiff(groups, control)
                pvals <- c()
                stats <- c()
                names <- c()
                for (g in others) {{
                a <- d[d[[group_col]] == control, value_col]
                b <- d[d[[group_col]] == g, value_col]
                # usar t.test Welch (var not assumed equal)
                res <- try(t.test(as.numeric(a), as.numeric(b), var.equal=FALSE), silent=TRUE)
                if (inherits(res, "try-error")) {{
                    pvals <- c(pvals, NA)
                    stats <- c(stats, NA)
                }} else {{
                    pvals <- c(pvals, res$p.value)
                    stats <- c(stats, res$statistic)
                }}
                names <- c(names, paste(control, "vs", g))
                }}
                p_adj <- p.adjust(pvals, method = padj_method)
                reject <- ifelse(!is.na(p_adj) & p_adj < alpha, TRUE, FALSE)
                out_df <- data.frame(comparison = names, statistic = stats, p_raw = pvals, p_adj = p_adj, reject = reject, stringsAsFactors=FALSE)
                write.csv(out_df, out_csv, row.names=FALSE)
            """).strip()
            
            args = [in_csv, group_col, value_col, str(control_label), out_csv, p_adjust_method, str(alpha)]

        stdout, stderr, _ = _run_r_script(r_code, args, timeout=timeout)

        if not os.path.exists(out_csv):
            raise RuntimeError(f"R não gerou saída esperada. stdout: {stdout}\\nstderr: {stderr}")

        res = pd.read_csv(out_csv)
        return res
