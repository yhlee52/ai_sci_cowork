"""운영 제약: `lab.py hardware`가 이 PC를 탐색해 lab.config.json → compute.limits에 건 값을 읽고 지킨다.

    from labkit import lab_limits
    lim = lab_limits()   # 예: {"device": "cuda", "precision": "bf16", "vram_budget_gb": 7.2, "dataloader_workers": 0, ...}
    loader = DataLoader(ds, batch_size=..., num_workers=lim.get("dataloader_workers", 0))

VRAM 예산은 Run과 get_device()가 자동으로 건다 (넘으면 메모리 부족 오류로 멈춘다). Run은 최대 VRAM 사용량을 기록한다.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_CONFIG = "lab.config.json"


def _lab_root() -> Path | None:
    cwd = Path.cwd().resolve()
    for c in (os.environ.get("LAB_ROOT"), Path(__file__).resolve().parents[1], cwd, *cwd.parents):
        if c and (Path(c) / _CONFIG).exists():
            return Path(c)
    return None


def lab_limits() -> dict:
    """이 연구실의 운영 제약. 연구실 밖이거나 아직 탐색 전이면 빈 dict."""
    root = _lab_root()
    if root is None:
        return {}
    try:
        cfg = json.loads((root / _CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dict((cfg.get("compute") or {}).get("limits") or {})


def apply_vram_cap() -> float | None:
    """torch가 이미 불려 있고 CUDA를 쓰면 이 프로세스의 VRAM 사용을 예산 안으로 묶는다. 건 비율을 돌려준다."""
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_available():
        return None
    budget = lab_limits().get("vram_budget_gb")
    if not budget:
        return None
    frac = None
    for i in range(torch.cuda.device_count()):
        total = torch.cuda.get_device_properties(i).total_memory / 2**30
        frac = max(0.05, min(1.0, float(budget) / total))
        torch.cuda.set_per_process_memory_fraction(frac, i)
    return frac


def reset_peak_vram() -> None:
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def peak_vram_gb() -> float | None:
    """이 프로세스가 지금까지 쓴 최대 VRAM(GB). CUDA를 안 쓰면 None."""
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_available():
        return None
    return round(max(torch.cuda.max_memory_allocated(i) for i in range(torch.cuda.device_count())) / 2**30, 2)
