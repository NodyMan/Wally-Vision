"""
Builds the 29-second SkyBlink demo (1920x1080, 30 fps, H.264) from real screenshots of the running app.
No stock footage, no generated imagery: every frame is the app showing real SPHEREx data.
Developed with SI assistance (Claude); reviewed by team #1.
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAW = Path(r"C:\skyblink_video\raw")
OUT = Path(r"C:\skyblink_video\SkyBlink_demo.mp4")
W, H, FPS = 1920, 1080, 30
BG = (241, 244, 239)
INK = (20, 24, 19)
MUTED = (106, 115, 102)
GREEN = (74, 154, 63)
F = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(f"{F}\\{name}", size)


LIGHT, REG, SEMI = "segoeuil.ttf", "segoeui.ttf", "seguisb.ttf"
IMG = {p.stem: Image.open(p).convert("RGB") for p in RAW.glob("*.png")}


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def crop_view(img, box0, box1, t):
    """Ken Burns: interpolate a 16:9 crop box and scale it to the frame."""
    e = ease(t)
    b = [a + (b_ - a) * e for a, b_ in zip(box0, box1)]
    return img.crop(tuple(int(round(v)) for v in b)).resize((W, H), Image.LANCZOS)


def caption(frame, text, alpha=1.0):
    if not text or alpha <= 0:
        return frame
    f = font(SEMI, 40)
    d = ImageDraw.Draw(frame)
    tw = d.textlength(text, font=f)
    pad_x, box_h = 34, 84
    x0 = (W - tw) / 2 - pad_x
    y0 = H - 140
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x0 + 4, y0 + 8, x0 + tw + 2 * pad_x + 4, y0 + box_h + 8], 22, fill=(0, 0, 0, int(40 * alpha)))
    ld.rounded_rectangle([x0, y0, x0 + tw + 2 * pad_x, y0 + box_h], 22, fill=(255, 255, 255, int(245 * alpha)))
    ld.text((x0 + pad_x, y0 + box_h / 2), text, font=f, fill=INK + (int(255 * alpha),), anchor="lm")
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def title_card(t, end=False):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(230, 234, 228))
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(230, 234, 228))
    a = ease(t * 2.5)
    def txt(xy, s, f, fill):
        c = tuple(int(BG[i] + (fill[i] - BG[i]) * a) for i in range(3))
        d.text(xy, s, font=f, fill=c, anchor="mm")
    if not end:
        txt((W / 2, 400), "SkyBlink", font(LIGHT, 170), INK)
        txt((W / 2, 545), "Compare NASA SPHEREx infrared images of one patch of sky,", font(REG, 46), MUTED)
        txt((W / 2, 610), "taken months apart, and see what moved.", font(REG, 46), MUTED)
        txt((W / 2, 760), "NASA Space Apps Challenge 2026  ·  Planet X and SPHEREx", font(SEMI, 32), GREEN)
    else:
        txt((W / 2, 330), "SkyBlink", font(LIGHT, 150), INK)
        txt((W / 2, 470), "Real data, honest labels, three languages.", font(REG, 46), MUTED)
        txt((W / 2, 600), "Data: NASA/IPAC IRSA — SPHEREx spectral images (DR1, QR3)", font(REG, 34), INK)
        txt((W / 2, 650), "Catalogs: Gaia DR3 (ESA), CatWISE2020  ·  Software: Astropy, reproject", font(REG, 34), INK)
        txt((W / 2, 770), "Not an official NASA product", font(REG, 30), MUTED)
    return im


def phone_scene(t):
    """Russian desktop view on the left, the phone on the right."""
    bg = crop_view(IMG["barnard_ru"], (80, 0, 1840, 990), (180, 60, 1740, 937), t)
    bg = Image.blend(bg, Image.new("RGB", (W, H), BG), 0.25)
    ph = IMG["phone_ru"]
    ph_h = 960
    ph = ph.resize((int(ph.size[0] * ph_h / ph.size[1]), ph_h), Image.LANCZOS)
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.size[0] - 1, ph.size[1] - 1], 46, fill=255)
    x = int(W - ph.size[0] - 150 + (1 - ease(t * 1.6)) * 120)
    y = (H - ph_h) // 2
    shadow = Image.new("L", (ph.size[0] + 80, ph.size[1] + 80), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([40, 50, ph.size[0] + 40, ph.size[1] + 50], 46, fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    bg.paste((0, 0, 0), (x - 40, y - 40), shadow)
    frame = Image.new("RGB", (ph.size[0] + 24, ph.size[1] + 24), (28, 33, 27))
    fm = Image.new("L", frame.size, 0)
    ImageDraw.Draw(fm).rounded_rectangle([0, 0, frame.size[0] - 1, frame.size[1] - 1], 56, fill=255)
    bg.paste(frame, (x - 12, y - 12), fm)
    bg.paste(ph, (x, y), mask)
    return bg


VIEW = (80, 180, 1840, 1170)   # 16:9 box around tiles + image + side panel in the 1920x1400 shots
BLINK = ["eps_frames_0", "eps_frames_1", "eps_frames_2", "eps_frames_3"]

# (duration s, render(t in 0..1, seconds into scene) -> Image, caption)
SCENES = [
    (3.0, lambda t, s: title_card(t), ""),
    (4.5, lambda t, s: crop_view(IMG["home_en"], (0, 0, 1920, 1080), (200, 90, 1720, 945), t),
     "Search any star, or start with the five challenge objects"),
    # blink: image only (the tiles in frames mode carry a separate measurement; the video quotes the diff one)
    (6.5, lambda t, s: crop_view(IMG[BLINK[int(s / 0.55) % 4]], (250, 320, 1750, 1164), (350, 380, 1550, 1055), t),
     "Real SPHEREx visits of Epsilon Indi B, aligned pixel to pixel"),
    (7.0, lambda t, s: crop_view(IMG["eps_diff"], (100, 170, 1820, 1137), (560, 420, 1600, 1005), t),
     "Difference mode: measured shift 6.0 ± 1.1″, catalogue predicts 6.5″"),
    (4.5, lambda t, s: phone_scene(t), "English · Русский · Oʻzbekcha, on any phone"),
    (3.5, lambda t, s: title_card(t, end=True), ""),
]
FADE = 0.4

assert sum(d for d, _, _ in SCENES) <= 29.5, "Space Apps limit is 30 s"

cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
       str(OUT)]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
prev_last = None
for i, (dur, render, cap) in enumerate(SCENES):
    n = int(round(dur * FPS))
    for k in range(n):
        s = k / FPS
        img = render(k / max(n - 1, 1), s)
        # caption fades in after 0.4 s and out before the scene ends
        ca = min(1.0, max(0.0, (s - 0.4) / 0.3)) * min(1.0, max(0.0, (dur - s - 0.15) / 0.3))
        img = caption(img, cap, ca)
        if prev_last is not None and s < FADE:
            img = Image.blend(prev_last, img, s / FADE)
        proc.stdin.write(np.asarray(img, dtype=np.uint8).tobytes())
        last = img
    prev_last = last
    print(f"scene {i + 1}/{len(SCENES)} done", flush=True)
proc.stdin.close()
proc.wait()
print("written", OUT, OUT.stat().st_size // 1024, "KB")
