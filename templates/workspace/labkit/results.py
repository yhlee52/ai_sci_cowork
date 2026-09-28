"""실행 기록에서 results.json을 만든다. 보고하는 숫자는 항상 코드가 만들고, 손으로 쓰지 않는다."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


def collect_results(exp_dir: str | Path, exp_id: str, hypothesis: str, setup: dict | None = None,
                    notes: str = "") -> dict:
    """hypothesis, setup의 설명 문장과 notes는 한글로 쓴다."""
    exp_dir = Path(exp_dir)
    runs = []
    for mfile in sorted((exp_dir / "runs").glob("*/metrics.json")):
        m = json.loads(mfile.read_text(encoding="utf-8"))
        if str(m["condition"]).startswith("pilot"):
            continue  # 파일럿은 코드가 도는지 확인하는 용도이고, 증거가 아니다
        runs.append({"run_id": m["run_id"], "condition": m["condition"], "seed": m["seed"],
                     "status": m["status"], "metrics": m.get("final", {}), "wall_min": m.get("wall_min")})
    ok = [r for r in runs if r["status"] == "complete"]
    summary: dict = {}
    for r in ok:
        for k, v in r["metrics"].items():
            if isinstance(v, (int, float)):
                summary.setdefault(r["condition"], {}).setdefault(k, []).append(v)
    for cond, metrics in summary.items():
        for k, vals in metrics.items():
            metrics[k] = {"mean": statistics.fmean(vals),
                          "std": statistics.stdev(vals) if len(vals) > 1 else 0.0, "n": len(vals)}
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
           "runs": runs, "summary": summary, "notes": notes,
           "gpu_minutes": round(sum(r["wall_min"] or 0 for r in runs), 2)}
    (exp_dir / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return res
