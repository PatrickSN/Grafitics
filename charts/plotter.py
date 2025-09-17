import numpy as np
from matplotlib.figure import Figure
import seaborn as sns
from charts.annotations import annotate_significance


def generate_barplot(
    df,
    group_col,
    value_col,
    bar_color="#2ca02c",
    pmap_pairwise=None,
    pmap_vs_control=None,
    control=None,
    alpha=0.05,
    show_legend=True,
    title="",
    ylabel="",
    xlabel="",
    figsize=(8, 5),
    fontsize=10,
    bracket_scope='control',
    color_mode="Unique"   # "Unique" ou "Alternate"
):
    """
    Gera um barplot com barras de erro (SEM) e adiciona anotações de significância,
    permitindo escolher cor única ou cores alternadas.
    """
    fig = Figure(figsize=figsize, dpi=300)
    ax = fig.add_subplot(111)

    # estilo dos eixos
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # dados básicos
    grp = df.groupby(group_col)[value_col]
    means = grp.mean()
    sem = grp.sem()
    labels = list(means.index)
    x = np.arange(len(labels))

    # controle de cores
    if color_mode == "Alternate":
        # paleta alternada baseada no seaborn
        palette = sns.color_palette("Set2", len(labels))
    else:
        # cor única
        palette = [bar_color] * len(labels)

    # desenhar barras
    bars = ax.bar(x, means.values, yerr=sem.values, capsize=6, label=value_col)
    for b, c in zip(bars, palette):
        b.set_color(c)

    ax.set_ylim(0, means.values.max() * 1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=fontsize)
    ax.set_ylabel(ylabel or "", fontsize=fontsize)
    ax.set_xlabel(xlabel or "", fontsize=fontsize)
    ax.set_title(title or "", fontsize=fontsize)

    # Pontos individuais
    sns.stripplot(x=group_col, y=value_col, data=df, hue=group_col,
                  jitter=0.1, size=1, palette='dark:black', ax=ax, legend=show_legend)

    if show_legend:
        ax.legend(fontsize=fontsize)
    elif ax.get_legend():
        ax.get_legend().remove()

    fig.tight_layout()

    # call annotations
    pmap_pairwise = pmap_pairwise or {}
    pmap_vs_control = pmap_vs_control or {}
    means_arr = np.array(means.values)
    sem_arr = np.array(sem.values)

    try:
        annotate_significance(
            ax=ax,
            labels=labels,
            means_arr=means_arr,
            sem_arr=sem_arr,
            pmap_pairwise=pmap_pairwise,
            pmap_vs_control=pmap_vs_control,
            control=control,
            alpha=alpha,
            bracket_scope=bracket_scope,
            fontsize=fontsize
        )
    except Exception:
        # não interrompe a plotagem caso anotações falhem
        pass

    return fig
