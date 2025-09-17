group_col <- "genotype"
value_col <- "expression"
alpha <- 0.05
control <- "control"
out_csv <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/saida2.csv"

if (!requireNamespace("DescTools", quietly=TRUE)) {{
    install.packages("DescTools", repos="https://cloud.r-project.org")
}}
library(DescTools)
library(readxl)

d <- read_xlsx("L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/exemplos.xlsx", sheet="Dunnet")
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
