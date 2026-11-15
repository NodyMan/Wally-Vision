"""Full-HD screenshots of the running SkyBlink app (headless Chrome), for the demo video. Real app, real data.
Developed with SI assistance (Claude); reviewed by team #1.
"""
import subprocess
import sys
import time
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = r"C:\skyblink_video\chrome-profile"
OUT = Path(r"C:\skyblink_video\raw")
BASE = "http://localhost:3010"
EPS = "ra=331.04383&dec=-56.78269&fov=300&det=6&name=Epsilon%20Indi%20B"

SHOTS = [
    ("home_en", "/en", (1920, 1080)),
    ("eps_frames_0", f"/en/view?{EPS}&mode=frames&t=0", (1920, 1400)),
    ("eps_frames_1", f"/en/view?{EPS}&mode=frames&t=1", (1920, 1400)),
    ("eps_frames_2", f"/en/view?{EPS}&mode=frames&t=2", (1920, 1400)),
    ("eps_frames_3", f"/en/view?{EPS}&mode=frames&t=3", (1920, 1400)),
    ("eps_diff", f"/en/view?{EPS}&mode=diff", (1920, 1400)),
    ("eps_bands", f"/en/view?ra=331.04383&dec=-56.78269&fov=300&det=all&mode=sum&name=Epsilon%20Indi%20B", (1920, 1400)),
    ("barnard_ru", "/ru/view?ra=269.452083&dec=4.693364&fov=300&mode=diff&det=2&name=%D0%97%D0%B2%D0%B5%D0%B7%D0%B4%D0%B0%20%D0%91%D0%B0%D1%80%D0%BD%D0%B0%D1%80%D0%B4%D0%B0", (1920, 1400)),
    ("home_uz", "/uz", (1920, 1080)),
    ("phone_ru", f"/ru/view?{EPS}&mode=diff", (390, 844)),
]


def shot(name: str, path: str, size: tuple[int, int]) -> None:
    out = OUT / f"{name}.png"
    args = [CHROME, "--headless=new", f"--user-data-dir={PROFILE}", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2" if size[0] < 800 else "--force-device-scale-factor=1",
            f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=30000",
            f"--screenshot={out}", BASE + path]
    t0 = time.time()
    subprocess.run(args, capture_output=True, timeout=180)
    print(name, "ok" if out.exists() else "MISSING", f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    wanted = set(sys.argv[1:])
    for n, p, s in SHOTS:
        if not wanted or n in wanted:
            shot(n, p, s)
