"""Affiche A4 en couleur autour du code QR de la page de notation.

Lit print/qr-code.png, public/products.json et les photos des produits,
et produit print/affiche-qr.pdf.

    python print/affiche.py
"""
import argparse
import json
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = Path("C:/Windows/Fonts")
W, H = A4
M = 34

NAVY = HexColor("#002470")       # bleu du logo
ORANGE = HexColor("#C27C31")     # or du logo
CREAM = HexColor("#FBF1E3")
TEXT = HexColor("#1C2440")
MUTED = HexColor("#5B6380")

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
    gray = ImageOps.invert(bg.convert("L")).point(lambda v: 255 if v > 24 else 0)
    return png(bg.convert("RGB").crop(gray.getbbox()))


def qr():
    """Code QR agrandi au plus proche voisin : des modules nets à l'impression."""
    img = Image.open(HERE / "qr-code.png").convert("RGBA")
    bg = Image.new("RGBA", img.size, "white")
    bg.alpha_composite(img)
    return png(bg.convert("L").resize((img.width * 4, img.height * 4), Image.NEAREST))


def round_photo(path, size=360):
    """Photo recadrée en carré au centre, découpée en disque."""
    img = ImageOps.fit(Image.open(path).convert("RGB"), (size, size), centering=(0.5, 0.45))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return png(out)


def centred(c, text, y, font, size, color):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(W / 2, y, text)


