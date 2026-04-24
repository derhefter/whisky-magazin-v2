"""
Favicon-Generator für whisky.MAGAZIN
Erstellt WM-Monogramm in Brand-Farben:
  Background: #1C1108 (dunkles Whisky-Braun)
  Schrift:    #C8963E (Brand-Amber)
  Schrift:    Georgia Bold (ähnlich wie Fraunces)
"""

import io
import struct
from PIL import Image, ImageDraw, ImageFont

# ─── Brand-Farben ───────────────────────────────────────────────
AMBER       = (200, 150, 62)        # #C8963E
AMBER_LIGHT = (220, 175, 95)        # heller Akzent für Dot
DARK_BG     = (28, 17, 8)           # #1C1108 - dunkles Whisky-Braun
TRANSPARENT = (0, 0, 0, 0)

FONT_PATH   = "C:/Windows/Fonts/georgiab.ttf"  # Georgia Bold


def make_favicon_png(size: int) -> Image.Image:
    """Erstellt ein quadratisches Favicon-PNG der gegebenen Größe."""
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Abgerundetes Rechteck als Hintergrund
    radius = max(2, size // 6)
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=radius,
        fill=DARK_BG + (255,)
    )

    # ── Schriftgrößen je nach Canvas-Größe ──
    if size >= 96:
        font_w = ImageFont.truetype(FONT_PATH, int(size * 0.44))
        font_m = ImageFont.truetype(FONT_PATH, int(size * 0.38))
        dot_r  = max(2, size // 22)
        w_top  = int(size * 0.06)
        m_top  = int(size * 0.54)
        dot_cy = int(size * 0.515)
    elif size >= 48:
        font_w = ImageFont.truetype(FONT_PATH, int(size * 0.46))
        font_m = ImageFont.truetype(FONT_PATH, int(size * 0.40))
        dot_r  = max(2, size // 20)
        w_top  = int(size * 0.04)
        m_top  = int(size * 0.52)
        dot_cy = int(size * 0.505)
    elif size >= 32:
        font_w = ImageFont.truetype(FONT_PATH, int(size * 0.50))
        font_m = ImageFont.truetype(FONT_PATH, int(size * 0.42))
        dot_r  = max(1, size // 18)
        w_top  = int(size * 0.02)
        m_top  = int(size * 0.52)
        dot_cy = int(size * 0.495)
    else:
        # 16×16: nur "W", kein M (zu eng)
        font_w = ImageFont.truetype(FONT_PATH, int(size * 0.78))
        draw.text(
            (size // 2, size // 2),
            "W",
            fill=AMBER + (255,),
            font=font_w,
            anchor="mm"
        )
        # kleiner Dot unten rechts
        dot_r = max(1, size // 10)
        draw.ellipse(
            [size - dot_r * 3, size - dot_r * 3,
             size - dot_r,     size - dot_r],
            fill=AMBER_LIGHT + (255,)
        )
        return img

    # ── "W" zentriert oben ──────────────────────────────────────
    bbox_w = draw.textbbox((0, 0), "W", font=font_w)
    glyph_w = bbox_w[2] - bbox_w[0]
    x_w = (size - glyph_w) // 2 - bbox_w[0]
    draw.text((x_w, w_top - bbox_w[1]), "W", fill=AMBER + (255,), font=font_w)

    # ── Amber-Punkt als Trennzeichen (wie "whisky.MAGAZIN") ──────
    cx = size // 2
    draw.ellipse(
        [cx - dot_r, dot_cy - dot_r, cx + dot_r, dot_cy + dot_r],
        fill=AMBER_LIGHT + (255,)
    )

    # ── "M" zentriert unten ─────────────────────────────────────
    bbox_m = draw.textbbox((0, 0), "M", font=font_m)
    glyph_m = bbox_m[2] - bbox_m[0]
    x_m = (size - glyph_m) // 2 - bbox_m[0]
    draw.text((x_m, m_top - bbox_m[1]), "M", fill=AMBER + (255,), font=font_m)

    return img


def build_ico(images: dict) -> bytes:
    """Baut eine .ico-Datei aus einem Dict {size: PIL.Image}."""
    sizes = sorted(images.keys())
    num   = len(sizes)
    png_blobs = {}
    for sz in sizes:
        buf = io.BytesIO()
        images[sz].save(buf, format="PNG", optimize=True)
        png_blobs[sz] = buf.getvalue()

    # ICO-Header
    header = struct.pack("<HHH", 0, 1, num)

    # Directory entries (je 16 Bytes)
    directory = b""
    offset = 6 + num * 16
    for sz in sizes:
        blob = png_blobs[sz]
        w = h = 0 if sz >= 256 else sz
        directory += struct.pack(
            "<BBBBHHII",
            w, h,        # width, height (0 = 256)
            0, 0,        # color count, reserved
            1, 32,       # planes, bit count
            len(blob),   # size of image data
            offset       # offset in file
        )
        offset += len(blob)

    return header + directory + b"".join(png_blobs[sz] for sz in sizes)


# ─── Generierung ────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    output_dir = "site-v2"
    os.makedirs(output_dir, exist_ok=True)

    print("Generiere Favicon-PNGs...")
    sizes_ico   = [16, 32, 48]
    sizes_extra = [64, 180, 192, 512]

    all_imgs = {}
    for sz in sizes_ico + sizes_extra:
        img = make_favicon_png(sz)
        all_imgs[sz] = img
        print(f"  {sz}×{sz} ✓")

    # ── favicon.ico (16, 32, 48) ─────────────────────────────────
    ico_bytes = build_ico({sz: all_imgs[sz] for sz in sizes_ico})
    with open(f"{output_dir}/favicon.ico", "wb") as f:
        f.write(ico_bytes)
    print("  favicon.ico geschrieben ✓")

    # ── favicon-32x32.png ────────────────────────────────────────
    all_imgs[32].save(f"{output_dir}/favicon-32x32.png", "PNG")
    all_imgs[16].save(f"{output_dir}/favicon-16x16.png", "PNG")
    print("  favicon-16x16.png / favicon-32x32.png ✓")

    # ── apple-touch-icon.png (180×180) ───────────────────────────
    all_imgs[180].save(f"{output_dir}/apple-touch-icon.png", "PNG")
    print("  apple-touch-icon.png (180×180) ✓")

    # ── android-chrome-192x192.png ───────────────────────────────
    all_imgs[192].save(f"{output_dir}/android-chrome-192x192.png", "PNG")
    all_imgs[512].save(f"{output_dir}/android-chrome-512x512.png", "PNG")
    print("  android-chrome-192x192.png / 512x512.png ✓")

    # ── SVG-Favicon (vektoriell, skaliert perfekt) ───────────────
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="5" fill="#1C1108"/>
  <text x="16" y="14.5"
        font-family="Fraunces,Georgia,serif"
        font-size="14" font-weight="700"
        fill="#C8963E"
        text-anchor="middle"
        dominant-baseline="auto">W</text>
  <circle cx="16" cy="19" r="1.6" fill="#DCAF5F"/>
  <text x="16" y="29"
        font-family="Fraunces,Georgia,serif"
        font-size="12" font-weight="700"
        fill="#C8963E"
        text-anchor="middle"
        dominant-baseline="auto">M</text>
</svg>'''
    with open(f"{output_dir}/favicon.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("  favicon.svg ✓")

    # ── site.webmanifest ─────────────────────────────────────────
    manifest = '''{
  "name": "whisky.MAGAZIN",
  "short_name": "Whisky Magazin",
  "icons": [
    {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"}
  ],
  "theme_color": "#1C1108",
  "background_color": "#1C1108",
  "display": "standalone"
}'''
    with open(f"{output_dir}/site.webmanifest", "w", encoding="utf-8") as f:
        f.write(manifest)
    print("  site.webmanifest ✓")

    print("\nAlle Favicon-Dateien erfolgreich erstellt!")
