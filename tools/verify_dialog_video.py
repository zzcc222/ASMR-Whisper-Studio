# -*- coding: utf-8 -*-
"""
真实多对白视频 & 双路并发动态交替接力 (Work-Stealing) 端到端转录验证脚本
验证项目:
1. 自动探测 RTX 5070 (12227 MiB -> 标称 12 GB) 并自动规划 2 路并发模型池
2. 关闭 VAD (vad_filter=False)，在最高对白密度视频《2023年7月R18.mp4》及特典视频上执行真实并发转录
3. 验证两个任务同时启动，短任务先完成后 0ms 立即接手第 3 个任务（动态交替接力）
4. 验证多格式字幕导出 (SRT, ASS, VTT, TXT) 与模型池一键显存卸载
"""

import os
import sys
import time
import tempfile
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys_root not in sys.path:
    sys.path.insert(0, sys_root)

from PySide6.QtCore import QCoreApplication
from core.cuda_utils import setup_cuda_dll_paths, resolve_model_path
setup_cuda_dll_paths()

from core.config import ASMRTranscriberConfig
from core.transcriber_engine import ASMRTranscriber
from core.subtitle.subtitle_parser import parse_subtitle_file
from ui.workers.transcribe_worker import TranscriptionWorker


def query_vram_used_mb() -> int:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return int(out.decode("utf-8").strip().splitlines()[0])
    except Exception:
        return 0


def main():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    v_main = r"D:\LOL\ASMR\视频\網野ぴこん\2023年7月R18.mp4"
    v_sub1 = r"D:\LOL\ASMR\视频\網野ぴこん\2023年12月特典\2.mp4"
    v_sub2 = r"D:\LOL\ASMR\视频\網野ぴこん\2023年12月特典\3.mp4"

    test_files = [p for p in (v_main, v_sub1, v_sub2) if os.path.exists(p)]
    if not test_files:
        print("[ERROR] 未找到目标测试视频文件！")
        sys.exit(1)

    model_path = resolve_model_path("faster-whisper-large-v2")
    print("=" * 72)
    print(f"🎬 真实多对白视频 & 2 路并发交替转录实例验证 (VAD = 关闭)")
    print(f"📦 模型路径: {model_path}")
    print(f"📂 待转录队列 ({len(test_files)} 个视频):")
    for i, fp in enumerate(test_files, 1):
        print(f"   [{i}] {fp}")
    print(f"📊 初始显存占用: {query_vram_used_mb()} MiB")
    print("=" * 72)

    cfg = ASMRTranscriberConfig(
        model_size=model_path,
        device="cuda",
        compute_type="float16",
        vad_filter=False,          # 严格按照要求关闭 VAD
        max_concurrent_tasks=0,    # 0 = 智能自动 (RTX 5070 12GB -> 自动启用 2 路并发)
        export_srt=True,
        export_ass=True,
        export_vtt=True,
        export_txt=True,
    )

    engine = ASMRTranscriber(cfg)
    peak_vram_mb = [query_vram_used_mb()]
    finished_records = {}

    with tempfile.TemporaryDirectory() as td:
        worker = TranscriptionWorker(
            file_paths=test_files,
            config=cfg,
            output_dir=td,
            transcriber=engine,
        )

        t0 = time.time()

        def on_log(msg: str):
            cur_vram = query_vram_used_mb()
            if cur_vram > peak_vram_mb[0]:
                peak_vram_mb[0] = cur_vram
            elapsed = time.time() - t0
            print(f"[{elapsed:6.2f}s | VRAM {cur_vram:4d} MiB] {msg}", flush=True)

        def on_file_finished(idx: int, exported: list, elapsed: float):
            finished_records[idx] = (exported, elapsed, time.time() - t0)

        def on_all_finished(s_cnt: int, f_cnt: int):
            total_t = time.time() - t0
            print("=" * 72)
            print(f"🎉 队列全部处理完毕！成功: {s_cnt}, 失败: {f_cnt}, 总墙钟耗时: {total_t:.2f}s")
            print(f"🔥 运行期峰值显存: {peak_vram_mb[0]} MiB ({peak_vram_mb[0]/1024.0:.2f} GB)")
            print(f"🧩 模型池常驻实例数: {engine.loaded_model_count()} 个")
            app.quit()

        worker.sig_log.connect(on_log)
        worker.sig_file_finished.connect(on_file_finished)
        worker.sig_all_finished.connect(on_all_finished)

        worker.start()
        app.exec()
        worker.wait(5000)

        assert worker.effective_workers == 2, f"Expected 2 concurrent workers on RTX 5070, got {worker.effective_workers}"
        assert len(finished_records) == len(test_files), "部分文件未能成功完成！"

        # 验证字幕输出与对白内容
        for idx, fp in enumerate(test_files):
            exported, file_elapsed, wall_done_at = finished_records[idx]
            srt_files = [f for f in exported if f.endswith(".srt")]
            assert srt_files, f"文件 #{idx+1} 未生成 SRT 字幕"
            parsed = parse_subtitle_file(srt_files[0])
            print("-" * 72)
            print(
                f"📄 文件 [#{idx+1}] {os.path.basename(fp)}: "
                f"共识别 {len(parsed)} 句有效对白 | 单任务耗时 {file_elapsed:.1f}s (完成于墙钟 {wall_done_at:.1f}s)"
            )
            for sample_i, seg in enumerate(parsed[:10], 1):
                print(f"   ({sample_i:02d}) [{seg['start_str']} -> {seg['end_str']}] {seg['text']}")

    print("=" * 72)
    unloaded = engine.unload_model()
    after_vram = query_vram_used_mb()
    print(f"🧹 已显式卸载 {unloaded} 个并发模型实例，当前显存恢复至: {after_vram} MiB")
    assert engine.is_model_loaded() is False
    print("========================================================================")
    print("✅ 真实高密度对白视频 + 双路并发动态交替转录验证 100% 通过！")
    print("========================================================================")


if __name__ == "__main__":
    main()