def spaced(c, text, y, font, size, color, tracking):
    """Texte centré avec espacement des lettres (titres en capitales)."""
    width = sum(pdfmetrics.stringWidth(ch, font, size) for ch in text) + tracking * (len(text) - 1)
    t = c.beginText(W / 2 - width / 2, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(tracking)
    t.textOut(text)
    c.saveState()             # l'espacement ne doit pas déborder sur les textes suivants
    c.drawText(t)
    c.restoreState()


def face(c, cx, cy, r, level):
    """Visage de 0 (Bof) à 4 (Top), en or plein avec traits bleus."""
    c.setFillColor(ORANGE)
    c.circle(cx, cy, r, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.setStrokeColor(NAVY)
    for dx in (-r * 0.36, r * 0.36):
        c.circle(cx + dx, cy + r * 0.22, r * 0.11, stroke=0, fill=1)
    c.setLineWidth(r * 0.13)
    c.setLineCap(1)
    my, half = cy - r * 0.32, r * 0.42
    p = c.beginPath()
    if level == 0:
        p.moveTo(cx - half, my - r * 0.1)
        p.curveTo(cx - half * 0.4, my + r * 0.18, cx + half * 0.4, my + r * 0.18, cx + half, my - r * 0.1)
    elif level == 1:
        p.moveTo(cx - half, my)
        p.lineTo(cx + half, my)
    else:
        depth = (0.16, 0.3, 0.42)[level - 2]
        p.moveTo(cx - half, my + r * 0.08)
        p.curveTo(cx - half * 0.4, my - r * depth, cx + half * 0.4, my - r * depth, cx + half, my + r * 0.08)
    c.drawPath(p, stroke=1, fill=0)


def build(out):
    fonts()
    data = json.loads((ROOT / "public/products.json").read_text(encoding="utf-8"))
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle("Affiche dégustation NEDILI")
    c.setAuthor("NEDILI")

    # Logo
    img = logo()
    iw, ih = img.getSize()
    lw = 104
    lh = lw * ih / iw
    top = H - M
    c.drawImage(img, W / 2 - lw / 2, top - lh, lw, lh)
    y = top - lh - 22

    # Accroche
    spaced(c, "DÉGUSTATION", y, "UI-Bold", 10, ORANGE, 3)
    y -= 36
    centred(c, "Vous avez goûté ?", y, "UI-Bold", 34, NAVY)
    y -= 38
    centred(c, "Donnez-nous votre avis !", y, "UI-Bold", 34, ORANGE)
    y -= 24
    centred(c, "Scannez le code avec votre téléphone, une minute suffit.", y, "UI", 12.5, MUTED)

    # Bloc du code QR sur fond crème
    band_top = y - 20
    band_h = 336
    c.setFillColor(CREAM)
    c.roundRect(M, band_top - band_h, W - 2 * M, band_h, 22, stroke=0, fill=1)

    card = 206
    cx0 = W / 2 - card / 2
    cy0 = band_top - 26 - card
    c.setFillColor(NAVY)
    c.roundRect(cx0 - 8, cy0 - 8, card + 16, card + 16, 22, stroke=0, fill=1)
    c.setFillColor(white)
    c.roundRect(cx0, cy0, card, card, 15, stroke=0, fill=1)
    q = card - 36                     # marge blanche autour du code, utile au scan
    c.drawImage(qr(), cx0 + 18, cy0 + 18, q, q)

    # Pastille « Scannez-moi » à cheval sur le bas de la carte
    label = "Scannez-moi"
    pw = pdfmetrics.stringWidth(label, "UI-Bold", 13) + 36
    ph = 28
    py = cy0 - 8 - ph / 2
    c.setFillColor(ORANGE)
    c.roundRect(W / 2 - pw / 2, py, pw, ph, ph / 2, stroke=0, fill=1)
    centred(c, label, py + 9, "UI-Bold", 13, white)

    # Échelle des visages, comme sur la page de notation
    labels = ["Bof", "Moyen", "Bon", "Très bon", "Top"]
    step = 62
    fy = py - 36
    for i, name in enumerate(labels):
        fx = W / 2 + (i - 2) * step
        face(c, fx, fy, 15, i)
        c.setFont("UI-Semi", 8.5)
        c.setFillColor(NAVY)
        c.drawCentredString(fx, fy - 26, name)

    y = band_top - band_h - 30

    # Trois étapes
    steps = [("1", "Scannez", "le code QR"), ("2", "Choisissez", "le produit goûté"), ("3", "Notez", "en un geste")]
    col = (W - 2 * M) / 3
    for i, (n, title, sub) in enumerate(steps):
        x = M + col * i + col / 2
        c.setFillColor(NAVY)
        c.circle(x - 46, y + 4, 13, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("UI-Bold", 13)
        c.drawCentredString(x - 46, y - 0.5, n)
        c.setFillColor(NAVY)
        c.setFont("UI-Bold", 13)
        c.drawString(x - 26, y + 3, title)
        c.setFillColor(MUTED)
        c.setFont("UI", 9.5)
        c.drawString(x - 26, y - 10, sub)

    # Produits en dégustation
    y -= 38
    spaced(c, "EN DÉGUSTATION AUJOURD'HUI", y, "UI-Bold", 9, ORANGE, 2.2)
    items = data["items"]
    d = 56
    gap = (W - 2 * M - len(items) * d) / (len(items) - 1)
    gap = min(gap, 16)
    total = len(items) * d + gap * (len(items) - 1)
    x = W / 2 - total / 2
    py = y - 18 - d
    for n, item in enumerate(items, 1):
        c.drawImage(round_photo(ROOT / "public" / item["image"]), x, py, d, d, mask="auto")
        c.setFillColor(NAVY)
        c.circle(x + d - 6, py + d - 6, 9, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("UI-Bold", 7.5)
        c.drawCentredString(x + d - 6, py + d - 8.6, f"{n:02d}")
        x += d + gap
    cats = " · ".join(cat["label"] for cat in data["categories"])
    centred(c, cats, py - 18, "UI-Semi", 10.5, NAVY)

    # Pied de page
    centred(c, "Pas de téléphone ? Demandez une fiche papier à l'équipe.", M + 22, "UI", 10, MUTED)
    centred(c, URL_LABEL, M + 6, "UI-Semi", 10, NAVY)

    c.save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "affiche-qr.pdf"))
    args = ap.parse_args()
    build(Path(args.out))
    print("PDF créé :", args.out)
