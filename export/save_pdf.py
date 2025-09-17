from tkinter import filedialog, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

def export_report_pdf(app):
    if app.last_summary_df is None:
        messagebox.showinfo("Atenção","Execute a análise antes de exportar.")
        return
    fpath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                         filetypes=[("PDF","*.pdf")])
    if not fpath: return

    img_buf = io.BytesIO()
    if app.fig is not None:
        app.fig.savefig(img_buf, format="png", dpi=300, bbox_inches="tight")
    img_buf.seek(0)
    img = ImageReader(img_buf)

    c = canvas.Canvas(fpath, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold",14)
    c.drawString(40, height-40, "Relatório estatístico")
    c.drawImage(img, 40, height-300, width=500, height=250)
    c.showPage()
    c.save()

    messagebox.showinfo("Exportado", f"PDF salvo em {fpath}")
