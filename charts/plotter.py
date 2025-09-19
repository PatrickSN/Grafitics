import numpy as np
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import seaborn as sns
from charts.annotations import annotate_significance
from scipy.stats import ttest_ind
from stats.helpers import stars_from_p

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
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_title(title, fontsize=fontsize)

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


def generate_barplot_ttest(
    df,
    group_col,
    fator_col,
    value_col,
    title="",
    ylabel="",
    xlabel="",
    alpha=0.05,
    figsize=(8, 5),
    fontsize=10
):
    """
    Gera gráfico estilo t-test two-by-two:
    - eixo X = fator (ex: condition)
    - barras = média de value_col
    - hue = group_col (ex: genotype)
    - error bars = SEM
    - asterisco acima das comparações significativas
    """

    # calcular estatísticas resumo
    summary_stats = df.groupby([group_col, fator_col])[value_col].agg(['mean','sem']).reset_index()
    summary_stats.rename(columns={'sem':'SE'}, inplace=True)

    # ordem dos fatores no eixo X
    ordens = sorted(summary_stats[group_col].unique())

    # mapa de significância (comparando entre grupos dentro de cada fator)
    sig_map = {}
    for fator in ordens:
        sub = df[df[group_col] == fator]
        groups = sub[fator_col].unique()
        if len(groups) == 2:  # só funciona para dois grupos por fator
            g1, g2 = groups
            vals1 = sub[sub[fator_col] == g1][value_col]
            vals2 = sub[sub[fator_col] == g2][value_col]
            stat, pval = ttest_ind(vals1, vals2, equal_var=False)
            if pval < alpha:
                sig_map[fator] = "*" if pval < alpha else "ns"

    # criar figura
    fig, ax = plt.subplots(figsize=figsize, dpi=300)

    # gráfico de barras
    sns.barplot(
        data=summary_stats,
        x=group_col,
        y="mean",
        hue=fator_col,
        ax=ax,
        capsize=0.1,
        palette="Set2",
        order=ordens
    )

    # stripplot com dados individuais
    sns.stripplot(
        x=group_col,
        y=value_col,
        data=df,
        hue=fator_col,
        order=ordens,
        dodge=True,
        jitter=0.1,
        size=1,
        palette='dark:black',
        ax=ax
    )

    # corrigir duplicação de legenda (barplot + stripplot)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[:len(df[fator_col].unique())], labels[:len(df[fator_col].unique())], loc="upper center", ncol=2, frameon=False)

    # adicionar barras de erro manuais
    names = summary_stats[fator_col].unique()
    y_max = summary_stats['mean'].max()*1.25
    for i, row in summary_stats.iterrows():
        fator = row[group_col]
        grupo = row[fator_col]
        media = row['mean']
        erro = row['SE']
        idx_fator = ordens.index(fator)
        deslocamento = -0.2 if grupo == names[0] else 0.2
        x_pos = idx_fator + deslocamento
        ax.errorbar(x=x_pos, y=media, yerr=erro, fmt='none', c='black', capsize=5, linewidth=0.5)

    # adicionar significância entre as barras de cada fator
    for fator in ordens:
        sig = sig_map.get(fator, "")
        if sig and sig != "ns":
            idx_fator = ordens.index(fator)
            x0 = idx_fator - 0.2
            x1 = idx_fator + 0.2
            y_linha = summary_stats['mean'].max()*1.1
            ax.plot([x0, x1], [y_linha, y_linha], c='black', linewidth=1)
            ax.text(idx_fator, y_linha, sig, ha='center', va='bottom', fontsize=fontsize)

    
    ax.set_ylim(0, y_max)
    ax.set_xticklabels(ordens, rotation=45, ha='right', fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_title(title, fontsize=fontsize)

    sns.despine()
    fig.tight_layout()

    return fig

def generate_multi_barplot(
    df,
    x_col,
    group_col,
    value_col,
    title="",
    ylabel="",
    xlabel="",
    alpha=0.05,
    figsize=(8, 5),
    fontsize=10,
    colors=None,
    show_error=True,
    show_std=False
):
    """
    Gera gráfico de barras agrupadas (grupos lado-a-lado por categoria),
    desenha erro (SEM por padrão ou desvio padrão se show_std=True),
    plota pontos individuais e adiciona anotações de significância (ttest
    entre pares de 'group_col' dentro de cada categoria de 'x_col').

    Retorna matplotlib.figure.Figure
    """
    # agregações
    means = df.groupby([x_col, group_col])[value_col].mean().unstack(fill_value=np.nan)
    sem = df.groupby([x_col, group_col])[value_col].sem().unstack(fill_value=0)
    std = df.groupby([x_col, group_col])[value_col].std().unstack(fill_value=0)

    labels = list(means.index)
    groups = list(means.columns)

    n_cat = len(labels)
    n_grp = len(groups)
    if n_cat == 0 or n_grp == 0:
        # figura vazia
        fig = Figure(figsize=figsize, dpi=300)
        fig.add_subplot(111).text(0.5, 0.5, "Sem dados", ha="center")
        return fig

    x = np.arange(n_cat)
    total_width = 0.8
    bar_width = total_width / n_grp

    fig = Figure(figsize=figsize, dpi=300)
    ax = fig.add_subplot(111)

    # cores padrão se não fornecidas
    if colors is None:
        cmap = plt.get_cmap("tab10")
        colors = [cmap(i) for i in range(n_grp)]

    # desenha barras para cada grupo (hue)
    pos_arrays = {}
    for i, grp in enumerate(groups):
        pos_arr = x - total_width/2 + i*bar_width + bar_width/2
        pos_arrays[grp] = pos_arr  # array de posições por categoria
        heights = means[grp].values
        errs = (std[grp].values if show_std else (sem[grp].values if show_error else None))
        ax.bar(pos_arr, heights, width=bar_width, label=str(grp),
               color=colors[i % len(colors)], yerr=errs, capsize=5)

    # stripplot com dados individuais (sobrepor usando posições categóricas)
    sns.stripplot(
        x=x_col,
        y=value_col,
        hue=group_col,
        data=df,
        order=labels,
        dodge=True,
        jitter=0.12,
        size=2,
        palette='dark:black',
        ax=ax
    )

    # layout e rótulos
    ax.set_xticks(x)
    ax.set_xticklabels([str(l) for l in labels], rotation=45, ha='right', fontsize=fontsize)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.set_title(title, fontsize=fontsize)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    handles, labs = ax.get_legend_handles_labels()
    by_label = dict(zip(labs, handles))  # remove duplicados mantendo o último
    ax.legend(by_label.values(), by_label.keys(),
            fontsize=max(10, fontsize-2))
    #ax.legend(by_label.values(), by_label.keys(),fontsize=max(10, fontsize-2), ncol=2, frameon=False, loc="upper center")

    # ajuste de limites para margem superior
    # usar máximo das médias + erro para cálculo de offset
    combined_max = np.nanmax((means.values + (std.values if show_std else sem.values))) if means.size else 1.0
    ax.set_ylim(0, combined_max * 1.25)

    # --- anotações de significância por categoria (pares de grupos dentro de cada x) ---
    # configuração de offsets por categoria para evitar sobreposição
    base_range = (np.nanmax(means.values) - np.nanmin(means.values)) if means.size else 1.0
    base_offset = base_range * 0.06 if base_range > 0 else 0.5

    # Nova lógica: fixar todas as anotações em 1.15 * maior média
    max_mean = np.nanmax(means.values) if means.size else 1.0
    annotation_y = max_mean * 1.15
    # altura das pernas do bracket
    h = base_range * 0

    for idx_cat, label in enumerate(labels):
        # testar todos os pares de grupos dentro desta categoria
        for i in range(len(groups)):
            for j in range(i+1, len(groups)):
                g1 = groups[i]
                g2 = groups[j]
                vals1 = df[(df[x_col] == label) & (df[group_col] == g1)][value_col].dropna().values
                vals2 = df[(df[x_col] == label) & (df[group_col] == g2)][value_col].dropna().values
                if len(vals1) < 2 or len(vals2) < 2:
                    continue
                try:
                    stat, pval = ttest_ind(vals1, vals2, equal_var=False)
                except Exception:
                    continue
                star = stars_from_p(pval, alpha=alpha, all_pvalue=False)
                if not star:
                    continue  # sem anotação se não significativo

                # posições das barras específicas para esta categoria
                pos_i = pos_arrays[g1][idx_cat]
                pos_j = pos_arrays[g2][idx_cat]

                # desenha bracket com topo fixo em annotation_y
                ax.plot([pos_i, pos_i], [annotation_y - h, annotation_y], linewidth=1.2, color='black')
                ax.plot([pos_j, pos_j], [annotation_y - h, annotation_y], linewidth=1.2, color='black')
                ax.plot([pos_i, pos_j], [annotation_y, annotation_y], linewidth=1.2, color='black')
                # texto com estrelas acima do bracket
                ax.text((pos_i + pos_j) / 2.0, annotation_y + h * 0.2, star, ha='center', va='bottom', fontsize=fontsize, fontweight='bold')

    # garantir que ylim acomode as anotações fixas
    top_needed = annotation_y + base_offset
    cur_ymin, cur_ymax = ax.get_ylim()
    if top_needed > cur_ymax:
        ax.set_ylim(cur_ymin, top_needed)

    fig.tight_layout()
    return fig