library(readxl)

group_col <- "genotype"
value_col <- "expression"
alpha <- 0.05
out_csv <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/saida.csv"

d <- read_xlsx("L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/exemplos.xlsx", sheet="Tukey")
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
