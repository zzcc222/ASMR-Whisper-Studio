# 🎙️ ASMR Whisper Studio

<p align="center">
  <b>High-Performance Local AI Speech-to-Text & Hardsub/Softsub Studio for Japanese ASMR & Videos</b><br>
  <i>专为日系同人音声（ASMR）与影视打造的本地 AI 语音识别转录与字幕压制工作站</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v3.4.0-8B5CF6?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0078D6?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Engine-CTranslate2%20%2B%20CUDA%2012.8-76B900?style=flat-square" alt="Engine">
  <img src="https://img.shields.io/badge/UI-PySide6%20(Qt6)-41CD52?style=flat-square" alt="UI">
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square" alt="License">
</p>

<p align="center">
  <b>🌐 Language / 语言：</b> <a href="./README.md"><b>← 简体中文文档</b></a> &nbsp;|&nbsp; <b>English</b>
</p>

---

## 📖 Overview

**ASMR Whisper Studio** is a modern, self-contained desktop speech transcription and subtitle burning workstation built with `faster-whisper` (`CTranslate2` + `CUDA 12.8`) and `PySide6` (`Qt6`).

Engineered specifically for Japanese ASMR, Doujin voice works (R18 ASMR), and videos, it addresses common pain points such as **ultra-soft binaural whispers, ambient noise interference, infinite repetition hallucinations**, and **underutilized GPU VRAM during multi-file batch transcription**. It runs **100% offline locally**, ensuring complete privacy and out-of-the-box convenience.

---

## ✨ Key Features

### 1. ⚡ VRAM-Aware Multi-Stream GPU Concurrent Transcription
- **Intelligent VRAM Tier Planning**: Automatically probes your NVIDIA GPU's total and free VRAM (using ~`6 GB` per full `large-v2 / large-v3` instance as a safe baseline) and assigns optimal concurrency:
  - `≤ 8GB VRAM` ➔ **1 Concurrent Task** (VRAM-saving single stream)
  - `12GB VRAM` ➔ **2 Concurrent Tasks**
  - `16GB VRAM` ➔ **2–3 Dynamic Concurrent Tasks** (automatically scales based on real-time available free VRAM)
  - `24GB VRAM` ➔ **4 Concurrent Tasks**
  - `32GB VRAM` ➔ **5 Concurrent Tasks**
  - `48GB – 96GB+ Workstation GPUs` ➔ Up to **16 Concurrent Tasks** via a scrollable selector.
- **Dedicated `WhisperModelPool` & Dynamic Work-Stealing**: Runs independent model instances across parallel CUDA streams. Whenever any file finishes, its worker slot immediately picks up the next queued file with zero idle waiting. Supports one-click VRAM unloading after completion.

### 2. 🖥️ Single-Window Live Subtitle Preview & Task Pinning
- **Real-Time Task Selector Dropdown**: Preserves a clean, distraction-free single-window live subtitle view while allowing instant switching between queued, active (`⚡ Transcribing`), and finished (`✅ Completed`) files.
- **Auto-Follow & Manual Pinning**: Equipped with an **Auto-Follow (`🔄`) / Pinned (`📌`)** toggle button. Manually selecting a task automatically pins the view so newly started or completed background tasks never cause unexpected jumps.

### 3. 🛡️ Japanese R18 ASMR Anti-Hallucination & Whisper Tuning
- **Full-Audio Hotword Anchoring & Presets**: Continuously injects domain context across all 30-second sliding windows. Includes built-in **⚪ Blank (General)**, **🎧 R18 ASMR**, and **🎬 AV** vocabulary presets, plus custom preset management and smart prompt extraction from `.txt` / `.md` / `.json` files.
- **Repetition Suppression & Standalone Moan Filtering**: Isolates cross-segment context (`condition_on_previous_text=False`) to eliminate infinite repetition loops, and filters out dialogue-free standalone moan/noise lines while **preserving 100% of in-dialogue breaths and vocal nuances**.
- **Whisper Native Segmentation & Configurable Silero VAD**: Keeps VAD off by default to protect delicate whispers, with optional fine-grained sliders for VAD activation threshold, minimum silence duration, and speech padding.

