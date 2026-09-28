"""labkit — 연구실 공용 실험 코드. 새로 짜기 전에 먼저 여기서 찾아 쓴다.

    from labkit import Run, seed_everything, get_device, collect_results, setup_korean_plot

torch와 matplotlib는 필요할 때만 불러오므로, 실행 기록과 결과 집계는 torch 없이도 동작한다.
"""
import sys

for _stream in (sys.stdout, sys.stderr):  # Windows 콘솔 기본값(cp949)에서 한글 출력이 깨지지 않도록
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .plot import setup_korean_plot
from .repro import get_device, git_commit, seed_everything
from .results import collect_results
from .run import Run

__all__ = ["Run", "collect_results", "get_device", "git_commit", "seed_everything", "setup_korean_plot"]
