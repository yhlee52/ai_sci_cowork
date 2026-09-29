"""labkit 단위 테스트 (torch 없이 도는 부분만)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates" / "workspace"))

from labkit import Run, bootstrap_ci, check_overlap, collect_results, compare, report_metric, seed_from_env, summarize  # noqa: E402


class TestStats(unittest.TestCase):
    def test_compare_directions(self):
        self.assertTrue(compare([0.71, 0.72, 0.70], [0.65, 0.66, 0.64], goal="max")["verdict"].startswith("개선"))
        self.assertTrue(compare([0.65, 0.66, 0.64], [0.71, 0.72, 0.70], goal="max")["verdict"].startswith("악화"))
        c = compare([1.0, 1.1, 0.9], [1.2, 1.3, 1.1], goal="min")
        self.assertGreater(c["improvement"], 0)
        self.assertTrue(compare([1.20, 1.25, 1.22], [1.21, 1.19, 1.24], goal="min")["verdict"].startswith("판단 불가"))

    def test_single_seed_is_never_conclusive(self):
        c = compare([0.9], [0.8], goal="max")
        self.assertTrue(c["verdict"].startswith("판단 불가"))
        self.assertTrue(c["notes"])

    def test_summarize_and_bootstrap(self):
        self.assertEqual(summarize([1, 2, 3])["mean"], 2.0)
        self.assertIsNone(bootstrap_ci([1.0]))
        lo, hi = bootstrap_ci([1, 2, 3, 4])
        self.assertLessEqual(lo, hi)


class TestLeakage(unittest.TestCase):
    def test_overlap(self):
        with redirect_stdout(io.StringIO()):
            r = check_overlap(["a", "b", "c"], ["c", "d"])
        self.assertEqual(r["overlap"], 1)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check_overlap(["a"], ["x"])["overlap"], 0)


class TestRunAndResults(unittest.TestCase):
    def test_collect_results_with_comparisons_and_pilot_excluded(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            for s in range(3):
                with Run(tmp, "baseline", s) as r:
                    r.finish(val_acc=0.60 + 0.01 * s)
                with Run(tmp, "wd", s) as r:
                    r.finish(val_acc=0.70 + 0.01 * s)
            with Run(tmp, "pilot-wd", 0) as r:
                r.finish(val_acc=0.99)
            try:
                with Run(tmp, "wd", 9) as r:
                    raise RuntimeError("실패 테스트")
            except RuntimeError:
                pass
            res = collect_results(tmp, "EXP-001", "가설", goal={"val_acc": "max"})
            self.assertEqual(res["status"], "partial")
            self.assertEqual(res["summary"]["wd"]["val_acc"]["n"], 3)
            self.assertNotIn("pilot-wd", res["summary"])
            self.assertTrue(res["comparisons"]["wd"]["val_acc"]["verdict"].startswith("개선"))
            saved = json.loads((Path(tmp) / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["exp_id"], "EXP-001")

    def test_metric_line_and_seed_env(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            report_metric("val_loss", 0.125)
        self.assertEqual(buf.getvalue().strip(), "LAB_METRIC val_loss=0.125")
        os.environ["LAB_SEED"] = "7"
        try:
            self.assertEqual(seed_from_env(), 7)
        finally:
            del os.environ["LAB_SEED"]


if __name__ == "__main__":
    unittest.main()
