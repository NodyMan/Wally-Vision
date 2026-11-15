"""
Builds video/SkyBlink_demo.mp4 (1080p30, <= 30 s): the screen recording made by record.mjs + spoken narration.
  python video/build_video.py                     # narration from narration.txt via text-to-speech (edge-tts)
  python video/build_video.py --voice my_voice.m4a  # your own recording of narration.txt instead of TTS
Read narration.txt at a calm pace, one line per scene, about 27 s in total.
Developed with SI assistance (Claude); reviewed by team #1.
"""
import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REC = Path(r"C:\skyblink_video\rec")
WORK = Path(r"C:\skyblink_video\tts")
OUT = HERE / "SkyBlink_demo.mp4"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
VOICE, RATE = "en-US-AndrewNeural", "+10%"
HOME_BOX = (200, 50, 1720, 905)     # 16:9 crops of the 1920x1080 recording
VIEW_BOX = (250, 230, 1650, 1017)

ap = argparse.ArgumentParser()
ap.add_argument("--voice", help="your own narration recording (any audio format ffmpeg reads)")
args = ap.parse_args()

lines = [re.match(r"\[(\w+)\]\s*(.*)", l).groups()
         for l in (HERE / "narration.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
log = json.loads((REC / "log.json").read_text())
frames, marks, mouse = log["frames"], log["marks"], log["mouse"]


def duration(path):
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


# ---- narration clips (TTS) -------------------------------------------------------------------
clips = {}
if not args.voice:
    import edge_tts
    WORK.mkdir(exist_ok=True)

    async def tts():
        for i, (key, text) in enumerate(lines):
            path = WORK / f"{i}_{key}.mp3"
            for _ in range(8):   # the free endpoint sometimes answers with no audio: retry
                try:
                    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))
                    if path.stat().st_size > 1000:
                        break
                except Exception as e:  # noqa: BLE001
                    print("tts retry", key, e)
                    await asyncio.sleep(1)
            clips[key] = (path, duration(path))
    asyncio.run(tts())
    for k, (_, d) in clips.items():
        print(f"{k}: {d:.2f} s")


def need(key, default):
    return clips[key][1] + 0.25 if key in clips else default


# ---- scenes: (name, rec start, rec end, out duration, crop, narration keys) ---------------------
m = marks
scenes = [
    ("home", 0.0, m["card"], max(m["card"], need("home", 0) + 0.3), HOME_BOX, ["home"]),
    ("card", m["card"], m["blink"], need("card", 5.9), VIEW_BOX, ["card"]),
    ("blink", m["blink"], m["diff"], 4.2, VIEW_BOX, ["blink"]),
    ("diff", m["diff"], m["lang"], need("diff", 8.1) + need("diff2", 4.8) + 0.2, VIEW_BOX, ["diff", "diff2"]),
]
total = sum(s[3] for s in scenes)
print(f"video {total:.2f} s")
assert total <= 30.0, "Space Apps demo limit is 30 s"

ftimes = np.array([f["t"] for f in frames])
mtimes = np.array([p["t"] for p in mouse])
cache = {}


def frame_at(t):
    i = int(max(0, np.searchsorted(ftimes, t, side="right") - 1))
    name = frames[i]["name"]
    if name not in cache:
        cache.clear()
        cache[name] = Image.open(REC / "frames" / name).convert("RGB")
    return cache[name]


def cursor_at(t):
    i = int(np.searchsorted(mtimes, t, side="right") - 1)
    if i < 0:
        return None
    return mouse[i]["x"], mouse[i]["y"]


CURSOR = [(0, 0), (0, 26), (7, 20), (12, 31), (16, 29), (11, 18), (20, 18)]
F_LOW = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", 34)
F_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)


def lower_third(img, text, alpha, font=F_LOW, y=H - 120):
    if alpha <= 0:
        return img
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = d.textlength(text, font=font)
    x0 = (W - tw) / 2 - 28
    d.rounded_rectangle([x0, y, x0 + tw + 56, y + 66], 18, fill=(255, 255, 255, int(235 * alpha)))
    d.text((x0 + 28, y + 33), text, font=font, fill=(20, 24, 19, int(255 * alpha)), anchor="lm")
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                         "-pix_fmt", "yuv420p", str(WORK / "video_only.mp4")], stdin=subprocess.PIPE)
placements = []   # (key, out start)
t_out = 0.0
for name, r0, r1, dur, box, keys in scenes:
    at = t_out + 0.25
    for k in keys:
        placements.append((k, at))
        at += need(k, 0)
    n = int(round(dur * FPS))
    for k in range(n):
        s = k / FPS
        rt = min(r0 + s, r1 - 0.05)          # real time while the recording lasts, then hold
        src = frame_at(rt)
        sx, sy = (box[2] - box[0]) / W, (box[3] - box[1]) / H
        img = src.crop(box).resize((W, H), Image.LANCZOS)
        c = cursor_at(rt)
        if c:
            cx, cy = (c[0] - box[0]) / sx, (c[1] - box[1]) / sy
            d = ImageDraw.Draw(img)
            pts = [(cx + px * 1.3, cy + py * 1.3) for px, py in CURSOR]
            d.polygon(pts, fill=(255, 255, 255), outline=(20, 24, 19), width=2)
        if name == "diff":
            a = min(1, max(0, (s - 1.2) / 0.4))
            img = lower_third(img, "Measured shift 6.0 ± 1.1″   ·   catalogue 6.5″", a)
        if name == "diff" and s > dur - 3.2:
            a = min(1, (s - (dur - 3.2)) / 0.4)
            img = lower_third(img, "SPHEREx data: NASA/IPAC IRSA  ·  SkyBlink, NASA Space Apps 2026  ·  not an official NASA product",
                              a, F_SMALL, 40)
        if t_out == 0 and s < 0.4:
            img = Image.blend(Image.new("RGB", (W, H), (241, 244, 239)), img, s / 0.4)
        proc.stdin.write(np.asarray(img, dtype=np.uint8).tobytes())
    t_out += dur
    print("scene", name, "done")
proc.stdin.close()
proc.wait()

# ---- audio -------------------------------------------------------------------------------------
if args.voice:
    audio_inputs = ["-i", args.voice]
    filt = f"[1:a]adelay=300|300,apad,atrim=0:{total:.2f},afade=t=out:st={total - 0.6:.2f}:d=0.6[a]"
else:
    audio_inputs, parts = [], []
    for j, (k, start) in enumerate(placements):
        audio_inputs += ["-i", str(clips[k][0])]
        ms = int(start * 1000)
        parts.append(f"[{j + 1}:a]adelay={ms}|{ms}[a{j}]")
    filt = ";".join(parts) + ";" + "".join(f"[a{j}]" for j in range(len(placements))) + \
        f"amix=inputs={len(placements)}:normalize=0,apad,atrim=0:{total:.2f}[a]"
subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(WORK / "video_only.mp4"), *audio_inputs,
                "-filter_complex", filt, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", "-shortest", str(OUT)], check=True)
print("written", OUT, f"{duration(OUT):.2f} s")
