"""labkit — 연구실 공용 실험 코드. 새로 짜기 전에 먼저 여기서 찾아 쓴다.

    from labkit import Run, seed_everything, get_device, collect_results, setup_korean_plot
    from labkit import compare, check_overlap, report_metric, seed_from_env

torch와 matplotlib는 필요할 때만 불러오므로, 실행 기록, 결과 집계, 통계는 torch 없이도 동작한다.
"""
import sys

for _stream in (sys.stdout, sys.stderr):  # Windows 콘솔 기본값(cp949)에서 한글 출력이 깨지지 않도록
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .leakage import check_overlap
from .plot import setup_korean_plot
from .repro import get_device, git_commit, report_metric, seed_everything, seed_from_env
from .results import collect_results
from .run import Run
from .stats import bootstrap_ci, compare, summarize

__all__ = [
    "Run", "bootstrap_ci", "check_overlap", "collect_results", "compare", "get_device", "git_commit",
    "report_metric", "seed_everything", "seed_from_env", "setup_korean_plot", "summarize",
]
