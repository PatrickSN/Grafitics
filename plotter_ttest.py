import pandas as pd
from charts.plotter import *

# carregar tabela de teste
df = pd.read_excel("data/exemplos.xlsx", sheet_name="t-test")

# parâmetros do gráfico
fig = generate_multi_barplot(
    df=df, 
    x_col= "genotype",
    group_col= "condition",
    value_col =  "expression",
    title="",
    ylabel="",
    xlabel="",
    alpha=0.05,
    figsize=(8, 5),
    fontsize=10

)
out_file = "grafico_ttest_output.png"
fig.savefig(out_file, dpi=300)


df = pd.DataFrame({
    "trat": ["A","A","A","A","A","A","B","B","B","B","B","B","C","C","C","C","C","C"],
    "cond": ["X","Y","X","Y","X","Y","X","Y","X","Y","X","Y","X","Y","X","Y","X","Y"],
    "valor": [1.2, 1.5,1.0,1.3,1.4,1.1, 2.0,2.2,2.3,2.4,2.5,2.1, 3.0,3.1,3.2,3.3,3.4,3.5]
})

fig = generate_multi_barplot(
    df=df, 
    x_col="trat",
    group_col="cond",
    value_col="valor",
    title="Gráfico de barras múltiplas",


)

# salvar o gráfico
out_file = "grafico_output.png"
fig.savefig(out_file, dpi=300)
print(f"Gráfico salvo em {out_file}")


# agrupa por duas colunas e calcula média e SEM
grp = df.groupby(["trat", "cond"])["valor"]
means = grp.mean()            # Series com MultiIndex (trat, cond)
sems = grp.sem()

print(means)
print(sems)