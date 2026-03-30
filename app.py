#!/usr/bin/env python3
"""
app.py — Browser-based GUI for scriptr
Runs in your browser via Gradio (auto-installed on first run).
"""

import subprocess
import sys
import shutil
import re
from pathlib import Path

# ── Bootstrap Gradio ──────────────────────────────────────────────────────────

def _pip(pkg):
    print(f"Installing {pkg}…")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet",
         "--break-system-packages", pkg],
    )

try:
    import gradio as gr
except ImportError:
    _pip("gradio")
    import gradio as gr

# ── Dep helpers ───────────────────────────────────────────────────────────────

REQUIRED = {"yt_dlp": "yt-dlp", "faster_whisper": "faster-whisper"}

def _can_import(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False

def missing_deps():
    return [pkg for imp, pkg in REQUIRED.items() if not _can_import(imp)]

def has_ffmpeg():
    return shutil.which("ffmpeg") is not None

# ── Core logic ────────────────────────────────────────────────────────────────

def fmt_ts(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"

def format_script(url, video_path, segments):
    WORDS = 9
    PAD   = "       "
    lines = ["", "═" * 52, f"🎬  SOURCE : {url}", f"📁  FILE   : {video_path}", "═" * 52, ""]
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        words  = text.split()
        chunks = [" ".join(words[i:i+WORDS]) for i in range(0, len(words), WORDS)]
        block  = f"[{fmt_ts(seg['start'])}] {chunks[0]}"
        for c in chunks[1:]:
            block += f"\n{PAD}{c}"
        lines.append(block)
    return "\n".join(lines) + "\n"

def download_video(url, output_dir):
    import yt_dlp
    opts = {
        "outtmpl":     str(output_dir / "%(title)s.%(ext)s"),
        "format":      "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet":       True,
        "no_warnings": True,
        "noplaylist":  True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        if not path.exists():
            for ext in ("mp4", "mkv", "webm"):
                alt = path.with_suffix(f".{ext}")
                if alt.exists():
                    return alt
        return path if path.exists() else None

def extract_audio(video_path):
    """Extract audio from video using ffmpeg."""
    audio_path = video_path.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vn", str(audio_path)],
        capture_output=True, check=True
    )
    return audio_path

# ── Gradio actions ────────────────────────────────────────────────────────────

def install_deps():
    log = ""
    missing = missing_deps()
    if not missing:
        yield "✅ All packages already installed."
        return
    for pkg in missing:
        log += f"Installing {pkg}…\n"
        yield log
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--break-system-packages", pkg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            log += f"  ✓ {pkg} installed\n"
        except Exception as e:
            log += f"  ✗ {pkg} failed: {e}\n"
        yield log

    still = missing_deps()
    if not still:
        log += "\n✅ All packages installed! You can now press Start.\n"
    else:
        log += f"\n⚠️  Some failed: {still}\n"
    if not has_ffmpeg():
        log += "\n⚠️  ffmpeg still needed — run:  brew install ffmpeg\n"
    yield log


def run_batch(urls_text, model_name, out_dir):
    from faster_whisper import WhisperModel

    log = ""

    def emit(msg):
        nonlocal log
        log += msg + "\n"
        return log

    urls = [u.strip() for u in re.split(r"[,\n]+", urls_text) if u.strip()]
    if not urls:
        yield emit("⚠️  No URLs entered.")
        return

    missing = missing_deps()
    if missing:
        yield emit(f"⚠️  Missing packages: {', '.join(missing)}\nClick 'Install Packages' first.")
        return
    if not has_ffmpeg():
        yield emit("⚠️  ffmpeg not found.\nInstall it with:  brew install ffmpeg")
        return

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    yield emit(f"Loading Whisper '{model_name}' model…")
    try:
        model = WhisperModel(model_name, device="auto", compute_type="auto")
    except Exception as e:
        yield emit(f"✗ Failed to load model: {e}")
        return

    yield emit(f"Ready. Processing {len(urls)} video(s)…\n")
    results = []

    for i, url in enumerate(urls, 1):
        yield emit(f"[{i}/{len(urls)}]  {url}")
        yield emit("  ↳ Downloading…")
        try:
            vpath = download_video(url, out_path)
        except Exception as e:
            yield emit(f"  ✗ {e}\n")
            results.append(False)
            continue
        if not vpath:
            yield emit("  ✗ File not found after download\n")
            results.append(False)
            continue
        yield emit(f"  ✓ {vpath.name}")

        yield emit("  ↳ Extracting audio…")
        try:
            audio_path = extract_audio(vpath)
            yield emit(f"  ✓ Audio → {audio_path.name}")
        except Exception as e:
            yield emit(f"  ✗ {e}\n")
            results.append(False)
            continue

        yield emit("  ↳ Transcribing…")
        try:
            segments, _ = model.transcribe(str(vpath))
            segments = [{"start": s.start, "text": s.text} for s in segments]
        except Exception as e:
            yield emit(f"  ✗ {e}\n")
            results.append(False)
            continue

        txt = vpath.with_suffix(".txt")
        txt.write_text(format_script(url, str(vpath), segments), encoding="utf-8")
        yield emit(f"  ✓ Script → {txt.name}\n")
        results.append(True)

    ok, fail = sum(results), len(results) - sum(results)
    yield emit("─" * 52)
    yield emit(f"Done — {ok} succeeded, {fail} failed.")
    if ok:
        yield emit(f"Files saved to: {out_path.resolve()}")

# ── Audio extraction helper ──────────────────────────────────────────────────

def extract_audio_from_upload(video_file):
    if video_file is None:
        return None, "⚠️  No file selected."
    try:
        video_path = Path(video_file)
        audio_path = extract_audio(video_path)
        return str(audio_path), f"✅ Audio extracted: {audio_path.name}"
    except Exception as e:
        return None, f"✗ Error: {e}"

# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="scriptr") as demo:

    with gr.Tabs():
        with gr.Tab("TikTok Downloader"):
            gr.Markdown("# scriptr")
            gr.Markdown("Download & transcribe TikTok videos — locally, no API costs")

            urls_box = gr.Textbox(
                label="TikTok URLs",
                placeholder="Paste URLs here — one per line, or comma-separated",
                lines=6,
            )

            with gr.Row():
                model_dd = gr.Dropdown(
                    label="Whisper model",
                    choices=["tiny", "base", "small", "medium", "large"],
                    value="small",
                    scale=1,
                )
                out_dir = gr.Textbox(
                    label="Output folder",
                    value="./downloads",
                    scale=3,
                )

            with gr.Row():
                install_btn = gr.Button("⬇  Install Packages", variant="secondary", scale=1)
                start_btn   = gr.Button("▶  Start",            variant="primary",   scale=3)

            log_box = gr.Textbox(
                label="Output",
                lines=14,
                interactive=False,
            )

            install_btn.click(install_deps, outputs=log_box)
            start_btn.click(run_batch, inputs=[urls_box, model_dd, out_dir], outputs=log_box)

        with gr.Tab("Audio Extractor"):
            gr.Markdown("# Extract Audio")
            gr.Markdown("Pull audio from a local video file and save as WAV")

            video_upload = gr.File(
                label="Upload video file",
                file_types=["video"],
            )

            extract_audio_btn = gr.Button("▶  Extract Audio", variant="primary")

            with gr.Row():
                audio_output = gr.File(label="Download audio")
                status_output = gr.Textbox(label="Status", interactive=False)

            extract_audio_btn.click(
                extract_audio_from_upload,
                inputs=[video_upload],
                outputs=[audio_output, status_output],
            )

if __name__ == "__main__":
    missing = missing_deps()
    if missing:
        print(f"\n[scriptr] Missing packages: {', '.join(missing)}")
        print("[scriptr] Click 'Install Packages' in the UI to set them up.\n")
    if not has_ffmpeg():
        print("[scriptr] ⚠️  ffmpeg not found — brew install ffmpeg\n")

    demo.launch(
        inbrowser=True,
        theme=gr.themes.Base(primary_hue="purple", neutral_hue="slate"),
    )
