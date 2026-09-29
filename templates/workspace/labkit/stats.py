"""통계 도구 (표준 라이브러리만 사용). 시드 몇 개짜리 작은 실험에서도 정직하게 비교하기 위한 최소한의 도구.

    from labkit.stats import compare
    c = compare(treat=[0.71, 0.72, 0.70], base=[0.65, 0.66, 0.64], goal="max")
    c["verdict"]   # "개선 (95% 신뢰구간이 0보다 큼)" 등

- 차이는 항상 "개선량"으로 보고한다: goal="max"이면 처리-기준, goal="min"이면 기준-처리. 양수면 좋아진 것.
- 신뢰구간은 부트스트랩(재표집)으로 구한다. 시드가 적으면 구간이 넓게 나오는 것이 정상이다.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Callable, Sequence


def _mean(xs: Sequence[float]) -> float:
    return statistics.fmean(xs)


def summarize(values: Sequence[float]) -> dict:
    """평균, 표준편차, 개수, 표준오차."""
    vals = [float(v) for v in values]
    n = len(vals)
    if n == 0:
        return {"mean": None, "std": None, "n": 0, "sem": None}
    std = statistics.stdev(vals) if n > 1 else 0.0
    return {"mean": _mean(vals), "std": std, "n": n, "sem": std / math.sqrt(n) if n > 1 else None}


def bootstrap_ci(values: Sequence[float], stat: Callable[[Sequence[float]], float] = _mean,
                 n_boot: int = 5000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float] | None:
    """값 하나의 통계량에 대한 부트스트랩 신뢰구간."""
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return None
    rng = random.Random(seed)
    boots = sorted(stat([rng.choice(vals) for _ in vals]) for _ in range(n_boot))
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


def hedges_g(a: Sequence[float], b: Sequence[float]) -> float | None:
    """효과 크기 (a-b, 작은 표본 보정). 두 집단 모두 2개 이상이고 분산이 있어야 계산한다."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    va, vb = statistics.variance(a), statistics.variance(b)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return None
    d = (_mean(a) - _mean(b)) / pooled
    return d * (1 - 3 / (4 * (na + nb) - 9))


def compare(treat: Sequence[float], base: Sequence[float], goal: str = "max",
            n_boot: int = 5000, alpha: float = 0.05, seed: int = 0) -> dict:
    """처리(treat)가 기준(base)보다 나은지. 개선량 = (goal이 max면 treat-base, min이면 base-treat)."""
    if goal not in ("max", "min"):
        raise ValueError("goal은 'max' 또는 'min'이어야 합니다")
    t = [float(v) for v in treat]
    b = [float(v) for v in base]
    if not t or not b:
        raise ValueError("비교할 값이 비어 있습니다")
    sign = 1.0 if goal == "max" else -1.0
    improvement = sign * (_mean(t) - _mean(b))
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        rt = [rng.choice(t) for _ in t]
        rb = [rng.choice(b) for _ in b]
        boots.append(sign * (_mean(rt) - _mean(rb)))
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    p_improve = sum(1 for x in boots if x > 0) / n_boot
    base_mean = _mean(b)
    rel = improvement / abs(base_mean) if base_mean else None
    g = hedges_g(t, b)
    if min(len(t), len(b)) < 2:
        verdict = "판단 불가 (시드가 1개뿐이라 변동을 알 수 없음)"
    elif lo > 0:
        verdict = f"개선 ({int((1 - alpha) * 100)}% 신뢰구간이 0보다 큼)"
    elif hi < 0:
        verdict = f"악화 ({int((1 - alpha) * 100)}% 신뢰구간이 0보다 작음)"
    else:
        verdict = f"판단 불가 ({int((1 - alpha) * 100)}% 신뢰구간이 0을 포함)"
    notes = []
    if min(len(t), len(b)) < 3:
        notes.append("시드가 3개 미만이라 신뢰구간을 믿기 어렵습니다")
    return {
        "goal": goal, "improvement": improvement, "relative_improvement": rel,
        "ci_low": lo, "ci_high": hi, "confidence": 1 - alpha, "p_improve": p_improve,
        "hedges_g": None if g is None else sign * g, "n_treat": len(t), "n_base": len(b),
        "verdict": verdict, "notes": notes,
    }
