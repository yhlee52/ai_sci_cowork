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

    def test_summary_kind_is_indexed(self):
        sid = lab(self.lab, "next", "summary").stdout.strip()
        self.assertEqual(sid, "SUM-001")
        (self.lab / "research/summaries/SUM-001-grokking.md").write_text(
            "# SUM-001: Grokking 논문 요약\n> status: done | tags: grokking | session: 001 | summary: 일반화가 늦게 온다\n"
            "근거: EXP-404\n", encoding="utf-8")
        self.assertIn("SUM-001 [요약/완료]", lab(self.lab, "find", "--type", "요약").stdout)
        self.assertIn("EXP-404", lab(self.lab, "lint").stdout)  # SUM 안의 ID도 참조 점검 대상

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
        g = self.tmp / "judge2.md"  # 두 번째 판정자: C1과 C3를 다르게 봤다
        g.write_text("C1 > C3\nC2 > C4\nC2 > C3\nC1 > C4\nC3 > C4\nC1 > C2\n", encoding="utf-8")
        out = lab(self.lab, "rank", "score", "--file", str(f), "--file", str(g)).stdout
        self.assertIn("판정자 2명, 경기 12개, 판정자끼리 엇갈린 쌍 2/6개", out)
        self.assertEqual([ln.split("|")[2].strip() for ln in out.splitlines()[3:]][0], "C1")

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

    def test_unpack_refuses_paths_outside_output(self):
        evil = self.tmp / "evil.md"
        evil.write_text("### 파일: ../escape.txt\n```\nx\n```\n\n### 파일: ok/inside.txt\n```\ny\n```\n", encoding="utf-8")
        out = self.tmp / "out" / "deep"
        r = lab(self.tmp, "unpack-md", str(evil), "--out", str(out))
        self.assertIn("건너뜀", r.stdout)
        self.assertFalse((self.tmp / "out" / "escape.txt").exists())
        self.assertTrue((out / "ok" / "inside.txt").exists())
        # 회사 PC에서 쓰는 복원 스크립트도 같은 규칙
        bundle = self.tmp / "bundle.md"
        (self.tmp / "s").mkdir()
        (self.tmp / "s" / "a.py").write_text("x = 1\n", encoding="utf-8")
        lab(self.tmp, "pack-md", "a.py", "--root", str(self.tmp / "s"), "--out", str(bundle))
        snippet = bundle.read_text(encoding="utf-8").split("````python\n", 1)[1].split("\n````", 1)[0]
        (self.tmp / "restore.py").write_text(snippet, encoding="utf-8")
        out2 = self.tmp / "out2" / "deep"
        subprocess.run([sys.executable, str(self.tmp / "restore.py"), str(evil), str(out2)], env=ENV,
                       capture_output=True, check=True)
        self.assertFalse((self.tmp / "out2" / "escape.txt").exists())
        self.assertTrue((out2 / "ok" / "inside.txt").exists())

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


