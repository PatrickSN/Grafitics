args <- commandArgs(trailingOnly = TRUE)
{
in_csv     <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/input.csv" #args[1]
group_col  <- 'genotype'#args[2]
fator_col  <- 'condition'#args[3]
value_col  <- 'expression'#args[4]
control    <- 'control'#args[5]
out_csv    <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/saida.csv"#args[6]
alpha <- as.numeric('0.05')
}
# instalar pacotes ausentes automaticamente (opcional)
needed <- c("dplyr", "rlang")
for (p in needed) {
    if (!requireNamespace(p, quietly = TRUE)) {
        install.packages(p, repos = "https://cloud.r-project.org")
    }
}
library(dplyr)
library(rlang)


names <- c()
stats <- c()

# Ler os dados
data <- read.csv(in_csv, stringsAsFactors=FALSE)

# t-test por grupo (group_col) — agora também captura a estatística t e a string de comparação
t_test_results <- data %>%
  group_by(!!sym(group_col)) %>%
  group_modify(~{
    df <- .
    lv <- unique(df[[fator_col]])
    if (length(lv) == 2) {
      g1 <- df[[value_col]][df[[fator_col]] == lv[1]]
      g2 <- df[[value_col]][df[[fator_col]] == lv[2]]
      res <- tryCatch(t.test(g1, g2, var.equal = FALSE), error = function(e) NULL)
      pval <- if (is.null(res)) NA_real_ else res$p.value
      stat <- if (is.null(res)) NA_real_ else as.numeric(res$statistic)
      comp <- paste0(unique(df[[group_col]]), ": ", lv[1], " vs ", lv[2])
      tibble(p_value = pval, statistic = stat, comparison = comp)
    } else {
      tibble(p_value = NA_real_, statistic = NA_real_, comparison = NA_character_)
    }
  }) %>% ungroup()

# extrai vetores para gerar a saída no mesmo formato do teste-t.r
pvals <- t_test_results$p_value
stats <- t_test_results$statistic
first_col <- names(t_test_results)[1]
last_col  <- names(t_test_results)[ncol(t_test_results)]
names <- paste0(as.character(t_test_results[[first_col]]), as.character(t_test_results[[last_col]]))

# ajustar p-valor (escolha de método: "BH" por padrão)
p_adj <- p.adjust(pvals, method = "BH")
reject <- ifelse(!is.na(p_adj) & p_adj < alpha, TRUE, FALSE)

out_df <- data.frame(comparison = names, statistic = stats, p_raw = pvals, p_adj = p_adj, reject = reject, stringsAsFactors=FALSE)
# Salvar em CSV
write.csv(out_df, out_csv, row.names = FALSE)

