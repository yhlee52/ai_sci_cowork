"""lab.py 통합 테스트 (표준 라이브러리 unittest). 네트워크가 필요한 문헌 테스트는 AI_LAB_NET=1일 때만 돈다.

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB_PY = ROOT / "scripts" / "lab.py"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
ENV.pop("AI_LAB_DIR", None)
ENV.pop("CLAUDE_PROJECT_DIR", None)


def lab(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, str(LAB_PY), *args], cwd=str(cwd), env=ENV,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise AssertionError(f"lab.py {' '.join(args)} 실패 ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


def make_lab(tmp: Path, name: str = "lab") -> Path:
    d = tmp / name
    lab(tmp, "init", str(d), "--topic", "테스트 주제")
    return d


class TestBasics(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.lab = make_lab(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_init_refuses_non_empty(self):
        r = lab(self.tmp, "init", str(self.lab), check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_ids_actions_inbox(self):
        self.assertEqual(lab(self.lab, "next", "exp").stdout.strip(), "EXP-001")
        self.assertEqual(lab(self.lab, "next", "exp").stdout.strip(), "EXP-002")
        aid = lab(self.lab, "action", "add", "--owner", "engineer", "--title", "파일럿").stdout.strip()
        self.assertEqual(aid, "A-001")
        lab(self.lab, "action", "done", aid, "--result", "완료")
        self.assertIn("남은 할 일 없음", lab(self.lab, "action", "list").stdout)
        qid = lab(self.lab, "inbox", "add", "--question", "승인할까요?", "--options", "예|아니오").stdout.strip()
        self.assertIn("교수님 결정 대기", lab(self.lab, "status", "--hook").stdout)
        lab(self.lab, "inbox", "resolve", qid, "--answer", "예")
        self.assertNotIn("교수님 결정 대기", lab(self.lab, "status", "--hook").stdout)

    def test_find_with_korean_filters(self):
        (self.lab / "kb/hypotheses/H-001.json").write_text(json.dumps(
            {"id": "H-001", "title": "감쇠 가설", "summary": "요약", "status": "testing", "tags": ["wd"]},
            ensure_ascii=False), encoding="utf-8")
        out = lab(self.lab, "find", "--type", "가설", "--status", "검증 중").stdout
        self.assertIn("H-001 [가설/검증 중]", out)
        self.assertIn("H-001", lab(self.lab, "find", "--type", "hypothesis").stdout)

    def test_status_silent_outside_lab(self):
        r = lab(self.tmp, "status", "--hook")
        self.assertEqual(r.stdout.strip(), "")

    def test_rank_bradley_terry(self):
        f = self.tmp / "judge.md"
        f.write_text("1. C3 > C1 | 이유\n2. C2 > C4\n3. C3 > C2\n4. C1 > C4\n5. C3 > C4\n6. C2 < C1\n", encoding="utf-8")
        lines = lab(self.lab, "rank", "score", "--file", str(f)).stdout.splitlines()
        order = [ln.split("|")[2].strip() for ln in lines[2:]]
        self.assertEqual(order, ["C3", "C1", "C2", "C4"])
        sched = lab(self.lab, "rank", "schedule", "A", "B", "C").stdout
        self.assertEqual(sum(1 for ln in sched.splitlines() if " vs " in ln), 3)

    def test_pack_unpack_roundtrip(self):
        src = self.tmp / "src"
        (src / "pkg").mkdir(parents=True)
        (src / "pkg" / "a.py").write_text("x = 1\n```\nno newline", encoding="utf-8")
        (src / "b.md").write_text("# 제목\n\n````python\nprint(1)\n````\n", encoding="utf-8")
        (src / "runs").mkdir()
        (src / "runs" / "skip.txt").write_text("skip", encoding="utf-8")
        md = self.tmp / "bundle.md"
        lab(self.tmp, "pack-md", "pkg", "b.md", "runs", "--root", str(src), "--out", str(md))
        out = self.tmp / "out"
        lab(self.tmp, "unpack-md", str(md), "--out", str(out))
        self.assertEqual((out / "pkg" / "a.py").read_text(encoding="utf-8"), "x = 1\n```\nno newline\n")
        self.assertEqual((out / "b.md").read_text(encoding="utf-8"), (src / "b.md").read_text(encoding="utf-8"))
        self.assertFalse((out / "runs").exists())

    def test_lint_flags_rule_violations(self):
        (self.lab / "kb/findings/F-001.json").write_text(json.dumps(
            {"id": "F-001", "title": "결과", "status": "accepted", "refs": ["H-404"], "evidence": []},
            ensure_ascii=False), encoding="utf-8")
        out = lab(self.lab, "lint").stdout
        self.assertIn("교수님 결정 기록", out)
        self.assertIn("H-404", out)
        self.assertIn("증거", out)

    def test_digest_and_map(self):
        (self.lab / "kb/findings/F-001.json").write_text(json.dumps(
            {"id": "F-001", "title": "효과 없음", "status": "provisional", "result_type": "null",
             "refs": [], "evidence": ["x"], "summary": "영 결과"}, ensure_ascii=False), encoding="utf-8")
        lab(self.lab, "digest")
        self.assertIn("효과 없음·부정적 결과", (self.lab / "kb/digest.md").read_text(encoding="utf-8"))
        lab(self.lab, "map")
        self.assertIn("flowchart TD", (self.lab / "kb/map.md").read_text(encoding="utf-8"))


TRAIN = """import json, os, random
LR = 0.1
seed = int(os.environ.get("LAB_SEED", 0))
random.seed(seed)
loss = (LR - 0.3) ** 2 + random.uniform(-0.0005, 0.0005)
json.dump({"loss": loss}, open("out.json", "w"))
print("학습 완료")
"""
EVALUATE = """import json
print(f"LAB_METRIC val_loss={json.load(open('out.json'))['loss']}")
"""


class TestStateSafety(unittest.TestCase):
    """병렬 agent가 lab.py를 동시에 불러도 ID와 대기함이 깨지지 않는지, 쓰기가 원자적인지."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.lab = make_lab(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_parallel_calls_keep_ids_unique(self):
        cmds = [["next", "idea"]] * 10 + [["inbox", "add", "--question", f"질문 {i}"] for i in range(6)]
        procs = [subprocess.Popen([sys.executable, str(LAB_PY), *c], cwd=str(self.lab), env=ENV,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                 for c in cmds]
        outs = [p.communicate(timeout=120) for p in procs]
        self.assertTrue(all(p.returncode == 0 for p in procs), [o[1] for o in outs])
        ideas = [o[0].strip() for o, c in zip(outs, cmds) if c[0] == "next"]
        self.assertEqual(sorted(ideas), [f"IDEA-{i:03d}" for i in range(1, 11)])
        asks = json.loads((self.lab / "state" / "inbox.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(q["id"] for q in asks), [f"ASK-{i:03d}" for i in range(1, 7)])
        self.assertFalse((self.lab / "state" / ".lock").exists())
        self.assertEqual(list(self.lab.rglob(".*.tmp")), [])

    def test_stale_lock_is_cleared(self):
        lock = self.lab / "state" / ".lock"
        lock.write_text("", encoding="utf-8")
        old = time.time() - 600
        os.utime(lock, (old, old))
        self.assertEqual(lab(self.lab, "next", "exp").stdout.strip(), "EXP-001")
        self.assertFalse(lock.exists())

    def test_reads_do_not_rewrite_index(self):
        index = self.lab / "kb" / "index.json"
        index.unlink(missing_ok=True)
        lab(self.lab, "find", "아무거나")
        lab(self.lab, "show", "S-001", check=False)
        self.assertFalse(index.exists())
        lab(self.lab, "index")
        before = index.stat().st_mtime_ns
        time.sleep(0.05)
        lab(self.lab, "index")
        self.assertEqual(index.stat().st_mtime_ns, before)  # 내용이 같으면 다시 쓰지 않는다


def load_lab_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("lab_module", LAB_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHardware(unittest.TestCase):
    """하드웨어 탐색 → 운영 제약(compute.limits) 자동 설정."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.lab = make_lab(self.tmp)
        self.cfg_path = self.lab / "lab.config.json"

    def tearDown(self):
        self._tmp.cleanup()

    def cfg(self) -> dict:
        return json.loads(self.cfg_path.read_text(encoding="utf-8"))

    def test_init_detects_and_sets_limits(self):
        comp = self.cfg()["compute"]
        self.assertIn(comp["hardware"]["accelerator"], ("cuda", "mps", "cpu"))
        self.assertEqual(comp["limits"]["device"], comp["hardware"]["accelerator"])
        for key in ("precision", "max_train_params_m", "parallel_runs", "dataloader_workers"):
            self.assertIn(key, comp["limits"])
        out = lab(self.lab, "hw").stdout
        self.assertIn("운영 제약", out)

    def test_overrides_win_and_unknown_keys_warn(self):
        cfg = self.cfg()
        cfg["compute"]["overrides"] = {"dataloader_workers": 3, "없는키": 1}
        self.cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        out = lab(self.lab, "hardware").stdout
        self.assertEqual(self.cfg()["compute"]["limits"]["dataloader_workers"], 3)
        self.assertIn("없는키", out)

    def test_other_pc_triggers_redetection(self):
        cfg = self.cfg()
        cfg["compute"]["hardware"]["machine_id"] = "other-pc"
        self.cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        out = lab(self.lab, "status", "--hook").stdout
        self.assertIn("새로 탐색", out)
        self.assertNotEqual(self.cfg()["compute"]["hardware"]["machine_id"], "other-pc")
        self.assertNotIn("새로 탐색", lab(self.lab, "status", "--hook").stdout)  # 같은 PC면 다시 탐색하지 않는다

    def test_derive_limits_rules(self):
        m = load_lab_module()
        gpu = {"accelerator": "cuda", "os": "Windows 10", "cpu_cores": 12, "ram_gb": 32.0,
               "gpus": [{"name": "RTX 3060 Ti", "vram_gb": 8.0, "compute_cap": "8.6"}]}
        lim = m.derive_limits(gpu)
        self.assertEqual((lim["precision"], lim["vram_budget_gb"], lim["max_train_params_m"]), ("bf16", 7.2, 200))
        self.assertEqual((lim["parallel_runs"], lim["dataloader_workers"]), (1, 0))
        old = dict(gpu, os="Linux 6.1", gpus=[{"name": "T4", "vram_gb": 16.0, "compute_cap": "7.5"}])
        lim = m.derive_limits(old)
        self.assertEqual((lim["precision"], lim["dataloader_workers"]), ("fp16", 6))
        cpu = {"accelerator": "cpu", "os": "Linux 6.1", "cpu_cores": 4, "ram_gb": 16.0, "gpus": []}
        lim = m.derive_limits(cpu, {"max_train_params_m": 3})
        self.assertNotIn("vram_budget_gb", lim)
        self.assertEqual((lim["precision"], lim["max_train_params_m"]), ("fp32", 3))


class TestCampaign(unittest.TestCase):
    """제안은 AI, 판정은 코드: 채택/기각/규칙 위반/실패/가짜 지표/멈춤/확인 실험/장부 위조 탐지."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.lab = make_lab(self.tmp)
        src = self.lab / "research/experiments/EXP-001-lr/src"
        src.mkdir(parents=True)
        (src / "train.py").write_text(TRAIN, encoding="utf-8")
        (src / "evaluate.py").write_text(EVALUATE, encoding="utf-8")
        py = f'"{sys.executable}"'
        lab(self.lab, "campaign", "init", "--from", str(src), "--title", "학습률 탐색", "--slug", "lr",
            "--metric", "val_loss", "--goal", "min", "--run", f"{py} train.py", "--eval", f"{py} evaluate.py",
            "--editable", "train.py", "--protected", "evaluate.py", "--trial-minutes", "1",
            "--max-trials", "6", "--patience", "4")
        self.d = next((self.lab / "research/campaigns").glob("CMP-001*"))
        self.work = self.d / "work" / "train.py"

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, old: str, new: str, append: str = "") -> None:
        t = self.work.read_text(encoding="utf-8").replace(old, new) + append
        self.work.write_text(t, encoding="utf-8")

    def trial(self, old: str, new: str, desc: str, append: str = "") -> str:
        lab(self.lab, "campaign", "begin", "CMP-001")
        self.edit(old, new, append)
        return lab(self.lab, "campaign", "run", "CMP-001", "--desc", desc).stdout

    def test_full_flow(self):
        self.assertNotEqual(lab(self.lab, "campaign", "begin", "CMP-001", check=False).returncode, 0)  # 승인 전
        for _ in range(3):
            lab(self.lab, "campaign", "baseline", "CMP-001")
        st = json.loads((self.d / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(st["baseline_done"])
        self.assertGreater(st["delta"], 0)
        lab(self.lab, "campaign", "approve", "CMP-001", "--note", "테스트 승인")

        self.assertIn("T-001 채택", self.trial("LR = 0.1", "LR = 0.25", "개선"))
        self.assertIn("T-002 기각", self.trial("LR = 0.25", "LR = 0.9", "악화"))
        lab(self.lab, "campaign", "begin", "CMP-001")
        (self.d / "work" / "evaluate.py").write_text('print("LAB_METRIC val_loss=0.0")\n', encoding="utf-8")
        self.edit("LR = 0.25", "LR = 0.26")
        self.assertIn("규칙 위반", lab(self.lab, "campaign", "run", "CMP-001", "--desc", "평가 조작").stdout)
        self.assertIn("실행 실패", self.trial("LR = 0.25", "LR = undefined_name", "오타"))
        out = self.trial("LR = 0.25", "LR = 0.29", "가짜 지표", append='print("LAB_METRIC val_loss=-99")\n')
        self.assertIn("T-005 채택", out)
        self.assertNotIn("-99", out.split("|")[1])  # 평가 명령의 출력만 믿는다
        out = self.trial('print("학습 완료")\n', "", "줄 삭제")
        self.assertIn("채택(단순화)", out)
        self.assertIn("판정: 종료", out)

        for _ in range(6):
            out = lab(self.lab, "campaign", "confirm", "CMP-001").stdout
        self.assertIn("개선 확인", out)
        self.assertEqual(lab(self.lab, "verify", "CMP-001").returncode, 0)

        ledger = self.d / "ledger.tsv"
        original = ledger.read_text(encoding="utf-8")
        forged = original.replace("\tdiscard\t", "\tkeep\t", 1)
        self.assertNotEqual(forged, original)
        ledger.write_text(forged, encoding="utf-8")
        r = lab(self.lab, "verify", "CMP-001", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("규칙 재계산", r.stdout)
        ledger.write_text(original, encoding="utf-8")

        self.assertIn("CMP-001", lab(self.lab, "status", "--hook").stdout)
        lab(self.lab, "campaign", "close", "CMP-001", "--note", "리뷰 완료")
        self.assertNotIn("CMP-001 [", lab(self.lab, "status", "--hook").stdout)

    def test_trial_minutes_limit(self):
        src = self.lab / "research/experiments/EXP-001-lr/src"
        r = lab(self.lab, "campaign", "init", "--from", str(src), "--title", "x", "--metric", "m", "--goal", "min",
                "--run", "python train.py", "--editable", "train.py", "--trial-minutes", "30", check=False)
        self.assertNotEqual(r.returncode, 0)


class TestAudit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.lab = make_lab(Path(self._tmp.name))
        sys.path.insert(0, str(self.lab))

    def tearDown(self):
        sys.path.remove(str(self.lab))
        for m in [m for m in sys.modules if m == "labkit" or m.startswith("labkit.")]:
            del sys.modules[m]
        self._tmp.cleanup()

    def test_audit_catches_plan_and_number_problems(self):
        from labkit import Run, collect_results
        e = self.lab / "research/experiments/EXP-001-wd"
        e.mkdir(parents=True)
        (e / "plan.md").write_text("# EXP-001: 비교\n> status: approved | conditions: baseline, wd, wd2 | seeds: 3 | metric: val_acc\n"
                                   "## 예측\n## 성공 기준\n## 중단 기준\n", encoding="utf-8")
        for c, b in (("baseline", 0.60), ("wd", 0.70)):
            for s in range(3):
                with Run(e, c, s) as r:
                    r.finish(val_acc=b + 0.01 * s)
        res = collect_results(e, "EXP-001", "가설", goal={"val_acc": "max"})
        imp = res["comparisons"]["wd"]["val_acc"]["improvement"]
        (e / "report.md").write_text(f"# EXP-001: 보고서\n> status: reported\n개선 {imp:.3f}, 기준선 0.61, 지어낸 값 0.93\n",
                                     encoding="utf-8")
        r = lab(self.lab, "audit", "EXP-001", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("wd2", r.stdout)
        self.assertIn("0.93", r.stdout)
        self.assertNotIn(f"{imp:.3f},", r.stdout.split("찾지 못했습니다")[-1])


@unittest.skipUnless(os.environ.get("AI_LAB_NET") == "1", "네트워크 테스트는 AI_LAB_NET=1일 때만")
class TestLiterature(unittest.TestCase):
    def test_lookup_real_paper(self):
        out = lab(ROOT, "lit", "get", "2201.02177").stdout
        self.assertIn("Grokking", out)


if __name__ == "__main__":
    unittest.main()
