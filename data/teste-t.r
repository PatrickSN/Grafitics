args <- commandArgs(trailingOnly=TRUE)
in_csv <- args[1]
group_col <- args[2]
value_col <- args[3]
control <- args[4]
out_csv <- args[5]
padj_method <- args[6]
alpha <- as.numeric(args[7])

{
    in_csv     <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/input2.csv"
    group_col  <- 'genotype'   # permanece disponível se necessário
    value_col  <- 'expression'
    control    <- 'control'
    out_csv    <- "L:/Projetos/Lab/Projetos/Gerador_GraficosV3/data/saida2.csv"
    padj_method <- "holm"
    alpha <- 0.05
}

d <- read.csv(in_csv, stringsAsFactors=FALSE)
d[[group_col]] <- as.character(d[[group_col]])
groups <- unique(d[[group_col]])
others <- setdiff(groups, control)
pvals <- c()
stats <- c()
names <- c()
for (g in others) {
a <- d[d[[group_col]] == control, value_col]
b <- d[d[[group_col]] == g, value_col]
# usar t.test Welch (var not assumed equal)
res <- try(t.test(as.numeric(a), as.numeric(b), var.equal=FALSE), silent=TRUE)
if (inherits(res, "try-error")) {
    pvals <- c(pvals, NA)
    stats <- c(stats, NA)
} else {
    pvals <- c(pvals, res$p.value)
    stats <- c(stats, res$statistic)
}
names <- c(names, paste(control, "vs", g))
}
p_adj <- p.adjust(pvals, method = padj_method)
reject <- ifelse(!is.na(p_adj) & p_adj < alpha, TRUE, FALSE)
out_df <- data.frame(comparison = names, statistic = stats, p_raw = pvals, p_adj = p_adj, reject = reject, stringsAsFactors=FALSE)
write.csv(out_df, out_csv, row.names=FALSE)