class TestReport(unittest.TestCase):
    """HTML 리포트: 회의록의 결정, 지식베이스 항목, 실험 결과가 파일에서 그대로 모인다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.lab = make_lab(self.tmp)
        lab(self.lab, "next", "session")
        (self.lab / "meetings" / "session_001.md").write_text(
            "# Session 001\n\n## 회의 1 (plan): 첫 질문\n### 논의 요약\n- 이론 연구원 → H-001 제안\n"
            "### 답과 결정\n- D1 [C, 교수님] 조건은 두 개로 한다\n\n## 작업 로그\n- A-001 · 연구 엔지니어 · EXP-001 · 완료\n",
            encoding="utf-8")
        exp = self.lab / "research/experiments/EXP-001-ls"
        exp.mkdir(parents=True)
        (exp / "plan.md").write_text("# EXP-001: 비교\n> status: approved | session: 001 | metric: ece | goal: min\n", encoding="utf-8")
        summary = {"baseline": {"ece": {"mean": 0.0612, "std": 0.002, "n": 3}}, "ls01": {"ece": {"mean": 0.0317, "std": 0.002, "n": 3}}}
        comp = {"ls01": {"ece": {"improvement": 0.0295, "ci_low": 0.027, "ci_high": 0.032, "verdict": "개선 (95% 신뢰구간이 0보다 큼)"}}}
        (exp / "results.json").write_text(json.dumps({"exp_id": "EXP-001", "status": "complete", "hypothesis": "ECE가 줄어든다",
                                                      "runs": [], "summary": summary, "comparisons": comp, "gpu_minutes": 3.5},
                                                     ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def assert_valid_html(self, text: str) -> None:
        from html.parser import HTMLParser
        void = {"meta", "br", "img", "hr", "circle", "line", "rect", "polyline", "polygon"}
        stack = []

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag not in void:
                    stack.append(tag)

            def handle_endtag(self, tag):
                if tag not in void:
                    self_ok = stack and stack[-1] == tag
                    if not self_ok:
                        raise AssertionError(f"닫는 태그 불일치: {tag} (열린 태그 {stack[-3:]})")
                    stack.pop()
        P().feed(text)
        self.assertEqual(stack, [])

    def test_session_and_experiment_reports(self):
        out = lab(self.lab, "report").stdout
        self.assertIn("session_001.html", out)
        html_text = (self.lab / "reports" / "session_001.html").read_text(encoding="utf-8")
        self.assert_valid_html(html_text)
        for s in ("결정된 사항", "조건은 두 개로 한다", "주요 논의", "작업 기록", "실험 결과", "0.0612", "개선 (95% 신뢰구간이 0보다 큼)"):
            self.assertIn(s, html_text)
        lab(self.lab, "report", "EXP-001")
        exp_html = (self.lab / "reports" / "EXP-001.html").read_text(encoding="utf-8")
        self.assert_valid_html(exp_html)
        self.assertIn("<svg", exp_html)
        self.assertNotEqual(lab(self.lab, "report", "EXP-999", check=False).returncode, 0)

    def test_auto_respects_config(self):
        cfg_path = self.lab / "lab.config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["report"]["after_activities"] = False
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(lab(self.lab, "report", "--auto").stdout.strip(), "")
        self.assertFalse((self.lab / "reports").exists())


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
        self.assertIn("개선 (95% 신뢰구간이 0보다 큼)", out)  # 실험과 같은 판정 함수(labkit.stats, Welch t)
        confirm = json.loads((self.d / "confirm.json").read_text(encoding="utf-8"))
        self.assertEqual(confirm["method"], "welch_t")
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

        lab(self.lab, "report", "CMP-001")
        cmp_html = (self.lab / "reports" / "CMP-001.html").read_text(encoding="utf-8")
        self.assertIn("확인 실험", cmp_html)
        self.assertIn("<svg", cmp_html)
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

    PLAN = ("# EXP-001: 비교\n> status: draft | conditions: baseline, wd | seeds: 3 | metric: val_acc\n"
            "## 예측\n- 개선 0.05 이상\n## 성공 기준\n## 중단 기준\n")

    def _experiment(self) -> tuple[Path, dict]:
        from labkit import Run, collect_results
        e = self.lab / "research/experiments/EXP-001-wd"
        e.mkdir(parents=True, exist_ok=True)
        (e / "plan.md").write_text(self.PLAN, encoding="utf-8")
        lab(self.lab, "approve", "EXP-001", "--note", "테스트 승인")
        for c, b in (("baseline", 0.60), ("wd", 0.70)):
            for s in range(3):
                with Run(e, c, s, config={"lr": 0.003}) as r:
                    r.finish(val_acc=b + 0.01 * s)
        return e, collect_results(e, "EXP-001", "가설", goal={"val_acc": "max"})

    def test_numbers_with_korean_particles_are_checked(self):
        e, res = self._experiment()
        imp = res["comparisons"]["wd"]["val_acc"]["improvement"]
        (e / "report.md").write_text(f"# EXP-001: 보고서\n> status: reported\n개선은 {imp:.2f}로 확인됐고 기준선은 0.61이다.\n"
                                     "학습률 0.003, 예측 0.05, torch 2.5.1, Python 3.11, arXiv 2201.02177\n"
                                     "## 3.2 결과\n", encoding="utf-8")
        r = lab(self.lab, "audit", "EXP-001")
        self.assertIn("숫자 4개가 결과 파일과 일치합니다", r.stdout)  # 0.10, 0.61, 0.003(설정), 0.05(사전 등록)
        for fake in ("정확도가 0.93로 올랐다", "93%로 향상", "기준선보다 23점 높다", "효과 크기는 1.87이다"):
            (e / "report.md").write_text(f"# EXP-001: 보고서\n> status: reported\n{fake}\n", encoding="utf-8")
            r = lab(self.lab, "audit", "EXP-001", check=False)
            self.assertNotEqual(r.returncode, 0, fake)  # 지어낸 숫자는 경고가 아니라 실패
            self.assertIn("결과 파일에서 찾지 못했고 출처도 없습니다", r.stdout, fake)

    def test_sourced_numbers_are_listed_not_failed(self):
        e, _ = self._experiment()
        (e / "report.md").write_text("# EXP-001: 보고서\n> status: reported\n원 논문 보고치는 0.87이다 (P-001).\n"
                                     "| 데이터 크기 0.45백만 (출처: DS-001) | 기준선 0.61 |\n", encoding="utf-8")
        r = lab(self.lab, "audit", "EXP-001")
        self.assertIn("출처", r.stdout)
        self.assertIn("0.87", r.stdout)

    def test_source_mark_does_not_cover_the_whole_paragraph(self):
        e, _ = self._experiment()
        # 문단 하나 = 한 줄. 출처는 마지막 문장에만 붙었으므로 앞 문장의 지어낸 0.93은 실패해야 한다
        (e / "report.md").write_text("# EXP-001: 보고서\n> status: reported\n기준선은 0.61이고 우리 방법은 0.93이다. "
                                     "원 논문은 0.87을 보고했다 (출처: P-001 표 2).\n", encoding="utf-8")
        r = lab(self.lab, "audit", "EXP-001", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("0.93", r.stdout.split("[실패]")[1])
        self.assertNotIn("0.87", r.stdout.split("[실패]")[1])

    def test_prereg_tampering_and_early_runs_fail(self):
        from labkit import Run
        e = self.lab / "research/experiments/EXP-001-wd"
        e.mkdir(parents=True)
        (e / "plan.md").write_text(self.PLAN, encoding="utf-8")
        with self.assertRaises(PermissionError):  # 승인 전 본 실험은 labkit이 막는다
            with Run(e, "baseline", 0):
                pass
        with Run(e, "pilot-wd", 0) as r:  # 파일럿은 자율
            r.finish(val_acc=0.5)
        self.assertNotEqual(lab(self.lab, "approve", "EXP-404", check=False).returncode, 0)
        e, _ = self._experiment()
        out = lab(self.lab, "audit", "EXP-001").stdout
        self.assertIn("사전 등록 확인", out)
        self.assertIn("status: approved", (e / "plan.md").read_text(encoding="utf-8"))
        (e / "plan.md").write_text(self.PLAN.replace("0.05", "0.01"), encoding="utf-8")  # 결과를 본 뒤 예측을 고침
        r = lab(self.lab, "audit", "EXP-001", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("plan.md가 바뀌었습니다", r.stdout)
        lab(self.lab, "approve", "EXP-001", "--note", "예측 수정 승인")
        r = lab(self.lab, "audit", "EXP-001", check=False)
        self.assertIn("2번 승인", r.stdout)  # 다시 승인하면 통과하지만, 바꾼 사실은 경고로 남는다
        self.assertNotIn("전에 시작한 실행", r.stdout)  # 실행은 첫 승인 뒤에 시작됐다
        self.assertEqual(r.returncode, 0)

    def test_runs_before_approval_fail_audit(self):
        e, _ = self._experiment()
        rec = json.loads((e / "prereg.json").read_text(encoding="utf-8"))
        rec["approvals"][0]["at"] = "2099-01-01T00:00:00"  # 승인이 실행보다 늦은 경우
        (e / "prereg.json").write_text(json.dumps(rec), encoding="utf-8")
        r = lab(self.lab, "audit", "EXP-001", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("전에 시작한 실행", r.stdout)

    def test_audit_catches_plan_and_number_problems(self):
        from labkit import Run, collect_results
        e = self.lab / "research/experiments/EXP-001-wd"
        e.mkdir(parents=True)
        (e / "plan.md").write_text("# EXP-001: 비교\n> status: approved | conditions: baseline, wd, wd2 | seeds: 3 | metric: val_acc\n"
                                   "## 예측\n## 성공 기준\n## 중단 기준\n", encoding="utf-8")
        lab(self.lab, "approve", "EXP-001")
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
        self.assertNotIn(f"{imp:.3f}", r.stdout.split("출처도 없습니다")[-1])  # 진짜 숫자는 실패 목록에 없어야 한다


@unittest.skipUnless(os.environ.get("AI_LAB_NET") == "1", "네트워크 테스트는 AI_LAB_NET=1일 때만")
class TestLiterature(unittest.TestCase):
    def test_lookup_real_paper(self):
        out = lab(ROOT, "lit", "get", "2201.02177").stdout
        self.assertIn("Grokking", out)


if __name__ == "__main__":
    unittest.main()
