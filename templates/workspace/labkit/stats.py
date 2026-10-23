"""통계 도구 (표준 라이브러리만 사용). 시드 몇 개짜리 작은 실험에서도 정직하게 비교하기 위한 최소한의 도구.

    from labkit.stats import compare
    c = compare(treat=[0.71, 0.72, 0.70], base=[0.65, 0.66, 0.64], goal="max")
    c["verdict"]   # "개선 (95% 신뢰구간이 0보다 큼)" 등

- 차이는 항상 "개선량"으로 보고한다: goal="max"이면 처리-기준, goal="min"이면 기준-처리. 양수면 좋아진 것.
- 신뢰구간은 Welch t 구간이다 (두 조건의 분산이 달라도 된다). 부트스트랩 백분위 구간은 시드 3개에서
  효과가 없는데도 "개선"을 약 11% 내므로(명목 2.5%) 판정에 쓰지 않는다. 시드가 적으면 구간이 넓은 것이 정상이다.
- lab.py(캠페인 확인 실험)도 이 파일을 그대로 불러 쓴다. 판정 규칙은 여기 한 곳에만 둔다 — 표준 라이브러리만 쓸 것.
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
    """값 하나의 통계량에 대한 부트스트랩 신뢰구간 (탐색용). 표본이 10개 미만이면 구간이 실제보다 좁게 나오므로
    두 조건의 비교 판정에는 compare()를 쓴다."""
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return None
    rng = random.Random(seed)
    boots = sorted(stat([rng.choice(vals) for _ in vals]) for _ in range(n_boot))
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


# ---------------------------------------------------------------- t 분포 (정규화 불완전 베타 함수로 계산)

def _betacf(a: float, b: float, x: float) -> float:
    """불완전 베타 함수의 연분수 전개 (Lentz 방법)."""
    tiny, eps = 1e-300, 3e-14
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)),
                   -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """자유도 df인 t 분포의 누적 확률 P(T ≤ t)."""
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def t_ppf(p: float, df: float) -> float:
    """t 분포의 분위수 (이분법). 예: t_ppf(0.975, 4) ≈ 2.776."""
    if not 0.0 < p < 1.0:
        raise ValueError("p는 0과 1 사이여야 합니다")
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


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


def compare(treat: Sequence[float], base: Sequence[float], goal: str = "max", alpha: float = 0.05) -> dict:
    """처리(treat)가 기준(base)보다 나은지. 개선량 = (goal이 max면 treat-base, min이면 base-treat).
    신뢰구간은 Welch t 구간, p_value는 양측 Welch t 검정."""
    if goal not in ("max", "min"):
        raise ValueError("goal은 'max' 또는 'min'이어야 합니다")
    t = [float(v) for v in treat]
    b = [float(v) for v in base]
    if not t or not b:
        raise ValueError("비교할 값이 비어 있습니다")
    sign = 1.0 if goal == "max" else -1.0
    improvement = sign * (_mean(t) - _mean(b))
    conf = int(round((1 - alpha) * 100))
    notes: list[str] = []
    lo = hi = df = p_value = None
    if min(len(t), len(b)) >= 2:
        vt, vb = statistics.variance(t) / len(t), statistics.variance(b) / len(b)
        se = math.sqrt(vt + vb)
        if se > 0:
            df = (vt + vb) ** 2 / ((vt ** 2 / (len(t) - 1) if vt else 0.0) + (vb ** 2 / (len(b) - 1) if vb else 0.0))
            half = t_ppf(1 - alpha / 2, df) * se
            lo, hi = improvement - half, improvement + half
            p_value = min(1.0, 2.0 * (1.0 - t_cdf(abs(improvement) / se, df)))
        else:
            lo = hi = improvement
            p_value = 1.0 if improvement == 0 else 0.0
            notes.append("두 조건 모두 시드 간 변동이 0입니다 — 시드가 실제로 적용되는지 확인할 것")
    if lo is None:
        verdict = "판단 불가 (시드가 1개뿐이라 변동을 알 수 없음)"
    elif lo > 0:
        verdict = f"개선 ({conf}% 신뢰구간이 0보다 큼)"
    elif hi < 0:
        verdict = f"악화 ({conf}% 신뢰구간이 0보다 작음)"
    else:
        verdict = f"판단 불가 ({conf}% 신뢰구간이 0을 포함)"
    if min(len(t), len(b)) < 3:
        notes.append("시드가 3개 미만이라 신뢰구간을 믿기 어렵습니다")
    base_mean = _mean(b)
    g = hedges_g(t, b)
    return {
        "goal": goal, "method": "welch_t", "improvement": improvement,
        "relative_improvement": improvement / abs(base_mean) if base_mean else None,
        "ci_low": lo, "ci_high": hi, "confidence": 1 - alpha, "df": df, "p_value": p_value,
        "hedges_g": None if g is None else sign * g, "n_treat": len(t), "n_base": len(b),
        "verdict": verdict, "notes": notes,
    }
