from tkinter import filedialog, messagebox


def save_chart(fig, figsize_inches=None, dpi_override=None):
    """Salva a figura mantendo o tamanho em polegadas definido em fig.get_size_inches().

    Para formatos raster (ex.: TIFF) o tamanho em pixels será figsize * fig.dpi.
    Usamos o DPI atualmente associado à figura para preservar o tamanho esperado.
    """
    if fig is None:
        messagebox.showinfo("Attention", "Generate a graph first.")
        return
    fpath = filedialog.asksaveasfilename(defaultextension=".svg",
                                         filetypes=[("SVG", "*.svg"), ("TIFF", "*.tiff")])
    if not fpath:
        return

    try:
        # Se o usuário forneceu figsize_inches, força o tamanho da figura em polegadas
        if figsize_inches is not None:
            try:
                # figsize_inches pode ser (w,h) em inteiros
                fig.set_size_inches(float(figsize_inches[0]), float(figsize_inches[1]), forward=True)
            except Exception:
                # ignorar falha e prosseguir
                pass

        # Determina o dpi para salvar imagens raster. Prioriza dpi_override > fig.get_dpi()
        try:
            fig_dpi = float(fig.get_dpi())
        except Exception:
            fig_dpi = None

        dpi_to_use = None
        if dpi_override is not None:
            try:
                dpi_to_use = float(dpi_override)
            except Exception:
                dpi_to_use = None
        elif fig_dpi is not None:
            dpi_to_use = fig_dpi

        save_kwargs = {}
        if dpi_to_use is not None:
            save_kwargs['dpi'] = int(dpi_to_use)

        # Salva a figura; para SVG o dpi não altera o vetor, para TIFF controla a resolução
        fig.savefig(fpath, **save_kwargs)
        messagebox.showinfo("Saved", f"Figure saved in {fpath}")
    except Exception as e:
        messagebox.showerror("Error when saving", str(e))
