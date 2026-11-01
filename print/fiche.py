"""Fiche de dégustation NEDILI à imprimer (A4, noir et blanc).

Lit public/products.json et produit print/fiche-degustation.pdf.

    python print/fiche.py
"""
import argparse
import json
from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path("C:/Windows/Fonts")
W, H = A4
M = 30                      # marge de page
INK = 0                     # noir
MUTED = 0.38                # gris des textes secondaires
LINE = 0.55                 # gris des traits

LEVELS = ["Bof", "Moyen", "Bon", "Très bon", "Top"]
BUY = ["Oui", "Peut-être", "Non"]

# Colonnes du tableau
X_NUM = M
X_NAME = M + 30
X_FACES = 258               # début des 5 cases de note
FACE_W = 33
X_BUY = X_FACES + 5 * FACE_W + 14
BUY_W = 42
BOX = 13                    # côté d'une case à cocher
ROW_MIN, ROW_MAX = 46, 72   # hauteur d'une ligne produit
ROW_PAGED = 58              # hauteur d'une ligne en recto verso, plus aérée
CONTACT_H = 68


def fonts():
    pdfmetrics.registerFont(TTFont("UI", str(FONTS / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("UI-Semi", str(FONTS / "seguisb.ttf")))
    pdfmetrics.registerFont(TTFont("UI-Bold", str(FONTS / "segoeuib.ttf")))
    pdfmetrics.registerFont(TTFont("UI-Light", str(FONTS / "segoeuil.ttf")))


def logo():
    """Logo recadré sur son contenu et passé en niveaux de gris."""
    src = Image.open(ROOT / "public/img/logo.webp").convert("RGBA")
    img = Image.new("RGBA", src.size, "white")
    img.alpha_composite(src)
    img = img.convert("L")
    bbox = Image.eval(img, lambda v: 255 - v).point(lambda v: 255 if v > 24 else 0).getbbox()
    buf = BytesIO()
    img.crop(bbox).save(buf, "PNG")
    buf.seek(0)
    return ImageReader(buf)


def face(c, cx, cy, r, level):
    """Petit visage au trait, de 0 (Bof) à 4 (Top)."""
    c.setLineWidth(0.9)
    c.circle(cx, cy, r)
    ey = cy + r * 0.25
    for dx in (-r * 0.36, r * 0.36):
        c.circle(cx + dx, ey, r * 0.1, stroke=0, fill=1)
    my = cy - r * 0.35
    half = r * 0.45
    p = c.beginPath()
    if level == 0:
        p.moveTo(cx - half, my - r * 0.12)
        p.curveTo(cx - half * 0.4, my + r * 0.2, cx + half * 0.4, my + r * 0.2, cx + half, my - r * 0.12)
        c.drawPath(p)
    elif level == 1:
        c.line(cx - half, my, cx + half, my)
    elif level == 2:
        p.moveTo(cx - half, my + r * 0.05)
        p.curveTo(cx - half * 0.4, my - r * 0.18, cx + half * 0.4, my - r * 0.18, cx + half, my + r * 0.05)
        c.drawPath(p)
    else:
        bottom = r * (0.3 if level == 3 else 0.42)
        p.moveTo(cx - half, my + r * 0.12)
        p.curveTo(cx - half * 0.5, my - bottom, cx + half * 0.5, my - bottom, cx + half, my + r * 0.12)
        p.close()
        c.drawPath(p, fill=level == 4, stroke=1)


def box(c, x, y, size=BOX):
    c.setLineWidth(0.9)
    c.roundRect(x, y, size, size, 2)


def dotted(c, x1, x2, y):
    c.saveState()
    c.setStrokeGray(LINE)
    c.setLineWidth(0.6)
    c.setDash(1, 2.2)
    c.line(x1, y, x2, y)
    c.restoreState()


def header(c):
    top = H - M
    img = logo()
    iw, ih = img.getSize()
    lw = 64
    lh = lw * ih / iw
    c.drawImage(img, M, top - lh, lw, lh, mask="auto")

    tx = W - M
    c.setFillGray(MUTED)
    c.setFont("UI-Semi", 8)
    c.drawRightString(tx, top - 12, "DÉGUSTATION · CONFITURES · TARTINADES · SAUCES · SIROPS")
    c.setFillGray(INK)
    c.setFont("UI-Bold", 22)
    c.drawRightString(tx, top - 38, "Votre avis compte")
    c.setFont("UI", 9.5)
    c.drawRightString(tx, top - 55, "Pour chaque produit goûté, cochez une case de note.")
    c.drawRightString(tx, top - 68, "Le reste est facultatif : quelques secondes suffisent.")

    return top - max(lh, 72) - 8


def table_head(c, y):
    """Légende des visages et des réponses d'achat, au-dessus du tableau."""
    c.setFillGray(INK)
    c.setStrokeGray(INK)
    c.setFont("UI-Semi", 8)
    c.drawString(X_NAME, y - 26, "Produit")
    for i, label in enumerate(LEVELS):
        cx = X_FACES + i * FACE_W + FACE_W / 2
        face(c, cx, y - 9, 8, i)
        c.setFont("UI", 7)
        c.drawCentredString(cx, y - 28, label)
    c.setFont("UI-Semi", 8)
    c.drawCentredString(X_BUY + 1.5 * BUY_W, y - 9, "L'achèteriez-vous ?")
    c.setFont("UI", 7)
    for i, label in enumerate(BUY):
        c.drawCentredString(X_BUY + i * BUY_W + BUY_W / 2, y - 28, label)
    y -= 36
    c.setLineWidth(1.2)
    c.line(M, y, W - M, y)
    return y


def category(c, y, cat):
    y -= 17
    c.setFillGray(INK)
    c.setFont("UI-Bold", 10.5)
    c.drawString(M, y, cat["label"].upper())
    tw = pdfmetrics.stringWidth(cat["label"].upper(), "UI-Bold", 10.5)
    c.setStrokeGray(LINE)
    c.setLineWidth(0.6)
    c.line(M + tw + 8, y + 3.5, W - M, y + 3.5)
    return y - 4


def product(c, y, num, item, tags, row):
    top = y
    # Numéro dans une pastille, comme sur le stand
    c.setFillGray(INK)
    c.circle(X_NUM + 10, top - 11, 10, stroke=0, fill=1)
    c.setFillGray(1)
    c.setFont("UI-Bold", 8.5)
    c.drawCentredString(X_NUM + 10, top - 14, f"{num:02d}")

    c.setFillGray(INK)
    c.setFont("UI-Semi", 10.5)
    c.drawString(X_NAME, top - 15, item["name"])

    c.setStrokeGray(INK)
    for i in range(5):
        box(c, X_FACES + i * FACE_W + (FACE_W - BOX) / 2, top - 20)
    for i in range(3):
        box(c, X_BUY + i * BUY_W + (BUY_W - BOX) / 2, top - 20)

    # Précisions à entourer
    ty = top - 30
    c.setFillGray(MUTED)
    c.setFont("UI", 7.5)
    c.drawString(X_NAME, ty, "Entourez :")
    x = X_NAME + 40
    c.setFillGray(INK)
    for t in tags:
        c.drawString(x, ty, t)
        x += pdfmetrics.stringWidth(t, "UI", 7.5) + 11

    cy = top - row + 4
    c.setFillGray(MUTED)
    c.drawString(X_NAME, cy, "Un mot :")
    dotted(c, X_NAME + 40, W - M, cy - 1)

    c.setStrokeGray(0.82)
    c.setLineWidth(0.5)
    c.line(X_NAME, top - row, W - M, top - row)
    return top - row


def contact(c, y):
    y -= 10
    pad = 12
    h = CONTACT_H
    c.setStrokeGray(INK)
    c.setLineWidth(0.9)
    c.roundRect(M, y - h, W - 2 * M, h, 8)
    x = M + pad
    c.setFillGray(INK)
    c.setFont("UI-Bold", 10.5)
    c.drawString(x, y - 18, "Restons en contact")
    c.setFillGray(MUTED)
    c.setFont("UI", 8)
    c.drawString(x + 100, y - 18, "Facultatif. Pour recevoir nos nouveautés et nos offres.")

    fy = y - 37
    mid = M + (W - 2 * M) * 0.38
    c.setFillGray(INK)
    c.setFont("UI", 8.5)
    c.drawString(x, fy, "Prénom")
    dotted(c, x + 36, mid - 14, fy - 1)
    c.drawString(mid, fy, "E-mail ou WhatsApp")
    dotted(c, mid + 84, W - M - pad, fy - 1)

    by = y - 57
    c.setStrokeGray(INK)
    box(c, x, by - 3, 12)
    c.setFont("UI", 8.5)
    c.drawString(x + 19, by, "J'accepte de recevoir les offres et nouveautés NEDILI")
    return y - h


def footer(c, last=True):
    if not last:
        c.setFillGray(MUTED)
        c.setFont("UI-Semi", 9)
        c.drawRightString(W - M, M, "Suite au verso")
        return
    c.setFillGray(INK)
    c.setFont("UI-Semi", 9.5)
    c.drawCentredString(W / 2, M + 12, "Merci pour votre participation !")
    c.setFillGray(MUTED)
    c.setFont("UI", 7.5)
    c.drawCentredString(W / 2, M, "Remettez cette fiche à l'équipe NEDILI sur le stand.")


def build(out):
    fonts()
    data = json.loads((ROOT / "public/products.json").read_text(encoding="utf-8"))
    tags = data.get("tags", {})

    # Premier passage à blanc pour mesurer la place libre, puis on la répartit
    # entre les lignes produit (plus de place pour écrire, sans trou en bas).
    # Si tout ne tient pas sur une page, la fiche passe en recto verso.
    spare = layout(canvas.Canvas(BytesIO(), pagesize=A4), data, tags, ROW_MIN) - (M + 40)
    paged = spare < 0
    row = ROW_PAGED if paged else min(ROW_MAX, ROW_MIN + spare / len(data["items"]))

    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle("Fiche de dégustation NEDILI")
    c.setAuthor("NEDILI")
    layout(c, data, tags, row, paged)
    footer(c)
    c.save()


def layout(c, data, tags, row, paged=False):
    bottom = M + 40

    def new_page():
        footer(c, last=False)
        c.showPage()
        return table_head(c, H - M)

    y = header(c)
    y = table_head(c, y)
    num = 0
    for cat in data["categories"]:
        # Une catégorie reste d'un seul tenant quand elle tient en entier sur la page suivante
        count = sum(1 for item in data["items"] if item["category"] == cat["id"])
        if paged and y - 21 - count * row < bottom:
            y = new_page()
        y = category(c, y, cat)
        for item in data["items"]:
            if item["category"] != cat["id"]:
                continue
            if paged and y - row < bottom:
                y = category(c, new_page(), {"label": cat["label"] + " (suite)"})
            num += 1
            y = product(c, y, num, item, tags.get(cat["id"], []), row)
    if paged and y - 10 - CONTACT_H < bottom:
        y = H - M
    return contact(c, y)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "fiche-degustation.pdf"))
    args = ap.parse_args()
    build(Path(args.out))
    print("PDF créé :", args.out)
