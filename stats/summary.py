import numpy as np

def summary_by_group(df, group_col, value_col):
    agg = df.groupby(group_col)[value_col].agg(['count','mean','std','median']).reset_index()
    agg['sem'] = agg['std'] / np.sqrt(agg['count'])
    return agg
