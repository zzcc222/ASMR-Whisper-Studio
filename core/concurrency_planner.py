# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 硬件显存感知与并发任务智能规划模块 (core.concurrency_planner)
- 精确探测 NVIDIA GPU 物理总显存与实时空闲显存 (nvidia-smi / CTranslate2 双通道)
- 标称显存容量对齐 (解决 12227 MiB = 11.94 GiB 向下取整导致 12G 显卡误判为 1 任务的问题)
- 基于「6GB / 任务」准则与「16GB 显卡动态空闲显存检测」计算最优并发任务数:
  * <= 8 GB  : 1 个任务
  * 12 GB    : 2 个任务
  * 16 GB    : 剩余可用显存充裕 (>= 12.5 GB) 时跑 3 个任务，否则稳健跑 2 个任务
  * 24 GB    : 4 个任务
  * >= 32 GB : 5 个任务
- 启动前根据实时剩余显存与队列文件总数自适应裁剪，杜绝空载浪费与后台显存冲突
"""

import sys
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, Any

# 实测 faster-whisper large-v2/v3 (float16) 显存消耗模型 (基于 RTX 5070 实测数据):
# - 第 1 个独立模型实例 (含进程级 CUDA Context + cuBLAS + 模型权重 + 推理工作区): ~4.1 GB
# - 同进程内每增加 1 个独立模型实例 (复用进程 CUDA Context，新增独立权重与 CUDA Stream): ~3.6 GB
FIRST_INSTANCE_VRAM_GB = 4.1
EXTRA_INSTANCE_VRAM_GB = 3.6
MAX_CONCURRENT_CAP = 16

STANDARD_VRAM_TIERS_GB = (
    4, 6, 8, 10, 11, 12, 16, 20, 24, 32, 36, 40, 48, 60, 64, 72, 80, 96, 128, 141
)


@dataclass
class GpuVramSnapshot:
    """GPU 硬件与实时显存状态快照"""
    gpu_name: str = ""
    raw_name: str = ""
    total_mb: float = 0.0
    free_mb: float = 0.0
    used_mb: float = 0.0
    nominal_gb: int = 0
    free_gb: float = 0.0
    is_cuda_available: bool = False


def normalize_nominal_vram_gb(total_mb: float) -> int:
    """
    将 nvidia-smi 报告的物理 MiB 对齐为标准标称显存容量 (GB)。
    例如 RTX 5070 报告 12227 MiB (11.94 GiB) -> 对齐为 12 GB；
    RTX 4080 报告 16376 MiB (15.99 GiB) -> 对齐为 16 GB；
    RTX 4090 报告 24564 MiB (23.99 GiB) -> 对齐为 24 GB。
    """
    if total_mb <= 0:
        return 0
    raw_gb = float(total_mb) / 1024.0
    for tier in STANDARD_VRAM_TIERS_GB:
        if (tier - 0.65) <= raw_gb <= (tier + 0.30):
            return tier
    return max(1, int(round(raw_gb + 0.3)))


def estimate_held_vram_gb(loaded_model_count: int) -> float:
    """估算本程序当前已加载的模型实例池在 GPU 中占用的显存 (GB)"""
    cnt = max(0, int(loaded_model_count or 0))
    if cnt == 0:
        return 0.0
    return FIRST_INSTANCE_VRAM_GB + EXTRA_INSTANCE_VRAM_GB * (cnt - 1)


def required_vram_for_workers(worker_count: int, safety_margin_gb: float = 0.3) -> float:
    """计算运行指定数量并发模型实例所需的可用显存 (GB)"""
    k = max(1, int(worker_count or 1))
    return FIRST_INSTANCE_VRAM_GB + EXTRA_INSTANCE_VRAM_GB * (k - 1) + safety_margin_gb


def query_gpu_vram_snapshot(timeout_sec: float = 2.0) -> GpuVramSnapshot:
    """
    实时查询当前主显卡的名称、总显存、空闲显存与已用显存。
    """
    snap = GpuVramSnapshot()
    try:
        cflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        res = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,memory.used",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            creationflags=cflags,
        )
        if res.returncode == 0 and res.stdout.strip():
            first_line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first_line.split(",")]
            if len(parts) >= 2:
                raw_name = parts[0]
                total_mb = float(parts[1])
                free_mb = float(parts[2]) if len(parts) >= 3 else max(0.0, total_mb - 1536.0)
                used_mb = float(parts[3]) if len(parts) >= 4 else max(0.0, total_mb - free_mb)
                clean_name = (
                    raw_name.replace("NVIDIA GeForce ", "")
                    .replace("NVIDIA ", "")
                    .replace("GeForce ", "")
                    .strip()
                )
                snap.raw_name = raw_name
                snap.gpu_name = clean_name
                snap.total_mb = total_mb
                snap.free_mb = free_mb
                snap.used_mb = used_mb
                snap.nominal_gb = normalize_nominal_vram_gb(total_mb)
                snap.free_gb = round(free_mb / 1024.0, 2)
                snap.is_cuda_available = True
                return snap
    except Exception:
        pass

    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            snap.gpu_name = "CUDA 硬件加速"
            snap.raw_name = "CUDA Device"
            snap.nominal_gb = 8
            snap.free_gb = 6.5
            snap.is_cuda_available = True
    except Exception:
        pass

    return snap


def calculate_tier_concurrency(
    nominal_gb: int,
    free_gb: Optional[float] = None,
    already_loaded_models: int = 0,
) -> int:
    """
    根据显卡标称显存容量 (GB) 与实时剩余显存计算推荐并发任务数：
    - <= 8 GB  : 1 个任务
    - 12 GB    : 2 个任务 (12 // 6 = 2)
    - 16 GB    : 若有效可用显存 >= 12.5 GB 则跑 3 个任务，否则跑 2 个任务
    - 24 GB    : 4 个任务 (24 // 6 = 4)
    - >= 32 GB : 5 个任务 (32 // 6 = 5)
    """
    if nominal_gb <= 8:
        return 1

    # 16 GB 显卡专属动态评估：剩余可用显存够 (>= 12.5 GB) 则跑 3 个任务，否则跑 2 个任务
    if 15 <= nominal_gb <= 18:
        held_gb = estimate_held_vram_gb(already_loaded_models)
        if free_gb is not None and free_gb > 0:
            usable_gb = free_gb + held_gb
        else:
            # 未提供实时 free_gb 时默认按系统占用 1.5 GB 估算 (16 - 1.5 = 14.5 GB >= 12.5 GB)
            usable_gb = float(nominal_gb) - 1.5
        return 3 if usable_gb >= 12.5 else 2

    return max(1, min(MAX_CONCURRENT_CAP, int(nominal_gb // 6)))


def plan_effective_concurrency(
    device: str = "cuda",
    requested_concurrency: int = 0,
    total_files: int = 1,
    already_loaded_models: int = 0,
    snapshot: Optional[GpuVramSnapshot] = None,
) -> Dict[str, Any]:
    """
    综合推理设备、用户配置、显卡总显存、实时可用显存与待处理文件数，规划最终并发方案。
    :param device: 'cuda' 或 'cpu'
    :param requested_concurrency: 0 表示智能自动，1~5 表示用户手动指定
    :param total_files: 当前队列待转录文件总数
    :param already_loaded_models: 当前 ASMRTranscriber 已常驻显存的模型实例数
    :param snapshot: 可选外部传入的 GPU 快照，未传则自动实时查询
    """
    dev = (device or "cuda").strip().lower()
    num_files = max(1, int(total_files or 1))
    req = max(0, int(requested_concurrency or 0))

    if dev == "cpu":
        return {
            "effective_workers": 1,
            "target_workers": 1,
            "recommended_workers": 1,
            "nominal_gb": 0,
            "usable_vram_gb": 0.0,
            "vram_stepped_down": False,
            "gpu_name": "CPU",
            "reason": "CPU 模式固定采用单任务满核推理",
        }

    snap = snapshot if snapshot is not None else query_gpu_vram_snapshot()
    if not snap.is_cuda_available:
        return {
            "effective_workers": 1,
            "target_workers": 1,
            "recommended_workers": 1,
            "nominal_gb": 0,
            "usable_vram_gb": 0.0,
            "vram_stepped_down": False,
            "gpu_name": "CPU (未检测到 CUDA)",
            "reason": "未检测到可用 CUDA 设备，自动回退为单任务模式",
        }

    held_gb = estimate_held_vram_gb(already_loaded_models)
    usable_vram_gb = round(snap.free_gb + held_gb, 2) if snap.free_gb > 0 else float(snap.nominal_gb)

    recommended = calculate_tier_concurrency(
        nominal_gb=snap.nominal_gb,
        free_gb=snap.free_gb,
        already_loaded_models=already_loaded_models,
    )

    desired = recommended if req <= 0 else min(MAX_CONCURRENT_CAP, req)

    # 根据实时可用显存进行安全水位校验，防止后台其它大型程序占满显存导致 OOM
    safety_margin = 0.35 if req <= 0 else 0.05
    target_workers = desired
    vram_stepped_down = False

    if snap.free_gb > 0:
        while target_workers > 1:
            needed_gb = required_vram_for_workers(target_workers, safety_margin_gb=safety_margin)
            if usable_vram_gb >= needed_gb:
                break
            target_workers -= 1
            vram_stepped_down = True

    # 按当前待处理文件总数按需裁剪，避免 1 个文件加载多个模型白占显存
    effective_workers = max(1, min(target_workers, num_files))

    if vram_stepped_down:
        reason = (
            f"检测到后台程序占用显存 (当前可用 {usable_vram_gb:.1f} GB / 总显存 {snap.nominal_gb} GB)，"
            f"并发数已从 {desired} 路自动安全调整为 {target_workers} 路"
        )
    elif effective_workers < target_workers:
        reason = (
            f"当前显存支持 {target_workers} 路并发 (总显存 {snap.nominal_gb}GB)，"
            f"因队列仅 {num_files} 个文件，按需启用 {effective_workers} 路模型实例"
        )
    else:
        mode_tag = "智能自动" if req <= 0 else "手动指定"
        reason = (
            f"{mode_tag} (总显存 {snap.nominal_gb}GB, 可用 {usable_vram_gb:.1f}GB) -> "
            f"启用 {effective_workers} 路并发交替转录"
        )

    return {
        "effective_workers": effective_workers,
        "target_workers": target_workers,
        "recommended_workers": recommended,
        "nominal_gb": snap.nominal_gb,
        "usable_vram_gb": usable_vram_gb,
        "vram_stepped_down": vram_stepped_down,
        "gpu_name": snap.gpu_name,
        "reason": reason,
    }


__all__ = [
    "FIRST_INSTANCE_VRAM_GB",
    "EXTRA_INSTANCE_VRAM_GB",
    "MAX_CONCURRENT_CAP",
    "GpuVramSnapshot",
    "normalize_nominal_vram_gb",
    "estimate_held_vram_gb",
    "required_vram_for_workers",
    "query_gpu_vram_snapshot",
    "calculate_tier_concurrency",
    "plan_effective_concurrency",
]
