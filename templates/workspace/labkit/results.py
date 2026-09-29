"""실행 기록에서 results.json을 만든다. 보고하는 숫자는 항상 코드가 만들고, 손으로 쓰지 않는다."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from .stats import compare


def collect_results(exp_dir: str | Path, exp_id: str, hypothesis: str, setup: dict | None = None,
                    notes: str = "", baseline: str | None = "baseline", goal: dict[str, str] | str | None = None) -> dict:
    """hypothesis, setup의 설명 문장과 notes는 한글로 쓴다.

    baseline: 기준 조건 이름. 그 조건이 있고 goal이 주어지면, 다른 조건마다 기준 대비 개선량과
              부트스트랩 95% 신뢰구간을 `comparisons`에 넣는다 (보고서의 차이 수치는 여기서 가져온다).
    goal: 지표별 방향. 예: {"val_acc": "max", "val_loss": "min"} 또는 모든 지표에 같은 "max"/"min".
    """
    exp_dir = Path(exp_dir)
    runs = []
    for mfile in sorted((exp_dir / "runs").glob("*/metrics.json")):
        m = json.loads(mfile.read_text(encoding="utf-8"))
        if str(m["condition"]).startswith("pilot"):
            continue  # 파일럿은 코드가 도는지 확인하는 용도이고, 증거가 아니다
        runs.append({"run_id": m["run_id"], "condition": m["condition"], "seed": m["seed"],
                     "status": m["status"], "metrics": m.get("final", {}), "wall_min": m.get("wall_min"),
                     "peak_vram_gb": m.get("peak_vram_gb")})
    ok = [r for r in runs if r["status"] == "complete"]
    values: dict[str, dict[str, list[float]]] = {}
    for r in ok:
        for k, v in r["metrics"].items():
            if isinstance(v, (int, float)):
                values.setdefault(r["condition"], {}).setdefault(k, []).append(float(v))
    summary = {cond: {k: {"mean": statistics.fmean(vals), "std": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                          "n": len(vals)} for k, vals in metrics.items()}
               for cond, metrics in values.items()}
    comparisons: dict = {}
    if baseline and baseline in values and goal:
        for cond, metrics in values.items():
            if cond == baseline:
                continue
            for k, vals in metrics.items():
                direction = goal.get(k) if isinstance(goal, dict) else goal
                if direction not in ("max", "min") or k not in values[baseline]:
                    continue
                comparisons.setdefault(cond, {})[k] = compare(vals, values[baseline][k], goal=direction)
    if not runs:
        status = "failed"
    elif len(ok) == len(runs):
        status = "complete"
    elif ok:
        status = "partial"
    else:
        status = "failed"
    failed = [r["run_id"] for r in runs if r["status"] != "complete"]
    if failed:
        notes = (notes + " " if notes else "") + f"완료되지 않은 실행은 요약에서 제외함: {failed}"
    res = {"exp_id": exp_id, "status": status, "hypothesis": hypothesis, "setup": setup or {},
           "runs": runs, "summary": summary, "baseline": baseline if comparisons else None,
           "comparisons": comparisons, "notes": notes,
           "gpu_minutes": round(sum(r["wall_min"] or 0 for r in runs), 2),
           "peak_vram_gb": max((r["peak_vram_gb"] for r in runs if r["peak_vram_gb"] is not None), default=None)}
    (exp_dir / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return res
