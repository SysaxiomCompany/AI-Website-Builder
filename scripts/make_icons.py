"""Generate the app icon and favicon (PNG + ICO) with Pillow. Run: python scripts/make_icons.py"""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "img")
S = 1024  # drawing size; downsampled for anti-aliasing


def draw_icon():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    grad = Image.new("RGBA", (S, S))
    px = grad.load()
    c1, c2 = (58, 87, 214), (125, 91, 214)
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * S)
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    # browser window
    d.rounded_rectangle((190, 250, 834, 760), radius=70, fill=(255, 255, 255, 255))
    d.rounded_rectangle((190, 250, 834, 360), radius=70, fill=(226, 232, 255, 255))
    d.rectangle((190, 320, 834, 360), fill=(226, 232, 255, 255))
    for i, cx in enumerate((260, 320, 380)):
        d.ellipse((cx - 17, 288 - 17 + 20, cx + 17, 288 + 17 + 20), fill=(58, 87, 214, 255))
    # page blocks
    d.rounded_rectangle((250, 420, 520, 470), radius=22, fill=(58, 87, 214, 255))
    d.rounded_rectangle((250, 500, 640, 536), radius=16, fill=(170, 182, 230, 255))
    d.rounded_rectangle((250, 566, 580, 602), radius=16, fill=(170, 182, 230, 255))
    d.rounded_rectangle((250, 640, 400, 710), radius=26, fill=(125, 91, 214, 255))
    # sparkle (the "AI" mark)
    cx, cy, r, w = 760, 700, 190, 38
    star = [(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w), (cx, cy + r), (cx - w, cy + w),
            (cx - r, cy), (cx - w, cy - w)]
    d.polygon(star, fill=(255, 205, 64, 255), outline=(255, 255, 255, 255))
    d.ellipse((cx + 150 - 28, cy - 190 - 28, cx + 150 + 28, cy - 190 + 28), fill=(255, 205, 64, 255))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    big = draw_icon()
    for size in (512, 180, 64, 32):
        big.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"icon-{size}.png" if size != 32 else "favicon-32.png"))
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
