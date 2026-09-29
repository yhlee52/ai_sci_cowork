"""실행(run) 하나 = 폴더 하나. 설정, 로그, 지표 흐름, 최종 지표를 남긴다.

    with Run(exp_dir, condition="baseline", seed=0, config=cfg, max_minutes=30) as run:
        for step in ...:
            run.log(step, loss=..., val_acc=...)      # metrics.jsonl에 추가 (+ 로그 한 줄)
            if run.over_budget(): break               # 계산 예산을 지킨다
        run.finish(val_acc=best)                      # metrics.json {"final": {...}} 저장

finish() 없이 블록을 벗어나면(예: 예외 발생) 상태가 "failed"로 기록된다.
지표를 지어내거나 채워 넣지 않는다 — 실패한 실행은 실패로 남긴다.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .limits import apply_vram_cap, lab_limits, peak_vram_gb, reset_peak_vram
from .repro import env_info, git_commit, seed_everything

STATUS_KO = {"complete": "완료", "partial": "부분 완료", "failed": "실패", "running": "실행 중"}


class Run:
    def __init__(self, exp_dir: str | Path, condition: str, seed: int, config: dict | None = None,
                 max_minutes: float | None = None, run_id: str | None = None, set_seed: bool = True):
        self.exp_dir = Path(exp_dir)
        self.condition, self.seed = condition, seed
        self.run_id = run_id or f"{condition}-s{seed}"
        self.dir = self.exp_dir / "runs" / self.run_id
        self.config = dict(config or {})
        self.max_seconds = max_minutes * 60 if max_minutes else None
        self.status = "running"
        self.final: dict = {}
        self.peak_vram_gb: float | None = None
        self._set_seed = set_seed

    # 컨텍스트 매니저 ----------------------------------------------------------
    def __enter__(self) -> "Run":
        self.dir.mkdir(parents=True, exist_ok=True)
        if self._set_seed:
            seed_everything(self.seed)
        apply_vram_cap()  # torch를 쓰는 실행이면 VRAM을 연구실 예산 안으로 묶는다
        reset_peak_vram()
        self.t0 = time.time()
        meta = {"run_id": self.run_id, "condition": self.condition, "seed": self.seed,
                "config": self.config, "git": git_commit(), "env": env_info(), "limits": lab_limits(),
                "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        (self.dir / "config.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger = logging.getLogger(f"labkit.{self.run_id}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        fh = logging.FileHandler(self.dir / "train.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.logger.addHandler(fh)
        self._metrics = open(self.dir / "metrics.jsonl", "a", encoding="utf-8")
        self.logger.info(f"시작 {self.run_id} 설정={self.config}")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.logger.exception("실행 실패")
            self.status = "failed"
        elif self.status == "running":
            self.status = "failed"
            self.logger.info("finish() 없이 종료됨 → 실패로 기록")
        try:
            self.peak_vram_gb = peak_vram_gb()
        except Exception:
            self.peak_vram_gb = None
        self._write_final(error=repr(exc) if exc else None)
        self._metrics.close()
        for h in list(self.logger.handlers):
            h.close()
            self.logger.removeHandler(h)
        vram = f" 최대 VRAM {self.peak_vram_gb}GB" if self.peak_vram_gb is not None else ""
        print(f"[{self.run_id}] {STATUS_KO.get(self.status, self.status)} {self.wall_minutes:.1f}분{vram} " +
              " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in self.final.items()))
        return False  # 예외를 삼키지 않는다

    # 사용 함수 ----------------------------------------------------------------
    @property
    def wall_minutes(self) -> float:
        return (time.time() - self.t0) / 60

    def over_budget(self) -> bool:
        return self.max_seconds is not None and time.time() - self.t0 > self.max_seconds

    def log(self, step: int, **metrics) -> None:
        rec = {"step": step, "t": round(time.time() - self.t0, 2), **{k: _num(v) for k, v in metrics.items()}}
        self._metrics.write(json.dumps(rec) + "\n")
        self._metrics.flush()
        self.logger.info(" ".join(f"{k}={v}" for k, v in rec.items()))

    def finish(self, status: str = "complete", **final_metrics) -> None:
        self.final = {k: _num(v) for k, v in final_metrics.items()}
        self.status = "partial" if (status == "complete" and self.over_budget()) else status

    def _write_final(self, error: str | None) -> None:
        out = {"run_id": self.run_id, "condition": self.condition, "seed": self.seed, "status": self.status,
               "final": self.final, "wall_min": round(self.wall_minutes, 2)}
        if self.peak_vram_gb is not None:
            out["peak_vram_gb"] = self.peak_vram_gb
        if error:
            out["error"] = error
        (self.dir / "metrics.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


def _num(v):
    try:
        import torch
        if isinstance(v, torch.Tensor):
            return v.item()
    except ImportError:
        pass
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
