"""Affiche A4 du code QR de la page de notation.

Mise en page sobre : une grille alignée à gauche, un titre fort, le code QR
en grand, deux couleurs (le bleu et l'or du logo), aucun ornement.

Lit print/qr-code.png et produit print/affiche-qr.pdf.

    python print/affiche.py
"""
import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = Path("C:/Windows/Fonts")
W, H = A4
M = 54                          # marge, et unité de la grille

NAVY = HexColor("#002470")      # bleu du logo
GOLD = HexColor("#C27C31")      # or du logo
INK = HexColor("#14181F")
MUTED = HexColor("#6A6F7A")

URL_LABEL = "nedili.space-visuals.online"


def fonts():
    pdfmetrics.registerFont(TTFont("UI", str(FONTS / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("UI-Semi", str(FONTS / "seguisb.ttf")))
    pdfmetrics.registerFont(TTFont("UI-Bold", str(FONTS / "segoeuib.ttf")))


def png(img):
    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return ImageReader(buf)


def logo():
    src = Image.open(ROOT / "public/img/logo.webp").convert("RGBA")
    bg = Image.new("RGBA", src.size, "white")
    bg.alpha_composite(src)
    ink = ImageOps.invert(bg.convert("L")).point(lambda v: 255 if v > 24 else 0)
    return png(bg.convert("RGB").crop(ink.getbbox()))


def qr():
    """Code QR agrandi au plus proche voisin : des modules nets à l'impression."""
    img = Image.open(HERE / "qr-code.png").convert("RGBA")
    bg = Image.new("RGBA", img.size, "white")
    bg.alpha_composite(img)
    return png(bg.convert("L").resize((img.width * 4, img.height * 4), Image.NEAREST))


def text(c, x, y, s, font, size, color, tracking=0.0):
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(tracking)
    t.textOut(s)
    c.saveState()             # l'espacement ne doit pas déborder sur les textes suivants
    c.drawText(t)
    c.restoreState()


def lines(c, x, y, rows, font, size, color, leading):
    for i, row in enumerate(rows):
        text(c, x, y - i * leading, row, font, size, color)


def build(out):
    fonts()
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle("Affiche dégustation NEDILI")
    c.setAuthor("NEDILI")

    # Logo, en haut à gauche
    img = logo()
    iw, ih = img.getSize()
    lw = 84
    lh = lw * ih / iw
    c.drawImage(img, M, H - M - lh, lw, lh)

    # Titre : deux mots, serrés
    size = 92
    y = H - M - lh - 118
    text(c, M - 4, y, "Goûtez.", "UI-Bold", size, NAVY, -3.5)
    text(c, M - 4, y - size * 0.92, "Notez.", "UI-Bold", size, GOLD, -3.5)

    y -= size * 0.92 + 46
    lines(c, M, y, ["Scannez le code, choisissez le produit goûté", "et donnez votre note. Une minute suffit."],
          "UI", 14, INK, 20)

    # Code QR en grand, aligné sur la marge
    q = 236
    qy = y - 48 - q
    c.drawImage(qr(), M, qy, q, q)

    # Légende à droite du code, calée sur son bas
    cx = M + q + 30
    lines(c, cx, qy + 52, ["Ouvrez l'appareil photo", "de votre téléphone et", "visez le code."],
          "UI", 10.5, MUTED, 15)

    # Pied : un filet, puis deux colonnes
    fy = M + 34
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.line(M, fy + 22, W - M, fy + 22)
    text(c, M, fy, "Confitures, sauces, sirops", "UI-Semi", 11, INK)
    text(c, M, fy - 16, "Pas de téléphone ? Demandez une fiche papier.", "UI", 9.5, MUTED)
    c.setFont("UI-Semi", 11)
    c.setFillColor(NAVY)
    c.drawRightString(W - M, fy, URL_LABEL)

    c.save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "affiche-qr.pdf"))
    args = ap.parse_args()
    build(Path(args.out))
    print("PDF créé :", args.out)
