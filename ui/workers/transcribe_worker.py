# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 异步多路并发推理后台工作线程 (ui.workers.transcribe_worker)
- 支持基于显卡总显存与实时空闲显存的 1~5 路多模型实例并发调度
- 采用动态交替接力 (Work-Stealing) 队列：任意一个任务先完成，立即无缝接手下一个等待文件，绝不互相等候
- 具备同目录重名文件原子防覆盖锁、运行期 CUDA OOM 自动收缩重试与全局一键秒停
"""

import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QThread, Signal

from core.concurrency_planner import plan_effective_concurrency
from core.config import ASMRTranscriberConfig
from core.nlp.prompt_parser import summarize_prompt
from core.transcriber_engine import ASMRTranscriber


class TranscriptionWorker(QThread):
    """异步多任务交替并发转录工作线程，支持复用与扩容 transcriber 模型池"""

    sig_file_started = Signal(int, str)                # (file_index, file_path)
    sig_progress = Signal(int, float, str)             # (file_index, pct, msg)
    sig_segment = Signal(int, float, float, str)       # (file_index, start, end, text)
    sig_segments_refined = Signal(int, list)           # (file_index, refined_segments)
    sig_file_finished = Signal(int, list, float)       # (file_index, exported_files, elapsed)
    sig_file_failed = Signal(int, str)                 # (file_index, error_msg)
    sig_all_finished = Signal(int, int)                # (success_count, fail_count)
    sig_log = Signal(str)                              # (log_message)

    def __init__(
        self,
        file_paths: List[str],
        config: ASMRTranscriberConfig,
        output_dir: Optional[str] = None,
        transcriber: Optional[ASMRTranscriber] = None,
    ):
        super().__init__()
        self.file_paths = list(file_paths or [])
        self.config = config
        self.output_dir = output_dir
        if transcriber is not None:
            self.transcriber = transcriber
            self.transcriber.config = self.config
        else:
            self.transcriber = ASMRTranscriber(config=self.config)
        self._is_stopped = False
        self._state_lock = threading.Lock()
        self._name_lock = threading.Lock()
        self.effective_workers: int = 1

    def stop(self):
        """请求中止所有正在进行及排队中的转录任务"""
        self._is_stopped = True
        self.transcriber.cancel()

    def _allocate_disambiguated_name(
        self,
        file_path: str,
        used_base_names: set,
    ) -> Tuple[str, str, bool]:
        """线程安全地计算输出目录与防重名覆盖基准文件名"""
        filename = os.path.basename(file_path)
        target_output_dir = self.output_dir if self.output_dir else os.path.dirname(os.path.abspath(file_path))
        norm_output_dir = os.path.normcase(os.path.abspath(target_output_dir))
        raw_base_name = os.path.splitext(filename)[0]

        with self._name_lock:
            disambiguated_name = raw_base_name
            counter = 1
            while (norm_output_dir, disambiguated_name) in used_base_names:
                disambiguated_name = f"{raw_base_name}_{counter}"
                counter += 1
            used_base_names.add((norm_output_dir, disambiguated_name))

        return target_output_dir, disambiguated_name, (disambiguated_name != raw_base_name)

    def _format_sub_log(self, msg: str, idx: int, is_concurrent: bool) -> str:
        """格式化子步骤树状日志，多路并发时自动附带 [#序号] 标签以区分任务流"""
        line = msg.strip()
        if line.startswith("-> "):
            line = line[3:].strip()
        elif line.startswith("->"):
            line = line[2:].strip()
        elif line.startswith("- "):
            line = line[2:].strip()

        prefix_tag = f"[#{idx + 1}] " if is_concurrent else ""
        if line.startswith("├─") or line.startswith("└─"):
            branch = line[:2]
            rest = line[2:].strip()
            return f"  {branch} {prefix_tag}{rest}"
        return f"  ├─ {prefix_tag}{line}"

    def _process_single_item(
        self,
        idx: int,
        file_path: str,
        total_files: int,
        used_base_names: set,
        model_instance: Optional[Any],
        is_concurrent: bool,
    ) -> str:
        """
        处理单个文件的完整生命周期，返回状态码:
        'success' | 'cancelled' | 'failed' | 'oom_retry'
        """
        filename = os.path.basename(file_path)
        self.sig_file_started.emit(idx, file_path)
        self.sig_log.emit(f"[{idx + 1}/{total_files}] 开始转录文件: {filename}")

        def on_prog(pct: float, msg: str):
            self.sig_progress.emit(idx, pct, msg)

        def on_seg(seg: dict):
            self.sig_segment.emit(idx, seg["start"], seg["end"], seg["text"])

        def on_log(msg: str):
            self.sig_log.emit(self._format_sub_log(msg, idx, is_concurrent))

        target_output_dir, disambiguated_name, was_renamed = self._allocate_disambiguated_name(
            file_path, used_base_names
        )
        if was_renamed:
            self.sig_log.emit(
                self._format_sub_log(
                    f"⚠️ 检测到同目录下重名文件，自动对当前字幕基准名进行防覆盖编号: {disambiguated_name}",
                    idx,
                    is_concurrent,
                )
            )

        try:
            call_kwargs = dict(
                audio_path=file_path,
                output_dir=target_output_dir,
                output_base_name=disambiguated_name,
                progress_callback=on_prog,
                segment_callback=on_seg,
                log_callback=on_log,
            )
            if model_instance is not None:
                call_kwargs["model_instance"] = model_instance
                call_kwargs["reset_cancel_on_start"] = False

            try:
                result = self.transcriber.transcribe(**call_kwargs)
            except TypeError:
                # 兼容外部自定义/单元测试 Mock 的精简 transcribe 签名
                call_kwargs.pop("model_instance", None)
                call_kwargs.pop("reset_cancel_on_start", None)
                result = self.transcriber.transcribe(**call_kwargs)

            if result.get("status") == "cancelled" or self._is_stopped:
                self.sig_log.emit(self._format_sub_log(f"⚠️ 文件 {filename} 转录已取消。", idx, is_concurrent))
                self.sig_file_failed.emit(idx, "已取消")
                return "cancelled"

            refined_segments = result.get("segments", [])
            if refined_segments is not None:
                self.sig_segments_refined.emit(idx, refined_segments)
            exported = result.get("exported_files", [])
            elapsed = result.get("elapsed", 0.0)
            self.sig_file_finished.emit(idx, exported, elapsed)
            exported_names = ", ".join([os.path.basename(f) for f in exported])
            self.sig_log.emit(f"✅ 文件 {filename} 转录成功！生成字幕: {exported_names}")
            return "success"

        except Exception as e:
            err_msg = str(e)
            is_oom = ("out of memory" in err_msg.lower()) or ("alloc" in err_msg.lower() and "cuda" in err_msg.lower())
            if is_oom and is_concurrent and model_instance is not None and not self._is_stopped:
                with self._name_lock:
                    norm_output_dir = os.path.normcase(os.path.abspath(target_output_dir))
                    used_base_names.discard((norm_output_dir, disambiguated_name))
                return "oom_retry"

            self.sig_log.emit(f"❌ 文件 {filename} 转录发生异常: {err_msg}")
            self.sig_file_failed.emit(idx, err_msg)
            return "failed"

    def run(self):
        success_count = 0
        fail_count = 0
        total_files = len(self.file_paths)

        if total_files == 0:
            self.sig_all_finished.emit(0, 0)
            return

        self.transcriber.reset_cancel()

        loaded_cnt = (
            self.transcriber.loaded_model_count()
            if hasattr(self.transcriber, "loaded_model_count")
            else (1 if self.transcriber.is_model_loaded() else 0)
        )
        req_concurrency = getattr(self.config, "max_concurrent_tasks", 0) or 0
        plan = plan_effective_concurrency(
            device=self.config.device,
            requested_concurrency=req_concurrency,
            total_files=total_files,
            already_loaded_models=loaded_cnt,
        )
        self.effective_workers = plan["effective_workers"]

        prompt_summary = summarize_prompt(self.config.initial_prompt)
        self.sig_log.emit(f"🚀 任务启动，待处理文件总数: {total_files}")
        self.sig_log.emit(
            f"⚙️ 目标设备: {self.config.device.upper()} | 模型: {self.config.model_size} | "
            f"精度: {self.config.compute_type} | 并发路数: {self.effective_workers} 路"
        )
        if plan.get("vram_stepped_down"):
            self.sig_log.emit(f"⚠️ {plan['reason']}")
        elif self.effective_workers > 1:
            self.sig_log.emit(f"⚡ 并发调度: {plan['reason']}")

        self.sig_log.emit(
            f"🛡️ ASMR 调优策略: Whisper原生字幕切分 | "
            f"上下文锁定={'开' if not self.config.condition_on_previous_text else '关'} | "
            f"VAD保护={'开' if self.config.vad_filter else '关'} | "
            f"娇喘过滤={'开' if self.config.filter_r18_moans else '关'} | "
            f"去重={'开' if self.config.deduplicate_identical else '关'}"
        )
        self.sig_log.emit(f"📝 提示词: {prompt_summary}")

        used_base_names = set()

        # 1. 若仅需单路执行 (1 个文件 / CPU / <=8GB 显卡)，采用轻量直通流
        if self.effective_workers <= 1:
            for idx, file_path in enumerate(self.file_paths):
                if self._is_stopped:
                    self.sig_log.emit(f"⚠️ 用户中止了任务，剩余 {total_files - idx} 个未处理文件已标记为取消。")
                    for rem_idx in range(idx, total_files):
                        self.sig_file_failed.emit(rem_idx, "已取消")
                        fail_count += 1
                    break

                status = self._process_single_item(
                    idx=idx,
                    file_path=file_path,
                    total_files=total_files,
                    used_base_names=used_base_names,
                    model_instance=None,
                    is_concurrent=False,
                )
                if status == "success":
                    success_count += 1
                else:
                    fail_count += 1
                    if self._is_stopped or status == "cancelled":
                        rem_count = total_files - 1 - idx
                        for rem_idx in range(idx + 1, total_files):
                            self.sig_file_failed.emit(rem_idx, "已取消")
                            fail_count += 1
                        if rem_count > 0:
                            self.sig_log.emit(f"⚠️ 用户中止了转录，后续 {rem_count} 个等待中的文件已标记为取消。")
                        break

            self.sig_all_finished.emit(success_count, fail_count)
            return

        # 2. 多路并发模式 (effective_workers >= 2): 准备模型实例池并执行动态交替接力 (Work-Stealing)
        try:
            if hasattr(self.transcriber, "prepare_model_pool"):
                models = self.transcriber.prepare_model_pool(
                    worker_count=self.effective_workers,
                    log_callback=lambda m: self.sig_log.emit(f"  ├─ {m}"),
                )
            else:
                models = [self.transcriber.load_model()]
        except Exception as load_err:
            err_str = str(load_err)
            self.sig_log.emit(f"❌ 加载 Whisper 模型池失败: {err_str}")
            for idx in range(total_files):
                self.sig_file_failed.emit(idx, err_str)
            self.sig_all_finished.emit(0, total_files)
            return

        if self._is_stopped:
            for idx in range(total_files):
                self.sig_file_failed.emit(idx, "已取消")
            self.sig_all_finished.emit(0, total_files)
            return

        actual_workers = max(1, min(len(models), total_files))
        is_concurrent = actual_workers > 1

        pending_queue: "queue.Queue[Tuple[int, str, bool]]" = queue.Queue()
        for idx, fp in enumerate(self.file_paths):
            pending_queue.put((idx, fp, False))

        def _worker_loop(slot_id: int, slot_model: Any):
            nonlocal success_count, fail_count
            while not self._is_stopped:
                try:
                    idx, file_path, is_retried = pending_queue.get_nowait()
                except queue.Empty:
                    break

                if self._is_stopped:
                    # 放回队列由主线程统一标记取消
                    pending_queue.put((idx, file_path, is_retried))
                    break

                status = self._process_single_item(
                    idx=idx,
                    file_path=file_path,
                    total_files=total_files,
                    used_base_names=used_base_names,
                    model_instance=slot_model,
                    is_concurrent=is_concurrent,
                )

                if status == "oom_retry" and not is_retried:
                    self.sig_log.emit(
                        f"⚠️ [槽位 #{slot_id + 1}] 检测到峰值显存压力 (CUDA OOM)，"
                        f"已自动回收当前冗余模型槽位并将《{os.path.basename(file_path)}》交由存活槽位无缝重试..."
                    )
                    if hasattr(self.transcriber, "shrink_pool_instance"):
                        self.transcriber.shrink_pool_instance(slot_model)
                    pending_queue.put((idx, file_path, True))
                    break

                with self._state_lock:
                    if status == "success":
                        success_count += 1
                    else:
                        fail_count += 1

        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = [
                executor.submit(_worker_loop, slot_id, models[slot_id])
                for slot_id in range(actual_workers)
            ]
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as w_err:
                    self.sig_log.emit(f"❌ 并发工作槽位异常: {w_err}")

        # 若因停止或所有并发槽位退出导致队列仍有剩余未处理项，全部安全收尾
        remaining_items: List[Tuple[int, str, bool]] = []
        while not pending_queue.empty():
            try:
                remaining_items.append(pending_queue.get_nowait())
            except queue.Empty:
                break

        remaining_items.sort(key=lambda x: x[0])
        if remaining_items:
            if self._is_stopped:
                self.sig_log.emit(f"⚠️ 用户中止了转录，剩余 {len(remaining_items)} 个等待中的文件已标记为取消。")
                for rem_idx, _, _ in remaining_items:
                    self.sig_file_failed.emit(rem_idx, "已取消")
                    fail_count += 1
            else:
                # 兜底：若因 OOM 回收后仍有未完成的重试项，使用主模型实例串行兜底完成
                primary_model = self.transcriber._model
                for rem_idx, rem_fp, _ in remaining_items:
                    if self._is_stopped:
                        self.sig_file_failed.emit(rem_idx, "已取消")
                        fail_count += 1
                        continue
                    st = self._process_single_item(
                        idx=rem_idx,
                        file_path=rem_fp,
                        total_files=total_files,
                        used_base_names=used_base_names,
                        model_instance=primary_model,
                        is_concurrent=False,
                    )
                    if st == "success":
                        success_count += 1
                    else:
                        fail_count += 1

        self.sig_all_finished.emit(success_count, fail_count)


__all__ = [
    "TranscriptionWorker",
]
