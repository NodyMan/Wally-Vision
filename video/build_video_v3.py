"""
Builds the SkyBlink demo video (≤ 30 s, 1080p30, H.264 + AAC):
  0–4 s   NASA SVS SPHEREx spacecraft animation (svs.gsfc.nasa.gov/14966, credit NASA/JPL-Caltech)
  4–24 s  screen recording of the real app (video/record_v3.mjs): home -> Epsilon Indi B blink -> difference,
          then UZ and RU views with Simple mode
  24–29 s end card with the live link
Voice: the team's ElevenLabs narration, cut to the sentences that are true for our data and fit 30 s
(the WISE 0855 "jumps off the screen" claim is left out: no shift is measurable for it in SPHEREx).
Music and sound effects are synthesized here (no third-party audio).

    python video/build_video_v3.py VOICE.mp3 [--nasa spacecraft_4k.mp4] [--rec C:\\skyblink_video\\v3\\rec]

Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, SR = 1920, 1080, 30, 44100
FONTS = Path(r"C:\Windows\Fonts")
LIVE_URL = "frontend-three-xi-80.vercel.app"

# voice: (source start, source end, output start) in seconds; cut points sit in pauses or word gaps
VOICE = [
    (0.00, 8.00, 0.00),     # NASA's SPHEREx telescope maps the entire sky in infrared, but raw space data is locked behind complex tools.
    (8.56, 9.96, 8.10),     # Meet SkyBlink.
    (12.93, 18.16, 9.60),   # In seconds, SkyBlink aligns real NASA epochs into an interactive flipbook.
    (18.16, 20.46, 14.83),  # Switch to difference mode and moving objects
    (24.50, 26.14, 17.15),  #   jump right off the screen.
    (37.40, 42.45, 18.95),  # Built for everyone in English, Uzbek and Russian, with a simple mode for beginners
    (45.14, 49.95, 24.15),  # SkyBlink. Turning NASA's infrared archive into discovery for everyone.
]
TOTAL = 29.3

# picture: (output start, output end, source, source time = output time + offset)
SHOTS = [
    (0.00, 4.00, "nasa", 0.0),
    (4.00, 9.60, "A", -1.60),    # home; hover on "Meet SkyBlink", click the Epsilon Indi card
    (9.60, 14.97, "A", 3.30),    # zoomed blink ("aligns real NASA epochs into an interactive flipbook")
    (14.97, 15.71, "A", 4.14),   # Difference: the click (19.69 in take A) lands on the word "difference"
    (15.71, 21.21, "A", 4.38),   # skip the 0.19 s loading flash (19.90–20.09 in take A)
    (21.21, 21.87, "B", -20.46), # Uzbek, on "Uzbek"
    (21.87, 24.15, "C", -19.81), # Russian + Simple mode click on "simple mode"
    (24.15, TOTAL, "end", 0.0),
]
LOWER_THIRD = (16.2, 21.1, "Epsilon Indi B  ·  measured shift 6.0 ± 1.1″  ·  catalogue predicts 6.5″")
NASA_CREDIT = "Credit: NASA/JPL-Caltech"
WHOOSH_AT = [3.80, 23.90]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def decode_audio(path: Path) -> np.ndarray:
    raw = subprocess.run([FF, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def build_voice(src: np.ndarray) -> np.ndarray:
    out = np.zeros(int(TOTAL * SR) + SR)
    fade = int(0.025 * SR)
    for a, b, o in VOICE:
        seg = src[int(a * SR):int(b * SR)].copy()
        ramp = np.linspace(0, 1, fade)
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
        i = int(o * SR)
        out[i:i + len(seg)] += seg
    return out[:int(TOTAL * SR)] / (np.abs(out).max() + 1e-9) * 0.84


def build_music(n: int, voice: np.ndarray) -> np.ndarray:
    t = np.arange(n) / SR
    chords = [[110.0, 164.81, 220.0, 261.63, 329.63], [87.31, 130.81, 174.61, 220.0, 261.63],
              [130.81, 196.0, 261.63, 329.63, 392.0], [98.0, 146.83, 196.0, 246.94, 293.66]]
    bar = 3.75
    music = np.zeros(n)
    for k in range(int(TOTAL / bar) + 2):
        notes = chords[k % 4]
        s0 = k * bar
        env = np.clip((t - s0) / 0.9, 0, 1) * np.clip((s0 + bar + 0.7 - t) / 0.7, 0, 1)
        if not env.any():
            continue
        for f in notes:
            for det in (0.9985, 1.0015):
                music += env * 0.05 * (np.sin(2 * np.pi * f * det * t) + 0.25 * np.sin(4 * np.pi * f * det * t))
        # soft arpeggio, eighth notes at 128 bpm
        step = 60 / 128 / 2
        for j in range(int(bar / step)):
            st = s0 + j * step
            f = notes[1:][j % 4] * 2
            i0 = int(st * SR)
            if i0 >= n:
                break
            m = min(n - i0, int(0.45 * SR))
            tt = np.arange(m) / SR
            music[i0:i0 + m] += 0.045 * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.16)
    # gentle low-pass, level, fades, ducking under the voice
    music = np.convolve(music, np.ones(12) / 12, mode="same")
    music *= 10 ** (-30 / 20) / (np.sqrt(np.mean(music ** 2)) + 1e-9)
    win = int(0.12 * SR)
    venv = np.convolve(np.abs(voice), np.ones(win) / win, mode="same")
    duck = 1 - 0.45 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
    fade = np.clip(t / 1.2, 0, 1) * np.clip((TOTAL - t) / 1.8, 0, 1)
    return music * duck * fade


def build_sfx(n: int, clicks: list[float]) -> np.ndarray:
    rng = np.random.default_rng(7)
    sfx = np.zeros(n)
    for at in WHOOSH_AT:
        m = int(0.7 * SR)
        noise = rng.standard_normal(m)
        tt = np.arange(m) / m
        out = np.zeros(m)
        for k in range(m):   # band-pass sweep: moving average of varying width
            pass
        widths = (40 - 34 * tt).astype(int)
        cs = np.concatenate([[0], np.cumsum(noise)])
        idx = np.arange(m)
        lo = np.clip(idx - widths, 0, m)
        out = (cs[idx + 1] - cs[lo]) / np.maximum(widths, 1)
        out -= np.convolve(out, np.ones(200) / 200, mode="same")
        out *= np.sin(np.pi * tt) ** 2
        out *= 10 ** (-19 / 20) / (np.abs(out).max() + 1e-9)
        i0 = int((at - 0.35) * SR)
        sfx[i0:i0 + m] += out[: max(0, min(m, n - i0))]
    for at in clicks:
        m = int(0.05 * SR)
        tt = np.arange(m) / SR
        c = 0.6 * np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt / 0.008) + 0.4 * rng.standard_normal(m) * np.exp(-tt / 0.003)
        c *= 10 ** (-17 / 20) / np.abs(c).max()
        i0 = int(at * SR)
        sfx[i0:i0 + m] += c[: max(0, min(m, n - i0))]
    return sfx


class Take:
    def __init__(self, folder: Path):
        log = json.loads((folder / "log.json").read_text(encoding="utf-8"))
        self.folder = folder
        self.frames = sorted(log["frames"], key=lambda f: f["t"])
        self.times = np.array([f["t"] for f in self.frames])
        self.mouse = log["mouse"]
        self.mt = np.array([m["t"] for m in self.mouse])
        self.clicks = [m["t"] for m in self.mouse if m.get("click")]
        self._cache: dict[str, Image.Image] = {}

    def frame(self, t: float) -> Image.Image:
        i = max(0, int(np.searchsorted(self.times, t, side="right")) - 1)
        name = self.frames[i]["name"]
        if name not in self._cache:
            self._cache = {name: Image.open(self.folder / "frames" / name).convert("RGB").resize((W, H))}
        return self._cache[name].copy()

    def cursor(self, t: float) -> tuple[float, float]:
        i = max(0, int(np.searchsorted(self.mt, t, side="right")) - 1)
        return self.mouse[i]["x"], self.mouse[i]["y"]


ARROW = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]


def draw_cursor(im: Image.Image, x: float, y: float, ripple: float | None) -> None:
    d = ImageDraw.Draw(im, "RGBA")
    if ripple is not None and ripple < 0.35:
        r = 10 + 60 * ripple
        d.ellipse([x - r, y - r, x + r, y + r], outline=(74, 154, 63, int(220 * (1 - ripple / 0.35))), width=4)
    pts = [(x + px * 1.15, y + py * 1.15) for px, py in ARROW]
    d.polygon([(px + 2, py + 2) for px, py in pts], fill=(0, 0, 0, 70))
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(20, 24, 19, 255))


def overlay_text_box(im: Image.Image, text: str, alpha: float) -> Image.Image:
    f = font("seguisb.ttf", 38)
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=f)
    x0, y0, h = 70, H - 150, 82
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x0, y0, x0 + tw + 70, y0 + h], 20, fill=(255, 255, 255, int(240 * alpha)))
    ld.rounded_rectangle([x0, y0, x0 + 10, y0 + h], 5, fill=(74, 154, 63, int(255 * alpha)))
    ld.text((x0 + 40, y0 + h / 2), text, font=f, fill=(20, 24, 19, int(255 * alpha)), anchor="lm")
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def end_card(t: float) -> Image.Image:
    im = Image.new("RGB", (W, H), (12, 16, 12))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W / 2 - 700, H / 2 - 420, W / 2 + 700, H / 2 + 300], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    im.paste((40, 90, 40), (0, 0), glow)
    d = ImageDraw.Draw(im)
    a = min(1.0, max(0.0, (t - 0.25) / 0.6))

    def txt(y, s, f, c):
        d.text((W / 2, y), s, font=f, fill=tuple(int(12 + (cc - 12) * a) for cc in c), anchor="mm")

    txt(400, "SkyBlink", font("segoeuil.ttf", 170), (240, 244, 238))
    txt(540, LIVE_URL, font("seguisb.ttf", 52), (124, 198, 107))
    txt(625, "NASA Space Apps Challenge 2026  ·  Planet X and SPHEREx", font("segoeui.ttf", 36), (180, 188, 176))
    txt(960, "SPHEREx data: NASA/IPAC IRSA  ·  Spacecraft animation: NASA/JPL-Caltech  ·  Not an official NASA product",
        font("segoeui.ttf", 24), (120, 128, 116))
    return im


def nasa_frames(clip: Path, start: float, dur: float, folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    if not any(folder.glob("*.png")):
        subprocess.run([FF, "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(clip),
                        "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}", str(folder / "n%04d.png")], check=True)
    return sorted(folder.glob("*.png"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("--nasa", default=r"C:\skyblink_video\v3\nasa\spacecraft_4k.mp4")
    ap.add_argument("--nasa-start", type=float, default=8.5)
    ap.add_argument("--rec", default=r"C:\skyblink_video\v3\rec")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "SkyBlink_demo.mp4"))
    args = ap.parse_args()
    work = Path(args.rec).parent

    takes = {k: Take(Path(args.rec) / k) for k in "ABC"}
    nasa = nasa_frames(Path(args.nasa), args.nasa_start, 4.0, work / "nasa_frames")

    # clicks inside the used parts of each take, in output time
    clicks = []
    for o0, o1, src, off in SHOTS:
        if src in takes:
            clicks += [c - off for c in takes[src].clicks if o0 <= c - off < o1]
    clicks.sort()

    voice = build_voice(decode_audio(Path(args.voice)))
    n = len(voice)
    mix = voice + build_music(n, voice) + build_sfx(n, clicks)
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    wav = work / "mix.f32"
    mix.astype(np.float32).tofile(wav)

    cmd = [FF, "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(wav),
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    credit_font = font("seguisb.ttf", 26)
    prev_last = None
    for k in range(int(TOTAL * FPS)):
        t = k / FPS
        o0, o1, src, off = next(s for s in SHOTS if s[0] <= t < s[1] or s is SHOTS[-1])
        if src == "nasa":
            im = Image.open(nasa[min(len(nasa) - 1, k)]).convert("RGB")
            d = ImageDraw.Draw(im)
            d.text((W - 38, H - 34), NASA_CREDIT, font=credit_font, fill=(0, 0, 0), anchor="rs")
            d.text((W - 40, H - 36), NASA_CREDIT, font=credit_font, fill=(235, 238, 232), anchor="rs")
        elif src == "end":
            im = end_card(t - o0)
            if prev_last is not None and t - o0 < 0.5:
                im = Image.blend(prev_last, im, (t - o0) / 0.5)
        else:
            tk = takes[src]
            st = t + off
            im = tk.frame(st)
            near = [c for c in tk.clicks if 0 <= st - c < 0.35]
            draw_cursor(im, *tk.cursor(st), (st - near[-1]) if near else None)
            prev_last = im
        a0, a1, label = LOWER_THIRD
        if a0 <= t < a1:
            im = overlay_text_box(im, label, min(1, (t - a0) / 0.3, (a1 - t) / 0.3))
        proc.stdin.write(np.asarray(im, dtype=np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print("written", args.out, f"{TOTAL:.1f} s; clicks at", [round(c, 2) for c in clicks])


if __name__ == "__main__":
    main()
