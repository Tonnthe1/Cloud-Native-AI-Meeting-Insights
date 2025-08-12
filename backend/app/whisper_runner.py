import os
import subprocess
import tempfile
from pathlib import Path

WHISPER_BIN = "/opt/whisper.cpp/main"
MODEL_PATH = "/opt/whisper.cpp/models/ggml-base.en.bin"

def transcribe_with_whisper_cpp(input_audio_path: str) -> str:
    audio = Path(input_audio_path)
    if not audio.exists():
        raise FileNotFoundError(f"audio not found: {audio}")

    if not Path(WHISPER_BIN).exists():
        raise RuntimeError("whisper.cpp binary not found")

    if not Path(MODEL_PATH).exists():
        raise RuntimeError("whisper.cpp model not found")

    with tempfile.TemporaryDirectory() as td:
        out_prefix = str(Path(td) / "out")
        cmd = [
            WHISPER_BIN,
            "-m", MODEL_PATH,
            "-f", str(audio),
            "-otxt",
            "-of", out_prefix,
            "-l", "en",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed: {res.stderr or res.stdout}")

        txt_file = Path(out_prefix + ".txt")
        if not txt_file.exists():
            alt = Path(out_prefix + ".wav.txt")
            txt_file = alt if alt.exists() else txt_file

        if not txt_file.exists():
            raise RuntimeError("whisper.cpp output .txt not found")

        return txt_file.read_text(encoding="utf-8", errors="ignore").strip()
