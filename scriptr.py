#!/usr/bin/env python3
"""
scriptr.py — Download TikTok videos and transcribe them locally.
Usage: python scriptr.py "url1,url2,url3" [--model small] [--output ./downloads]
"""

import subprocess
import sys
import os


# ── Self-installing bootstrap ─────────────────────────────────────────────────

REQUIRED_PACKAGES = {
    "yt_dlp": "yt-dlp",
    "faster_whisper": "faster-whisper",
}

def _install(pip_name):
    print(f"  Installing {pip_name}...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet", pip_name],
        stdout=subprocess.DEVNULL,
    )

def _check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("\n[!] ffmpeg is not installed — it's required for audio extraction.")
        print("    Install it with:  brew install ffmpeg")
        print("    Then re-run this script.\n")
        sys.exit(1)

def bootstrap():
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append((import_name, pip_name))

    if missing:
        print(f"[scriptr] Installing {len(missing)} missing package(s)...")
        for _, pip_name in missing:
            _install(pip_name)
        print("[scriptr] Done installing. Starting...\n")

    _check_ffmpeg()


bootstrap()

# ── Imports (after bootstrap ensures they exist) ──────────────────────────────

import argparse
import re
import textwrap
from pathlib import Path
from datetime import timedelta

import yt_dlp
import whisper


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_timestamp(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    total = int(td.total_seconds())
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def format_reel_script(url: str, video_path: str, segments: list) -> str:
    WORDS_PER_LINE = 9
    INDENT = "       "
    header = (
        "\n"
        "════════════════════════════════════════════════════════\n"
        f"🎬  SOURCE : {url}\n"
        f"📁  FILE   : {video_path}\n"
        "════════════════════════════════════════════════════════\n"
    )

    body_lines = []
    for seg in segments:
        ts = fmt_timestamp(seg["start"])
        text = seg["text"].strip()
        if not text:
            continue

        words = text.split()
        lines = [" ".join(words[i : i + WORDS_PER_LINE]) for i in range(0, len(words), WORDS_PER_LINE)]

        first = f"[{ts}] {lines[0]}"
        rest = [f"{INDENT}{line}" for line in lines[1:]]
        block = "\n".join([first] + rest)
        body_lines.append(block)

    return header + "\n".join(body_lines) + "\n"


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:80] or "video"


# ── Core logic ────────────────────────────────────────────────────────────────

def download_video(url: str, output_dir: Path) -> Path | None:
    ydl_opts = {
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp may merge to .mp4 even if original ext differs
        path = Path(filename)
        if not path.exists():
            # try common fallback extensions
            for ext in ("mp4", "mkv", "webm"):
                alt = path.with_suffix(f".{ext}")
                if alt.exists():
                    return alt
        return path if path.exists() else None


def extract_audio(video_path: Path) -> Path:
    """Extract audio from video using ffmpeg."""
    audio_path = video_path.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vn", str(audio_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return audio_path


def transcribe_video(video_path: Path, model) -> list:
    segments, _ = model.transcribe(str(video_path))
    return [{"start": s.start, "text": s.text} for s in segments]


def process_url(url: str, index: int, output_dir: Path, model) -> bool:
    url = url.strip()
    if not url:
        return False

    print(f"\n[{index}] {url}")
    print("  ↳ Downloading...", end=" ", flush=True)

    try:
        video_path = download_video(url, output_dir)
    except Exception as e:
        print(f"FAILED\n  Error: {e}")
        return False

    if not video_path:
        print("FAILED\n  Could not locate downloaded file.")
        return False

    print(f"OK → {video_path.name}")
    print("  ↳ Extracting audio...", end=" ", flush=True)

    try:
        audio_path = extract_audio(video_path)
        print(f"OK → {audio_path.name}")
    except Exception as e:
        print(f"FAILED\n  Error: {e}")
        return False

    print("  ↳ Transcribing (this may take a moment)...", end=" ", flush=True)

    try:
        segments = transcribe_video(video_path, model)
    except Exception as e:
        print(f"FAILED\n  Error: {e}")
        return False

    print("OK")

    script = format_reel_script(url, str(video_path), segments)
    txt_path = video_path.with_suffix(".txt")
    txt_path.write_text(script, encoding="utf-8")
    print(f"  ↳ Script saved → {txt_path.name}")

    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download TikTok videos and transcribe them locally."
    )
    parser.add_argument(
        "urls",
        nargs="?",
        help="Comma-separated TikTok URLs (omit to be prompted)",
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--output",
        default="./downloads",
        help="Output folder (default: ./downloads)",
    )
    args = parser.parse_args()

    if args.urls:
        raw_urls = args.urls
    else:
        raw_urls = input("Paste TikTok URLs (comma-separated):\n> ").strip()

    urls = [u.strip() for u in raw_urls.split(",") if u.strip()]
    if not urls:
        print("No URLs provided. Exiting.")
        sys.exit(0)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel

    print(f"\n[scriptr] Loading Whisper '{args.model}' model...")
    model = WhisperModel(args.model, device="auto", compute_type="auto")
    print(f"[scriptr] Model ready. Processing {len(urls)} URL(s)...\n")
    print("─" * 56)

    results = []
    for i, url in enumerate(urls, start=1):
        ok = process_url(url, i, output_dir, model)
        results.append((url, ok))

    succeeded = sum(1 for _, ok in results if ok)
    failed = len(results) - succeeded

    print("\n" + "─" * 56)
    print(f"[scriptr] Done. {succeeded} succeeded, {failed} failed.")
    if failed:
        print("  Failed URLs:")
        for url, ok in results:
            if not ok:
                print(f"    • {url}")
    print(f"  Output folder: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
