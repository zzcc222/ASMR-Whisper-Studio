# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 同进程多独立 WhisperModel 实例池管理器 (core.model_pool)
- 管理 1~N 个独立的 faster-whisper (CTranslate2) 模型实例
- 每个实例拥有独立的 C++ 模型副本、独立 CUDA Stream 与 cuBLAS Handle，实现真正的多流硬件并行
- 支持按需懒加载扩容 (已有 1 路常驻时，2 路并发仅需增量加载第 2 路)
- 具备加载期显存不足 (OOM) 自动刹停降级保护与一键全量显存卸载
"""

import gc
import logging
import threading
from typing import Any, Callable, List, Optional, Tuple

from core.config import ASMRTranscriberConfig
from core.cuda_utils import resolve_model_path

logger = logging.getLogger("WhisperModelPool")


class WhisperModelPool:
    """同进程多实例 Whisper 模型池"""

    def __init__(self):
        self._instances: List[Any] = []
        self._current_model_key: Optional[Tuple[str, str, int, str]] = None
        self._lock = threading.Lock()

    @property
    def primary_model(self) -> Optional[Any]:
        """获取主模型实例 (Slot 0)，保持向后兼容"""
        with self._lock:
            return self._instances[0] if self._instances else None

    @property
    def current_model_key(self) -> Optional[Tuple[str, str, int, str]]:
        return self._current_model_key

    def loaded_count(self) -> int:
        """当前池中已加载的模型实例数量"""
        with self._lock:
            return len(self._instances)

    def is_loaded(self) -> bool:
        with self._lock:
            return len(self._instances) > 0

    def set_external_primary_model(
        self,
        model: Optional[Any],
        model_key: Optional[Tuple[str, str, int, str]] = None,
    ):
        """兼容外部直接对 transcriber._model 赋值的情况（如单元测试 Mock 模型）"""
        with self._lock:
            if model is None:
                self._instances.clear()
                self._current_model_key = None
            else:
                if self._instances:
                    self._instances[0] = model
                else:
                    self._instances = [model]
                if model_key is not None:
                    self._current_model_key = model_key

    def unload_all(self) -> int:
        """卸载池中所有模型实例并彻底释放 GPU 显存，返回卸载的实例数"""
        with self._lock:
            count = len(self._instances)
            if count > 0:
                while self._instances:
                    inst = self._instances.pop()
                    del inst
                self._current_model_key = None
        if count > 0:
            gc.collect()
            logger.info(f"已从 GPU 显存中卸载 {count} 个 Whisper 模型实例。")
        return count

    def remove_instance(self, instance: Any) -> int:
        """在运行期发生单槽位异常/OOM 时移除指定冗余实例并释放其显存"""
        removed = False
        with self._lock:
            if instance in self._instances and len(self._instances) > 1:
                self._instances.remove(instance)
                removed = True
            remaining = len(self._instances)
        if removed:
            del instance
            gc.collect()
            logger.warning(f"已动态回收 1 个冗余模型实例，当前存活实例数: {remaining}")
        return remaining

    def _create_single_instance(
        self,
        actual_model_path: str,
        config: ASMRTranscriberConfig,
        compute_type: str,
        prompt_guard_installer: Optional[Callable[[Any], None]] = None,
    ) -> Any:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            actual_model_path,
            device=config.device,
            device_index=config.device_index,
            compute_type=compute_type,
            download_root=config.download_root,
        )
        if prompt_guard_installer is not None:
            prompt_guard_installer(model)
        return model

    def ensure_pool(
        self,
        config: ASMRTranscriberConfig,
        target_count: int = 1,
        force_reload: bool = False,
        prompt_guard_installer: Optional[Callable[[Any], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        """
        确保模型池中拥有 target_count 个就绪的独立 WhisperModel 实例：
        - 若首个实例尚未加载或配置已变更，执行带精度回退链的首实例加载；
        - 若已有 K 个实例且需要 N (N > K) 个实例，仅增量加载剩余 N - K 个实例；
        - 若加载第 2+ 个实例时显存不足，优雅捕获并返回已加载的实例列表。
        """
        def _log(msg: str):
            logger.info(msg)
            if log_callback:
                try:
                    log_callback(msg)
                except Exception:
                    pass

        target_count = max(1, int(target_count or 1))
        if config.device == "cpu" and config.compute_type in ("float16", "int8_float16", "bfloat16"):
            logger.warning(f"检测到 CPU 设备选用了不支持的计算精度 [{config.compute_type}]，自动安全降级为 [int8]")
            config.compute_type = "int8"

        actual_model_path = resolve_model_path(config.model_size)
        desired_key = (actual_model_path, config.device, config.device_index, config.compute_type)

        with self._lock:
            # 若已有外部注入的 Mock 模型且 key 匹配或未设 key，直接兼容返回
            if (
                self._instances
                and not force_reload
                and (self._current_model_key == desired_key or self._current_model_key is None)
            ):
                for inst in self._instances:
                    if prompt_guard_installer is not None:
                        prompt_guard_installer(inst)
                # 如果是单元测试注入的 非原生 WhisperModel mock 对象，不克隆新实例，直接返回
                first_cls_name = type(self._instances[0]).__name__
                if first_cls_name != "WhisperModel":
                    return list(self._instances)
            elif self._instances and (force_reload or self._current_model_key != desired_key):
                while self._instances:
                    inst = self._instances.pop()
                    del inst
                self._current_model_key = None
                gc.collect()

            # 1. 确保第 1 个主实例 (Slot #1) 已加载
            if not self._instances:
                compute_candidates = [config.compute_type]
                fallback_chain = (
                    ["float16", "int8_float16", "int8", "float32"]
                    if config.device == "cuda"
                    else ["int8", "float32"]
                )
                for fb in fallback_chain:
                    if fb not in compute_candidates:
                        compute_candidates.append(fb)

                last_err = None
                loaded_primary = None
                for cur_compute in compute_candidates:
                    _log(
                        f"正在加载 Whisper 模型 [{config.model_size}] "
                        f"(设备: {config.device}, 精度: {cur_compute})..."
                    )
                    try:
                        loaded_primary = self._create_single_instance(
                            actual_model_path=actual_model_path,
                            config=config,
                            compute_type=cur_compute,
                            prompt_guard_installer=prompt_guard_installer,
                        )
                        config.compute_type = cur_compute
                        self._current_model_key = (
                            actual_model_path,
                            config.device,
                            config.device_index,
                            cur_compute,
                        )
                        self._instances.append(loaded_primary)
                        logger.info("成功加载主 WhisperModel 实例 (#1)！")
                        break
                    except Exception as e:
                        last_err = e
                        logger.warning(f"以精度 [{cur_compute}] 加载主模型失败: {e}")

                if loaded_primary is None:
                    logger.error(f"加载 Whisper 模型严重错误: {last_err}")
                    raise last_err

            # 2. 按需增量加载第 2 .. target_count 个并发实例
            active_compute = self._current_model_key[3] if self._current_model_key else config.compute_type
            while len(self._instances) < target_count:
                slot_idx = len(self._instances) + 1
                _log(f"正在扩容加载第 #{slot_idx}/{target_count} 路并发 Whisper 模型实例...")
                try:
                    extra_model = self._create_single_instance(
                        actual_model_path=actual_model_path,
                        config=config,
                        compute_type=active_compute,
                        prompt_guard_installer=prompt_guard_installer,
                    )
                    self._instances.append(extra_model)
                    logger.info(f"成功加载第 #{slot_idx} 路并发 WhisperModel 实例！")
                except Exception as extra_err:
                    gc.collect()
                    _log(
                        f"⚠️ 加载第 #{slot_idx} 路并发模型时显存受限 ({extra_err})，"
                        f"自动安全锁定为 {len(self._instances)} 路并发运行。"
                    )
                    break

            return list(self._instances[:target_count])


__all__ = [
    "WhisperModelPool",
]
