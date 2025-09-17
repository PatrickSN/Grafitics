import pandas as pd
from tkinter import filedialog, messagebox
from pandas import ExcelWriter

def export_report_xlsx(app):
    if app.last_summary_df is None:
        messagebox.showinfo("Atenção","Execute a análise antes de exportar.")
        return
    fpath = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                         filetypes=[("Excel","*.xlsx")])
    if not fpath: return
    with ExcelWriter(fpath) as writer:
        app.df.to_excel(writer, sheet_name="raw_data", index=False)
        app.last_summary_df.to_excel(writer, sheet_name="summary", index=False)
        if app.last_stats_df is not None:
            app.last_stats_df.to_excel(writer, sheet_name="stats", index=False)
    messagebox.showinfo("Exportado", f"Relatório salvo em {fpath}")
