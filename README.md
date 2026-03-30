# scriptr

Download TikTok videos and transcribe them locally with OpenAI's Whisper — no API costs, everything runs on your machine.

## Features

- 🎬 **Download** TikTok videos directly
- 🎙️ **Transcribe** audio using Whisper (OpenAI's speech-to-text model)
- 📝 **Generate scripts** with timestamps
- 🖥️ **Two interfaces**: CLI (fast) or Web GUI (user-friendly)
- ⚡ **No API costs** — everything runs locally
- 🎯 **Batch processing** — handle multiple videos at once

## Installation

### Requirements

- Python 3.9+
- `ffmpeg` (for audio extraction)

### Install ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
```bash
choco install ffmpeg
```

### Get the code

```bash
git clone https://github.com/Project2Studios/tik-tok-scriptr.git
cd tik-tok-scriptr
```

## Usage

### Option 1: Web GUI (Easiest)

Start the browser-based interface:

```bash
python app.py
```

This opens a Gradio interface in your browser with:
- **TikTok Downloader tab**: Paste URLs, select Whisper model, download & transcribe
- **Audio Extractor tab**: Extract audio from local video files

The app will auto-install missing dependencies when you click "Install Packages".

### Option 2: Command Line

For quick batch processing or scripting:

```bash
python scriptr.py "url1,url2,url3" --model small --output ./downloads
```

Or enter URLs interactively:
```bash
python scriptr.py
# Then paste URLs when prompted
```

**Options:**
- `--model`: Whisper model size (default: `small`)
  - `tiny` — fastest, lowest quality
  - `base` — balanced
  - `small` — recommended default
  - `medium` — higher quality
  - `large` — best quality, slowest
- `--output`: Output folder (default: `./downloads`)

## Whisper Models

Larger models are more accurate but slower and need more VRAM:

| Model | Speed | Quality | VRAM |
|-------|-------|---------|------|
| tiny | ⚡⚡⚡ | ⭐ | ~1GB |
| base | ⚡⚡ | ⭐⭐ | ~1GB |
| small | ⚡ | ⭐⭐⭐ | ~2GB |
| medium | 🐢 | ⭐⭐⭐⭐ | ~5GB |
| large | 🐢🐢 | ⭐⭐⭐⭐⭐ | ~10GB |

## Output

Each processed video generates:
1. **Downloaded video** — MP4 file
2. **Audio file** — WAV extracted from the video
3. **Script file** — TXT with timestamps and transcribed text

Example script output:
```
════════════════════════════════════════════════════════
🎬  SOURCE : https://www.tiktok.com/...
📁  FILE   : video_title.mp4
════════════════════════════════════════════════════════

[0:05] This is the transcribed text from your video broken
       into readable chunks with timestamps
[0:12] Each timestamp shows when that line was spoken
```

## Troubleshooting

**ffmpeg not found:**
Make sure ffmpeg is installed and in your PATH. Test with:
```bash
ffmpeg -version
```

**Package installation fails:**
Try installing manually:
```bash
pip install yt-dlp faster-whisper
```

**TikTok URL not downloading:**
TikTok's API changes frequently — try updating yt-dlp:
```bash
pip install --upgrade yt-dlp
```

**Out of memory (OOM) errors:**
- Use a smaller model: `--model tiny` or `--model base`
- Close other applications to free up RAM
- On the web UI, select a smaller model before processing

## How it Works

1. **Download** — Uses `yt-dlp` to download the best available video quality
2. **Extract Audio** — Uses `ffmpeg` to pull audio from the video
3. **Transcribe** — Uses OpenAI's Whisper to convert speech to text
4. **Format** — Generates a readable script with timestamps

## License

MIT

## Contributing

Found a bug or have a feature request? Open an issue or submit a pull request!
