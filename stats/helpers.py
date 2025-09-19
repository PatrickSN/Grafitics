import numpy as np
import re

# networkx is optional; if available we use clique-based assignment for Tukey letters
try:
    import networkx as nx
    _HAS_NETWORKX = True
except Exception:
    _HAS_NETWORKX = False

def find_pvalue_column(df):
    """Procura colunas com 'p' ou 'padj' no nome. Retorna primeira candidata ou None."""
    if df is None: return None
    for c in df.columns:
        for k in ('p', 'p_value', 'pvalue','p.value','p-adj','p.adj','padj','p_adj', 'pval'):
            if c.lower() == k:
                return k 
            
    candidates = [c for c in df.columns if any(k in c.lower() for k in ('p','p_value','pvalue','p.value','p-adj','p.adj','padj','p_adj', 'pval'))]
    # prefer explicit p_adj etc
    for pref in candidates:
        for c in df.columns:
            if pref in c.lower():
                return c
    return candidates[0] if candidates else None

def parse_pair_name_for_group(comp_str, control_label=None):
    """Tenta extrair (g1,g2) de strings comuns: 'A-B', 'A vs B', 'A vs. B', 'A - B'."""
    s = str(comp_str)

    m = re.match(r"^(.*-\d+)-(.*)$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    for sep in [' vs ', ' VS ', ' Vs ', ' - ', '-', ' vs. ', ' x ', '/']:
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()]
            if len(parts)>=2:
                if ' : ' in parts[0]:
                    part = parts[0].split(' : ')
                    return  part[0], part[1],parts[1]
                return parts[0], parts[1]
    # fallback: if control_label is present try to isolate other
    if control_label and control_label in s:
        other = s.replace(control_label, '').replace('-', '').replace('vs', '').replace('VS', '').strip()
        if other:
            first = other.split()[0]
            return control_label, first
    return s, ''

def stars_from_p(p, alpha=0.05, all_pvalue=False):
    if p is None or (isinstance(p,float) and np.isnan(p)): return ''
    try:
        pval = float(p)
    except:
        return ''
    if all_pvalue:
        if pval <= 0.001: return '***'
        if pval <= 0.01: return '**'
        if pval <= 0.05: return '*'
        if pval <= 0.1: return '.'
    elif not all_pvalue:
        if pval <= alpha: return "*"
    return ''

def assign_letters_from_pairwise(groups, pairwise_p, alpha):
    """
    Greedy algorithm to assign letters (a,b,c...) so that groups that *do not*
    differ significantly (p >= alpha) share a letter.
    pairwise_p: dict keyed by frozenset({g1,g2}) -> p-value
    """
    # normalize groups to strings to ensure consistent key lookup
    groups = [str(g) for g in groups]

    # If networkx is available we build a graph where an edge means
    # 'no significant difference' (p >= alpha). Then we find maximal
    # cliques and assign a letter to each clique (groups may belong to
    # multiple cliques, producing labels like 'ab'). This follows the
    # example you provided.
    if _HAS_NETWORKX:
        G = nx.Graph()
        G.add_nodes_from(groups)
        # iterate pairs
        n = len(groups)
        for i in range(n):
            for j in range(i + 1, n):
                g1, g2 = groups[i], groups[j]
                key = frozenset({str(g1), str(g2)})
                p = pairwise_p.get(key, 1.0)
                try:
                    if np.isnan(p):
                        p = 1.0
                except Exception:
                    pass
                # add edge when NOT significantly different
                if p >= alpha:
                    G.add_edge(g1, g2)

        # find maximal cliques (each clique can share a letter)
        cliques = list(nx.find_cliques(G))

        out = {g: '' for g in groups}
        letra_ord = (chr(ord('a') + i) for i in range(26))
        for clique in cliques:
            try:
                letra = next(letra_ord)
            except StopIteration:
                # Ran out of single letters; continue with double letters aa, ab... (simple fallback)
                # This is unlikely for typical experiments.
                letra = 'z'
            for g in clique:
                out[str(g)] = out.get(str(g), '') + letra
        return out

    # Fallback: greedy overlapping algorithm (no networkx available)
    letters = []  # list of sets (containing string group names)

    for g in groups:
        added_to_any = False
        for s in letters:
            ok = True
            for m in s:
                key = frozenset({str(g), str(m)})
                p = pairwise_p.get(key, 1.0)
                try:
                    if np.isnan(p):
                        p = 1.0
                except Exception:
                    pass
                if p < alpha:
                    ok = False
                    break
            if ok:
                s.add(g)
                added_to_any = True
        if not added_to_any:
            letters.append(set([g]))

    out = {}
    for i, s in enumerate(letters):
        lab = chr(ord('a') + i)
        for g in s:
            out[str(g)] = out.get(str(g), '') + lab

    return out
