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

<p align="center">
  <b>🌐 语言 / Language：</b> <b>简体中文</b> &nbsp;|&nbsp; <a href="./README_EN.md"><b>English Documentation →</b></a>
</p>

---

## 📖 项目简介

**ASMR Whisper Studio** 是一款基于 `faster-whisper` (`CTranslate2` + `CUDA 12.8`) 与 `PySide6` 打造的现代化桌面端本地语音转录与字幕内嵌压制一体工作站。

针对日系耳语、同人音声（R18 ASMR）及影视作品中常见的**极微弱贴耳气声、环境白噪音干扰、模型无限复读幻觉**以及**大批量音视频文件低效排队**等痛点进行了全链路深度调优。软件支持 **100% 纯本地离线运行**，保护隐私且开箱即用。

---

## ✨ 核心特性

### 1. ⚡ 显存感知与多任务 GPU 并发交替转录
- **智能显存档位规划**：自动探测本机 NVIDIA 显卡总显存与实时空闲显存（以 `large-v2 / large-v3` 单路满载约 `6 GB` 为安全基准），自动匹配最佳并发路数：
  - `≤ 8GB 显存` ➔ **1 路并发**（单任务稳健模式）
  - `12GB 显存` ➔ **2 路并发**
  - `16GB 显存` ➔ **2 ~ 3 路动态并发**（自动检测剩余空闲显存充裕度动态分配）
  - `24GB 显存` ➔ **4 路并发**
  - `32GB 显存` ➔ **5 路并发**
  - `48GB ~ 96GB+ 专业工作站显卡` ➔ 最高支持 **16 路并发**，并提供滚动式手动档位切换。
- **独立显存实例池 (`WhisperModelPool`) 与动态工作窃取**：多文件并行推理，任意一路任务完成后 **0 等待立即接力下一个文件**，无需等待同批次其他任务结束；支持一键卸载全部模型实例清空显存。

### 2. 🖥️ 单大窗实时字幕预览与任务锁定切换
- **实时任务下拉选择栏**：保持清爽的单大窗流式字幕预览体验，顶部下拉栏实时标识所有任务的队列状态（`⏳ 等待中` / `⚡ 正在转录` / `✅ 已完成`）与已识别句数。
- **自动跟随与手动固定防跳转**：配备 `🔄 自动切换` / `📌 已固定当前` 状态按钮。当您手动下拉选择查看某一个任务时，系统自动固定当前视图，后台其他任务完成或新任务启动时**绝不强制跳转打断阅读**。

### 3. 🛡️ 日系 R18 ASMR 防幻觉与微弱耳语特化
- **全程热词锚定与多场景词库**：跨 30 秒滑窗全片持续注入先验语境，内置 **⚪ 空白 (通用预设)**、**🎧 R18 ASMR**、**🎬 AV** 词库预设，支持自定义预设增删改与外部文档（`.txt` / `.md` / `.json`）拖拽智能解析。
- **防复读与纯拟音净化**：支持隔离前文上下文依赖（彻底杜绝单字/短句死循环复读），智能过滤无实际台词的独立纯拟音/符号噪波整行，同时 **100% 原汁原味保留正常台词句内的喘息与语气词**。
- **Whisper 原生时间轴与 Silero VAD 按需微调**：默认关闭 VAD 以免误删微弱耳语；面对长静音较多的视频时，可按需开启并独立调节激活阈值、静音判定时长与前后缓冲。

### 4. 🎬 声学波形时间线、在线字幕微调与硬件加速压制
- **所见即所得 (WYSIWYG) 视听预览**：内置 16:9 视频/声学视窗与多轨动态音频波形时间线（支持 `Ctrl+滚轮` 缩放、重叠多行字幕同屏渲染、单击字幕直达片段、单句循环重播）。
- **在线台词与时间轴微调**：支持关键词实时搜索过滤、双击在线毫秒级微调时间轴与台词、右键增删字幕行及 `Ctrl+S` 原位回写保存（微调时间轴时**无损保留 ASS 逐词卡拉 OK `\k` 特效标签**）。
- **多格式导出与批量压制队列**：支持一键导出 `SRT` / `ASS (含逐词卡拉OK)` / `VTT` / `TXT`；提供 **FFmpeg NVENC 硬件加速硬字幕压制** 与 **MP4/MKV 软字幕极速无损合流**，支持多视频批量入队自动连续压制。

---

## 📦 安装与快速上手

### 方式一：安装包开箱即用（推荐大众用户）
1. 前往 [**Releases 发布页**](https://github.com/zzcc222/ASMR-Whisper-Studio/releases) 下载最新版本的 **`ASMR-Whisper-Studio-Setup(3.4).exe`** 并安装（已内置精简 Python 3.12 运行时、CUDA 12.8 核心加速库与 FFmpeg 工具链，无需配置系统环境变量）。
2. 将 CTranslate2 格式的 Whisper 模型文件夹（如 `faster-whisper-large-v2`、`faster-whisper-large-v3` 或 `faster-whisper-large-v3-turbo`）放入软件安装目录下的 `Model/` 文件夹中。
3. 启动 **ASMR Whisper Studio**，拖入音频或视频文件即可开始转录与字幕压制。

### 方式二：从源码运行（开发者环境）
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

## 🗂️ 项目架构

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
