def run_t_test(data: pd.DataFrame, group_col: str, fator_col: str, response_col: float) -> pd.DataFrame:
    """
    Para cada nível único de `fator_col`, faz um t-test entre as duas categorias de `group_col`.
    Parâmetros:
    - data: DataFrame contendo os dados.
    - group_col: Nome da coluna com os grupos (categorias).
    - fator_col: Nome da coluna com o fator (ex: 'time').
    - response_col: Nome da coluna com os dados de resposta (ex: 'value').

    Retorna um DataFrame com as colunas:
      - fator_col
      - group1, group2   (nomes das duas categorias)
      - n1, n2           (tamanhos amostrais)
      - t_stat, p_value
      - significance     ("ns", "*", "**", "***")
    """
    
    results = []

    if fator_col:
        # garante ordem consistente de tempos (se quiser custom, ajuste esta linha)
        fatores = data[fator_col].unique()
        for f in fatores:
            sub = data[data[fator_col] == f]
            groups = sub[group_col].unique()
            if len(groups) != 2:
                continue  # pula se não houver exatamente 2 grupos
            g1, g2 = groups
            v1 = sub[sub[group_col] == g1][response_col]
            v2 = sub[sub[group_col] == g2][response_col]
            t_stat, p = ttest_ind(v1, v2, equal_var=False)
            # monta notação de significância
            if p < 0.001:
                sig = '***'
            elif p < 0.01:
                sig = '**'
            elif p < 0.05:
                sig = '*'
            else:
                sig = 'ns'
            results.append({
                fator_col: f,
                'group1': g1,
                'group2': g2,
                'n1': len(v1),
                'n2': len(v2),
                't_stat': t_stat,
                'p_value': p,
                'significance': sig
            })

    else:
        # caso não tenha fator_col, faz t-test direto entre os grupos
        groups = data[group_col].unique()
        if len(groups) != 2:
            raise ValueError("Para t-test sem fator_col, deve haver exatamente 2 grupos.")
        g1, g2 = groups
        v1 = data[data[group_col] == g1][response_col]
        v2 = data[data[group_col] == g2][response_col]
        t_stat, p = ttest_ind(v1, v2, equal_var=False)
        # monta notação de significância
        if p < 0.001:
            sig = '***'
        elif p < 0.01:
            sig = '**'
        elif p < 0.05:
            sig = '*'
        else:
            sig = 'ns'
        results.append({
            group_col: 'Total',
            'group1': g1,
            'group2': g2,
            'n1': len(v1),
            'n2': len(v2),
            't_stat': t_stat,
            'p_value': p,
            'significance': sig
        })
    return pd.DataFrame(results)