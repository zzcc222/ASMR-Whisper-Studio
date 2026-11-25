# 🎙️ ASMR Whisper Studio

<p align="center">
  <b>专为日系同人音声（ASMR）与影视打造的本地 AI 语音识别转录与字幕压制工作站</b><br>
  <i>High-Performance Local AI Speech-to-Text & Hardsub/Softsub Studio for Japanese ASMR & Videos</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v3.4.0-8B5CF6?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0078D6?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Engine-CTranslate2%20%2B%20CUDA%2012.8-76B900?style=flat-square" alt="Engine">
  <img src="https://img.shields.io/badge/UI-PySide6%20(Qt6)-41CD52?style=flat-square" alt="UI">
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square" alt="License">
</p>

---

## 🇨🇳 项目简介

**ASMR Whisper Studio** 是一款基于 `faster-whisper` (`CTranslate2` + `CUDA 12.8`)、并通过 `PySide6` 打造的现代化桌面端本地语音转录与字幕内嵌压制一体工作站。

针对日系耳语、同人音声（R18 ASMR）及影视作品中常见的**极微弱贴耳气声、环境白噪音干扰、模型无限复读幻觉**以及**大批量音频/视频文件低效排队**等痛点进行了全链路深度调优。完全离线运行，保护隐私且开箱即用。

### ✨ 核心亮点

#### 1. ⚡ 显存感知与多任务 GPU 并发交替转录
- **智能显存档位规划**：自动探测本机 NVIDIA 显卡型号与总/空闲显存容量（以 `large-v2 / large-v3` 单路满载约 `6 GB` 为安全基准），自动匹配最佳并发路数（`8GB→1路`、`12GB→2路`、`16GB→2~3路动态感知`、`24GB→4路`、`32GB→5路`，最高支持 `96GB+` 专业工作站显卡 **16 路并发**）。
- **独立显存实例池 (`WhisperModelPool`) 与动态工作窃取**：多文件并行推理，任一任务完成后 0 等待立即拉取队列下一文件交替接力，榨干大显存显卡吞吐性能；任务结束后支持一键释放全部显存。

#### 2. 🖥️ 单大窗实时字幕预览与任务锁定切换
- **实时任务下拉选择栏**：单窗口沉浸式流式展示实时识别台词，顶部下拉栏实时标识各任务的队列状态（`⏳ 等待中` / `⚡ 正在转录` / `✅ 已完成`）与台词句数。
- **自动跟随与手动固定防跳转**：内置 `🔄 自动切换` / `📌 已固定当前` 切换按钮。当手动选择查看某一正在转录或已完成的任务字幕时，自动进入固定锁定状态，后台其他任务完成或新任务启动时界面绝不乱跳。

#### 3. 🛡️ 日系 R18 ASMR 防幻觉与微弱耳语特化
- **全程热词锚定与多场景词库**：跨 30 秒滑窗全片持续注入先验语境，内置 **⚪ 空白 (通用预设)**、**🎧 R18 ASMR**、**🎬 AV** 预设，并支持自定义预设管理与文档智能提取导入。
- **防复读与纯拟音净化**：支持隔离前文上下文依赖（杜绝单字/短句死循环复读），智能过滤无实际台词的独立纯拟音/符号噪波行，同时 100% 保留正常台词句内的喘息与语气词。
- **Whisper 原生时间轴与 Silero VAD 按需微调**：默认关闭 VAD 以免误删微弱耳语；针对长静音较多的视频，可按需开启并微调 Silero VAD 激活阈值、静音判定与前后缓冲。

#### 4. 🎬 声学波形时间线、在线字幕微调与硬件加速压制
- **所见即所得 (WYSIWYG) 视听预览**：内置 16:9 视频/声学视窗与多轨动态音频波形时间线（支持 `Ctrl+滚轮` 缩放、重叠双语/多行字幕同屏渲染、单击字幕跳转、单句重播）。
- **在线台词与时间轴微调**：支持关键词实时检索过滤、双击在线毫秒级微调时间轴与台词、增删字幕行及 `Ctrl+S` 原位回写保存（微调时间轴时无损保留 ASS 逐词卡拉 OK `\k` 标签）。
- **多格式导出与批量压制队列**：支持一键导出 `SRT` / `ASS (含逐词卡拉OK)` / `VTT` / `TXT`；支持 **FFmpeg NVENC 硬件加速硬字幕压制** 与 **MP4/MKV 软字幕极速无损合流**，并支持多视频批量排队自动接续压制。

---

### 📦 安装与使用说明

