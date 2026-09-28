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


def get_device(prefer: str = "cuda"):
    try:
        import torch
    except ImportError:
        return "cpu"
    if prefer == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
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