### 4. 🎬 Acoustic Waveform Timeline, Inline Subtitle Editor & NVENC Burner
- **16:9 WYSIWYG Preview & Multi-Track Timeline**: Built-in media player with live subtitle overlay and an interactive audio waveform timeline (`Ctrl + Wheel` zoom, overlapping multi-line subtitle rendering, click-to-seek, and single-line replay).
- **Inline Subtitle & Timestamp Editing**: Real-time keyword search filtering, double-click millisecond timestamp & text fine-tuning, row insertion/deletion, and `Ctrl+S` in-place saving (with **lossless preservation of ASS Karaoke `\k` tags** when adjusting timestamps).
- **Multi-Format Export & Batch Burning Queue**: Exports `SRT`, `ASS (with word-level Karaoke)`, `VTT`, and `TXT`. Supports **FFmpeg NVENC hardware-accelerated hardsub burning** and **lossless MP4/MKV softsub muxing** with automated batch queue processing.

---

## 📦 Installation & Quick Start

### Option 1: Standalone Installer (Recommended)
1. Download the latest **`ASMR-Whisper-Studio-Setup(3.4).exe`** from the [**Releases**](https://github.com/zzcc222/ASMR-Whisper-Studio/releases) page and run the installer (bundles a streamlined Python 3.12 runtime, CUDA 12.8 libraries, and FFmpeg — no system PATH setup required).
2. Place your CTranslate2 Whisper model folder (e.g., `faster-whisper-large-v2`, `faster-whisper-large-v3`, or `faster-whisper-large-v3-turbo`) inside the `Model/` folder in the installation directory.
3. Launch **ASMR Whisper Studio** and drag & drop your audio or video files to start transcribing.

### Option 2: Run from Source (Developer Environment)
```powershell
# 1. Clone the repository
git clone https://github.com/zzcc222/ASMR-Whisper-Studio.git
cd ASMR-Whisper-Studio

# 2. Install dependencies (Python 3.10–3.12 and NVIDIA GPU with CUDA 12.x driver recommended)
pip install -r requirements.txt

# 3. Place your Faster-Whisper model in ./Model and start the application
python main.py
```

---

## 🗂️ Project Architecture

```text
ASMR-Whisper-Studio/
├── main.py                         # Application entry point (Single-instance IPC, 60 FPS splash process & window bootstrap)
├── transcriber.py                  # Top-level facade for the transcription engine
├── core/                           # Backend core layer (strictly decoupled from UI)
│   ├── config.py                   # Transcription config dataclass & dual-path persistence (portable + %APPDATA%)
│   ├── concurrency_planner.py      # Real-time GPU VRAM probing & 1–16 way concurrency planner
│   ├── model_pool.py               # Multi-instance WhisperModel pool with lazy scaling & OOM fallback
│   ├── transcriber_engine.py       # Main Whisper transcription pipeline engine
│   ├── cuda_utils.py               # CUDA 12 DLL path injection & hardware diagnostics
│   ├── media/                      # PyAV / FFmpeg media probing, waveform extraction & FFmpeg burner command builder
│   ├── nlp/                        # Japanese anti-hallucination cleaning, R18 moan filtering & prompt parser
│   ├── subtitle/                   # SRT / ASS (Karaoke) / VTT / TXT parser, exporter & smart subtitle matcher
│   └── utils/                      # Multi-encoding safe text I/O utilities
├── ui/                             # Frontend presentation layer (PySide6 / Qt6 Apple-inspired light theme)
│   ├── main_window.py              # Main window container & cross-tab coordination
│   ├── sub_burner_tab.py           # Subtitle burner & acoustic preview workstation tab
│   ├── dialogs.py                  # Prompt recognizer dialog & inline subtitle edit dialog
│   ├── views/                      # Modular view panels (Queue, Config, Progress, Player, Burner Queue, Header/Footer)
│   ├── controllers/                # Controllers (TranscribeRunner, SubtitlePreviewBuffer, BurnerRunner, SettingsSync, Tray)
│   ├── components/                 # Custom interactive widgets (CollapsibleCard, AudioTimeline, ConcurrentSubtitleView)
│   └── workers/                    # QThread background workers (Concurrent transcribe, FFmpeg burner, Waveform, GPU detector)
├── scripts/                        # Inno Setup automated installer builder & uninstaller icon patcher
└── tools/                          # Dependency diagnostics & automated end-to-end verification suite
```
