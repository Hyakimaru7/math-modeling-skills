"""Deterministic teaching data; never represented as real measurements."""
from pathlib import Path
from datetime import date, timedelta
import csv, math, random
random_generator = random.Random(20261105)
target = Path(__file__).parent / "raw/demand.csv"
target.parent.mkdir(exist_ok=True)
with target.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "value"])
    for t in range(112):
        value = 90 + 0.32*t + 13*math.sin(2*math.pi*t/7) + random_generator.gauss(0, 2.4)
        writer.writerow([(date(2026,1,1)+timedelta(days=t)).isoformat(), f"{value:.6f}"])
