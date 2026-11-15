"""
Builds the long SkyBlink explainer (about 2 minutes, 1080p30, H.264 + AAC) from a narration of
video/narration_long.txt and real recordings of the app (record_v3.mjs A-C, record_v4.mjs D-G, record_long.mjs H-M).

The voice is transcribed (faster-whisper, word timestamps) and each paragraph's scene starts where the narrator starts
that paragraph, so any reading of the script lines up. Music and sound effects are synthesized (build_video_v4.py).

    python video/build_video_long.py VOICE.mp3 [--out video/SkyBlink_explainer.mp4]

Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_video_v4 as bv  # noqa: E402  (shared helpers: audio, music, sfx, cursor, overlays, end card)

W, H, FPS, SR = bv.W, bv.H, bv.FPS, bv.SR
HERE = Path(__file__).resolve().parent
REC_V3, REC_LONG = Path(r"C:\skyblink_video\v3"), Path(r"C:\skyblink_video\long\rec")
STATIC = HERE.parent / "backend" / "viewer" / "static_cache" / "epsilon-indi-b" / "frames"
TAKES = {**{k: REC_V3 / "rec" / k for k in "ABC"}, **{k: REC_V3 / "rec4" / k for k in "DEFG"},
         **{k: REC_LONG / k for k in "HIJKLM"}}
CANVAS = {"A": (420, 320, 1260, 1000), "D": (380, 60, 1000, 640), "H": (420, 320, 1260, 1000)}
EPS_LABEL = "Epsilon Indi B  ·  measured shift 6.0 ± 1.1″  ·  catalogue predicts 6.5″"
BARNARD_LABEL = "Barnard’s Star  ·  saturated core masked  ·  11.9 ± 1.3″  ·  catalogue 10.4″"

# one scene per paragraph of the script, in order: (kind, take segments [(take, start, end), ...], lower third)
SCENES = [
    ("tombaugh", [], None),
    ("nasa", [], None),
    ("take", [("A", 0.3, 4.9)], None),
    ("take", [("H", 0.5, 10.6)], None),
    ("take", [("A", 13.2, 18.2)], None),
    ("take", [("A", 19.5, 20.12), ("A", 20.27, 22.0)], None),
    ("take", [("A", 22.0, 26.0)], EPS_LABEL),
    ("take", [("H", 10.6, 17.6)], BARNARD_LABEL),
    ("take", [("D", 4.9, 10.5)], None),
    ("take", [("E", 5.1, 7.3), ("F", 4.75, 5.95)], None),
    ("take", [("J", 0.7, 8.4)], None),
    ("take", [("K", 0.3, 12.8)], None),
    ("take", [("L", 0.3, 15.9)], None),
    ("langs", [("A", 24.5, 25.3), ("B", 0.74, 1.4), ("C", 2.3, 3.6)], None),
    ("end", [], None),
]


def paragraphs() -> list[str]:
    t = (HERE / "narration_long.txt").read_text(encoding="utf-8")
    body = t.split("=== PASTE THIS INTO ELEVENLABS ===")[1].split("=== WHAT EACH PARAGRAPH SHOWS ===")[0]
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def paragraph_starts(voice: Path, paras: list[str]) -> tuple[list[float], float]:
    from faster_whisper import WhisperModel
    wav = voice.with_suffix(".16k.wav")
    subprocess.run([bv.FF, "-y", "-v", "error", "-i", str(voice), "-ac", "1", "-ar", "16000", str(wav)], check=True)
    segs, _ = WhisperModel("base.en", device="cpu", compute_type="int8").transcribe(str(wav), word_timestamps=True)
    words = [(norm(w.word), w.start, w.end) for s in segs for w in s.words if norm(w.word)]
    starts, i = [], 0
    for k, p in enumerate(paras):
        key = [norm(w) for w in p.split()[:3] if norm(w)]
        found = None
        for j in range(i, len(words)):
            got = [words[j + n][0] for n in range(len(key)) if j + n < len(words)]
            if sum(a == b or a.startswith(b[:4]) for a, b in zip(got, key)) >= 2:
                found = j
                break
        if found is None:   # fall back on word counts
            done = sum(len(q.split()) for q in paras[:k])
            found = min(len(words) - 1, max(i, round(done / sum(len(q.split()) for q in paras) * len(words))))
            print(f"paragraph {k + 1}: start not found, estimated", file=sys.stderr)
        starts.append(words[found][1])
        i = found + 1
    starts[0] = 0.0
    return starts, words[-1][2]


class Take(bv.Take):
    def __init__(self, name: str):
        super().__init__(TAKES[name])
        if name in CANVAS:   # drop the black "searching the archive" frames shown while a view loads
            keep = []
            for f in self.frames:
                a = np.asarray(Image.open(self.folder / "frames" / f["name"]).convert("L").crop(CANVAS[name]))
                if np.mean(a < 10) < 0.85:
                    keep.append(f)
            self.frames, self.times = keep, np.array([f["t"] for f in keep])


def seg_time(segs, takes, local: float, dur: float):
    """Which take and source time to show `local` seconds into a scene made of `segs`."""
    total = sum(e - s for _, s, e in segs)
    rate = min(3.0, max(0.6, total / dur))
    x = min(local * rate, total - 1e-3)
    for name, s, e in segs:
        if x < e - s:
            return takes[name], s + x
        x -= e - s
    name, s, e = segs[-1]
    return takes[name], e


def tombaugh_frame(local: float) -> Image.Image:
    im = Image.new("RGB", (W, H), (12, 16, 12))
    which = int(local / 0.7) % 2
    fid, label = [("7680794912aeb3f7d09f", "2025-04-29"), ("d05dd1deebb94e2abd96", "2026-09-22")][which]
    pix = Image.open(STATIC / f"{fid}.png").convert("RGB")
    pix = pix.resize((pix.width * 17, pix.height * 17), Image.NEAREST)
    x, y = (W - pix.width) // 2, (H - pix.height) // 2
    im.paste(pix, (x, y))
    d = ImageDraw.Draw(im)
    d.text((x, y - 24), f"SPHEREx  ·  {label}", font=bv.font("seguisb.ttf", 34), fill=(143, 208, 127), anchor="ls")
    d.text((W // 2, H - 40), "Real SPHEREx data  ·  the field of the brown dwarf Epsilon Indi B",
           font=bv.font("segoeui.ttf", 28), fill=(183, 196, 178), anchor="ms")
    return im


def phone_frame(bg: Image.Image, local: float, m: Take) -> Image.Image:
    bg = bg.filter(ImageFilter.GaussianBlur(6))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (241, 244, 239)), 0.35)
    ph = m.frame(min(local, m.times[-1] if len(m.times) else 0))
    ph_h = 960
    ph = ph.resize((int(ph.width * ph_h / ph.height), ph_h), Image.LANCZOS)
    x, y = (W - ph.width) // 2, (H - ph_h) // 2
    frame = Image.new("RGB", (ph.width + 28, ph_h + 28), (28, 33, 27))
    fm = Image.new("L", frame.size, 0)
    ImageDraw.Draw(fm).rounded_rectangle([0, 0, frame.width - 1, frame.height - 1], 60, fill=255)
    bg.paste(frame, (x - 14, y - 14), fm)
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], 48, fill=255)
    bg.paste(ph, (x, y), mask)
    return bg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("--nasa", default=r"C:\skyblink_video\v3\nasa\spacecraft_4k.mp4")
    ap.add_argument("--out", default=str(HERE / "SkyBlink_explainer.mp4"))
    args = ap.parse_args()
    work = Path(r"C:\skyblink_video\long\build")
    work.mkdir(parents=True, exist_ok=True)

    paras = paragraphs()
    assert len(paras) == len(SCENES), (len(paras), len(SCENES))
    starts, voice_end = paragraph_starts(Path(args.voice), paras)
    total = voice_end + 2.6
    bounds = [max(0.0, s - 0.15) if k else 0.0 for k, s in enumerate(starts)] + [total]
    for k, (a, b) in enumerate(zip(bounds, bounds[1:])):
        print(f"scene {k + 1:2d} {a:6.2f}-{b:6.2f}  {paras[k][:60]}")
    bv.CFG.TOTAL = total
    bv.CFG.WHOOSH_AT = [bounds[1], bounds[-2]]

    takes = {k: Take(k) for k in TAKES}
    nasa_len = round(bounds[2] - bounds[1] + 0.5, 1)
    nasa = bv.nasa_frames(Path(args.nasa), 3.0, nasa_len, work / f"nasa_frames_{nasa_len}")

    clicks = []
    for k, (kind, segs, _) in enumerate(SCENES):
        if kind in ("take", "langs") and segs:
            dur = bounds[k + 1] - bounds[k]
            tot = sum(e - s for _, s, e in segs)
            rate = min(3.0, max(0.6, tot / dur))
            off = 0.0
            for name, s, e in segs:
                clicks += [bounds[k] + (off + c - s) / rate for c in takes[name].clicks if s <= c < e]
                off += e - s
    clicks = sorted(c for c in clicks if c < total)

    raw = bv.decode_audio(Path(args.voice))
    voice = np.zeros(int(total * SR))
    voice[:min(len(raw), len(voice))] = raw[:len(voice)]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.84
    mix = voice + bv.build_music(len(voice), voice) + bv.build_sfx(len(voice), clicks)
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    wav = work / "mix.f32"
    mix.astype(np.float32).tofile(wav)

    cmd = [bv.FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(wav),
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    credit = bv.font("seguisb.ttf", 26)
    prev = None
    for i in range(int(total * FPS)):
        t = i / FPS
        k = max(j for j in range(len(SCENES)) if bounds[j] <= t)
        kind, segs, label = SCENES[k]
        local, dur = t - bounds[k], bounds[k + 1] - bounds[k]
        if kind == "tombaugh":
            im = tombaugh_frame(local)
        elif kind == "nasa":
            im = Image.open(nasa[min(len(nasa) - 1, int(local * FPS))]).convert("RGB")
            d = ImageDraw.Draw(im)
            d.text((W - 38, H - 34), bv.NASA_CREDIT, font=credit, fill=(0, 0, 0), anchor="rs")
            d.text((W - 40, H - 36), bv.NASA_CREDIT, font=credit, fill=(235, 238, 232), anchor="rs")
        elif kind == "end":
            im = bv.end_card(local)
            if prev is not None and local < 0.5:
                im = Image.blend(prev, im, local / 0.5)
        elif kind == "langs" and local > dur * 0.55:
            tk, st = seg_time(segs, takes, dur * 0.55, dur)
            im = phone_frame(tk.frame(st), local - dur * 0.55, takes["M"])
        else:
            span = dur * 0.55 if kind == "langs" else dur
            tk, st = seg_time(segs, takes, local, span)
            im = tk.frame(st)
            near = [c for c in tk.clicks if 0 <= st - c < 0.35]
            bv.draw_cursor(im, *tk.cursor(st), (st - near[-1]) if near else None)
        if label and local > 0.6:
            im = bv.overlay_text_box(im, label, min(1, (local - 0.6) / 0.3, (dur - local) / 0.3))
        if kind != "end":
            prev = im
        proc.stdin.write(np.asarray(im, dtype=np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print("written", args.out, f"{total:.1f} s")


if __name__ == "__main__":
    main()
