"""재현성 도구: 시드 고정, 장치 선택, git 커밋과 실행 환경 기록."""
from __future__ import annotations

import os
import platform
import random
import subprocess


def seed_everything(seed: int, deterministic: bool = False) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def seed_from_env(default: int = 0) -> int:
    """캠페인 실행기(lab.py campaign)가 넘겨 주는 시드(LAB_SEED). 없으면 default."""
    try:
        return int(os.environ.get("LAB_SEED", default))
    except ValueError:
        return default


def report_metric(name: str, value: float) -> None:
    """캠페인 실행기가 읽는 지표 줄을 출력한다: `LAB_METRIC 이름=값`.
    평가 코드(가능하면 수정 금지 파일)에서 부른다. 값을 지어내거나 고치지 않는다."""
    print(f"LAB_METRIC {name}={float(value):.10g}", flush=True)


def get_device(prefer: str | None = None):
    """연구실 운영 제약(compute.limits.device)의 장치. 쓸 수 없으면 CPU. CUDA면 VRAM 예산도 건다."""
    try:
        import torch
    except ImportError:
        return "cpu"
    from .limits import apply_vram_cap, lab_limits
    prefer = prefer or lab_limits().get("device", "cuda")
    if prefer == "cuda" and torch.cuda.is_available():
        apply_vram_cap()
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if prefer == "mps" and mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout.strip()
        return (out.stdout.strip() + ("-dirty" if dirty else "")) or None
    except Exception:
        return None


def env_info() -> dict:
    info = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import torch
        info["torch"] = torch.__version__
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return info
