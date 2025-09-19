import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from export.save_fig import save_chart


class PlotTab(ttk.Frame):
    """A reusable tab for previewing matplotlib figures inside the main GUI.

    Usage:
        from ui.plot_tab import PlotTab
        self.plot_tab = PlotTab(parent_notebook)
        notebook.add(self.plot_tab, text='Preview')

    Then, after you create a matplotlib.figure.Figure `fig`, call:
        self.plot_tab.update_figure(fig)

    The tab provides:
    - embedded canvas + matplotlib navigation toolbar
    - buttons to save the current figure (delegates to filedialog)
    - controls to toggle legend deduplication and automatic placement
    - a status label
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        if kwargs.get('fig') is not None:
            self.fig = kwargs.get('fig')
        else:
            self.fig = None
        self.canvas_plot = None
        self.dpi = 300
        self.figsize = (8, 8)  # default figsize in inches

        # Top controls
        ctrl = ttk.Frame(self)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        ttk.Button(ctrl, text="Save image", command=self.save_image).pack(side=tk.LEFT)

        self.best_loc_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Auto legend loc (""best"")", variable=self.best_loc_var).pack(side=tk.LEFT, padx=6)

        ttk.Button(ctrl, text="Refresh", command=self._refresh).pack(side=tk.LEFT, padx=6)

        # status
        self.status = ttk.Label(self, text="No figure loaded.")
        self.status.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=4)

        # canvas container
        self.canvas_container = ttk.Frame(self)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

    def set_figure(self, fig, dpi, figsize):
        self.fig = fig
        self.dpi = dpi
        self.figsize = figsize
        self.update_figure()

    def save_image(self):
        save_chart(fig=self.fig, figsize_inches=self.figsize, dpi_override=self.dpi)

    def update_figure(self):
        if self.fig is None:
            self.status.config(text="No figure loaded.")
            return

        # Ajusta o tamanho do canvas para o tamanho da figura
        w_in, h_in = self.figsize
        dpi = self.dpi
        width_px, height_px = int(w_in * dpi), int(h_in * dpi)

        if self.canvas_plot:
            self.canvas_plot.get_tk_widget().destroy()
            self.canvas_plot = None

        # recria canvas respeitando figsize/dpi
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.canvas_container)
        widget = self.canvas_plot.get_tk_widget()
        widget.config(width=width_px, height=height_px)  # trava no tamanho definido
        widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas_plot.draw()
        self.status.config(
            text=f"Figure loaded ({w_in:.1f}×{h_in:.1f} in, {dpi} dpi → {width_px}×{height_px}px)."
        )

    def _refresh(self):
        """Re-run the legend dedupe/loc logic on the currently loaded figure and redraw."""
        if self.fig is None:
            self.status.config(text="No figure to refresh.")
            return
        if self.best_loc_var.get():
            for ax in self.fig.get_axes():
                ax.legend(loc='best', frameon=False)
        self.canvas_plot.draw()
        self.status.config(text="Refreshed figure.")



# End of file
