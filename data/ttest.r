args <- commandArgs(trailingOnly = TRUE)

in_csv     <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/input.csv" #args[1]
group_col  <- 'genotype'#args[2]
fator_col  <- 'condition'#args[3]
value_col  <- 'expression'#args[4]
control    <- 'control'#args[5]
out_csv    <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/saida.csv"#args[6]
alpha <- as.numeric('0.05')

# instalar pacotes ausentes automaticamente (opcional)
needed <- c("dplyr", "rlang")
for (p in needed) {
    if (!requireNamespace(p, quietly = TRUE)) {
        install.packages(p, repos = "https://cloud.r-project.org")
    }
}
library(dplyr)
library(rlang)

# Ler os dados
data <- read.csv(in_csv, stringsAsFactors=FALSE)

# summary (média + se)
summary_data <- data %>%
group_by(!!sym(group_col), !!sym(fator_col)) %>%
summarise(
    mean_value = mean(.data[[value_col]], na.rm = TRUE),
    se_value   = sd(.data[[value_col]], na.rm = TRUE) / sqrt(sum(!is.na(.data[[value_col]]))),
    .groups = "drop"
)

# t-test por grupo (group_col)
t_test_results <- data %>%
group_by(!!sym(group_col)) %>%
summarise(
    p_value = {
    if (n_distinct(.data[[fator_col]]) == 2) {
        lv <- unique(.data[[fator_col]])
        g1 <- .data[[value_col]][.data[[fator_col]] == lv[1]]
        g2 <- .data[[value_col]][.data[[fator_col]] == lv[2]]
        out <- tryCatch(t.test(g1, g2)$p.value, error = function(e) NA_real_)
        out
    } else {
        NA_real_
    }
    },
    .groups = "drop"
)

# juntar e adicionar asterisco conforme seu R original
summary_data <- summary_data %>%
left_join(t_test_results, by = group_col) %>%
mutate(asterisk = ifelse(.data[[fator_col]] == control, "", ifelse(p_value <= alpha, "*", "")))

# Resultado final com médias, SE, p-values e marcação de significância
out_df <- summary_data %>%
  mutate(
    reject = ifelse(!is.na(p_value) & p_value <= alpha, TRUE, FALSE)
  )

# Salvar em CSV
write.csv(out_df, out_csv, row.names = FALSE)
