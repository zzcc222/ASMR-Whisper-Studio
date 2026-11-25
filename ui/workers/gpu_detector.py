# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 硬件环境与 GPU 状态感知器 (ui.workers.gpu_detector)
检测系统 CUDA、标称显存容量、推荐并发路数、CTranslate2 运行时状态并生成状态栏胶囊样式
"""

from typing import Tuple, Optional, Union
from PySide6.QtCore import QThread, Signal

from core.concurrency_planner import (
    GpuVramSnapshot,
    query_gpu_vram_snapshot,
    calculate_tier_concurrency,
)

_CACHED_SNAPSHOT: Optional[GpuVramSnapshot] = None
_CACHED_PROBED: bool = False


def get_cached_gpu_snapshot(force_refresh: bool = False) -> GpuVramSnapshot:
    """获取并缓存 GPU 硬件快照 (含标称显存 GB 与空闲显存)"""
    global _CACHED_SNAPSHOT, _CACHED_PROBED
    if _CACHED_PROBED and not force_refresh and _CACHED_SNAPSHOT is not None:
        return _CACHED_SNAPSHOT

    _CACHED_SNAPSHOT = query_gpu_vram_snapshot()
    _CACHED_PROBED = True
    return _CACHED_SNAPSHOT


def get_cached_gpu_desc(force_refresh: bool = False) -> Optional[str]:
    """获取并静态缓存 GPU 硬件型号与标称显存描述，防止多次执行 nvidia-smi 阻塞 UI 事件循环"""
    snap = get_cached_gpu_snapshot(force_refresh=force_refresh)
    if not snap.is_cuda_available:
        return None
    if snap.nominal_gb > 0 and snap.gpu_name != "CUDA 硬件加速":
        return f"{snap.gpu_name} · {float(snap.nominal_gb):.1f} GB"
    return snap.gpu_name or "CUDA 硬件加速"


def get_recommended_concurrency_label(force_refresh: bool = False) -> Tuple[int, str]:
    """获取当前系统的智能推荐并发数及通用下拉框展示文案（不含具体显卡型号名称）"""
    snap = get_cached_gpu_snapshot(force_refresh=force_refresh)
    if not snap.is_cuda_available or snap.nominal_gb <= 0:
        return 1, "⚡ 智能自动 (按显存自动匹配)"
    rec = calculate_tier_concurrency(
        nominal_gb=snap.nominal_gb,
        free_gb=snap.free_gb if snap.free_gb > 0 else None,
    )
    return rec, f"⚡ 智能自动 (当前推荐: {rec} 路并发)"


def detect_gpu_environment(
    current_dev: str = "cuda",
    is_model_loaded: Union[bool, int] = False,
    force_refresh: bool = False,
) -> Tuple[str, str]:
    """检测当前 GPU 显卡型号、显存大小与模型池就绪状态，返回 (显示文本, QSS样式表)"""
    dev = (current_dev or "cuda").strip().lower()
    loaded_cnt = int(is_model_loaded) if isinstance(is_model_loaded, int) and not isinstance(is_model_loaded, bool) else (1 if is_model_loaded else 0)

    if loaded_cnt > 1:
        loaded_hint = f" · {loaded_cnt} 路模型就绪"
    elif loaded_cnt == 1:
        loaded_hint = " · 模型就绪"
    else:
        loaded_hint = ""

    if dev == "cpu":
        return (
            f"💻 CPU 运算模式{loaded_hint}",
            "background-color: #F4F4F5; color: #52525B; border: 1px solid #E4E4E7; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;",
        )

    gpu_desc = get_cached_gpu_desc(force_refresh=force_refresh)

    if gpu_desc:
        return (
            f"🟢 {gpu_desc}{loaded_hint}",
            "background-color: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;",
        )
    else:
        return (
            "⚠️ 未检测到 CUDA (CPU 模式)",
            "background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;",
        )


class GpuProbeThread(QThread):
    """异步探测 GPU 硬件环境线程，防止主界面冷启动阻塞"""
    sig_probed = Signal(str, str)

    def __init__(self, current_dev: str = "cuda", is_model_loaded: Union[bool, int] = False, force_refresh: bool = False):
        super().__init__()
        self.current_dev = current_dev
        self.is_model_loaded = is_model_loaded
        self.force_refresh = force_refresh

    def run(self):
        desc, qss = detect_gpu_environment(
            self.current_dev,
            self.is_model_loaded,
            force_refresh=self.force_refresh,
        )
        self.sig_probed.emit(desc, qss)


__all__ = [
    "get_cached_gpu_snapshot",
    "get_cached_gpu_desc",
    "get_recommended_concurrency_label",
    "detect_gpu_environment",
    "GpuProbeThread",
]
