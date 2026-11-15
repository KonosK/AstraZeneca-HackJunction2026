import json
import os
import shutil
from pathlib import Path

import imageio_ffmpeg
import whisper

ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
shutil.copy(ff, ff.with_name("ffmpeg.exe"))
os.environ["PATH"] = str(ff.parent) + os.pathsep + os.environ.get("PATH", "")

model = whisper.load_model("base")
aud = Path(__file__).resolve().parents[1] / "public" / "audio" / "vo_norm.mp3"
result = model.transcribe(str(aud), language="en")
segs = [
    {
        "start": round(s["start"], 2),
        "end": round(s["end"], 2),
        "text": s["text"].strip(),
    }
    for s in result["segments"]
]
out = Path(__file__).resolve().parents[1] / "public" / "inspect" / "vo_segments.json"
out.write_text(json.dumps(segs, indent=2), encoding="utf-8")
for s in segs:
    print(f"{s['start']:6.2f}-{s['end']:6.2f}  {s['text']}")
