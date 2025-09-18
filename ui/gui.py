import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import pandas as pd
import threading, os, traceback

from stats.summary import summary_by_group
from stats.tests import tukey_test_r, dunnett_test_r, pairwise_ttests_vs_control_r
from stats.helpers import find_pvalue_column, parse_pair_name_for_group
from charts.plotter import generate_barplot
from export.save_fig import save_chart
from export.save_excel import export_report_xlsx
from export.save_pdf import export_report_pdf

EXAMPLE_PATH = os.path.join("data", "exemplos.xlsx")


class StatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Grafitics-v3")
        self.state('zoomed')
        self.minsize(1920,1080)
        self._build_ui()
        # ========= estilo para o botão ========= 
        self.style = ttk.Style()

        # data / state
        self.df = None
        self.fig = None
        self.canvas_plot = None
        self.last_stats_df = None
        self.last_summary_df = None
        self.last_test_method = None
        # maps for annotations
        self.pmap_pairwise = {}   # frozenset({g1,g2}) -> p
        self.pmap_vs_control = {} # other_group -> p
        self.control_selected = None

    def _build_ui(self):
        top = ttk.Frame(self, padding=6); top.pack(side=tk.TOP, fill=tk.X)
        left = ttk.Frame(top); left.pack(side=tk.LEFT, padx=6)
        right = ttk.Frame(top); right.pack(side=tk.RIGHT, padx=6)

        # file controls
        ttk.Button(left, text="Load file", command=self.load_file).grid(row=0, column=0, sticky="w")
        ttk.Button(left, text="Load example", command=self.load_example).grid(row=0, column=1, sticky="w")

        ttk.Label(left, text="sheet:").grid(row=1, column=0, sticky="w")
        self.sheet_cb = ttk.Combobox(left, values=[], state='readonly'); self.sheet_cb.grid(row=1,column=1)
        self.sheet_cb.bind("<<ComboboxSelected>>", self.on_sheet_select)

        ttk.Label(left, text="Group col:").grid(row=2, column=0, sticky="w")
        self.group_col_cb = ttk.Combobox(left, values=[], state='readonly'); self.group_col_cb.grid(row=2, column=1)
        ttk.Label(left, text="Value col:").grid(row=3, column=0, sticky="w")
        self.value_col_cb = ttk.Combobox(left, values=[], state='readonly'); self.value_col_cb.grid(row=3, column=1)

        ttk.Label(left, text="p value alpha:").grid(row=4, column=0, sticky="w")
        self.pvar = tk.DoubleVar(value=0.05)
        ttk.Radiobutton(left, text="0.10", variable=self.pvar, value=0.10).grid(row=4,column=1,sticky='w')
        ttk.Radiobutton(left, text="0.05", variable=self.pvar, value=0.05).grid(row=4,column=2,sticky='w')
        ttk.Radiobutton(left, text="0.01", variable=self.pvar, value=0.01).grid(row=4,column=3,sticky='w')
        ttk.Radiobutton(left, text="0.001", variable=self.pvar, value=0.001).grid(row=4,column=4,sticky='w')

        ttk.Label(left, text="Test:").grid(row=5,column=0, sticky='w')
        self.test_var = tk.StringVar(value="Tukey")
        ttk.Radiobutton(left, text="Tukey", variable=self.test_var, value="Tukey").grid(row=5,column=1, sticky='w')
        ttk.Radiobutton(left, text="Dunnett", variable=self.test_var, value="Dunnett").grid(row=5,column=2, sticky='w')
        ttk.Radiobutton(left, text="T-test", variable=self.test_var, value="T-test").grid(row=5,column=3, sticky='w')

        ttk.Label(left, text="Control (for Dunnett/T-test):").grid(row=6, column=0, sticky='w')
        self.control_cb = ttk.Combobox(left, values=[], state='readonly'); self.control_cb.grid(row=6,column=1)

        ttk.Button(left, text="Compute statistics", command=self.compute_stats_thread).grid(row=7,column=0, columnspan=2, pady=6)

        # t-test mode
        ttk.Label(left, text="T-test mode:").grid(row=8,column=0, sticky='w')
        self.ttest_mode = tk.StringVar(value='auto')
        ttk.Radiobutton(left, text="Auto", variable=self.ttest_mode, value='auto').grid(row=8,column=1, sticky='w')
        ttk.Radiobutton(left, text="Two-by-two", variable=self.ttest_mode, value='chipboard').grid(row=8,column=2, sticky='w')
        ttk.Radiobutton(left, text="Classic", variable=self.ttest_mode, value='classic').grid(row=8,column=3, sticky='w')
        ttk.Radiobutton(left, text="Control vs others", variable=self.ttest_mode, value='control').grid(row=8,column=4, sticky='w')

        self.status_lbl = ttk.Label(left, text="Select file", relief='sunken', anchor='w'); self.status_lbl.grid(row=9,column=0,columnspan=4, sticky='we', pady=(6,0))

        # ========= right panel (plot options) =========
        ttk.Label(right, text="Title:").grid(row=0,column=0, sticky='w'); self.title_ent = ttk.Entry(right, width=30); self.title_ent.grid(row=0,column=1)
        ttk.Label(right, text="X label:").grid(row=1,column=0, sticky='w'); self.xlabel_ent = ttk.Entry(right, width=30); self.xlabel_ent.grid(row=1,column=1)
        ttk.Label(right, text="Y label:").grid(row=2,column=0, sticky='w'); self.ylabel_ent = ttk.Entry(right, width=30); self.ylabel_ent.grid(row=2,column=1)
        self.bar_color="#0000ff"
        ttk.Label(right, text="Bar color:").grid(row=3,column=0, sticky='w'); self.color_btn = tk.Button(right, text="Escolher cor",command=self.pick_color, bg=self.bar_color, fg="white", activebackground=self.bar_color )
        self.color_btn.grid(row=3,column=1)

        # ========= BOOLEANS =========
        # ========= LINHA 4 =========
        self.legend_var = tk.BooleanVar(value=False); ttk.Checkbutton(right, text="Caption", variable=self.legend_var).grid(row=4,column=0, sticky='w')
        
        ttk.Label(right, text="Color Mode:").grid(row=4, column=1, sticky='e')
        self.color_mode_var = ttk.Combobox(right,values=["Unique", "Alternate"], state='readonly', textvariable="Unique")
        self.color_mode_var.grid(row=4, column=2, padx=10, pady=5, sticky="w")
        self.color_mode_var.set("Unique") 

        # ========= LINHA 5 =========
        self.brackets_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Show brackets", variable=self.brackets_var).grid(row=5,column=0, sticky='w')
        self.bracket_scope = tk.StringVar(value='control')
        ttk.Radiobutton(right, text="Control comparisons", variable=self.bracket_scope, value='control').grid(row=5,column=1, sticky='w')
        ttk.Radiobutton(right, text="All pairs", variable=self.bracket_scope, value='all').grid(row=5,column=2, sticky='w')

        # ========= LINHA 6 =========
        ttk.Label(right, text="Font size:").grid(row=6,column=0, sticky='w')
        self.font_spin = ttk.Spinbox(right, from_=6,to=30)
        self.font_spin.set(10)
        self.font_spin.grid(row=6,column=1)

        # ========= LINHA 7 =========
        ttk.Label(right, text="Image size (cm):").grid(row=7,column=0, sticky='w')
        size_frame = ttk.Frame(right)
        size_frame.grid(row=7,column=1)
        self.img_w = ttk.Spinbox(size_frame, from_=4,to=20,width=5)
        self.img_h = ttk.Spinbox(size_frame, from_=3,to=20,width=5)
        self.img_w.set(8)
        self.img_h.set(8)
        self.img_w.pack(side=tk.LEFT)
        ttk.Label(size_frame,text="x").pack(side=tk.LEFT)
        self.img_h.pack(side=tk.LEFT)

        # ========= DPI override ========= 
        ttk.Label(right, text="DPI:").grid(row=7, column=2, sticky='w')
        self.dpi_spin = ttk.Spinbox(right, from_=300, to=2400, increment=100, width=7)
        self.dpi_spin.set(600)
        self.dpi_spin.grid(row=7, column=3)

        # ========= LINHA 8 =========
        # ========= Buttons =========  
        ttk.Button(right, text="Chart generate", command=self.generate_chart_thread).grid(row=8,column=0, pady=6)
        ttk.Button(right, text="Save Chart", command=lambda: save_chart(
            self.fig,
            # convert cm -> inches (1 in = 2.54 cm)
            figsize_inches=(float(self.img_w.get())/2.54, float(self.img_h.get())/2.54),
            dpi_override=(int(self.dpi_spin.get()) if hasattr(self, 'dpi_spin') and self.dpi_spin.get() else None)
        )).grid(row=8,column=1)
        
        # ========= LINHA 9 =========
        ttk.Button(right, text="Export report (.xlsx)", command=lambda: export_report_xlsx(self)).grid(row=9,column=0)
        ttk.Button(right, text="Export report (.pdf)", command=lambda: export_report_pdf(self)).grid(row=9,column=1)

        # ========= bottom ========= 
        bottom = ttk.Frame(self, padding=6); bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        frame_table = ttk.LabelFrame(bottom, text="Data & preview"); frame_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree = ttk.Treeview(frame_table, columns=("a","b","c"), show='headings'); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_scroll = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=self.tree_scroll.set); self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        frame_stats = ttk.LabelFrame(bottom, text="Statistics & Plot"); frame_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.stats_text = tk.Text(frame_stats, width=60, height=12); self.stats_text.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        self.plot_frame = ttk.Frame(frame_stats); self.plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # ---------- file handling ----------
    def load_file(self):
        fpath = filedialog.askopenfilename(title="Open data file", filetypes=[("All data","*.csv *.xlsx *.xls"),("Excel","*.xlsx *.xls"),("CSV","*.csv")])
        if not fpath: return
        self._load_path(fpath)

    def load_example(self):
        if os.path.exists(EXAMPLE_PATH):
            self._load_path(EXAMPLE_PATH)
        else:
            messagebox.showwarning("Example not found", f"{EXAMPLE_PATH} not found.")

    def _load_path(self,fpath):
        _, ext = os.path.splitext(fpath.lower()); self.current_file = fpath
        try:
            if ext in (".xlsx",".xls"):
                xls = pd.ExcelFile(fpath); sheets = xls.sheet_names; self.sheet_cb['values'] = sheets; self.sheet_cb.set(sheets[0])
                self.current_sheet = sheets[0]; self.df = pd.read_excel(fpath, sheet_name=self.current_sheet)
            else:
                self.sheet_cb['values']=[]; self.current_sheet=None; self.df = pd.read_csv(fpath)
            self.status_lbl.config(text=f"Loaded: {os.path.basename(fpath)}"); self.populate_columns(); self.display_dataframe_preview()
        except Exception as e:
            messagebox.showerror("Load error", str(e)); self.status_lbl.config(text="Error loading file.")

    def on_sheet_select(self,event):
        sheet = self.sheet_cb.get()
        if not sheet: return
        self.current_sheet = sheet
        try:
            self.df = pd.read_excel(self.current_file, sheet_name=sheet); self.populate_columns(); self.display_dataframe_preview()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def populate_columns(self):
        if self.df is None: return
        cols = list(self.df.columns)
        self.group_col_cb['values'] = cols; self.value_col_cb['values'] = cols
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(self.df[c])]
        cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(self.df[c])]
        if numeric_cols: self.value_col_cb.set(numeric_cols[0])
        if cat_cols:
            self.group_col_cb.set(cat_cols[0])
            values = self.df[cat_cols[0]].dropna().unique().tolist()
            self.control_cb['values']=values
            if values: self.control_cb.set(values[0])

    def display_dataframe_preview(self):
        for c in self.tree['columns']: self.tree.heading(c, text="")
        for r in self.tree.get_children(): self.tree.delete(r)
        if self.df is None: return
        cols = list(self.df.columns)[:6]; self.tree['columns']=cols; self.tree['show']='headings'
        for c in cols: self.tree.heading(c,text=c); self.tree.column(c,width=120,anchor='w')
        for _,row in self.df.head(200).iterrows():
            vals=[self._format_val(row.get(c)) for c in cols]; self.tree.insert("",tk.END,values=vals)

    def _format_val(self,v):
        if pd.isna(v): return ""
        if isinstance(v,float): return f"{v:.6g}"
        return str(v)

    # ---------- compute stats ----------
    def compute_stats_thread(self):
        t = threading.Thread(target=self.compute_stats, daemon=True); t.start()

    def compute_stats(self):
        self.status_lbl.config(text="Calculating...")
        self.pmap_pairwise={}; self.pmap_vs_control={}; self.control_selected=None
        try:
            if self.df is None: raise RuntimeError("No files loaded.")
            group_col=self.group_col_cb.get(); value_col=self.value_col_cb.get(); control=self.control_cb.get(); self.control_selected=control
            if not group_col or not value_col: raise RuntimeError("Choose valid columns.")
            df = self.df[[group_col,value_col]].dropna().copy(); df[group_col]=df[group_col].astype(str); df[value_col]=pd.to_numeric(df[value_col],errors='coerce'); df=df.dropna(subset=[value_col])
            summ = summary_by_group(df, group_col, value_col)
            test=self.test_var.get(); alpha=float(self.pvar.get())
            result_text=[f"Summary by group:\n{summ.to_string(index=False)}\n\n"]

            # ---------------- Tukey (via R) ----------------
            if test=="Tukey":
                try:
                    tk_res = tukey_test_r(df, group_col, value_col, alpha=alpha, timeout=120)
                except Exception as e:
                    raise RuntimeError(f"Tukey (R) falhou: {e}")
                result_text.append("Tukey HSD results (R):\n"); result_text.append(tk_res.to_string(index=False))
                self.last_stats_df=tk_res; self.last_summary_df=summ; self.last_test_method="Tukey (R)"
                # fill pairwise pmap
                pcol = find_pvalue_column(tk_res)
                comp_col = 'comparison' if 'comparison' in tk_res.columns else tk_res.columns[0]
                for _,row in tk_res.iterrows():
                    comp = str(row.get(comp_col,''))
                    g1,g2 = parse_pair_name_for_group(comp)
                    p = row.get(pcol) if pcol in row.index else None
                    try: p = float(p)
                    except: p = None
                    if g1 and g2:
                        self.pmap_pairwise[frozenset({str(g1),str(g2)})] = p

            # ---------------- T-test ----------------
            elif test=="T-test":
                self.mode = self.ttest_mode.get()
                num_cols = len(self.df.columns)
                unique_groups = df[group_col].dropna().astype(str).unique().tolist()
                if self.mode=='auto':
                    if num_cols >= 3 and len(unique_groups) != 2: self.mode = 'chipboard'
                    elif len(unique_groups) == 2: self.mode = 'classic'
                    else: self.mode = 'control'

                if self.mode=='classic':
                    if len(unique_groups)!=2:
                        raise RuntimeError("Mode Classic t-test requires exactly 2 groups in the selected column.")
                    gA, gB = unique_groups[0], unique_groups[1]
                    # call R t.test pair (we have simpler pairwise wrapper)
                    tt = pairwise_ttests_vs_control_r(df, group_col, value_col, control_label=gA, alpha=alpha, p_adjust_method='holm', timeout=120)
                    # if we did control=gA it returns comparisons gA vs other(s). For classic that will be a single row.
                    result_text.append("T-test (R) results:\n"); result_text.append(tt.to_string(index=False))
                    self.last_stats_df=tt; self.last_summary_df=summ; self.last_test_method=f"T-test (R, mode={self.mode})"
                    # if one comparison, extract p and create pairwise map
                    for _,row in tt.iterrows():
                        comp=str(row.get('comparison',''))
                        g1,g2 = parse_pair_name_for_group(comp)
                        p = row.get('p_adj') if 'p_adj' in row.index else row.get('p_raw', None)
                        try: p=float(p)
                        except: p=None
                        if g1 and g2:
                            self.pmap_pairwise[frozenset({str(g1),str(g2)})] = p
                            # also fill vs_control map (if control present)
                            ctrl = g1 if 'vs' in comp and comp.startswith(str(g1)) else None
                            if ctrl:
                                other = g2
                                self.pmap_vs_control[str(other)] = p

                elif self.mode == 'chipboard':
                    if not len(unique_groups)!=2:
                        raise RuntimeError("Choose the column with the factors in group_col.")

                    cols = list(self.df.columns)
                    cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(self.df[c])]
                    if cat_cols:
                        for col in cat_cols:
                            groups = self.df[col].dropna().astype(str).unique().tolist()
                            try: 
                                if len(groups) == 2 and control in groups:
                                    fator_col = col
                                    df = self.df[[fator_col, group_col,value_col]].dropna().copy()
                                    break
                            except:
                                raise RuntimeError("Your table must contain at least one column with 2 unique treatments")

                    
                    tt = pairwise_ttests_vs_control_r(df, group_col, value_col, control_label=control, alpha=alpha, timeout=120, fator_col = fator_col)
                    result_text.append(f"T-test (R) {control} vs others:\n"); result_text.append(tt.to_string(index=False))

                else:
                    # control vs others (explicit)
                    if not control:
                        raise RuntimeError("Choose a control group for T-test (control mode).")
                    tt = pairwise_ttests_vs_control_r(df, group_col, value_col, control_label=control, alpha=alpha, p_adjust_method='holm', timeout=120)
                    result_text.append(f"T-test (R) {control} vs others:\n"); result_text.append(tt.to_string(index=False))
                    self.last_stats_df=tt; self.last_summary_df=summ; self.last_test_method="T-test (R, control-vs-others)"
                    pcol = find_pvalue_column(tt) or ('p_adj' if 'p_adj' in tt.columns else None)
                    for _,row in tt.iterrows():
                        comp=row.get('comparison',''); g1,g2=parse_pair_name_for_group(comp, control_label=control)
                        other = g2 if g1==control else (g1 if g2==control else None)
                        p = row.get('p_adj') if 'p_adj' in row.index else row.get(pcol)
                        try: p=float(p)
                        except: p=None
                        self.pmap_pairwise[frozenset({str(g1),str(g2)})] = p
                        if other: self.pmap_vs_control[str(other)] = p

            # ---------------- Dunnett (via R) ----------------
            elif test=="Dunnett":
                if not control:
                    raise RuntimeError("Choose a control group for Dunnett.")
                try:
                    dunnett_res = dunnett_test_r(df, group_col, value_col, control_label=control, alpha=alpha, timeout=180)
                except Exception as e:
                    # bubble-up error but provide helpful message
                    raise RuntimeError(f"Dunnett (R) falhou: {e}")
                result_text.append("Dunnett results (R):\n"); result_text.append(dunnett_res.to_string(index=False))
                self.last_stats_df = dunnett_res; self.last_summary_df = summ; self.last_test_method = "Dunnett (R)"
                pcol = find_pvalue_column(dunnett_res)
                comp_col = 'comparison' if 'comparison' in dunnett_res.columns else dunnett_res.columns[0]
                for _,row in dunnett_res.iterrows():
                    comp=str(row.get(comp_col,''))
                    g1,g2=parse_pair_name_for_group(comp, control_label=control)
                    other = g2 if g1==control else (g1 if g2==control else None)
                    p=None
                    if pcol and pcol in row.index:
                        try: p=float(row[pcol])
                        except: p=None
                    if g1 and g2:
                        self.pmap_pairwise[frozenset({str(g1),str(g2)})] = p
                    if other: self.pmap_vs_control[str(other)] = p

            else:
                result_text.append("Test not implemented.\n"); self.last_stats_df=None; self.last_summary_df=summ; self.last_test_method=None

            self.analysis_df = df; self.group_col_name = group_col; self.value_col_name = value_col; self.fator_col_name = fator_col
            self.stats_text.delete("1.0",tk.END); self.stats_text.insert(tk.END, "\n".join(result_text))
            self.status_lbl.config(text="Calculation completed.")
        except Exception as e:
            self.status_lbl.config(text=f"Erro: {e}")
            tb = traceback.format_exc()
            messagebox.showerror("Erro", f"{e}\n\n{tb}")

    # ---------- plotting ----------
    def pick_color(self):
        c = colorchooser.askcolor(title="Choose color", initialcolor=self.bar_color)[1]
        if c:
            self.bar_color = c
            # Atualiza a cor do botão
            self.color_btn.config(bg=self.bar_color, activebackground=self.bar_color)

    def generate_chart_thread(self):
        t=threading.Thread(target=self.generate_chart, daemon=True); t.start()

    def generate_chart(self):
        if not hasattr(self,'analysis_df') or self.analysis_df is None:
            messagebox.showinfo("Attention","Do the statistical analysis first."); return
        # call central plot generator (it will call annotations module using our p-maps)
        # convert image size from cm to inches for matplotlib (1 in = 2.54 cm)
        try:
            w_in = float(self.img_w.get()) / 2.54
            h_in = float(self.img_h.get()) / 2.54
        except Exception:
            w_in, h_in = 8/2.54, 8/2.54

        if self.mode == 'chipboard':
            pass
        else:
            self.fig = generate_barplot(
                df=self.analysis_df,
                group_col=self.group_col_name,
                value_col=self.value_col_name,
                bar_color=self.bar_color,
                pmap_pairwise=self.pmap_pairwise,
                pmap_vs_control=self.pmap_vs_control,
                control=self.control_selected,
                alpha=float(self.pvar.get()),
                show_legend=self.legend_var.get(),
                title=self.title_ent.get() or "",
                ylabel=self.ylabel_ent.get() or "",
                xlabel=self.xlabel_ent.get() or "",
                figsize=(w_in, h_in) if (w_in and h_in) else None,
                fontsize=int(self.font_spin.get()),
                bracket_scope=self.bracket_scope.get(),
                color_mode=self.color_mode_var.get()
            )
        # embed figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if self.canvas_plot:
            self.canvas_plot.get_tk_widget().destroy(); self.canvas_plot=None
        canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame); canvas.draw(); widget = canvas.get_tk_widget(); widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True); self.canvas_plot = canvas
