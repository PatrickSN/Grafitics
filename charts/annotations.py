import numpy as np
from stats.helpers import stars_from_p, assign_letters_from_pairwise

def _draw_bracket(ax, x1, x2, y, h, text, fontsize):
    ax.plot([x1,x1],[y-h,y], linewidth=1.2, color='black')
    ax.plot([x2,x2],[y-h,y], linewidth=1.2, color='black')
    ax.plot([x1,x2],[y,y], linewidth=1.2, color='black')
    if text:
        ax.text((x1+x2)/2.0, y + (h*0.2), text, ha='center', va='bottom', fontsize=fontsize, fontweight='bold')

def annotate_significance(
    ax,
    labels,
    means_arr,
    sem_arr,
    pmap_pairwise,
    pmap_vs_control,
    control=None,
    alpha=0.05,
    bracket_scope='control',
    fontsize=10,
    all_pvalue=False
):
    """
    Adiciona brackets entre pares significativos ou controle vs others.
    labels: list of group labels (in order)
    means_arr, sem_arr: numpy arrays same length as labels
    pmap_pairwise: dict[frozenset({g1,g2})] -> p
    pmap_vs_control: dict[str(group)] -> p  (control is key used separately)
    bracket_scope: 'control' or 'all'
    """
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin if ymax - ymin > 0 else max(np.abs(means_arr.max()),1.0)
    base_offset = yrange * 0.05
    x_positions = np.arange(len(labels))
    label_to_x = {str(l): x_positions[i] for i,l in enumerate(labels)}
    bracket_levels = []


    def get_next_y(base_y):
        min_gap = base_offset * 0.9
        y = base_y
        while any(abs(y - used) < min_gap for used in bracket_levels):
            y += min_gap
        bracket_levels.append(y)
        return y

    comps = []
    method_all = (bracket_scope == 'all')
    # all pairwise
    if method_all:
        for key,p in pmap_pairwise.items():
            if p is None: continue
            try:
                if float(p) < alpha:
                    a,b = list(key)
                    if str(a) in label_to_x and str(b) in label_to_x:
                        comps.append((label_to_x[str(a)], label_to_x[str(b)], float(p)))
            except:
                continue
    else:
        # control comparisons: for Dunnett-like tests prefer showing stars above
        # each bar rather than drawing brackets between control and others.
        # We'll skip adding bracket comps here and rely on the stars block
        # below which plots significance symbols directly above the affected bars.
        if control is not None:
            # no-op here (stars will be drawn later using pmap_vs_control)
            pass
        # (no further fallback here)
        else:
            # fallback: draw any significant pair from pairwise map
            for key,p in pmap_pairwise.items():
                if p is None: continue
                try:
                    if float(p) < alpha:
                        a,b = list(key)
                        if str(a) in label_to_x and str(b) in label_to_x:
                            comps.append((label_to_x[str(a)], label_to_x[str(b)], float(p)))
                except:
                    continue
    # normalize and sort to reduce overlaps (shorter spans first)
    comps_norm = []
    for a,b,p in comps:
        x1 = min(a,b); x2 = max(a,b)
        comps_norm.append((x1,x2,p))
    comps_norm.sort(key=lambda t: (t[1]-t[0], t[0]))

    for x1_idx, x2_idx, pval in comps_norm:
        top1 = means_arr[int(x1_idx)] + sem_arr[int(x1_idx)]
        top2 = means_arr[int(x2_idx)] + sem_arr[int(x2_idx)]
        base_y = max(top1, top2) + base_offset
        y = get_next_y(base_y)
        h = yrange * 0.03
        _draw_bracket(ax, x1_idx, x2_idx, y, h, stars_from_p(p=pval, alpha=alpha, all_pvalue=all_pvalue), fontsize=fontsize)

    if bracket_levels:
        highest = max(bracket_levels)
        if highest + base_offset*0.8 > ymax:
            ax.set_ylim(ymin, highest + base_offset*1.5)

    # Additionally, for control comparisons (e.g., Dunnett), show stars directly above each bar
    try:
        if pmap_vs_control:
            for i, lab in enumerate(labels):
                key = str(lab)
                p = pmap_vs_control.get(key, None)
                if p is None:
                    # maybe pairwise contains the frozenset
                    kset = frozenset({str(control), str(lab)}) if control is not None else None
                    if kset is not None:
                        p = pmap_pairwise.get(kset, None)
                s = stars_from_p(p)
                if s:
                    # stars slightly higher than letters to increase visibility
                    y = means_arr[i] + sem_arr[i] + (max(means_arr) - min(means_arr)) * 0.08
                    ax.text(i, y, s, ha='center', va='bottom', fontsize=fontsize, fontweight='bold')
            return
    except Exception:
        pass

    # Tukey letters: if we have pairwise pmap, create letters and plot above bars
    try:
        # ensure pairwise keys are stringified in helper
        letters = assign_letters_from_pairwise([str(l) for l in labels], pmap_pairwise, alpha)
        for i, lab in enumerate(labels):
            txt = letters.get(str(lab), '')
            if txt:
                # letters slightly above the error bar
                y = means_arr[i] + sem_arr[i] + (max(means_arr) - min(means_arr)) * 0.05
                ax.text(i, y, txt, ha='center', va='bottom', fontsize=fontsize, fontweight='bold')
    except Exception:
        pass