#### 方式一：安装包开箱即用（推荐）
1. 前往 [Releases](https://github.com/zzcc222/ASMR-Whisper-Studio/releases) 页面下载最新版本的 **`ASMR-Whisper-Studio-Setup(3.4).exe`** 并运行安装（已内置精简 Python 3.12 运行时、CUDA 12.8 核心加速库与 FFmpeg 工具链，无需配置系统环境变量）。
2. 将 CTranslate2 格式的 Whisper 模型文件夹（如 `faster-whisper-large-v2`、`faster-whisper-large-v3` 或 `faster-whisper-large-v3-turbo`）放入软件安装目录下的 `Model/` 文件夹中。
3. 双击桌面图标启动软件，拖入音频或视频文件即可开始离线转录与字幕压制。

#### 方式二：从源码运行（开发者环境）
```powershell
# 1. 克隆仓库
git clone https://github.com/zzcc222/ASMR-Whisper-Studio.git
cd ASMR-Whisper-Studio

# 2. 安装依赖 (需 Python 3.10 ~ 3.12 与支持 CUDA 12.x 的 NVIDIA 显卡驱动)
pip install -r requirements.txt

# 3. 将模型放入 ./Model 目录后启动主程序
python main.py
```

---

### 🗂️ 项目架构

```text
ASMR-Whisper-Studio/
├── main.py                         # 程序主入口 (单实例 IPC 通信、独立极光开屏进程与主窗体装配)
├── transcriber.py                  # 核心推理引擎顶层门面
├── core/                           # 后端核心层 (与 UI 彻底解耦)
│   ├── config.py                   # 转录参数模型与双路配置持久化 (本地便携 + %APPDATA%)
│   ├── concurrency_planner.py      # GPU 显存实时探测与 1~16 路并发任务规划器
│   ├── model_pool.py               # 多实例 WhisperModel 显存池与动态扩容/OOM 降级管理
│   ├── transcriber_engine.py       # Whisper 推理流水线主引擎
│   ├── cuda_utils.py               # CUDA 12 动态链接库路径注入与环境探测
│   ├── media/                      # PyAV / FFmpeg 媒体规格探测、动态波形提取与字幕压制构建
│   ├── nlp/                        # 日语防幻觉清洗、R18 独立拟音过滤与提示词文档解析
│   ├── subtitle/                   # SRT / ASS (Karaoke) / VTT / TXT 解析、导出与智能同名配对
│   └── utils/                      # 多编码文本安全读写工具
├── ui/                             # 前端表现层 (PySide6 / Qt6 Apple 灵动浅色风格)
│   ├── main_window.py              # 主窗口容器与跨标签页协同
│   ├── sub_burner_tab.py           # 字幕压制与声学预览工作台容器
│   ├── dialogs.py                  # 提示词解析弹窗与单句字幕在线微调弹窗
│   ├── views/                      # 业务视图子面板 (转录队列/模型配置/进度监控/播放器/压制队列)
│   ├── controllers/                # 业务协调控制器 (转录调度/字幕预览缓冲/压制执行/配置同步/系统托盘)
│   ├── components/                 # 自定义高帧率交互控件 (折叠抽屉/音频时间线/并发预览框/礼花动效)
│   └── workers/                    # QThread 后台工作线程 (多流并发转录/FFmpeg 压制/波形提取/GPU 检测)
├── scripts/                        # Inno Setup 自动化安装包编译与图标注入脚本
└── tools/                          # 依赖完整性诊断与前端/日志/真实视频端到端验证套件
```

---

## 🇬🇧 English Overview

**ASMR Whisper Studio** is a modern, self-contained desktop speech transcription and subtitle burning workstation built with `faster-whisper` (`CTranslate2` + `CUDA 12.8`) and `PySide6` (`Qt6`).

Engineered specifically for Japanese ASMR, Doujin voice works, and R18 videos, it solves common challenges such as ultra-soft binaural whispers, background noise hallucinations, infinite repetition loops, and underutilized GPU VRAM during batch transcription.

### ✨ Key Features

- **⚡ Multi-Stream GPU Concurrent Transcription**: Automatically detects NVIDIA GPU VRAM tiers (`8GB→1`, `12GB→2`, `16GB→2~3 dynamic`, `24GB→4`, `32GB→5`, up to **16 concurrent tasks** for `96GB+` workstation GPUs). Powered by `WhisperModelPool` and dynamic work-stealing so finished slots immediately pick up the next file without waiting.
- **🖥️ Single-Window Live Subtitle Preview & Task Pinning**: Features a live task selector dropdown and an **Auto-Follow (`🔄`) / Pinned (`📌`)** toggle. Manually selecting a task pins the preview so newly started or completed background tasks never cause unexpected jumps.
- **🛡️ Japanese ASMR Anti-Hallucination & Whisper Tuning**: Persistent hotword anchoring across all 30s sliding windows, context isolation to prevent repetition loops, standalone moan/noise line filtering (while preserving in-dialogue breaths), and Whisper native segment boundaries.
- **🎬 Waveform Timeline, Inline Subtitle Editor & NVENC Burner**: Real-time 16:9 WYSIWYG video/audio preview, interactive multi-track waveform timeline, inline subtitle timestamp/text editing (with lossless ASS Karaoke `\k` tag preservation), and hardware-accelerated **FFmpeg NVENC hardsub burning** & **MP4/MKV softsub muxing**.

### 🚀 Quick Start (Installer)
1. Download **`ASMR-Whisper-Studio-Setup(3.4).exe`** from [Releases](https://github.com/zzcc222/ASMR-Whisper-Studio/releases) and install (includes bundled Python 3.12 runtime, CUDA 12.8 libraries, and FFmpeg).
2. Drop your CTranslate2 Whisper model folder (e.g., `faster-whisper-large-v2`, `faster-whisper-large-v3`, or `faster-whisper-large-v3-turbo`) into the `Model/` directory inside the installation folder.
3. Launch **ASMR Whisper Studio** and drag & drop your audio or video files to start transcribing.
