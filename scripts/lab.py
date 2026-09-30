#!/usr/bin/env python3
"""ai-lab 워크스페이스 도구 (Python 표준 라이브러리만 사용).

ID 발급, 할 일, 결정 대기함, 지식베이스 색인과 검색을 결정적으로 처리해서
agent가 필요한 것만 읽도록 돕는다. 모든 출력은 한글이다.

  lab.py init <경로> [--name 이름] [--topic 주제] [--git]   새 연구실 만들기
  lab.py next <종류>                   새 ID 발급 (종류는 KINDS 참고)
  lab.py status [--hook]               연구실 현황 (세션 시작 hook이 사용)
  lab.py action add|done|list ...      할 일(action item)
  lab.py inbox add|resolve|list ...    교수님 결정 대기함 (C 등급)
  lab.py index                         kb/index.json 다시 만들기 (캐시, 권위는 개별 파일)
  lab.py find [검색어] [--type T] [--status S] [--tag X] [--limit N]
  lab.py show <ID>                     항목 하나 보기
  lab.py context <ID>                  항목 + 참조하는/참조되는 항목의 한 줄 요약
  lab.py history <ID>                  세션 로그에서 그 항목이 바뀐 이력
  lab.py verify <EXP-id>               실험 감사: 사전 등록 + results.json이 실행 기록과 일치하는지
  lab.py digest                        kb/digest.md 다시 만들기 (연구실이 아는 것 1쪽)
  lab.py pack-md <경로들> --out 묶음.md  코드 파일들을 복원 가능한 md 하나로 묶기 (회사로는 md만 가져갈 수 있다)
  lab.py unpack-md 묶음.md --out 폴더    md 묶음에서 원래 파일 복원
  lab.py campaign init|approve|baseline|begin|run|status|confirm|stop   자율 탐색 캠페인 (판정은 코드가)
  lab.py rank schedule C1 C2 ... / rank score --file 판정.md    쌍대 비교 순위 (아이디어 토너먼트)
  lab.py lit search|get|check           문헌 검색, 논문 조회, 논문 항목의 실존 확인 (arXiv, Semantic Scholar)
  lab.py audit <EXP-id|CMP-id>          검증 + 계획 대조 + 보고서 숫자 대조
  lab.py lint                           지식베이스 무결성 점검
  lab.py doctor [--torch]               실험 환경 진단
  lab.py map                            연구 지도(mermaid) 만들기 → kb/map.md
  lab.py report [세션|EXP-id|CMP-id] [--open]  결정·결과·실험을 모은 HTML 리포트 → reports/
  lab.py hardware [--refresh]           이 PC의 하드웨어 탐색 → 운영 제약(compute.limits) 자동 설정

연구실 루트 = 현재 폴더에서 위로 올라가며 lab.config.json이 있는 첫 폴더
(--lab 경로 또는 환경 변수 AI_LAB_DIR로 지정 가능).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import difflib
import hashlib
import itertools
import json
import math
import os
import platform
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PLUGIN_ROOT / "templates" / "workspace"
SELF = Path(__file__).resolve()
CONFIG = "lab.config.json"

# 종류 -> (ID 접두어, 지식베이스 type 또는 None)
KINDS = {
    "session": ("", None),
    "action": ("A-", None),
    "task": ("TASK-", "task"),
    "idea": ("IDEA-", "idea"),
    "lit": ("LIT-", "lit"),
    "exp": ("EXP-", "experiment"),
    "rev": ("REV-", "review"),
    "hypothesis": ("H-", "hypothesis"),
    "finding": ("F-", "finding"),
    "question": ("Q-", "question"),
    "decision": ("D-", "decision"),
    "paper": ("P-", "paper"),
    "dataset": ("DS-", "dataset"),
    "method": ("M-", "method"),
    "lesson": ("L-", "lesson"),
    "brainstorm": ("BS-", "brainstorm"),
    "release": ("REL-", "release"),
    "campaign": ("CMP-", "campaign"),
    "ask": ("ASK-", None),
}
# kb/<폴더>/<ID>.json 형태의 항목
KB_DIRS = {
    "hypothesis": "kb/hypotheses",
    "finding": "kb/findings",
    "question": "kb/questions",
    "decision": "kb/decisions",
    "paper": "kb/papers",
    "dataset": "kb/datasets",
    "method": "kb/methods",
    "lesson": "kb/lessons",
}
# 마크다운 파일, 또는 DIR_SUMMARY 중 처음 있는 파일에 요약이 있는 폴더
ARTIFACT_GLOBS = {
    "idea": "research/ideas/IDEA-*.md",
    "lit": "research/literature/LIT-*.md",
    "review": "research/reviews/REV-*.md",
    "task": "briefs/TASK-*.md",
    "experiment": "research/experiments/EXP-*",
    "brainstorm": "research/brainstorms/BS-*",
    "release": "research/releases/REL-*",
    "campaign": "research/campaigns/CMP-*",
}
DIR_SUMMARY = ("plan.md", "campaign.md", "summary.md", "report.md", "README.md")
ID_RE = re.compile(r"\b(?:IDEA|LIT|EXP|REV|TASK|ASK|REL|CMP|BS|DS|H|F|Q|D|P|M|A|L)-\d{3,}\b")
PREREG_KEYS = {  # 본 실험 전에 plan.md 제목(#)에 각 묶음의 단어가 하나씩 있어야 한다
    "예측": ("예측", "prediction"),
    "성공 기준": ("성공 기준", "success"),
    "중단 기준": ("중단 기준", "kill"),
}
TEXT_SUFFIXES = {".md", ".json", ".txt", ".toml", ""}

# 파일에는 영어 기계 표기로 저장하고, 화면에는 한글로 보여 준다
TYPE_KO = {
    "hypothesis": "가설", "finding": "결과", "question": "질문", "decision": "결정", "paper": "논문",
    "dataset": "데이터셋", "method": "방법", "lesson": "교훈", "idea": "아이디어", "lit": "문헌조사",
    "experiment": "실험", "review": "리뷰", "task": "과업", "brainstorm": "브레인스토밍",
    "release": "릴리스", "session": "세션", "campaign": "캠페인",
}
STATUS_KO = {
    "proposed": "제안됨", "testing": "검증 중", "supported": "지지됨", "refuted": "반박됨",
    "inconclusive": "결론 없음", "abandoned": "폐기됨", "provisional": "잠정", "accepted": "확정",
    "superseded": "대체됨", "open": "열림", "narrowed": "좁혀짐", "answered": "답변됨", "dropped": "중단됨",
    "in_force": "유효", "revised": "수정됨", "revoked": "철회됨", "skimmed": "훑어봄", "read": "읽음",
    "key": "핵심", "candidate": "후보", "in_use": "사용 중", "retired": "사용 종료", "implemented": "구현됨",
    "baseline": "베이스라인", "active": "유효", "obsolete": "폐기됨", "draft": "초안", "planned": "계획됨",
    "pilot-done": "파일럿 완료", "approved": "승인됨", "complete": "완료", "partial": "부분 완료",
    "failed": "실패", "empty": "비어 있음", "reported": "보고됨", "accept": "수용", "minor": "경미한 수정",
    "major": "대폭 수정", "reject": "거절", "done": "완료", "decided": "결정됨", "released": "배포됨",
    "logged": "기록됨", "running": "진행 중", "stopped": "종료됨", "confirmed": "확인 실험 완료", "closed": "닫힘",
    "keep": "채택", "keep-simpler": "채택(단순화)", "discard": "기각", "crash": "실행 실패",
    "timeout": "시간 초과", "invalid": "규칙 위반",
}
TYPE_FROM_KO = {v: k for k, v in TYPE_KO.items()}
STATUS_FROM_KO = {v: k for k, v in STATUS_KO.items()}


def ko_type(t: str) -> str:
    return TYPE_KO.get(t, t)


def ko_status(s: str) -> str:
    return STATUS_KO.get(s, s)


for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def today() -> str:
    return dt.date.today().isoformat()


def find_lab(explicit: str | None) -> Path | None:
    for c in (explicit, os.environ.get("AI_LAB_DIR")):
        if c and (Path(c) / CONFIG).exists():
            return Path(c).resolve()
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for p in [start, *start.parents]:
        if (p / CONFIG).exists():
            return p
    return None


def need_lab(args) -> Path:
    lab = find_lab(args.lab)
    if lab is None:
        sys.exit("오류: 연구실 폴더가 아닙니다 (lab.config.json을 찾지 못했습니다)")
    return lab


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"경고: {path}의 JSON 형식이 잘못되었습니다: {e}", file=sys.stderr)
        return default


def write_atomic(path: Path, text: str) -> None:
    """임시 파일에 끝까지 쓴 뒤 한 번에 바꿔 끼운다. 쓰는 도중 꺼져도(절전, 정전, 강제 종료)
    파일이 반쯤 잘린 채 남지 않는다 — 밤샘 캠페인의 state.json이나 counters.json이 깨지면 이어 갈 수 없다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(40):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:  # Windows: 다른 프로세스가 그 파일을 잠깐 열고 있으면 교체가 거부된다
                if attempt == 39:
                    raise
                time.sleep(0.05)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def save_json(path: Path, data) -> None:
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


LOCK_WAIT_S = 30
LOCK_STALE_S = 120
_lock_depth = 0


@contextlib.contextmanager
def state_lock(lab: Path):
    """state/*.json을 읽고-고치고-쓰는 동안 다른 lab.py가 끼어들지 못하게 한다.
    병렬로 돈 agent 둘이 동시에 ID를 받으면 같은 ID가 두 번 나갈 수 있기 때문이다. 같은 프로세스 안에서는 겹쳐 써도 된다."""
    global _lock_depth
    if _lock_depth:
        _lock_depth += 1
        try:
            yield
        finally:
            _lock_depth -= 1
        return
    path = lab / "state" / ".lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_WAIT_S
    while True:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):
            with contextlib.suppress(OSError):
                if time.time() - path.stat().st_mtime > LOCK_STALE_S:
                    path.unlink()  # 도중에 죽은 프로세스가 남긴 잠금
                    continue
            if time.monotonic() > deadline:
                sys.exit(f"오류: 다른 lab.py가 {LOCK_WAIT_S}초 넘게 state/.lock을 쥐고 있습니다. "
                         f"실행 중인 lab.py가 없다면 state/.lock 파일을 지우고 다시 실행하세요")
            time.sleep(0.05)
    _lock_depth = 1
    try:
        yield
    finally:
        _lock_depth = 0
        with contextlib.suppress(OSError):
            path.unlink()


def alloc(lab: Path, kind: str) -> str:
    path = lab / "state" / "counters.json"
    with state_lock(lab):
        counters = load_json(path, {})
        counters[kind] = counters.get(kind, 0) + 1
        save_json(path, counters)
    return f"{KINDS[kind][0]}{counters[kind]:03d}"


def rel(lab: Path, p: Path) -> str:
    return p.relative_to(lab).as_posix()


# ---------------------------------------------------------------- 색인

def md_meta(path: Path) -> dict:
    """첫 제목(#)과 `> 키: 값 | 키: 값` 메타 줄을 읽는다."""
    title, meta = "", {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:12]
    except OSError:
        return {}
    for line in lines:
        s = line.strip()
        if not title and s.startswith("#"):
            title = s.lstrip("#").strip()
            title = re.sub(r"^[A-Z]+-\d+\s*[:—-]\s*", "", title)
        elif s.startswith(">") and ":" in s:
            for part in s.lstrip("> ").split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
    return {
        "title": title,
        "status": meta.get("status", ""),
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "summary": meta.get("summary", ""),
        "session": meta.get("session", ""),
    }


def build_index(lab: Path) -> list[dict]:
    rows: list[dict] = []
    for typ, d in KB_DIRS.items():
        for f in sorted((lab / d).glob("*.json")):
            e = load_json(f, {})
            rows.append({
                "id": e.get("id", f.stem), "type": typ, "title": e.get("title", ""),
                "status": e.get("status", ""), "tags": e.get("tags", []),
                "summary": e.get("summary", ""), "session": e.get("updated_session", e.get("created_session", "")),
                "refs": e.get("refs", []), "path": rel(lab, f),
            })
    for typ, pattern in ARTIFACT_GLOBS.items():
        for p in sorted(lab.glob(pattern)):
            aid = ID_RE.match(p.name)
            if not aid:
                continue
            if p.is_dir():
                head = next((p / n for n in DIR_SUMMARY if (p / n).exists()), None)
                m = md_meta(head) if head else {"title": p.name}
                res = load_json(p / "results.json", {})
                status = res.get("status") or m.get("status") or "empty"
                summary = m.get("summary", "") or res.get("hypothesis", "")
            elif p.suffix == ".md":
                m = md_meta(p)
                status, summary = m.get("status", ""), m.get("summary", "")
            else:
                continue
            rows.append({
                "id": aid.group(0), "type": typ, "title": m.get("title", ""), "status": status,
                "tags": m.get("tags", []), "summary": summary, "session": m.get("session", ""),
                "refs": [], "path": rel(lab, p),
            })
    for f in sorted((lab / "kb" / "log").glob("session_*.json")):
        e = load_json(f, {})
        rows.append({
            "id": f"S-{e.get('session', f.stem[-3:])}", "type": "session", "title": e.get("title", ""),
            "status": "logged", "tags": e.get("tags", []), "summary": e.get("summary", ""),
            "session": e.get("session", ""), "refs": [], "path": rel(lab, f),
        })
    return rows


def write_index(lab: Path) -> list[dict]:
    rows = build_index(lab)
    path = lab / "kb" / "index.json"
    if load_json(path, {}).get("entries") != rows:  # 내용이 같으면 다시 쓰지 않는다 (날짜만 바뀐 변경을 git에 남기지 않도록)
        save_json(path, {"generated": today(), "note": "자동 생성 캐시입니다. 권위는 개별 파일에 있습니다. 직접 고치지 마세요.",
                         "entries": rows})
    return rows


def get_index(lab: Path) -> list[dict]:
    # 읽기 명령(find, show, context …)은 파일을 쓰지 않는다. 병렬 agent가 동시에 불러도 안전하다.
    # 연구실 규모에서는 매번 새로 만들어도 충분히 빠르다. kb/index.json은 index, digest, status가 갱신한다.
    return build_index(lab)


def line(r: dict) -> str:
    st = f"/{ko_status(r['status'])}" if r.get("status") else ""
    tags = f" #{' #'.join(r['tags'])}" if r.get("tags") else ""
    summ = f" — {r['summary']}" if r.get("summary") else ""
    return f"{r['id']} [{ko_type(r['type'])}{st}] {r['title']}{summ}{tags}  ({r['path']})"


def resolve(lab: Path, eid: str) -> dict | None:
    eid = eid.strip()
    if re.fullmatch(r"\d{1,3}", eid):
        eid = f"S-{int(eid):03d}"
    for r in get_index(lab):
        if r["id"].upper() == eid.upper():
            return r
    return None


# ---------------------------------------------------------------- 명령

def cmd_init(args) -> None:
    dest = Path(args.path).resolve()
    if (dest / CONFIG).exists():
        sys.exit(f"오류: {dest}는 이미 연구실입니다")
    if dest.exists() and any(p.name != ".git" for p in dest.iterdir()):
        sys.exit(f"오류: {dest} 폴더가 비어 있지 않습니다 (아무것도 지우지 않았습니다)")
    subs = {
        "{{LAB_NAME}}": args.name or dest.name,
        "{{TOPIC}}": args.topic or "(미정 — 첫 주기 계획 회의에서 정한다)",
        "{{DATE}}": today(),
    }
    for src in TEMPLATE_DIR.rglob("*"):
        out = dest / src.relative_to(TEMPLATE_DIR)
        if src.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.name == ".gitkeep":
            out.touch()
        elif src.suffix in TEXT_SUFFIXES or src.name.startswith("."):
            text = src.read_text(encoding="utf-8")
            for k, v in subs.items():
                text = text.replace(k, v)
            out.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(src, out)
    if args.git and not (dest / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=dest, check=False)
    print(f"연구실을 만들었습니다: {dest}")
    hw, lim, _ = ensure_hardware(dest, refresh=True)
    print(f"이 PC의 하드웨어를 탐색해 운영 제약을 걸었습니다: {limits_line(hw, lim)}")


def cmd_next(args) -> None:
    lab = need_lab(args)
    if args.kind not in KINDS:
        sys.exit(f"오류: 알 수 없는 종류 {args.kind!r}. 가능한 종류: {', '.join(KINDS)}")
    print(alloc(lab, args.kind))


def cmd_status(args) -> None:
    lab = find_lab(args.lab)
    if lab is None:
        if args.hook:
            return  # 연구실 밖에서는 아무것도 출력하지 않는다
        sys.exit("오류: 연구실 폴더가 아닙니다")
    cfg = load_json(lab / CONFIG, {})
    counters = load_json(lab / "state" / "counters.json", {})
    session = counters.get("session", 0)
    cyc = cycle_meta(lab)
    cyc_txt = ""
    if cyc:
        done = max(0, session - cyc["start"] + 1) if session >= cyc["start"] else 0
        cyc_txt = f", 주기 {cyc['cycle']}: 세션 {done}/{cyc['length']}"
        if done >= cyc["length"]:
            cyc_txt += " → 회고할 때입니다"
    out = [f"# 연구실: {cfg.get('lab_name', lab.name)}  (예산 프로필: {cfg.get('budget_profile', 'economy')}, "
           f"마지막 세션: {session:03d}{cyc_txt})"]
    roadmap = lab / "ROADMAP.md"
    if roadmap.exists():
        summ = md_section(roadmap.read_text(encoding="utf-8"), "요약", 8)
        if summ:
            out.append("\n## 장기 (ROADMAP.md 요약)\n" + summ)
    for label, rel_path, limit in (("중기 (state/cycle.md)", "state/cycle.md", 2500),
                                   ("단기 (state/lab_state.md)", "state/lab_state.md", 3000)):
        f = lab / rel_path
        if f.exists():
            text = "\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip())
            out.append(f"\n## {label}\n" + (text if len(text) <= limit else text[:limit] + f"\n…(생략됨. {rel_path}를 읽으세요)"))
    asks = [q for q in load_json(lab / "state" / "inbox.json", []) if q.get("status") == "open"]
    if asks:
        out.append(f"\n## ⚠ 교수님 결정 대기 ({len(asks)}건) — 가장 먼저 여쭙는다")
        out += [f"- {q['id']} [{q.get('from', '?')}] {q['question']}" + (f"  (선택지: {q['options']})" if q.get("options") else "")
                for q in asks]
    camps = active_campaign_lines(lab)
    if camps:
        out.append(f"\n## 자율 탐색 캠페인 ({len(camps)}건) — 자세히: lab.py campaign status <ID>")
        out += camps
    acts = [a for a in load_json(lab / "state" / "actions.json", []) if a.get("status") == "open"]
    if acts:
        out.append(f"\n## 남은 할 일 ({len(acts)}건)")
        out += [f"- {a['id']} [{a['owner']}] {a['title']}" for a in acts[:15]]
    try:
        lint = lint_issues(lab)
    except Exception:  # 점검은 현황 보기를 막지 않는다
        lint = []
    serious = [m for lvl, m in lint if lvl in ("실패", "경고")]
    if serious:
        out.append(f"\n## 점검 경고 {len(serious)}건 (lab.py lint)")
        out += [f"- {m}" for m in serious[:5]]
    try:
        hw, lim, redetected = ensure_hardware(lab)
        if lim:
            note = " — 이 PC에서 새로 탐색함" if redetected else ""
            out.append(f"\n## 하드웨어와 운영 제약 (자동 탐색{note}, 자세히: lab.py hardware)\n- {limits_line(hw, lim)}")
    except Exception as e:  # 탐색 실패가 현황 보기를 막지 않는다
        out.append(f"\n(하드웨어 탐색 실패: {e})")
    rows = write_index(lab)
    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        c = counts.setdefault(r["type"], {})
        key = r["status"] or "-"
        c[key] = c.get(key, 0) + 1
    if rows:
        parts = [f"{ko_type(t)} {sum(c.values())} ({', '.join(f'{ko_status(k)} {v}' for k, v in c.items())})"
                 for t, c in sorted(counts.items())]
        out.append("\n## 지식베이스\n- " + "; ".join(parts))
    if args.hook:
        out.append(f'\n연구실 도구 (필요한 것만 읽기): python "{SELF}" find|show|context|history|digest|audit|inbox|campaign|lit|report ...')
    print("\n".join(out))


def md_section(text: str, heading: str, max_lines: int) -> str:
    """첫 번째 `## <heading>` 절의 본문을 앞에서부터 max_lines줄까지 돌려준다."""
    lines, grab = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            if grab:
                break
            grab = heading in ln
            continue
        if grab and ln.strip():
            lines.append(ln)
    return "\n".join(lines[:max_lines])


def cycle_meta(lab: Path) -> dict | None:
    f = lab / "state" / "cycle.md"
    if not f.exists():
        return None
    m = md_meta(f)
    raw = {}
    for ln in f.read_text(encoding="utf-8").splitlines()[:12]:
        if ln.strip().startswith(">"):
            for part in ln.lstrip("> ").split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    raw[k.strip().lower()] = v.strip()
    try:
        return {"cycle": int(raw.get("cycle", 0)), "start": int(raw.get("start_session", 1)),
                "length": int(raw.get("length", 3)), "title": m.get("title", "")}
    except ValueError:
        return None


def cmd_inbox(args) -> None:
    """교수님만 정할 수 있는 질문. agent가 올리고, 메인 세션이 여쭙고 기록한다."""
    lab = need_lab(args)
    with state_lock(lab):  # 두 agent가 동시에 올려도 한쪽 질문이 사라지지 않도록
        _inbox(lab, args)


def _inbox(lab: Path, args) -> None:
    path = lab / "state" / "inbox.json"
    items = load_json(path, [])
    if args.op == "add":
        if not args.question:
            sys.exit("오류: inbox add에는 --question이 필요합니다")
        qid = alloc(lab, "ask")
        items.append({"id": qid, "from": args.frm or "lead", "question": args.question, "options": args.options,
                      "ref": args.ref, "context": args.context, "status": "open", "created": today()})
        save_json(path, items)
        print(qid)
    elif args.op == "resolve":
        for q in items:
            if q["id"] == args.id:
                q.update(status="answered", answer=args.answer, answered=today())
                save_json(path, items)
                print(f"{args.id} 답변 기록 완료")
                return
        sys.exit(f"오류: 대기함에 {args.id}가 없습니다")
    else:
        shown = items if args.all else [q for q in items if q["status"] == "open"]
        for q in shown:
            extra = f" → {q['answer']}" if q.get("answer") else ""
            print(f"{q['id']} [{ko_status(q['status'])}] [{q.get('from')}] {q['question']}"
                  + (f" (선택지: {q['options']})" if q.get("options") else "")
                  + (f" 관련: {q['ref']}" if q.get("ref") else "") + extra)
        if not shown:
            print("(결정 대기 항목 없음)")


def exp_dir(lab: Path, eid: str) -> Path | None:
    hits = [p for p in (lab / "research" / "experiments").glob(f"{eid}*") if p.is_dir()]
    return hits[0] if hits else None


def cmd_verify(args) -> None:
    """실험(EXP) 또는 캠페인(CMP) 하나의 증거를 결정적으로 감사한다."""
    lab = need_lab(args)
    if args.id.upper().startswith("CMP-"):
        issues = campaign_verify(lab, campaign_dir(lab, args.id))
    else:
        d = exp_dir(lab, args.id)
        if d is None:
            sys.exit(f"오류: {args.id} 실험 폴더가 없습니다")
        issues = verify_experiment(d)
    fails = print_issues(issues)
    print(f"검증 {args.id}: {'실패' if fails else '통과'} (실패 {fails}건)")
    if fails:
        sys.exit(1)


def print_issues(issues: list[tuple[str, str]]) -> int:
    for lvl, msg in issues:
        print(f"[{lvl}] {msg}")
    return sum(1 for lvl, _ in issues if lvl == "실패")


def verify_experiment(d: Path) -> list[tuple[str, str]]:
    """사전 등록, results.json ↔ 실행 기록(runs/*/metrics.json) 일치 여부."""
    issues: list[tuple[str, str]] = []
    plan = d / "plan.md"
    if not plan.exists():
        issues.append(("실패", "plan.md가 없습니다"))
    else:
        text = plan.read_text(encoding="utf-8").lower()
        heads = " ".join(ln for ln in text.splitlines() if ln.startswith("#"))
        for key, words in PREREG_KEYS.items():
            if not any(w in heads for w in words):
                issues.append(("경고", f"plan.md에 사전 등록 항목 '{key}' 제목이 없습니다"))
        st = md_meta(plan).get("status", "")
        issues.append(("정보", f"계획 상태: {ko_status(st) if st else '(없음)'}"))
    res = load_json(d / "results.json", None)
    if res is None:
        issues.append(("경고", "results.json이 없습니다 (실행 전이면 정상)"))
    else:
        for k in ("exp_id", "status", "runs", "summary"):
            if k not in res:
                issues.append(("실패", f"results.json에 '{k}' 항목이 없습니다"))
        per_cond: dict[str, int] = {}
        for r in res.get("runs", []):
            rid = r.get("run_id")
            rd = d / "runs" / str(rid)
            per_cond[r.get("condition", "?")] = per_cond.get(r.get("condition", "?"), 0) + 1
            if not rid or not rd.is_dir():
                issues.append(("실패", f"실행 {rid}: runs/{rid}/ 폴더가 없습니다 (결과가 실행 기록으로 뒷받침되지 않음)"))
                continue
            if not any(rd.iterdir()):
                issues.append(("실패", f"실행 {rid}: 실행 폴더가 비어 있습니다"))
            mfile = rd / "metrics.json"
            if mfile.exists():
                logged = load_json(mfile, {}).get("final", {})
                for mk, mv in (r.get("metrics") or {}).items():
                    lv = logged.get(mk)
                    if isinstance(mv, (int, float)) and isinstance(lv, (int, float)) and abs(mv - lv) > 1e-9 * max(1, abs(lv)):
                        issues.append(("실패", f"실행 {rid}: {mk} 값이 results.json에는 {mv}, metrics.json에는 {lv}입니다"))
            else:
                issues.append(("경고", f"실행 {rid}: metrics.json이 없습니다 (labkit.Run을 쓰세요)"))
            if r.get("status", "complete") == "complete" and not r.get("metrics"):
                issues.append(("실패", f"실행 {rid}: 완료로 표시됐지만 지표가 없습니다"))
            elif r.get("status") in ("failed", "partial"):
                issues.append(("정보", f"실행 {rid}: {ko_status(r['status'])} (요약에서 제외됨 — 숨기지 말고 보고할 것)"))
        if res.get("status") == "complete":
            few = {c: n for c, n in per_cond.items() if n < 3}
            if few:
                issues.append(("경고", f"시드가 3개 미만인 조건: {few}"))
    return issues


def cmd_digest(args) -> None:
    """kb/digest.md를 다시 만든다 — 연구실이 지금 아는 것 1쪽 (LLM 불필요)."""
    lab = need_lab(args)
    rows = write_index(lab)
    by = lambda t, *st: [r for r in rows if r["type"] == t and (not st or r["status"] in st)]
    cap = 15

    def block(title: str, items: list[dict], extra=lambda r: "") -> list[str]:
        if not items:
            return []
        out = [f"\n## {title} ({len(items)}건)"]
        out += [f"- {r['id']} {r['title']}{extra(r)}" + (f" — {r['summary']}" if r["summary"] else "") for r in items[:cap]]
        if len(items) > cap:
            out.append(f"- … {len(items) - cap}건 더 있음: lab.py find --type {items[0]['type']}")
        return out

    conf_ko = {"low": "낮음", "medium": "중간", "high": "높음"}

    def conf(r: dict) -> str:
        e = load_json(lab / r["path"], {})
        c = e.get("confidence", "?")
        return f" [확신도 {conf_ko.get(c, c)}]"

    def field(r: dict, key: str, default=""):
        return load_json(lab / r["path"], {}).get(key, default) if r["path"].endswith(".json") else default

    findings = by("finding", "accepted", "provisional")
    neg = [r for r in findings if field(r, "result_type") in ("null", "negative")]
    pos = [r for r in findings if r not in neg]
    lessons = by("lesson", "active")
    exp_lessons = [r for r in lessons if re.search(r"engineer|explorer|실험|학습", str(field(r, "applies_to")))]
    failed_dirs = (by("hypothesis", "refuted", "abandoned") + by("experiment", "failed") +
                   [r for r in by("campaign") if (load_json(lab / r["path"] / "state.json", {}) or {}).get("best_trial") == "baseline"
                    and r["status"] in ("stopped", "confirmed")])
    lines = ["# 연구실 지식 요약본",
             f"> {today()}에 `lab.py digest`가 자동 생성함 — 직접 고치지 마세요. 권위는 개별 항목에 있습니다."]
    lines += block("확정된 결과", [r for r in pos if r["status"] == "accepted"], conf)
    lines += block("잠정 결과 (아직 확정 전)", [r for r in pos if r["status"] == "provisional"], conf)
    lines += block("효과 없음·부정적 결과 (이것도 지식이다)", neg, lambda r: f" [{ko_status(r['status'])}]")
    lines += block("검증 중인 가설", by("hypothesis", "testing"))
    lines += block("제안된 가설", by("hypothesis", "proposed"))
    lines += block("지지된 가설", by("hypothesis", "supported"))
    lines += block("실패한 방향 (다시 하지 말 것, 하려면 이유를 밝힐 것)", failed_dirs, lambda r: f" [{ko_status(r['status'])}]")
    lines += block("자율 탐색 캠페인", by("campaign"), lambda r: f" [{ko_status(r['status'])}]")
    lines += block("열린 연구 질문", by("question", "open", "narrowed"))
    lines += block("유효한 결정", by("decision", "in_force"))
    lines += block("실험 전략 기억 (효과가 있었던 방법·설정)", exp_lessons + by("method", "implemented", "baseline"))
    lines += block("운영 교훈", [r for r in lessons if r not in exp_lessons])
    lines += block("핵심 논문", by("paper", "key"))
    lines += block("사용 중인 데이터셋", by("dataset", "in_use"))
    lines += block("회사에 가져간 릴리스", by("release"))
    if len(lines) == 2:
        lines.append("\n(아직 쌓인 지식이 없습니다)")
    (lab / "kb").mkdir(exist_ok=True)
    write_atomic(lab / "kb" / "digest.md", "\n".join(lines) + "\n")
    print(f"kb/digest.md를 만들었습니다 ({len(lines)}줄)")


def cmd_action(args) -> None:
    lab = need_lab(args)
    with state_lock(lab):
        _action(lab, args)


def _action(lab: Path, args) -> None:
    path = lab / "state" / "actions.json"
    actions = load_json(path, [])
    if args.op == "add":
        if not args.owner or not args.title:
            sys.exit("오류: action add에는 --owner와 --title이 필요합니다")
        aid = alloc(lab, "action")
        actions.append({"id": aid, "owner": args.owner, "title": args.title, "ref": args.ref,
                        "session": args.session, "status": "open", "created": today()})
        save_json(path, actions)
        print(aid)
    elif args.op == "done":
        for a in actions:
            if a["id"] == args.id:
                a.update(status="done", closed=today(), result=args.result)
                save_json(path, actions)
                print(f"{args.id} 완료 처리")
                return
        sys.exit(f"오류: 할 일 {args.id}가 없습니다")
    else:
        shown = actions if args.all else [a for a in actions if a["status"] == "open"]
        for a in shown:
            ref = f" (관련: {a['ref']})" if a.get("ref") else ""
            print(f"{a['id']} [{ko_status(a['status'])}] [{a['owner']}] {a['title']}{ref}")
        if not shown:
            print("(남은 할 일 없음)")


def cmd_index(args) -> None:
    lab = need_lab(args)
    print(f"항목 {len(write_index(lab))}개를 색인했습니다 → kb/index.json")


def cmd_find(args) -> None:
    lab = need_lab(args)
    q = (args.text or "").lower()
    want_type = TYPE_FROM_KO.get(args.type, args.type) if args.type else None
    want_status = STATUS_FROM_KO.get(args.status, args.status) if args.status else None
    hits = []
    for r in get_index(lab):
        if want_type and r["type"] != want_type:
            continue
        if want_status and r["status"] != want_status:
            continue
        if args.tag and args.tag.lower() not in [t.lower() for t in r["tags"]]:
            continue
        hay = " ".join([r["id"], r["title"], r["summary"], " ".join(r["tags"])]).lower()
        if q and q not in hay:
            continue
        hits.append(r)
    for r in hits[: args.limit]:
        print(line(r))
    if len(hits) > args.limit:
        print(f"… {len(hits) - args.limit}건 더 있음 (--type/--status/--tag로 좁혀 보세요)")
    if not hits:
        print("(찾은 항목 없음)")


def print_entry(lab: Path, r: dict, max_lines: int) -> None:
    p = lab / r["path"]
    if p.is_dir():  # 실험 등 폴더: 요약 파일 + results.json 요약
        print(f"== {r['id']} ({r['path']})")
        for name in DIR_SUMMARY:
            if (p / name).exists():
                txt = (p / name).read_text(encoding="utf-8").splitlines()
                print(f"--- {name}")
                print("\n".join(txt[:max_lines]) + ("\n…" if len(txt) > max_lines else ""))
        res = load_json(p / "results.json", None)
        if res is not None:
            print("--- results.json (요약)")
            print(json.dumps({k: res.get(k) for k in ("status", "hypothesis", "summary", "notes")}, ensure_ascii=False, indent=1))
        return
    txt = p.read_text(encoding="utf-8").splitlines()
    print(f"== {r['id']} ({r['path']})")
    print("\n".join(txt[:max_lines]) + (f"\n… ({len(txt) - max_lines}줄 더 있음)" if len(txt) > max_lines else ""))


def cmd_show(args) -> None:
    lab = need_lab(args)
    r = resolve(lab, args.id)
    if not r:
        sys.exit(f"오류: {args.id}를 찾지 못했습니다 (lab.py find {args.id} 로 검색해 보세요)")
    print_entry(lab, r, args.max_lines)


def cmd_context(args) -> None:
    lab = need_lab(args)
    r = resolve(lab, args.id)
    if not r:
        sys.exit(f"오류: {args.id}를 찾지 못했습니다")
    print_entry(lab, r, args.max_lines)
    p = lab / r["path"]
    text = ""
    if p.is_file():
        text = p.read_text(encoding="utf-8")
    elif p.is_dir():
        text = " ".join((p / n).read_text(encoding="utf-8") for n in DIR_SUMMARY if (p / n).exists())
    index = get_index(lab)
    idx = {x["id"]: x for x in index}
    refs = sorted(set(ID_RE.findall(text)) - {r["id"]})
    backrefs = [x for x in index if r["id"] in x.get("refs", [])]
    if refs:
        print("\n--- 이 항목이 참조하는 것")
        for ref in refs:
            print(line(idx[ref]) if ref in idx else f"{ref} (지식베이스에 없음)")
    if backrefs:
        print("\n--- 이 항목을 참조하는 것")
        for x in backrefs:
            print(line(x))


def cmd_history(args) -> None:
    lab = need_lab(args)
    target = args.id.upper()
    found = False
    for f in sorted((lab / "kb" / "log").glob("session_*.json")):
        log = load_json(f, {})
        for ev in log.get("events", []):
            blob = json.dumps(ev, ensure_ascii=False).upper()
            if re.search(rf"\b{re.escape(target)}\b", blob):
                found = True
                ch = "; ".join(f"{c.get('target')}: {c.get('change')}" for c in ev.get("changes", []))
                print(f"S-{log.get('session')} {log.get('date', '')} {ev.get('id')} [{ev.get('type')}] {ev.get('summary')}"
                      + (f"  ⇒ {ch}" if ch else ""))
    if not found:
        print("(기록된 변화 없음)")


# ---------------------------------------------------------------- md 묶음 (회사로는 md 파일만 가져갈 수 있다)

LANG_BY_SUFFIX = {".py": "python", ".toml": "toml", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
                  ".md": "markdown", ".txt": "text", ".sh": "bash", ".ps1": "powershell", ".cfg": "ini", ".ini": "ini"}
PACK_SKIP_DIRS = {"runs", "__pycache__", ".venv", ".rel-venv", ".git", "data", "figures", "wandb"}
PACK_MAX_BYTES = 200_000
FILE_HEADING = "### 파일: "
# 회사 PC에서 이 스크립트를 restore.py로 저장하고 `python restore.py 묶음.md [출력폴더]`로 실행하면 파일이 복원된다.
# lab.py unpack-md도 똑같은 규칙을 쓴다 (둘을 함께 고칠 것).
RESTORE_SNIPPET = r'''import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
out_dir = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")
pattern = re.compile(r"^### 파일: (.+?)\n(`{3,})[^\n]*\n(.*?)\n\2$", re.S | re.M)
for rel_path, fence, body in pattern.findall(text):
    target = out_dir / rel_path.strip()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body + "\n", encoding="utf-8")
    try:
        print("복원:", target)
    except UnicodeEncodeError:
        print("restored:", ascii(str(target)))'''
RESTORE_RE = re.compile(r"^### 파일: (.+?)\n(`{3,})[^\n]*\n(.*?)\n\2$", re.S | re.M)


def _pack_files(root: Path, targets: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """묶을 텍스트 파일 (상대 경로, 내용)과 건너뛴 항목 목록을 돌려준다."""
    files: list[tuple[str, str]] = []
    skipped: list[str] = []
    for t in targets:
        p = (root / t).resolve()
        cands = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else []
        if not cands:
            skipped.append(f"{t} (없음)")
        for f in cands:
            rp = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
            if any(part in PACK_SKIP_DIRS for part in Path(rp).parts):
                continue
            if f.stat().st_size > PACK_MAX_BYTES:
                skipped.append(f"{rp} (너무 큼)")
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                skipped.append(f"{rp} (텍스트 파일 아님)")
                continue
            files.append((rp, text))
    return files, skipped


def cmd_pack_md(args) -> None:
    """여러 텍스트 파일을 복원 가능한 md 파일 하나로 묶는다."""
    import hashlib
    root = Path(args.root).resolve() if args.root else Path.cwd()
    files, skipped = _pack_files(root, args.paths)
    if not files:
        sys.exit("오류: 묶을 텍스트 파일이 없습니다")
    lines = [f"# {args.title or '코드 묶음'}", "",
             "> 이 문서는 코드 파일들을 md 하나에 담은 것입니다. 아래 **복원 방법**대로 하면 원래 파일로 되돌릴 수 있습니다.",
             f"> `lab.py pack-md`로 {today()}에 생성. 파일 {len(files)}개.", "",
             "## 복원 방법", "",
             "1. 아래 코드 블록을 `restore.py`라는 파일로 저장합니다.",
             "2. `python restore.py 이_문서.md 출력폴더` 를 실행합니다. (출력폴더를 생략하면 현재 폴더)",
             "3. 아래 파일 목록의 sha256 값으로 복원이 정확한지 확인할 수 있습니다.", "",
             "````python", RESTORE_SNIPPET, "````", "",
             "## 파일 목록", "", "| 파일 | 줄 수 | sha256 (앞 12자리) |", "|---|---|---|"]
    for rp, text in files:
        body = text[:-1] if text.endswith("\n") else text
        digest = hashlib.sha256((body + "\n").encode("utf-8")).hexdigest()[:12]
        lines.append(f"| `{rp}` | {body.count(chr(10)) + 1} | `{digest}` |")
    if skipped:
        lines += ["", "빠진 항목: " + ", ".join(skipped)]
    lines += ["", "## 파일 내용"]
    for rp, text in files:
        body = text[:-1] if text.endswith("\n") else text
        longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
        fence = "`" * max(3, longest + 1)
        lines += ["", f"{FILE_HEADING}{rp}", f"{fence}{LANG_BY_SUFFIX.get(Path(rp).suffix, '')}", body, fence]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}에 파일 {len(files)}개를 묶었습니다" + (f" (빠진 항목 {len(skipped)}개: {', '.join(skipped)})" if skipped else ""))


def cmd_unpack_md(args) -> None:
    """pack-md로 만든 md 파일에서 원래 파일들을 복원한다 (복원 스크립트와 같은 규칙)."""
    text = Path(args.md).read_text(encoding="utf-8")
    out_dir = Path(args.out)
    found = RESTORE_RE.findall(text)
    if not found:
        sys.exit("오류: 복원할 파일 블록이 없습니다")
    for rel_path, _fence, body in found:
        target = out_dir / rel_path.strip()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body + "\n", encoding="utf-8")
        print("복원:", target)


# ---------------------------------------------------------------- 자율 탐색 캠페인
# 원칙: 제안은 AI가, 판정은 코드가 한다. 실행, 시간 제한, 지표 읽기, 채택/기각을 모두 여기서 결정적으로 처리한다.
# (자기 평가에 맡긴 반복 실험은 개선이 없어도 "개선됐다"고 착각한다 — progress mirage)

CAMPAIGN_SKIP_DIRS = {"runs", "__pycache__", ".venv", "data", "figures", "wandb", ".ipynb_checkpoints", "outputs", "checkpoints"}
CAMPAIGN_SKIP_SUFFIX = {".pt", ".pth", ".ckpt", ".safetensors", ".pyc", ".log", ".npy", ".npz", ".bin"}
MAX_TRIAL_MINUTES = 7      # Claude Code가 명령 하나를 기다리는 한계(10분) 안에 실행 + 평가가 끝나야 한다
HARD_TIMEOUT_S = 570
CONFIRM_SEED_OFFSET = 100  # 확인 실험은 탐색에 쓰지 않은 새 시드로 한다 (시드에 맞춘 우연을 걸러낸다)
EVAL_MARK = "\n----- 평가 출력 -----\n"
LEDGER_HEADER = "trial\tparent\tseed\tmetric\timprovement\tstatus\tminutes\tlines\tdescription\n"


def campaign_dir(lab: Path, cid: str) -> Path:
    hits = [p for p in (lab / "research" / "campaigns").glob(f"{cid.upper()}*") if p.is_dir()]
    if not hits:
        sys.exit(f"오류: {cid} 캠페인 폴더가 없습니다")
    return hits[0]


def _code_files(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not root.exists():
        return out
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rp = f.relative_to(root)
        if any(part in CAMPAIGN_SKIP_DIRS for part in rp.parts) or f.suffix in CAMPAIGN_SKIP_SUFFIX:
            continue
        out[rp.as_posix()] = f
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_code(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for rp, f in _code_files(src).items():
        t = dst / rp
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _hours_since(iso: str | None) -> float:
    if not iso:
        return 0.0
    return (dt.datetime.now() - dt.datetime.fromisoformat(iso)).total_seconds() / 3600


def md_meta_raw(path: Path) -> dict:
    """메타 줄(`> 키: 값 | 키: 값`)의 모든 키."""
    meta: dict[str, str] = {}
    if not path.exists():
        return meta
    for ln in path.read_text(encoding="utf-8").splitlines()[:12]:
        s = ln.strip()
        if s.startswith(">") and ":" in s:
            for part in s.lstrip("> ").split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
    return meta


def set_md_status(md: Path, status: str) -> None:
    if not md.exists():
        return
    text = md.read_text(encoding="utf-8")
    new = re.sub(r"(?m)^(>\s*status:\s*)[^|\n]*", lambda m: m.group(1) + status + " ", text, count=1)
    if new != text:
        write_atomic(md, new)  # plan.md(사전 등록), campaign.md(계약)가 잘리면 되돌릴 수 없다


def _kill_tree(p: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, check=False)
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def _run_cmd(cmd: str, cwd: Path, env: dict, timeout_s: float) -> tuple[int | None, bool, str, float]:
    kwargs: dict = dict(cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    t0 = time.time()
    p = subprocess.Popen(cmd, **kwargs)
    try:
        out, _ = p.communicate(timeout=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        try:
            out, _ = p.communicate(timeout=30)
        except Exception:
            out = b""
        timed_out = True
    return p.returncode, timed_out, (out or b"").decode("utf-8", errors="replace"), (time.time() - t0) / 60


def _parse_metric(text: str, name: str, regex: str | None = None) -> float | None:
    pat = re.compile(regex) if regex else re.compile(rf"LAB_METRIC\s+{re.escape(name)}\s*=\s*([-+0-9.eEnaifNAIF]+)")
    found = pat.findall(text)
    if not found:
        return None
    last = found[-1] if isinstance(found[-1], str) else found[-1][0]
    try:
        v = float(last)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _metric_from_log(log: str, cfg: dict) -> float | None:
    source = log.split(EVAL_MARK, 1)[1] if cfg.get("eval_cmd") and EVAL_MARK in log else log
    return _parse_metric(source, cfg["metric"], cfg.get("metric_regex"))


def _execute(lab: Path, d: Path, cfg: dict, code_dir: Path, seed: int, label: str) -> dict:
    """한 번 실행한다. 지표는 로그에서 코드가 읽는다. 평가 명령이 있으면 그 출력에서만 읽는다."""
    env = os.environ.copy()
    env.update(LAB_SEED=str(seed), LAB_ROOT=str(lab), LAB_CAMPAIGN=cfg["id"], LAB_TRIAL=label,
               PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    timeout = min(cfg["trial_minutes"] * 60 + 150, HARD_TIMEOUT_S)
    rc, timed_out, out, mins = _run_cmd(cfg["run_cmd"], code_dir, env, timeout)
    log = out
    if cfg.get("eval_cmd") and not timed_out and rc == 0:
        remaining = max(30.0, HARD_TIMEOUT_S - mins * 60)
        rc, timed_out, eval_out, m2 = _run_cmd(cfg["eval_cmd"], code_dir, env, remaining)
        mins += m2
        log = out + EVAL_MARK + eval_out
    metric = None if (timed_out or rc != 0) else _metric_from_log(log, cfg)
    status = "timeout" if timed_out else ("crash" if metric is None else "ok")
    return {"metric": metric, "status": status, "minutes": mins, "log": log, "rc": rc}


def _save_log(path: Path, log: str, keep_lines: int = 400) -> None:
    lines = log.splitlines()
    if len(lines) > keep_lines:
        lines = [f"… (앞부분 {len(lines) - keep_lines}줄 생략)"] + lines[-keep_lines:]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _improvement(goal: str, new: float, old: float) -> float:
    return (new - old) if goal == "max" else (old - new)


def _ledger_rows(d: Path) -> list[dict]:
    path = d / "ledger.tsv"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    keys = lines[0].split("\t")
    return [dict(zip(keys, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def _ledger_add(d: Path, row: dict) -> None:
    keys = LEDGER_HEADER.strip().split("\t")
    vals = [str(row.get(k, "")).replace("\t", " ").replace("\n", " ") for k in keys]
    with open(d / "ledger.tsv", "a", encoding="utf-8") as f:
        f.write("\t".join(vals) + "\n")


def _fmt(v, nd: int = 6) -> str:
    return "-" if v is None else f"{v:.{nd}g}"


def _stop_reason(cfg: dict, st: dict) -> str | None:
    if st.get("stopped"):
        return st["stopped"]
    n = st.get("n_trials", 0)
    if n >= cfg["max_trials"]:
        return f"시도 횟수 소진 ({n}/{cfg['max_trials']})"
    if st.get("started_at") and _hours_since(st["started_at"]) >= cfg["max_hours"]:
        return f"시간 예산 소진 ({cfg['max_hours']}시간)"
    if n - st.get("last_keep", 0) >= cfg["patience"]:
        return f"개선 정체 (최근 {cfg['patience']}번 연속 채택 없음)"
    if st.get("crash_streak", 0) >= cfg["crash_limit"]:
        return f"연속 실행 실패 {st['crash_streak']}번 — 사람의 확인이 필요합니다"
    return None


def _decision_line(cfg: dict, st: dict) -> str:
    if not cfg.get("approved"):
        return "판정: 승인 대기 (교수님 승인 전에는 탐색을 시작하지 않습니다)"
    if not st.get("baseline_done"):
        return "판정: 기준선 측정 필요 (lab.py campaign baseline)"
    reason = _stop_reason(cfg, st)
    if reason:
        return f"판정: 종료 — {reason}"
    left_trials = cfg["max_trials"] - st.get("n_trials", 0)
    left_hours = cfg["max_hours"] - _hours_since(st.get("started_at"))
    return f"판정: 계속 (남은 시도 {left_trials}번, 남은 시간 약 {max(0.0, left_hours):.1f}시간)"


def _mark_stopped(d: Path, st: dict, reason: str) -> None:
    if not st.get("stopped"):
        st["stopped"] = reason
        st["stopped_at"] = _now()
        save_json(d / "state.json", st)
        set_md_status(d / "campaign.md", "stopped")


def _bootstrap_compare(treat: list[float], base: list[float], goal: str, n_boot: int = 5000, seed: int = 0) -> dict:
    """labkit.stats.compare와 같은 규칙 (lab.py는 표준 라이브러리만 쓰므로 따로 구현)."""
    sign = 1.0 if goal == "max" else -1.0
    rng = random.Random(seed)
    imp = sign * (statistics.fmean(treat) - statistics.fmean(base))
    boots = sorted(sign * (statistics.fmean([rng.choice(treat) for _ in treat]) -
                           statistics.fmean([rng.choice(base) for _ in base])) for _ in range(n_boot))
    lo, hi = boots[int(0.025 * n_boot)], boots[min(n_boot - 1, int(0.975 * n_boot))]
    if min(len(treat), len(base)) < 2:
        verdict = "판단 불가 (시드가 1개뿐)"
    elif lo > 0:
        verdict = "개선 확인 (95% 신뢰구간이 0보다 큼)"
    elif hi < 0:
        verdict = "오히려 악화 (95% 신뢰구간이 0보다 작음)"
    else:
        verdict = "판단 불가 (95% 신뢰구간이 0을 포함 — 우연일 수 있음)"
    return {"improvement": imp, "ci_low": lo, "ci_high": hi, "verdict": verdict,
            "p_improve": sum(1 for x in boots if x > 0) / n_boot, "n_treat": len(treat), "n_base": len(base)}


def _check_trial_rules(d: Path, cfg: dict, st: dict) -> tuple[list[str], dict]:
    """수정 가능 파일만 바뀌었는지, 수정 금지 파일이 원본 그대로인지. (위반 목록, 변경 통계)"""
    best, work = _code_files(d / "best"), _code_files(d / "work")
    editable = set(cfg["editable"])
    problems: list[str] = []
    for rp in sorted(set(best) | set(work)):
        if rp in editable:
            if rp not in work:
                problems.append(f"수정 가능 파일 {rp}이(가) 사라졌습니다")
            continue
        if rp not in work:
            problems.append(f"{rp}이(가) 삭제되었습니다 (수정 금지)")
        elif rp not in best:
            problems.append(f"새 파일 {rp}이(가) 생겼습니다 (수정 가능 파일 목록에 없음)")
        elif _sha(work[rp]) != _sha(best[rp]):
            problems.append(f"{rp}이(가) 바뀌었습니다 (수정 금지)")
    for rp, h in st.get("protected_hashes", {}).items():
        if rp in work and _sha(work[rp]) != h:
            problems.append(f"평가/보호 파일 {rp}이(가) 원본과 다릅니다")
    diff_lines: list[str] = []
    added = removed = 0
    for rp in sorted(editable):
        a = best[rp].read_text(encoding="utf-8", errors="replace").splitlines() if rp in best else []
        b = work[rp].read_text(encoding="utf-8", errors="replace").splitlines() if rp in work else []
        for ln in difflib.unified_diff(a, b, fromfile=f"best/{rp}", tofile=f"work/{rp}", lineterm=""):
            diff_lines.append(ln)
            if ln.startswith("+") and not ln.startswith("+++"):
                added += 1
            elif ln.startswith("-") and not ln.startswith("---"):
                removed += 1
    return problems, {"patch": "\n".join(diff_lines), "added": added, "removed": removed}


CAMPAIGN_MD = """# {cid}: {title}
> status: draft | tags: {tags} | session: {session} | summary: {metric}({goal_ko}) 자율 탐색, 최대 {max_trials}번 × {trial_minutes}분

> 이 문서는 교수님이 승인하는 **탐색 계약**이다. 승인 뒤에는 이 범위 안에서만 자율로 시도하고, 채택/기각은 lab.py가 지표로 판정한다.

## 목적의 사슬
- (예: MS-n → Q-xxx → H-xxx → EXP-xxx 파일럿 → 이 캠페인)

## 목표 지표
- 지표: `{metric}` ({goal_ko}) — 평가 코드가 `LAB_METRIC {metric}=값` 줄로 출력
- 실행: `{run_cmd}`{eval_line}
- 한 번의 시도: {trial_minutes}분 고정 예산 (같은 시간 안에서 비교해야 공정하다)

## 탐색 범위
- 수정 가능: {editable}
- 수정 금지 (원본과 해시로 대조): {protected}
- 금지: 평가 방법·데이터 분할 바꾸기, 새 패키지 설치, 데이터 파일 수정, 시드를 골라 쓰기
- 단순함 기준: 성능이 같다면 더 짧은 코드를 채택한다

## 예산과 멈춤 조건
- 최대 {max_trials}번 시도 / 최대 {max_hours}시간
- 연속 {patience}번 채택이 없으면 멈춤 / 연속 {crash_limit}번 실행 실패면 멈추고 사람을 부름
- 채택 문턱: 기준선 반복 측정의 표준편차 × 2 와 {min_delta} 중 큰 값 (잡음으로 인한 가짜 개선을 막는다)

## 확인 실험
- 탐색이 끝나면 최종안과 기준선을 **탐색에 쓰지 않은 새 시드 {confirm_seeds}개**로 다시 돌려 신뢰구간으로 비교한다.
- 결과 확정(F-)은 확인 실험과 리뷰를 거친 뒤 교수님이 결정한다 (C 등급).

## 승인 기록
"""


def cmd_campaign(args) -> None:
    lab = need_lab(args)
    op = args.op
    if op == "init":
        return _campaign_init(lab, args)
    if not args.id:
        sys.exit("오류: 캠페인 ID가 필요합니다 (예: CMP-001)")
    d = campaign_dir(lab, args.id)
    cfg = load_json(d / "campaign.json", {})
    st = load_json(d / "state.json", {})
    {"approve": _campaign_approve, "baseline": _campaign_baseline, "begin": _campaign_begin,
     "run": _campaign_run, "status": _campaign_status, "confirm": _campaign_confirm,
     "stop": _campaign_stop, "close": _campaign_close}[op](lab, d, cfg, st, args)


def _campaign_init(lab: Path, args) -> None:
    src = Path(args.src or "").resolve()
    if not args.src or not src.is_dir():
        sys.exit("오류: --from 으로 코드 폴더를 지정하세요 (예: research/experiments/EXP-003-x/src)")
    for need in ("title", "metric", "goal", "run", "editable"):
        if not getattr(args, need):
            sys.exit(f"오류: --{need} 가 필요합니다")
    if args.goal not in ("min", "max"):
        sys.exit("오류: --goal 은 min 또는 max")
    if args.trial_minutes > MAX_TRIAL_MINUTES:
        sys.exit(f"오류: 한 번의 시도는 {MAX_TRIAL_MINUTES}분 이하여야 합니다 (명령 하나가 10분 안에 끝나야 함)")
    editable = [x.strip() for x in args.editable.split(",") if x.strip()]
    protected = [x.strip() for x in (args.protected or "").split(",") if x.strip()]
    files = _code_files(src)
    missing = [f for f in editable + protected if f not in files]
    if missing:
        sys.exit(f"오류: 코드 폴더에 없는 파일: {missing} (있는 파일: {list(files)[:20]})")
    if set(editable) & set(protected):
        sys.exit("오류: 같은 파일이 수정 가능이면서 수정 금지일 수 없습니다")
    cid = alloc(lab, "campaign")
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", args.slug or "campaign").strip("-").lower() or "campaign"
    d = lab / "research" / "campaigns" / f"{cid}-{slug}"
    d.mkdir(parents=True)
    _copy_code(src, d / "baseline")
    _copy_code(src, d / "best")
    (d / "trials").mkdir()
    cfg = {"id": cid, "title": args.title, "source": rel(lab, src) if src.is_relative_to(lab) else str(src),
           "metric": args.metric, "goal": args.goal, "run_cmd": args.run, "eval_cmd": args.eval,
           "metric_regex": args.metric_regex, "editable": editable, "protected": protected,
           "trial_minutes": args.trial_minutes, "max_trials": args.max_trials, "max_hours": args.max_hours,
           "patience": args.patience, "crash_limit": args.crash_limit, "min_delta": args.min_delta,
           "baseline_repeats": args.baseline_repeats, "confirm_seeds": args.confirm_seeds, "seed": args.seed,
           "created": _now(), "approved": None, "approval_note": None}
    save_json(d / "campaign.json", cfg)
    st = {"protected_hashes": {f: _sha(d / "baseline" / f) for f in protected}, "baseline_runs": [],
          "baseline_done": False, "baseline_metric": None, "noise_std": None, "delta": args.min_delta,
          "best_metric": None, "best_trial": None, "n_trials": 0, "last_keep": 0, "crash_streak": 0,
          "open_trial": None, "started_at": None, "stopped": None, "confirm": None}
    save_json(d / "state.json", st)
    (d / "ledger.tsv").write_text(LEDGER_HEADER, encoding="utf-8")
    (d / "notes.md").write_text("# 탐색 노트\n\n> 효과가 있었던 것, 없었던 것, 다음 시도에 도움이 될 것만 한두 줄씩 쌓는다. 같은 실패를 반복하지 않기 위한 기록이다.\n\n",
                                encoding="utf-8")
    counters = load_json(lab / "state" / "counters.json", {})
    goal_ko = "낮을수록 좋음" if args.goal == "min" else "높을수록 좋음"
    (d / "campaign.md").write_text(CAMPAIGN_MD.format(
        cid=cid, title=args.title, tags=args.tags or "campaign", session=f"{counters.get('session', 0):03d}",
        metric=args.metric, goal_ko=goal_ko, run_cmd=args.run,
        eval_line=f"\n- 평가 (수정 금지): `{args.eval}` — 지표는 이 출력에서만 읽는다" if args.eval else "",
        trial_minutes=args.trial_minutes, editable=", ".join(f"`{x}`" for x in editable),
        protected=", ".join(f"`{x}`" for x in protected) or "(없음 — 평가 코드를 보호 파일로 두기를 권장)",
        max_trials=args.max_trials, max_hours=args.max_hours, patience=args.patience, crash_limit=args.crash_limit,
        min_delta=args.min_delta, confirm_seeds=args.confirm_seeds), encoding="utf-8")
    if not protected:
        print("경고: 수정 금지 파일이 없습니다. 지표를 계산하는 평가 코드는 수정 금지로 두어야 지표를 속일 수 없습니다.")
    print(f"{cid} 캠페인을 만들었습니다: {rel(lab, d)}")
    print("다음: campaign.md를 다듬고 → 기준선 측정(lab.py campaign baseline) → 교수님 승인(lab.py campaign approve)")


def _campaign_approve(lab, d, cfg, st, args) -> None:
    cfg["approved"] = _now()
    cfg["approval_note"] = args.note or "교수님 승인"
    save_json(d / "campaign.json", cfg)
    set_md_status(d / "campaign.md", "approved")
    with open(d / "campaign.md", "a", encoding="utf-8") as f:
        f.write(f"- {cfg['approved']}: {cfg['approval_note']}\n")
    print(f"{cfg['id']} 승인 기록 완료")
    print(_decision_line(cfg, st))


def _campaign_baseline(lab, d, cfg, st, args) -> None:
    """기준선을 서로 다른 시드로 반복 측정한다. 호출 한 번에 실행 한 번 (명령 시간 제한 때문)."""
    if args.reset:
        st.update(baseline_runs=[], baseline_done=False, baseline_metric=None, noise_std=None,
                  best_metric=None, best_trial=None, delta=cfg["min_delta"])
        save_json(d / "state.json", st)
        print("기준선 측정 기록을 지웠습니다")
        return
    if st.get("n_trials"):
        sys.exit("오류: 탐색이 이미 시작되어 기준선을 다시 잴 수 없습니다")
    repeats = cfg["baseline_repeats"]
    runs = st["baseline_runs"]
    if st.get("baseline_done"):
        print(f"기준선 측정은 이미 끝났습니다: {_fmt(st['baseline_metric'])} (표준편차 {_fmt(st['noise_std'])}, 채택 문턱 {_fmt(st['delta'])})")
        return
    i = len(runs)
    seed = cfg["seed"] + i
    label = f"B-{i + 1}"
    scratch = d / "scratch"
    _copy_code(d / "baseline", scratch)
    r = _execute(lab, d, cfg, scratch, seed, label)
    _save_log(d / "trials" / f"{label}.log", r["log"])
    runs.append({"label": label, "seed": seed, "metric": r["metric"], "status": r["status"], "minutes": round(r["minutes"], 2)})
    _ledger_add(d, {"trial": label, "parent": "-", "seed": seed, "metric": _fmt(r["metric"], 10), "improvement": "",
                    "status": "baseline" if r["status"] == "ok" else r["status"], "minutes": f"{r['minutes']:.1f}",
                    "lines": "", "description": "기준선 반복 측정"})
    print(f"기준선 {label} (시드 {seed}): {ko_status(r['status']) if r['status'] != 'ok' else '완료'} 지표 {_fmt(r['metric'])} ({r['minutes']:.1f}분)")
    if r["status"] != "ok":
        print("--- 로그 끝부분 ---")
        print("\n".join(r["log"].splitlines()[-25:]))
        print("기준선이 실패하면 탐색을 시작할 수 없습니다. 코드를 고친 뒤 `lab.py campaign baseline --reset` 후 다시 재세요.")
        save_json(d / "state.json", st)
        return
    ok = [x for x in runs if x["status"] == "ok"]
    if len(ok) >= repeats:
        first = next(x for x in ok if x["seed"] == cfg["seed"]) if any(x["seed"] == cfg["seed"] for x in ok) else ok[0]
        noise = statistics.stdev([x["metric"] for x in ok]) if len(ok) > 1 else 0.0
        st.update(baseline_done=True, baseline_metric=first["metric"], noise_std=noise,
                  delta=max(cfg["min_delta"], 2 * noise), best_metric=first["metric"], best_trial="baseline")
        print(f"기준선 측정 완료: 탐색 기준값 {_fmt(first['metric'])} (시드 {first['seed']}), 시드 간 표준편차 {_fmt(noise)}")
        print(f"채택 문턱 δ = {_fmt(st['delta'])} (이보다 크게 좋아져야 채택)")
    else:
        print(f"기준선 측정 {len(ok)}/{repeats} — 같은 명령을 한 번 더 실행하세요")
    save_json(d / "state.json", st)


def _campaign_begin(lab, d, cfg, st, args) -> None:
    if not cfg.get("approved"):
        sys.exit("오류: 교수님 승인 전입니다 (C 등급). lab.py campaign approve 가 먼저입니다")
    if not st.get("baseline_done"):
        sys.exit("오류: 기준선을 먼저 측정하세요 (lab.py campaign baseline)")
    reason = _stop_reason(cfg, st)
    if reason:
        _mark_stopped(d, st, reason)
        print(f"판정: 종료 — {reason}")
        return
    if not st.get("started_at"):
        st["started_at"] = _now()
        set_md_status(d / "campaign.md", "running")
    trial = st.get("open_trial") or f"T-{st['n_trials'] + 1:03d}"
    st["open_trial"] = trial
    _copy_code(d / "best", d / "work")
    save_json(d / "state.json", st)
    print(f"시도 {trial} 준비 완료. 현재 최고: {_fmt(st['best_metric'])} ({st['best_trial']}), 채택 문턱 δ={_fmt(st['delta'])}")
    print("수정 가능 파일: " + ", ".join(rel(lab, d / "work" / f) for f in cfg["editable"]))
    print(f"아이디어 하나만 바꾼 뒤: lab.py campaign run {cfg['id']} --desc \"무엇을 왜 바꿨는지\"  (Bash timeout 600000으로 실행)")


def _campaign_run(lab, d, cfg, st, args) -> None:
    trial = st.get("open_trial")
    if not trial or not (d / "work").exists():
        sys.exit("오류: 열린 시도가 없습니다. lab.py campaign begin 을 먼저 실행하세요")
    if not args.desc:
        sys.exit("오류: --desc 로 무엇을 바꿨는지 한 줄로 적으세요")
    problems, ch = _check_trial_rules(d, cfg, st)
    if not problems and not ch["patch"].strip():
        sys.exit("오류: 수정 가능 파일에 바뀐 내용이 없습니다")
    (d / "trials" / f"{trial}.patch").write_text(ch["patch"] + "\n", encoding="utf-8")
    parent, best = st["best_trial"], st["best_metric"]
    if problems:
        status, metric, mins, imp = "invalid", None, 0.0, None
        (d / "trials" / f"{trial}.log").write_text("규칙 위반으로 실행하지 않음:\n" + "\n".join(problems) + "\n", encoding="utf-8")
    else:
        r = _execute(lab, d, cfg, d / "work", cfg["seed"], trial)
        _save_log(d / "trials" / f"{trial}.log", r["log"])
        metric, mins = r["metric"], r["minutes"]
        imp = None if metric is None else _improvement(cfg["goal"], metric, best)
        if r["status"] != "ok":
            status = r["status"]
        elif imp is not None and imp > 0 and imp >= st["delta"]:
            status = "keep"
        elif imp is not None and ch["added"] < ch["removed"] and imp > -st["delta"]:
            status = "keep-simpler"
        else:
            status = "discard"
    st["n_trials"] += 1
    if status in ("keep", "keep-simpler"):
        for rp in cfg["editable"]:
            shutil.copy2(d / "work" / rp, d / "best" / rp)
        st.update(best_metric=metric, best_trial=trial, last_keep=st["n_trials"])
    st["crash_streak"] = st.get("crash_streak", 0) + 1 if status in ("crash", "timeout", "invalid") else 0
    st["open_trial"] = None
    save_json(d / "state.json", st)
    _ledger_add(d, {"trial": trial, "parent": parent, "seed": cfg["seed"], "metric": _fmt(metric, 10),
                    "improvement": "" if imp is None else f"{imp:+.6g}", "status": status, "minutes": f"{mins:.1f}",
                    "lines": f"+{ch['added']}/-{ch['removed']}", "description": args.desc})
    tail = f" (최고 {_fmt(best)} 대비 {imp:+.4g})" if imp is not None else ""
    print(f"{trial} {ko_status(status)} | 지표 {_fmt(metric)}{tail} | {mins:.1f}분 | +{ch['added']}/-{ch['removed']}줄 | {args.desc}")
    if problems:
        print("규칙 위반: " + "; ".join(problems))
    elif status in ("crash", "timeout"):
        print("--- 로그 끝부분 ---")
        print("\n".join((d / "trials" / f"{trial}.log").read_text(encoding="utf-8").splitlines()[-25:]))
    reason = _stop_reason(cfg, st)
    if reason:
        _mark_stopped(d, st, reason)
    print(_decision_line(cfg, st))


def _campaign_status(lab, d, cfg, st, args) -> None:
    goal_ko = "낮을수록 좋음" if cfg["goal"] == "min" else "높을수록 좋음"
    meta = md_meta_raw(d / "campaign.md")
    print(f"# {cfg['id']}: {cfg['title']}  [{ko_status(meta.get('status', ''))}]")
    print(f"- 지표 {cfg['metric']} ({goal_ko}), 시도당 {cfg['trial_minutes']}분, 수정 가능: {', '.join(cfg['editable'])}")
    if st.get("baseline_done"):
        gain = _improvement(cfg["goal"], st["best_metric"], st["baseline_metric"])
        rel_gain = f" ({gain / abs(st['baseline_metric']):+.2%})" if st["baseline_metric"] else ""
        print(f"- 기준선 {_fmt(st['baseline_metric'])} → 현재 최고 {_fmt(st['best_metric'])} ({st['best_trial']}), 개선 {gain:+.4g}{rel_gain}")
        print(f"- 채택 문턱 δ={_fmt(st['delta'])} (기준선 표준편차 {_fmt(st['noise_std'])})")
    print(f"- 시도 {st.get('n_trials', 0)}/{cfg['max_trials']}, 경과 {_hours_since(st.get('started_at')):.1f}/{cfg['max_hours']}시간, "
          f"마지막 채택 뒤 {st.get('n_trials', 0) - st.get('last_keep', 0)}/{cfg['patience']}번, 연속 실패 {st.get('crash_streak', 0)}번")
    rows = [r for r in _ledger_rows(d) if r["trial"].startswith("T-")]
    keeps = [r for r in rows if r["status"] in ("keep", "keep-simpler")]
    if keeps:
        print("- 채택 이력: " + " → ".join(f"{r['trial']}({r['improvement']})" for r in keeps))
    if rows:
        print("## 최근 시도")
        for r in rows[-8:]:
            print(f"  {r['trial']} {ko_status(r['status'])} {r['metric']} {r['improvement']} {r['lines']} {r['description']}")
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print("- 집계: " + ", ".join(f"{ko_status(k)} {v}" for k, v in counts.items()))
    if st.get("confirm") and st["confirm"].get("result"):
        c = st["confirm"]["result"]
        print(f"## 확인 실험: {c['verdict']} (개선 {c['improvement']:+.4g}, 95% 신뢰구간 [{c['ci_low']:+.4g}, {c['ci_high']:+.4g}])")
    print(_decision_line(cfg, st))


def _campaign_confirm(lab, d, cfg, st, args) -> None:
    """최종안과 기준선을 새 시드로 번갈아 실행한다. 호출 한 번에 실행 한 번."""
    reason = _stop_reason(cfg, st)
    if not reason and not args.force:
        sys.exit("오류: 탐색이 아직 끝나지 않았습니다 (--force 로 강제할 수 있음)")
    if reason:
        _mark_stopped(d, st, reason)
    if st.get("best_trial") in (None, "baseline"):
        print("채택된 개선이 없어 확인 실험이 필요 없습니다. 결과: 이 탐색 범위에서는 기준선보다 나은 안을 찾지 못함 (영(null) 결과로 기록할 것)")
        st["confirm"] = {"best_trial": "baseline", "result": {"verdict": "채택된 개선 없음", "improvement": 0.0,
                                                               "ci_low": 0.0, "ci_high": 0.0}}
        save_json(d / "state.json", st)
        return
    conf = st.get("confirm") or {}
    if conf.get("best_trial") != st["best_trial"]:
        conf = {"best_trial": st["best_trial"], "runs": {}}
    seeds = [cfg["seed"] + CONFIRM_SEED_OFFSET + i for i in range(cfg["confirm_seeds"])]
    plan = [(arm, s) for s in seeds for arm in ("baseline", "best")]
    todo = [(arm, s) for arm, s in plan if f"{arm}-s{s}" not in conf["runs"]]
    if todo:
        arm, s = todo[0]
        label = f"C-{arm}-s{s}"
        scratch = d / "scratch"
        _copy_code(d / arm, scratch)
        r = _execute(lab, d, cfg, scratch, s, label)
        _save_log(d / "trials" / f"{label}.log", r["log"])
        conf["runs"][f"{arm}-s{s}"] = {"metric": r["metric"], "status": r["status"], "minutes": round(r["minutes"], 2)}
        st["confirm"] = conf
        save_json(d / "state.json", st)
        done = len(plan) - len(todo) + 1
        print(f"확인 실험 {done}/{len(plan)}: {'기준선' if arm == 'baseline' else '최종안'} 시드 {s} → {ko_status(r['status']) if r['status'] != 'ok' else '완료'} {_fmt(r['metric'])} ({r['minutes']:.1f}분)")
        if done < len(plan):
            print("같은 명령을 다시 실행해 다음 확인 실행을 진행하세요")
            return
    base = [v["metric"] for k, v in conf["runs"].items() if k.startswith("baseline") and v["status"] == "ok"]
    best = [v["metric"] for k, v in conf["runs"].items() if k.startswith("best") and v["status"] == "ok"]
    if not base or not best:
        print("확인 실험 실행이 실패해서 비교할 수 없습니다. 로그를 확인하세요 (trials/C-*.log)")
        return
    result = _bootstrap_compare(best, base, cfg["goal"])
    result.update(baseline_values=base, best_values=best, seeds=seeds, best_trial=st["best_trial"])
    conf["result"] = result
    st["confirm"] = conf
    save_json(d / "state.json", st)
    save_json(d / "confirm.json", result)
    set_md_status(d / "campaign.md", "confirmed")
    print(f"확인 실험 완료 ({len(best)}+{len(base)}회, 새 시드 {seeds}): {result['verdict']}")
    print(f"- 기준선 평균 {_fmt(statistics.fmean(base))}, 최종안 평균 {_fmt(statistics.fmean(best))}, "
          f"개선 {result['improvement']:+.4g}, 95% 신뢰구간 [{result['ci_low']:+.4g}, {result['ci_high']:+.4g}]")


def _campaign_stop(lab, d, cfg, st, args) -> None:
    _mark_stopped(d, st, args.reason or "교수님 요청으로 중단")
    print(f"{cfg['id']} 탐색을 멈췄습니다: {st['stopped']}")


def _campaign_close(lab, d, cfg, st, args) -> None:
    """리뷰와 교수님 결정까지 끝난 캠페인을 닫는다 (현황 목록에서 빠진다)."""
    if not st.get("stopped"):
        _mark_stopped(d, st, args.reason or "종료 처리")
    st["closed"] = _now()
    st["close_note"] = args.note or ""
    save_json(d / "state.json", st)
    set_md_status(d / "campaign.md", "closed")
    with open(d / "campaign.md", "a", encoding="utf-8") as f:
        f.write(f"- {st['closed']}: 닫음 — {args.note or '리뷰와 결정 완료'}\n")
    print(f"{cfg['id']} 캠페인을 닫았습니다")


def campaign_verify(lab: Path, d: Path) -> list[tuple[str, str]]:
    """장부(ledger)의 모든 숫자를 로그에서 다시 읽어 대조하고, 채택 판정을 규칙대로 다시 계산한다."""
    cfg = load_json(d / "campaign.json", {})
    st = load_json(d / "state.json", {})
    issues: list[tuple[str, str]] = []
    rows = _ledger_rows(d)
    for r in rows:
        log = d / "trials" / f"{r['trial']}.log"
        if r["status"] == "invalid":
            continue
        if not log.exists():
            issues.append(("실패", f"{r['trial']}: 로그가 없습니다"))
            continue
        if r["status"] in ("keep", "keep-simpler", "discard", "baseline"):
            m = _metric_from_log(log.read_text(encoding="utf-8"), cfg)
            try:
                lv = float(r["metric"])
            except ValueError:
                lv = None
            if m is None or lv is None or abs(m - lv) > 1e-6 * max(1.0, abs(m)):
                issues.append(("실패", f"{r['trial']}: 장부 지표 {r['metric']}이(가) 로그의 값 {m}과 다릅니다"))
        if r["trial"].startswith("T-") and not (d / "trials" / f"{r['trial']}.patch").exists():
            issues.append(("경고", f"{r['trial']}: 변경 내용(patch)이 없습니다"))
    if st.get("baseline_done"):
        best, best_trial = st["baseline_metric"], "baseline"
        for r in rows:
            if not r["trial"].startswith("T-") or r["status"] not in ("keep", "keep-simpler", "discard"):
                continue
            m = float(r["metric"])
            imp = _improvement(cfg["goal"], m, best)
            added, removed = (int(x) for x in re.findall(r"\d+", r["lines"])[:2]) if r["lines"] else (0, 0)
            should = "keep" if (imp > 0 and imp >= st["delta"]) else (
                "keep-simpler" if (added < removed and imp > -st["delta"]) else "discard")
            if should != r["status"]:
                issues.append(("실패", f"{r['trial']}: 장부 판정 {r['status']} ≠ 규칙 재계산 {should}"))
            if r["status"] in ("keep", "keep-simpler"):
                best, best_trial = m, r["trial"]
        if st.get("best_trial") != best_trial or abs((st.get("best_metric") or 0) - best) > 1e-9 * max(1.0, abs(best)):
            issues.append(("실패", f"상태 파일의 최고안({st.get('best_trial')})이 장부 재계산({best_trial})과 다릅니다"))
    for rp, h in st.get("protected_hashes", {}).items():
        for arm in ("best", "baseline"):
            f = d / arm / rp
            if not f.exists() or _sha(f) != h:
                issues.append(("실패", f"{arm}/{rp}: 보호 파일이 원본과 다릅니다"))
    base_files, best_files = _code_files(d / "baseline"), _code_files(d / "best")
    for rp in set(base_files) | set(best_files):
        if rp in cfg.get("editable", []):
            continue
        if rp not in best_files or rp not in base_files or _sha(base_files[rp]) != _sha(best_files[rp]):
            issues.append(("실패", f"수정 가능 목록에 없는 {rp}이(가) 기준선과 최종안에서 다릅니다"))
    conf = (st.get("confirm") or {})
    for key, v in (conf.get("runs") or {}).items():
        log = d / "trials" / f"C-{key}.log"
        if v["status"] == "ok":
            m = _metric_from_log(log.read_text(encoding="utf-8"), cfg) if log.exists() else None
            if m is None or abs(m - v["metric"]) > 1e-6 * max(1.0, abs(m)):
                issues.append(("실패", f"확인 실험 {key}: 기록 {v['metric']} ≠ 로그 {m}"))
    issues.append(("정보", f"장부 {len(rows)}줄, 채택 {sum(1 for r in rows if r['status'] in ('keep', 'keep-simpler'))}번, "
                           f"확인 실험 {'있음' if conf.get('result') else '없음'}"))
    return issues


def active_campaign_lines(lab: Path) -> list[str]:
    out = []
    for d in sorted((lab / "research" / "campaigns").glob("CMP-*")):
        if not d.is_dir():
            continue
        status = md_meta_raw(d / "campaign.md").get("status", "")
        if status not in ("draft", "approved", "running", "stopped", "confirmed"):
            continue
        cfg, st = load_json(d / "campaign.json", {}), load_json(d / "state.json", {})
        if not cfg:
            continue
        best = st.get("best_metric")
        gain = _improvement(cfg["goal"], best, st["baseline_metric"]) if st.get("baseline_done") and best is not None else None
        gain_txt = f", 기준선 대비 {gain:+.4g}" if gain is not None else ""
        extra = {"draft": " → 기준선 측정과 교수님 승인 필요", "approved": " → 탐색 시작 가능",
                 "stopped": " → 확인 실험 필요" if not (st.get("confirm") or {}).get("result") else "",
                 "confirmed": " → 리뷰와 교수님 결정 필요 (끝나면 campaign close)"}.get(status, "")
        out.append(f"- {cfg['id']} [{ko_status(status)}] {cfg['title']}: 시도 {st.get('n_trials', 0)}/{cfg['max_trials']}, "
                   f"최고 {_fmt(best)}{gain_txt}{extra}")
    return out


# ---------------------------------------------------------------- 쌍대 비교 순위 (아이디어 토너먼트)

def cmd_rank(args) -> None:
    if args.op == "schedule":
        items = list(dict.fromkeys(args.items))
        if len(items) < 2:
            sys.exit("오류: 후보가 2개 이상 필요합니다")
        rng = random.Random(args.seed)
        pairs = list(itertools.combinations(items, 2))
        rng.shuffle(pairs)
        print(f"# 쌍대 비교 일정 ({len(pairs)}쌍). 각 줄에 이긴 쪽을 앞에 써서 `A > B | 이유` 형식으로 기록하세요.")
        for i, (a, b) in enumerate(pairs, 1):
            print(f"{i}. {b} vs {a}" if rng.random() < 0.5 else f"{i}. {a} vs {b}")
        return
    text = Path(args.file).read_text(encoding="utf-8")
    games: list[tuple[str, str]] = []
    for ln in text.splitlines():
        m = re.match(r"^\s*(?:\d+[.)]\s*)?([\w가-힣-]+)\s*([<>])\s*([\w가-힣-]+)", ln)
        if m:
            a, op, b = m.groups()
            games.append((a, b) if op == ">" else (b, a))
    if not games:
        sys.exit("오류: `A > B` 형식의 판정 줄을 찾지 못했습니다")
    players = sorted({p for g in games for p in g})
    wins = {p: 0.0 for p in players}
    n: dict[tuple[str, str], float] = {}
    for w, l in games:
        wins[w] += 1
        n[(w, l)] = n.get((w, l), 0) + 1
        n[(l, w)] = n.get((l, w), 0) + 1
    for a, b in itertools.combinations(players, 2):  # 모든 쌍에 반 무승부씩을 더해 0승 후보도 점수가 생기게 한다
        wins[a] += 0.5
        wins[b] += 0.5
        n[(a, b)] = n.get((a, b), 0) + 1
        n[(b, a)] = n.get((b, a), 0) + 1
    p = {x: 1.0 for x in players}
    for _ in range(500):  # Bradley-Terry 최대우도 (MM 알고리즘)
        new = {}
        for i in players:
            denom = sum(n.get((i, j), 0) / (p[i] + p[j]) for j in players if j != i)
            new[i] = wins[i] / denom if denom else p[i]
        g = math.exp(statistics.fmean(math.log(v) for v in new.values()))
        p = {k: v / g for k, v in new.items()}
    raw = {x: sum(1 for w, _ in games if w == x) for x in players}
    lost = {x: sum(1 for _, l in games if l == x) for x in players}
    print("| 순위 | 후보 | 승 | 패 | 점수(Elo 환산) |")
    print("|---|---|---|---|---|")
    for rank, x in enumerate(sorted(players, key=lambda k: -p[k]), 1):
        print(f"| {rank} | {x} | {raw[x]} | {lost[x]} | {1500 + 400 * math.log10(p[x]):.0f} |")


# ---------------------------------------------------------------- 문헌 도구 (실제 서지 정보로 인용 환각을 막는다)

HTTP_HEADERS = {"User-Agent": "ai-lab/0.7 (research-lab tool)", "Accept": "*/*"}  # Accept가 없으면 arXiv가 406을 돌려준다


def _http_get(url: str, timeout: float = 20.0, retries: int = 2) -> str | None:
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HTTP_HEADERS), timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:  # 공개 API의 요청 제한: 잠시 기다렸다 다시
                time.sleep(3 * (attempt + 1))
                continue
            if e.code in (403, 406) and shutil.which("curl"):  # 일부 사이트 방화벽은 Python 접속만 거부한다
                body = _curl_get(url, timeout)
                if body is not None:
                    return body
            print(f"경고: {url.split('?')[0]} 접속 실패 (HTTP {e.code})", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"경고: {url.split('?')[0]} 접속 실패 ({e})", file=sys.stderr)
            return None
    return None


def _curl_get(url: str, timeout: float) -> str | None:
    try:
        r = subprocess.run(["curl", "-sSL", "--max-time", str(int(timeout)), "-A", HTTP_HEADERS["User-Agent"], url],
                           capture_output=True, timeout=timeout + 5)
        return r.stdout.decode("utf-8", errors="replace") if r.returncode == 0 and r.stdout else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _clean(s: str) -> str:
    import html as _html
    return _html.unescape(" ".join(s.split()))


def _arxiv_entries(xml: str) -> list[dict]:
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        g = lambda tag: (re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", e, re.S) or [None, ""])[1]
        aid = re.sub(r"v\d+$", "", g("id").rsplit("/abs/", 1)[-1])
        out.append({"id": "arXiv:" + aid, "title": _clean(g("title")),
                    "year": g("published")[:4], "authors": [_clean(a) for a in re.findall(r"<name>(.*?)</name>", e)],
                    "abstract": _clean(g("summary")), "url": "https://arxiv.org/abs/" + aid,
                    "venue": "arXiv", "citations": None})
    return out


def _arxiv_search(q: str, limit: int) -> list[dict]:
    words = [w for w in re.findall(r"[\w-]+", q) if len(w) > 1]
    query = urllib.parse.quote(" AND ".join(f"all:{w}" for w in words))
    xml = _http_get(f"https://export.arxiv.org/api/query?search_query={query}&start=0&max_results={limit}&sortBy=relevance")
    return _arxiv_entries(xml) if xml else []


def _s2_papers(data: list[dict]) -> list[dict]:
    out = []
    for p in data:
        ext = p.get("externalIds") or {}
        pid = f"arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else (f"DOI:{ext['DOI']}" if ext.get("DOI") else f"S2:{p.get('paperId')}")
        out.append({"id": pid, "title": p.get("title") or "", "year": str(p.get("year") or ""),
                    "authors": [a.get("name", "") for a in p.get("authors") or []], "abstract": p.get("abstract") or "",
                    "url": p.get("url") or "", "venue": p.get("venue") or "", "citations": p.get("citationCount")})
    return out


S2_FIELDS = "title,year,venue,externalIds,citationCount,authors,url,abstract"


def _s2_search(q: str, limit: int) -> list[dict]:
    body = _http_get(f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(q)}&limit={limit}&fields={S2_FIELDS}")
    if not body:
        return []
    try:
        return _s2_papers(json.loads(body).get("data") or [])
    except json.JSONDecodeError:
        return []


def _lookup(pid: str) -> dict | None:
    pid = pid.strip()
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", pid)
    if m and ("arxiv" in pid.lower() or re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", pid)):
        xml = _http_get(f"https://export.arxiv.org/api/query?id_list={m.group(1)}")
        ents = _arxiv_entries(xml) if xml else []
        return ents[0] if ents and ents[0]["title"] else None
    key = pid if ":" in pid else f"DOI:{pid}"
    body = _http_get(f"https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(key, safe=':/')}?fields={S2_FIELDS}")
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    return _s2_papers([data])[0] if data.get("title") else None


def _norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", " ", s.lower()).strip()


def _paper_line(p: dict) -> str:
    au = p["authors"][0] + (" 외" if len(p["authors"]) > 1 else "") if p["authors"] else "?"
    cit = f", 인용 {p['citations']}" if p.get("citations") is not None else ""
    return f"{p['id']} ({p['year']}{', ' + p['venue'] if p.get('venue') and p['venue'] != 'arXiv' else ''}{cit}) {p['title']} — {au} | {p['url']}"


def cmd_lit(args) -> None:
    if args.op == "search":
        q = " ".join(args.terms)
        results: list[dict] = []
        if args.source in ("arxiv", "both"):
            results += _arxiv_search(q, args.limit)
        if args.source in ("s2", "both"):
            seen = {_norm_title(p["title"]) for p in results}
            results += [p for p in _s2_search(q, args.limit) if _norm_title(p["title"]) not in seen]
        if args.since:
            results = [p for p in results if p["year"].isdigit() and int(p["year"]) >= args.since]
        if not results:
            print("(찾은 논문 없음 — 영어 검색어로 바꾸거나 --source 를 바꿔 보세요)")
        for p in results:
            print(_paper_line(p))
        return
    if args.op == "get":
        p = _lookup(" ".join(args.terms))
        if not p:
            sys.exit("오류: 논문을 찾지 못했습니다 (arXiv ID 예: 2201.02177, DOI 예: 10.1038/xxx)")
        print(_paper_line(p))
        print(f"저자: {', '.join(p['authors'][:8])}")
        print(f"초록: {p['abstract'][:1500]}")
        return
    lab = need_lab(args)
    papers = sorted((lab / "kb" / "papers").glob("P-*.json"))
    if not papers:
        print("(확인할 논문 항목이 없습니다)")
        return
    bad = 0
    for f in papers:
        e = load_json(f, {})
        ref = e.get("arxiv") or e.get("doi") or ""
        if not ref and "arxiv.org/abs/" in (e.get("url") or ""):
            ref = e["url"].rsplit("/abs/", 1)[1]
        if not ref:
            print(f"[경고] {e.get('id', f.stem)}: arXiv ID나 DOI가 없어 확인할 수 없습니다 ({e.get('title', '')[:60]})")
            bad += 1
            continue
        p = _lookup(ref)
        if not p:
            print(f"[확인 불가] {e.get('id')}: {ref} 조회 실패 (네트워크 또는 잘못된 ID)")
            bad += 1
            continue
        sim = difflib.SequenceMatcher(None, _norm_title(e.get("title", "")), _norm_title(p["title"])).ratio()
        if sim >= 0.85:
            print(f"[정상] {e.get('id')}: {p['title'][:80]}")
        else:
            print(f"[불일치] {e.get('id')}: 기록된 제목 '{e.get('title', '')[:60]}' ≠ 실제 '{p['title'][:60]}' (유사도 {sim:.2f})")
            bad += 1
        time.sleep(0.5)  # 공개 API 예의상 간격
    print(f"논문 {len(papers)}개 확인, 문제 {bad}개")


# ---------------------------------------------------------------- 감사 (Chain-of-Evidence 식 점검)

NUM_TOKEN = re.compile(r"(?<![\w./-])([-+−]?\d+\.\d+%?|\d+(?:\.\d+)?%)(?![\w/-])")


def _all_numbers(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, dict):
        for v in obj.values():
            out += _all_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _all_numbers(v)
    return out


def _source_numbers(d: Path) -> list[float]:
    nums: list[float] = []
    for src in ("results.json", "confirm.json", "campaign.json", "state.json"):
        if (d / src).exists():
            nums += _all_numbers(load_json(d / src, {}))
    for r in _ledger_rows(d):
        for k in ("metric", "improvement"):
            try:
                nums.append(float(r.get(k, "")))
            except ValueError:
                pass
    return nums


def report_number_check(d: Path, rep: Path | None = None, sources: list[Path] | None = None) -> list[tuple[str, str]]:
    """보고서의 소수·백분율 숫자가 결과 파일(results.json, confirm.json, 장부)의 값과 반올림 기준으로 일치하는지."""
    rep = rep or next((d / n for n in ("report.md", "summary.md") if (d / n).exists()), None)
    if rep is None:
        return [("정보", "보고서가 없어 숫자 대조를 건너뜀")]
    nums: list[float] = []
    for s in (sources or [d]):
        nums += _source_numbers(s)
    text = re.sub(r"```.*?```", " ", rep.read_text(encoding="utf-8"), flags=re.S)
    tokens = NUM_TOKEN.findall(text)
    unmatched = []
    for tok in tokens:
        pct = tok.endswith("%")
        s = tok.rstrip("%").replace("−", "-")
        val = abs(float(s))
        dec = len(s.split(".")[1]) if "." in s else 0
        tol = 0.5 * 10 ** (-dec) + 1e-12
        cands = [abs(n) for n in nums] + ([abs(n) * 100 for n in nums] if pct else [])
        if not any(abs(val - c) <= tol for c in cands):
            unmatched.append(tok)
    if not tokens:
        return [("정보", f"{rep.name}에 대조할 소수/백분율 숫자가 없습니다")]
    if unmatched:
        return [("경고", f"{rep.name}의 숫자 {len(tokens)}개 중 {len(unmatched)}개는 결과 파일에서 찾지 못했습니다 "
                        f"(출처를 밝히거나 결과 파일에서 계산할 것): {', '.join(unmatched[:12])}")]
    return [("정보", f"{rep.name}의 숫자 {len(tokens)}개가 모두 결과 파일과 일치합니다")]


def spec_check(d: Path) -> list[tuple[str, str]]:
    """계획(plan.md 메타 줄의 conditions/seeds/metric)대로 실행했는지."""
    meta = md_meta_raw(d / "plan.md")
    res = load_json(d / "results.json", None)
    if res is None:
        return []
    issues = []
    conds = [c.strip() for c in meta.get("conditions", "").split(",") if c.strip()]
    summary = res.get("summary", {})
    for c in conds:
        if c not in summary:
            issues.append(("실패", f"계획한 조건 '{c}'의 결과가 없습니다 (계획 위반 또는 누락)"))
    extra = [c for c in summary if conds and c not in conds]
    if extra:
        issues.append(("경고", f"계획에 없던 조건이 결과에 있습니다: {extra} (사후 추가라면 보고서에 밝힐 것)"))
    seeds = meta.get("seeds", "")
    if seeds.isdigit():
        for c, metrics in summary.items():
            ns = [m.get("n", 0) for m in metrics.values()] or [0]
            if min(ns) < int(seeds):
                issues.append(("경고", f"조건 '{c}'의 시드 수 {min(ns)}개 < 계획 {seeds}개"))
    metric = meta.get("metric", "")
    if metric and summary and not any(metric in m for m in summary.values()):
        issues.append(("실패", f"계획한 주 지표 '{metric}'가 결과에 없습니다"))
    if not meta.get("conditions"):
        issues.append(("정보", "plan.md 메타 줄에 conditions/seeds/metric이 없어 계획 대조를 일부 건너뜀"))
    return issues


def cmd_audit(args) -> None:
    lab = need_lab(args)
    if args.report:  # 논문·요약 같은 임의 문서의 숫자를 지정한 실험/캠페인 결과와 대조
        rep = Path(args.report)
        if not rep.exists():
            sys.exit(f"오류: {rep} 파일이 없습니다")
        ids = [x.strip() for x in (args.sources or "").split(",") if x.strip()]
        if not ids:
            sys.exit("오류: --sources 로 숫자의 출처 실험/캠페인 ID를 쉼표로 지정하세요 (예: EXP-001,CMP-002)")
        dirs = [campaign_dir(lab, i) if i.upper().startswith("CMP-") else (exp_dir(lab, i) or sys.exit(f"오류: {i} 없음"))
                for i in ids]
        issues = report_number_check(dirs[0], rep, dirs)
        cited = sorted(set(re.findall(r"\bP-\d{3,}\b", rep.read_text(encoding="utf-8"))))
        missing = [p for p in cited if not (lab / "kb" / "papers" / f"{p}.json").exists()]
        if missing:
            issues.append(("실패", f"문서가 인용한 논문 항목이 지식베이스에 없습니다: {missing}"))
        elif cited:
            issues.append(("정보", f"인용 {len(cited)}개가 논문 항목으로 존재함 (실존 여부는 lab.py lit check)"))
        fails = print_issues(issues)
        print(f"감사 {rep.name}: {'실패' if fails else '통과'} (실패 {fails}건, 경고 {sum(1 for l, _ in issues if l == '경고')}건)")
        if fails:
            sys.exit(1)
        return
    if not args.id:
        sys.exit("오류: 감사할 EXP-/CMP- ID 또는 --report 문서를 지정하세요")
    eid = args.id.upper()
    if eid.startswith("CMP-"):
        d = campaign_dir(lab, eid)
        issues = campaign_verify(lab, d) + report_number_check(d)
    else:
        d = exp_dir(lab, eid)
        if d is None:
            sys.exit(f"오류: {eid} 실험 폴더가 없습니다")
        issues = verify_experiment(d) + spec_check(d) + report_number_check(d)
    issues.append(("정보", "사람(비평가)이 볼 것: 보고서의 방법 설명이 실제 코드와 같은지, 검증하지 않은 조건으로 일반화하지 않았는지"))
    fails = print_issues(issues)
    warns = sum(1 for lvl, _ in issues if lvl == "경고")
    print(f"감사 {eid}: {'실패' if fails else '통과'} (실패 {fails}건, 경고 {warns}건)")
    if fails:
        sys.exit(1)


# ---------------------------------------------------------------- 점검 (지식베이스 무결성), 환경 진단, 연구 지도

def lint_issues(lab: Path) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    rows = get_index(lab)
    known = {r["id"] for r in rows}
    known |= {a["id"] for a in load_json(lab / "state" / "actions.json", [])}
    known |= {q["id"] for q in load_json(lab / "state" / "inbox.json", [])}
    for r in rows:
        p = lab / r["path"]
        if p.is_dir():
            text = " ".join((p / n).read_text(encoding="utf-8") for n in DIR_SUMMARY if (p / n).exists())
        else:
            text = p.read_text(encoding="utf-8") if p.exists() else ""
        missing = sorted({m for m in ID_RE.findall(text) if m not in known and m != r["id"]})
        if missing:
            issues.append(("경고", f"{r['id']}: 없는 항목을 참조합니다 {missing[:6]}"))
        if r["type"] in ("idea", "lit", "review", "experiment", "brainstorm", "release", "campaign") and not r["status"]:
            issues.append(("경고", f"{r['id']}: 머리말 메타 줄(> status: …)이 없어 검색·색인이 부정확합니다"))
    for f in sorted((lab / "kb" / "findings").glob("F-*.json")):
        e = load_json(f, {})
        if e.get("status") == "accepted" and e.get("decided_by") != "교수님":
            issues.append(("실패", f"{e.get('id', f.stem)}: 확정(accepted)인데 교수님 결정 기록(decided_by)이 없습니다"))
        if not e.get("evidence"):
            issues.append(("경고", f"{e.get('id', f.stem)}: 증거(evidence) 경로가 없습니다"))
    today_d = dt.date.today()
    for q in load_json(lab / "state" / "inbox.json", []):
        if q.get("status") == "open" and q.get("created"):
            age = (today_d - dt.date.fromisoformat(q["created"])).days
            if age >= 7:
                issues.append(("경고", f"{q['id']}: 교수님 결정을 {age}일째 기다리는 중입니다"))
    for a in load_json(lab / "state" / "actions.json", []):
        if a.get("status") == "open" and a.get("created"):
            age = (today_d - dt.date.fromisoformat(a["created"])).days
            if age >= 21:
                issues.append(("정보", f"{a['id']}: {age}일째 열린 할 일 — 계속할지 정리할지 정할 것"))
    for relp, limit in (("state/lab_state.md", 40), ("state/cycle.md", 40), ("ROADMAP.md", 60), ("CLAUDE.md", 60)):
        f = lab / relp
        if f.exists():
            n = len([ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()])
            if n > limit:
                issues.append(("경고", f"{relp}가 {n}줄입니다 (권장 {limit}줄 이하 — 매번 읽히므로 짧게)"))
    digest = lab / "kb" / "digest.md"
    newest = max((f.stat().st_mtime for f in (lab / "kb").rglob("*.json") if f.name != "index.json"), default=0)
    if newest and (not digest.exists() or digest.stat().st_mtime < newest):
        issues.append(("정보", "kb/digest.md가 최신이 아닙니다 (lab.py digest)"))
    return issues


def cmd_lint(args) -> None:
    lab = need_lab(args)
    issues = lint_issues(lab)
    if not issues:
        print("점검 통과: 문제를 찾지 못했습니다")
        return
    fails = print_issues(issues)
    print(f"점검 결과: 실패 {fails}건, 경고 {sum(1 for l, _ in issues if l == '경고')}건, 정보 {sum(1 for l, _ in issues if l == '정보')}건")


# ---------------------------------------------------------------- HTML 리포트 (세션·실험·캠페인)

def _report_mod():
    if str(SELF.parent) not in sys.path:
        sys.path.insert(0, str(SELF.parent))
    import report_html
    return report_html


def _audit_verdict(lab: Path, eid: str) -> str:
    try:
        if eid.startswith("CMP-"):
            d = campaign_dir(lab, eid)
            issues = campaign_verify(lab, d) + report_number_check(d)
        else:
            d = exp_dir(lab, eid)
            if d is None:
                return "확인 불가"
            issues = verify_experiment(d) + spec_check(d) + report_number_check(d)
    except (SystemExit, OSError, ValueError, KeyError):
        return "확인 불가"
    fails = sum(1 for lvl, _ in issues if lvl == "실패")
    return f"실패 {fails}건" if fails else "통과"


def _figures(R, d: Path, limit: int) -> str:
    out = []
    figs = [f for f in sorted((d / "figures").glob("*")) if f.suffix.lower() in (".png", ".svg", ".jpg", ".jpeg")]
    for f in figs[:limit]:
        if f.stat().st_size > 3_000_000:
            out.append(f'<p class="empty">{R.esc(f.name)}: 3MB가 넘어 넣지 않았습니다 ({R.esc(rel(d.parent.parent.parent, f))})</p>')
        else:
            out.append(R.img_tag(f.read_bytes(), f.name))
    if len(figs) > limit:
        out.append(f'<p class="muted">그림 {len(figs) - limit}개 더 있음: {R.esc(rel(d.parent.parent.parent, d / "figures"))}</p>')
    return "".join(out)


def _md_details(R, path: Path, label: str, open_: bool = False) -> str:
    if not path.exists():
        return ""
    return (f'<details{" open" if open_ else ""}><summary>{R.esc(label)}</summary>'
            f"{R.md_to_html(path.read_text(encoding='utf-8'))}</details>")


def _exp_block(lab: Path, R, eid: str, full: bool) -> str:
    d = exp_dir(lab, eid)
    if d is None:
        return ""
    m, meta = md_meta(d / "plan.md"), md_meta_raw(d / "plan.md")
    res = load_json(d / "results.json", {})
    chips = [f"계획 {ko_status(m.get('status', '')) or '-'}"]
    if res:
        chips.append(f"결과 {ko_status(res.get('status', ''))}")
        chips.append(f"GPU {res.get('gpu_minutes', 0)}분")
        if res.get("peak_vram_gb") is not None:
            chips.append(f"최대 VRAM {res['peak_vram_gb']}GB")
    parts = [f'<h3><span class="id">{eid}</span> {R.esc(m.get("title") or d.name)}</h3><div>'
             + "".join(f'<span class="chip">{R.esc(c)}</span>' for c in chips)
             + (R.audit_badge(_audit_verdict(lab, eid)) if res else "") + "</div>"]
    if res.get("hypothesis") or m.get("summary"):
        parts.append(f'<p class="muted">{R.inline(res.get("hypothesis") or m.get("summary"))}</p>')
    summ = res.get("summary") or {}
    if summ:
        metrics = sorted({k for c in summ.values() for k in c})
        rows = [[cond] + [f"{R.fmt(v[k]['mean'])} ± {R.fmt(v[k]['std'], 2)} (n={v[k]['n']})" if k in v else "-" for k in metrics]
                for cond, v in summ.items()]
        parts.append(R.table_html(["조건"] + metrics, rows, num_cols=tuple(range(1, len(metrics) + 1))))
        main = meta.get("metric") if meta.get("metric") in metrics else metrics[0]
        parts.append(R.svg_bars(summ, main))
    comps = res.get("comparisons") or {}
    if comps:
        rows = []
        for cond, mm in comps.items():
            for k, c in mm.items():
                rows.append([R.esc(cond), R.esc(k), R.esc(f"{c['improvement']:+.4g}"),
                             R.esc(f"[{c['ci_low']:+.4g}, {c['ci_high']:+.4g}]"), R.badge(c.get("verdict", ""))])
        parts.append("<h4>기준선 대비 (코드가 계산한 부트스트랩 95% 신뢰구간)</h4>")
        parts.append(R.table_html(["조건", "지표", "개선량", "95% 신뢰구간", "판정"], rows, raw=True, num_cols=(2, 3)))
    if res.get("notes"):
        parts.append(f'<p class="muted">{R.inline(res["notes"])}</p>')
    if not res:
        parts.append('<p class="empty">아직 results.json이 없습니다 (본 실험 전이거나 진행 중).</p>')
    parts.append(_figures(R, d, 12 if full else 2))
    parts.append(_md_details(R, d / "report.md", "보고서 (report.md)", open_=full))
    if full:
        parts.append(_md_details(R, d / "plan.md", "실험 계획과 사전 등록 (plan.md)"))
    return "".join(parts)


def _cmp_block(lab: Path, R, cid: str, full: bool) -> str:
    hits = [p for p in (lab / "research" / "campaigns").glob(f"{cid}*") if p.is_dir()]
    if not hits:
        return ""
    d = hits[0]
    cfg, st = load_json(d / "campaign.json", {}), load_json(d / "state.json", {})
    if not cfg:
        return ""
    meta = md_meta_raw(d / "campaign.md")
    rows = [r for r in _ledger_rows(d) if r["trial"].startswith("T-")]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    parts = [f'<h3><span class="id">{cid}</span> {R.esc(cfg.get("title", ""))}</h3><div>'
             f'<span class="chip">{R.esc(ko_status(meta.get("status", "")))}</span>'
             f'<span class="chip">지표 {R.esc(cfg.get("metric"))} ({"낮을수록" if cfg.get("goal") == "min" else "높을수록"} 좋음)</span>'
             + (R.audit_badge(_audit_verdict(lab, cid)) if rows else "") + "</div>"]
    stats = [("시도", f"{st.get('n_trials', 0)}/{cfg.get('max_trials')}")]
    if st.get("baseline_done"):
        gain = _improvement(cfg["goal"], st["best_metric"], st["baseline_metric"])
        stats += [("기준선", _fmt(st["baseline_metric"])), (f"최고 ({st.get('best_trial')})", _fmt(st["best_metric"])),
                  ("개선량", f"{gain:+.4g}"), ("채택 문턱 δ", _fmt(st.get("delta")))]
    stats.append(("채택", str(counts.get("keep", 0) + counts.get("keep-simpler", 0))))
    parts.append(R.stats_grid(stats))
    c = (st.get("confirm") or {}).get("result")
    if c:
        parts.append(f'<p>새 시드 확인 실험: {R.badge(c["verdict"])} 개선 {c["improvement"]:+.4g}, '
                     f'95% 신뢰구간 [{c["ci_low"]:+.4g}, {c["ci_high"]:+.4g}]</p>')
    elif st.get("stopped"):
        parts.append(f'<p class="muted">멈춘 이유: {R.esc(st["stopped"])} · 확인 실험 전</p>')
    if rows:
        parts.append(R.svg_campaign(rows, st.get("baseline_metric"), cfg.get("goal", "max"), cfg.get("metric", "")))
        shown = rows if full else [r for r in rows if r["status"] in ("keep", "keep-simpler")]
        if shown:
            parts.append("<h4>" + ("모든 시도" if full else "채택된 시도") + "</h4>")
            parts.append(R.table_html(["시도", "지표", "개선량", "판정", "변경 줄", "설명"],
                                      [[r["trial"], _fmt_cell(r["metric"]), _fmt_cell(r["improvement"], sign=True), ko_status(r["status"]),
                                        r["lines"], r["description"]] for r in shown], num_cols=(1, 2)))
    parts.append(_md_details(R, d / "summary.md", "요약 보고서 (summary.md)", open_=full))
    if full:
        parts.append(_md_details(R, d / "campaign.md", "승인된 탐색 계약 (campaign.md)"))
        parts.append(_md_details(R, d / "notes.md", "탐색 노트 (notes.md)"))
    return "".join(parts)


def _fmt_cell(v: str, sign: bool = False) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return v or "-"
    return f"{x:+.4g}" if sign else f"{x:.6g}"


def _minutes_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    """회의록을 (## 제목, {### 소제목: 본문}) 목록으로 나눈다. 소제목 앞의 본문은 키 ""에 둔다."""
    blocks: list[tuple[str, dict[str, str]]] = []
    cur, sub, buf = None, "", []
    for ln in text.splitlines() + ["## "]:
        if ln.startswith("## ") or ln.startswith("### "):
            if cur is not None:
                cur[1][sub] = "\n".join(buf).strip()
            buf = []
            if ln.startswith("## "):
                cur = (ln[3:].strip(), {})
                blocks.append(cur)
                sub = ""
            else:
                sub = ln[4:].strip()
            continue
        buf.append(ln)
    return [b for b in blocks if b[0]]


def _kb_entries(lab: Path, kind: str, session: str) -> list[dict]:
    out = []
    for f in sorted((lab / KB_DIRS[kind]).glob("*.json")):
        e = load_json(f, {})
        if session in (e.get("created_session"), e.get("updated_session")):
            out.append(e)
    return out


def _session_report(lab: Path, R, num: str) -> tuple[str, str]:
    mfile = lab / "meetings" / f"session_{num}.md"
    minutes = mfile.read_text(encoding="utf-8") if mfile.exists() else ""
    log = load_json(lab / "kb" / "log" / f"session_{num}.json", {})
    if not minutes and not log:
        sys.exit(f"오류: 세션 {num}의 회의록도 세션 로그도 없습니다")
    blocks = _minutes_blocks(minutes)
    ids = set(ID_RE.findall(minutes + json.dumps(log, ensure_ascii=False)))
    exps = sorted({i for i in ids if i.startswith("EXP-")} |
                  {ID_RE.match(p.name).group(0) for p in (lab / "research" / "experiments").glob("EXP-*")
                   if p.is_dir() and md_meta(p / "plan.md").get("session") == num})
    cmps = sorted(i for i in ids if i.startswith("CMP-"))
    decisions, findings = _kb_entries(lab, "decision", num), _kb_entries(lab, "finding", num)
    actions = [a for a in load_json(lab / "state" / "actions.json", []) if str(a.get("session", "")).zfill(3) == num]
    asks = [q for q in load_json(lab / "state" / "inbox.json", []) if q.get("status") == "open"]
    meetings = [b for b in blocks if b[0].startswith("회의")]

    def subs(prefixes: tuple[str, ...]) -> list[tuple[str, str, str]]:
        return [(title, k, v) for title, secs in blocks for k, v in secs.items() if v and k.startswith(prefixes)]

    body = []
    body.append(R.section("한눈에 보기", (f"<p>{R.inline(log['summary'])}</p>" if log.get("summary") else
                                       '<p class="empty">세션 정리(/ai-lab:archive) 전이라 요약은 회의록에서만 모았습니다.</p>')
                          + R.stats_grid([("회의", str(len(meetings))), ("기록된 결정", str(len(decisions))),
                                          ("결과(F-)", str(len(findings))), ("실험", str(len(exps))), ("캠페인", str(len(cmps))),
                                          ("새 할 일", str(len(actions))), ("결정 대기", str(len(asks)))])))
    decided = subs(("답과 결정",))
    items = [f"<h3>{R.esc(tt)}</h3>{R.md_to_html(v)}" for tt, _, v in decided]
    if decisions:
        items.append("<h3>지식베이스에 기록된 결정 (이유와 이견)</h3>" if decided else "")
        for e in decisions:
            dissent = "".join(f"<li>{R.esc(x.get('who', ''))}: {R.inline(x.get('view', ''))}</li>" for x in e.get("dissent") or [])
            items.append(f'<div class="item decision"><strong><span class="id">{R.esc(e.get("id"))}</span> {R.esc(e.get("title", ""))}</strong>'
                         f'<div class="meta">{R.esc(e.get("class", ""))} 등급 · 결정: {R.esc(e.get("decided_by", ""))} · {R.esc(ko_status(e.get("status", "")))}</div>'
                         f'<p>{R.inline(e.get("decision", e.get("summary", "")))}</p>'
                         + (f'<p class="muted">이유: {R.inline(e["reason"])}</p>' if e.get("reason") else "")
                         + (f'<p class="muted">이견</p><ul>{dissent}</ul>' if dissent else "") + "</div>")
    if items:
        body.append(R.section("결정된 사항", "".join(items)))
    if findings:
        items = []
        for e in findings:
            kind = {"positive": "효과 있음", "null": "효과 없음", "negative": "부정적 결과"}.get(e.get("result_type", ""), "")
            items.append(f'<div class="item finding"><strong><span class="id">{R.esc(e.get("id"))}</span> {R.esc(e.get("title", ""))}</strong>'
                         f'<div class="meta">{R.esc(ko_status(e.get("status", "")))} · {R.esc(kind)} · 확신도 {R.esc(e.get("confidence", "-"))}</div>'
                         f'<p>{R.inline(e.get("statement", e.get("summary", "")))}</p>'
                         + (f'<p class="muted">검증하지 않은 범위: {R.inline(e["scope_limits"])}</p>' if e.get("scope_limits") else "")
                         + (f'<p class="muted">근거: {R.inline(", ".join(map(str, e["evidence"])))}</p>' if e.get("evidence") else "") + "</div>")
        body.append(R.section("연구 결과 (F-)", "".join(items)))
    changes = [(c.get("target", ""), c.get("change", ""), ev.get("summary", "")) for ev in log.get("events", []) for c in ev.get("changes", [])]
    if changes:
        body.append(R.section("상태 변화", R.table_html(["대상", "변화", "사건"], [[R.inline(a), R.inline(b), R.inline(c)] for a, b, c in changes], raw=True)))
    else:
        got = subs(("가설", "상태 변화"))
        if got:
            body.append(R.section("상태 변화", "".join(R.md_to_html(v) for _, _, v in got)))
    talk = subs(("논의 요약", "교수님 발언", "이견"))
    if talk:
        html_parts, last = [], None
        for title, k, v in talk:
            if title != last:
                html_parts.append(f"<h3>{R.esc(title)}</h3>")
                last = title
            html_parts.append(f"<h4>{R.esc(k)}</h4>{R.md_to_html(v)}")
        body.append(R.section("주요 논의", "".join(html_parts)))
    work = [(t, secs.get("", "")) for t, secs in blocks if t.startswith(("작업 로그", "캠페인"))]
    if any(v for _, v in work):
        body.append(R.section("작업 기록", "".join(f"<h3>{R.esc(t)}</h3>{R.md_to_html(v)}" for t, v in work if v)))
    blocks_html = [x for x in (_exp_block(lab, R, e, False) for e in exps) if x]
    if blocks_html:
        body.append(R.section("실험 결과", "<hr>".join(blocks_html)))
    blocks_html = [x for x in (_cmp_block(lab, R, c, False) for c in cmps) if x]
    if blocks_html:
        body.append(R.section("자율 탐색 캠페인", "<hr>".join(blocks_html)))
    if actions:
        body.append(R.section("이 세션의 할 일", R.table_html(
            ["ID", "담당", "할 일", "상태", "결과"],
            [[a["id"], a.get("owner", ""), a.get("title", ""), ko_status(a.get("status", "")), a.get("result") or ""] for a in actions])))
    if asks:
        body.append(R.section("교수님 결정 대기", "".join(
            f'<div class="item"><span class="id">{R.esc(q["id"])}</span> {R.inline(q["question"])}'
            + (f'<div class="meta">선택지: {R.esc(q["options"])}</div>' if q.get("options") else "") + "</div>" for q in asks)))
    if minutes:
        body.append(R.section("부록: 회의록 전문", f"<details><summary>meetings/session_{num}.md 펼치기</summary>{R.md_to_html(minutes)}</details>"))
    title = f"세션 {num} 리포트" + (f": {log['title']}" if log.get("title") else "")
    return title, "".join(body)


def cmd_report(args) -> None:
    lab = need_lab(args)
    rcfg = load_json(lab / CONFIG, {}).get("report", {})
    if args.auto and not rcfg.get("after_activities", True):
        return  # 교수님이 활동 뒤 자동 리포트를 꺼 두었다
    R = _report_mod()
    target = " ".join(args.target).strip().upper()
    m = ID_RE.search(target)
    if m and m.group(0).startswith(("EXP-", "CMP-")):
        tid = m.group(0)
        block = _cmp_block(lab, R, tid, True) if tid.startswith("CMP-") else _exp_block(lab, R, tid, True)
        if not block:
            sys.exit(f"오류: {tid}를 찾지 못했습니다")
        row = resolve(lab, tid) or {}
        title = f"{tid}: {row.get('title', '')}".rstrip(": ")
        body, name = R.section("실험 결과" if tid.startswith("EXP-") else "자율 탐색 캠페인", block), tid
    else:
        nums = re.findall(r"\d{1,3}", target)
        if nums:
            num = f"{int(nums[0]):03d}"
        else:
            files = sorted((lab / "meetings").glob("session_*.md"))
            if not files:
                sys.exit("오류: 아직 회의록이 없습니다 (세션을 먼저 시작하세요)")
            num = files[-1].stem[-3:]
        title, body = _session_report(lab, R, num)
        name = f"session_{num}"
    cfg = load_json(lab / CONFIG, {})
    html_text = R.page(title, f"{cfg.get('lab_name', lab.name)} · 연구실 리포트", f"만든 날 {today()}", body,
                       f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M')} 생성")
    out = lab / "reports" / f"{name}.html"
    write_atomic(out, html_text)
    print(f"HTML 리포트: {out}")
    if args.open or (args.auto and rcfg.get("open", True)):
        try:
            import webbrowser
            webbrowser.open(out.as_uri())
        except Exception:
            pass  # 브라우저를 못 열어도 파일은 만들어져 있다


# ---------------------------------------------------------------- 하드웨어 탐색과 운영 제약

VRAM_HEADROOM = 0.9      # 화면 출력과 다른 프로그램 몫으로 10%는 남긴다
BYTES_PER_PARAM = 18     # AdamW 혼합 정밀도 학습에서 파라미터 하나당 가중치·기울기·옵티마이저 상태 (대략)
ACTIVATION_SHARE = 0.5   # 메모리의 절반은 활성값(activation)과 배치 몫으로 남긴다
CPU_TRAIN_PARAMS_M = 10  # GPU가 없으면 메모리보다 속도가 한계다


def _machine_id() -> str:
    """이 PC를 알아보는 짧은 지문. 호스트 이름을 그대로 저장하지 않는다."""
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}|{os.cpu_count()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _ram_gb() -> float | None:
    try:
        if sys.platform == "win32":
            import ctypes

            class _MemStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (n, ctypes.c_ulonglong) for n in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile",
                                                      "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual",
                                                      "ullAvailExtendedVirtual")]
            m = _MemStatus()
            m.dwLength = ctypes.sizeof(_MemStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return round(m.ullTotalPhys / 2**30, 1)
            return None
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    except (OSError, ValueError, AttributeError):
        return None


def _nvidia_gpus() -> list[dict]:
    for fields in ("name,memory.total,compute_cap", "name,memory.total"):  # 오래된 드라이버는 compute_cap을 모른다
        try:
            r = subprocess.run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return []
        if r.returncode != 0:
            continue
        gpus = []
        for ln in r.stdout.strip().splitlines():
            parts = [p.strip() for p in ln.split(",")]
            try:
                g = {"name": parts[0], "vram_gb": round(float(parts[1]) / 1024, 1)}
            except (IndexError, ValueError):
                continue
            if len(parts) > 2 and re.fullmatch(r"\d+\.\d+", parts[2]):
                g["compute_cap"] = parts[2]
            gpus.append(g)
        return gpus
    return []


def detect_hardware(lab: Path) -> dict:
    gpus = _nvidia_gpus()
    if gpus:
        accel = "cuda"
    elif sys.platform == "darwin" and platform.machine() == "arm64":
        accel = "mps"
    else:
        accel = "cpu"
    return {"detected": today(), "machine_id": _machine_id(), "os": f"{platform.system()} {platform.release()}",
            "cpu_cores": os.cpu_count(), "ram_gb": _ram_gb(), "disk_free_gb": round(shutil.disk_usage(lab).free / 1e9),
            "accelerator": accel, "gpus": gpus}


def derive_limits(hw: dict, overrides: dict | None = None) -> dict:
    """탐색한 하드웨어에서 운영 제약을 계산한다. 교수님이 overrides에 적은 값이 우선한다."""
    accel, gpus, ram = hw.get("accelerator", "cpu"), hw.get("gpus") or [], hw.get("ram_gb")
    lim: dict = {"device": accel}
    if accel == "cuda":
        caps = [float(g.get("compute_cap") or 0) for g in gpus]
        lim["precision"] = "bf16" if min(caps) >= 8.0 else "fp16"
        mem = min(g["vram_gb"] for g in gpus) * VRAM_HEADROOM
        lim["vram_budget_gb"] = round(mem, 1)
    elif accel == "mps":  # Apple 통합 메모리: RAM의 절반까지만 가속기 몫으로 본다
        lim["precision"] = "fp32"
        mem = (ram or 8) * 0.5
    else:
        lim["precision"] = "fp32"
        mem = None
    lim["max_train_params_m"] = (int(mem * 1e9 * ACTIVATION_SHARE / BYTES_PER_PARAM / 1e7) * 10
                                 if mem else CPU_TRAIN_PARAMS_M)
    lim["parallel_runs"] = max(1, len(gpus))
    lim["dataloader_workers"] = 0 if hw.get("os", "").startswith("Windows") else min(8, (hw.get("cpu_cores") or 2) // 2)
    if ram:
        lim["ram_budget_gb"] = round(ram * 0.6, 1)
    lim.update({k: v for k, v in (overrides or {}).items() if k in lim})
    return lim


def ensure_hardware(lab: Path, refresh: bool = False) -> tuple[dict, dict, bool]:
    """처음이거나 PC가 바뀌었을 때(또는 refresh) 하드웨어를 탐색하고, 운영 제약을
    lab.config.json → compute.limits에 건다. (하드웨어, 제약, 새로 탐색했는지)를 돌려준다."""
    path = lab / CONFIG
    cfg = load_json(path, None)
    if not isinstance(cfg, dict):
        return {}, {}, False
    comp = cfg.setdefault("compute", {})
    hw = comp.get("hardware") or {}
    redetected = refresh or hw.get("machine_id") != _machine_id()
    if redetected:
        hw = detect_hardware(lab)
    limits = derive_limits(hw, comp.get("overrides"))
    if redetected or comp.get("limits") != limits:
        comp["hardware"], comp["limits"] = hw, limits
        with state_lock(lab):
            save_json(path, cfg)
    return hw, limits, redetected


def limits_line(hw: dict, lim: dict) -> str:
    gpus = hw.get("gpus") or []
    if gpus:
        head = " + ".join(f"{g['name']} {g['vram_gb']}GB" for g in gpus)
    elif lim.get("device") == "mps":
        head = f"Apple GPU (통합 메모리 {hw.get('ram_gb')}GB)"
    else:
        head = "GPU 없음 (CPU로 실행)"
    parts = [f"{head}, {lim.get('precision')}"]
    if lim.get("vram_budget_gb"):
        parts.append(f"VRAM 예산 {lim['vram_budget_gb']}GB")
    parts.append(f"처음부터 학습하는 모델 약 {lim.get('max_train_params_m')}M 파라미터 이하")
    parts.append(f"동시 실행 {lim.get('parallel_runs')}")
    parts.append(f"DataLoader workers {lim.get('dataloader_workers')}")
    if lim.get("ram_budget_gb"):
        parts.append(f"RAM 예산 {lim['ram_budget_gb']}GB")
    return " · ".join(parts)


def cmd_hardware(args) -> None:
    lab = need_lab(args)
    hw, lim, redetected = ensure_hardware(lab, refresh=args.refresh)
    if not hw:
        sys.exit("오류: lab.config.json을 읽지 못했습니다")
    comp = load_json(lab / CONFIG, {}).get("compute", {})
    print(f"# 하드웨어 ({hw.get('detected')} 탐색{', 방금 새로 탐색함' if redetected else ''})")
    print(f"- OS {hw.get('os')} · CPU 코어 {hw.get('cpu_cores')} · RAM {hw.get('ram_gb')}GB · 디스크 여유 {hw.get('disk_free_gb')}GB")
    for i, g in enumerate(hw.get("gpus") or []):
        print(f"- GPU {i}: {g['name']} · {g['vram_gb']}GB · compute {g.get('compute_cap', '알 수 없음')}")
    if not hw.get("gpus"):
        print("- NVIDIA GPU 없음" + (" (Apple GPU 사용)" if lim.get("device") == "mps" else ""))
    print("\n# 운영 제약 (lab.config.json → compute.limits, 연구원은 이 안에서 계획한다)")
    print(f"- {limits_line(hw, lim)}")
    if lim.get("vram_budget_gb"):
        print("- labkit이 실행마다 VRAM 사용을 예산 안으로 묶고, 최대 사용량을 기록한다 (파일럿으로 실제 크기를 확인)")
    over = comp.get("overrides") or {}
    unknown = [k for k in over if k not in lim]
    print(f"- 교수님이 정한 값(overrides): {json.dumps(over, ensure_ascii=False) if over else '없음'}")
    if unknown:
        print(f"경고: overrides의 {', '.join(unknown)}는 알 수 없는 키라서 무시했습니다")
    print('\n제약을 바꾸려면 lab.config.json → compute.overrides에 같은 키로 적으세요. 예: {"vram_budget_gb": 5}. '
          "PC를 바꾸면 다음 세션 시작 때 자동으로 다시 탐색합니다 (지금 다시: lab.py hardware --refresh).")


def cmd_doctor(args) -> None:
    lab = find_lab(args.lab)
    checks: list[tuple[str, str, str]] = []

    def probe(name: str, cmd: list[str], timeout: float = 20) -> None:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            out = (r.stdout or r.stderr).strip().splitlines()
            checks.append(("정상" if r.returncode == 0 else "주의", name, out[0] if out else f"종료 코드 {r.returncode}"))
        except FileNotFoundError:
            checks.append(("주의", name, "설치되어 있지 않거나 PATH에 없음"))
        except subprocess.TimeoutExpired:
            checks.append(("주의", name, "응답 없음 (시간 초과)"))

    checks.append(("정상" if sys.version_info >= (3, 10) else "주의", "Python (lab.py 실행)", sys.version.split()[0]))
    probe("git", ["git", "--version"])
    probe("uv", ["uv", "--version"])
    probe("GPU (nvidia-smi)", ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    if lab:
        free = shutil.disk_usage(lab).free / 1e9
        checks.append(("정상" if free > 10 else "주의", "디스크 여유 공간", f"{free:.0f} GB"))
        checks.append(("정상" if (lab / ".venv").exists() else "정보", "실험용 가상환경 (.venv)",
                       "있음" if (lab / ".venv").exists() else "아직 없음 — 첫 실험 때 uv sync로 만든다"))
        if args.torch and (lab / ".venv").exists():
            try:
                r = subprocess.run(["uv", "run", "python", "-c",
                                    "import torch;print(torch.__version__, 'CUDA', torch.cuda.is_available())"],
                                   cwd=str(lab), capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
                out = (r.stdout or r.stderr).strip().splitlines()
                checks.append(("정상" if r.returncode == 0 and "True" in r.stdout else "주의", "torch / CUDA",
                               out[-1] if out else "확인 실패"))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                checks.append(("주의", "torch / CUDA", "확인 실패"))
    for lvl, name, detail in checks:
        print(f"[{lvl}] {name}: {detail}")
    if lab:
        hw, lim, _ = ensure_hardware(lab)
        if lim:
            print(f"[정보] 운영 제약 (lab.py hardware): {limits_line(hw, lim)}")


def cmd_map(args) -> None:
    """연구 지도: 마일스톤 → 질문 → 가설 → 실험/캠페인 → 결과를 mermaid 그림으로 kb/map.md에 쓴다."""
    lab = need_lab(args)
    order = {"question": 1, "hypothesis": 2, "experiment": 3, "campaign": 3, "finding": 4}
    rows = [r for r in get_index(lab) if r["type"] in order]
    nodes = {r["id"]: r for r in rows}
    ms_rows = []
    roadmap = lab / "ROADMAP.md"
    if roadmap.exists():
        for ln in roadmap.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*(MS-\d+)\s*\|\s*([^|]*)\|(?:[^|]*\|)?\s*([^|]*)\|", ln)
            if m and m.group(2).strip():
                ms_rows.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    edges: set[tuple[str, str]] = set()
    for r in rows:
        p = lab / r["path"]
        text = (" ".join((p / n).read_text(encoding="utf-8") for n in DIR_SUMMARY if (p / n).exists())
                if p.is_dir() else p.read_text(encoding="utf-8"))
        for m in set(ID_RE.findall(text)):
            if m in nodes and m != r["id"] and order[nodes[m]["type"]] < order[r["type"]]:
                edges.add((m, r["id"]))
        for ms in set(re.findall(r"\bMS-\d+\b", text)):
            if any(ms == x[0] for x in ms_rows):
                edges.add((ms, r["id"]))
    nid = lambda x: x.replace("-", "_")
    esc = lambda s: s.replace('"', "'").replace("[", "(").replace("]", ")")[:24]
    good = {"accepted", "supported", "confirmed", "complete"}
    bad = {"refuted", "abandoned", "failed", "superseded", "dropped", "crash"}
    busy = {"testing", "running", "approved", "planned", "pilot-done", "provisional"}
    lines = ["flowchart TD"]
    for ms, title, _ in ms_rows:
        lines.append(f'  {nid(ms)}(["{ms}<br/>{esc(title)}"]):::ms')
    for r in rows:
        cls = "good" if r["status"] in good else "bad" if r["status"] in bad else "busy" if r["status"] in busy else "idle"
        lines.append(f'  {nid(r["id"])}["{r["id"]}<br/>{esc(r["title"])}<br/>({ko_status(r["status"]) or "-"})"]:::{cls}')
    for a, b in sorted(edges):
        lines.append(f"  {nid(a)} --> {nid(b)}")
    lines += ["  classDef ms fill:#eef,stroke:#557", "  classDef good fill:#e6f4ea,stroke:#2e7d32",
              "  classDef bad fill:#eee,stroke:#999,color:#777", "  classDef busy fill:#e3f2fd,stroke:#1565c0",
              "  classDef idle fill:#fff,stroke:#999"]
    out = ["# 연구 지도", f"> {today()}에 `lab.py map`이 자동 생성함. 초록=확정/지지, 파랑=진행 중, 회색=반박/폐기. "
           "GitHub에서는 그림으로 보이고, VSCode에서는 mermaid 미리보기 확장이 있으면 보인다.", "", "```mermaid", *lines, "```"]
    write_atomic(lab / "kb" / "map.md", "\n".join(out) + "\n")
    print(f"kb/map.md를 만들었습니다 (항목 {len(rows) + len(ms_rows)}개, 연결 {len(edges)}개)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="lab.py", description="ai-lab 연구실 도구")
    ap.add_argument("--lab", help="연구실 경로 (기본: 자동 탐색)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="새 연구실 만들기"); p.add_argument("path"); p.add_argument("--name")
    p.add_argument("--topic"); p.add_argument("--git", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("next", help="새 ID 발급"); p.add_argument("kind"); p.set_defaults(fn=cmd_next)
    p = sub.add_parser("status", help="연구실 현황"); p.add_argument("--hook", action="store_true")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("action", help="할 일 관리")
    p.add_argument("op", choices=["add", "done", "list"]); p.add_argument("id", nargs="?")
    for flag in ("--owner", "--title", "--ref", "--session", "--result"):
        p.add_argument(flag)
    p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_action)

    p = sub.add_parser("index", help="색인 다시 만들기"); p.set_defaults(fn=cmd_index)
    p = sub.add_parser("find", help="지식베이스 검색"); p.add_argument("text", nargs="?"); p.add_argument("--type")
    p.add_argument("--status"); p.add_argument("--tag"); p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_find)
    for name, fn, h in (("show", cmd_show, "항목 하나 보기"), ("context", cmd_context, "항목과 연결된 항목 보기")):
        p = sub.add_parser(name, help=h); p.add_argument("id"); p.add_argument("--max-lines", type=int, default=80)
        p.set_defaults(fn=fn)
    p = sub.add_parser("history", help="항목의 변화 이력"); p.add_argument("id"); p.set_defaults(fn=cmd_history)

    p = sub.add_parser("inbox", help="교수님 결정 대기함")
    p.add_argument("op", choices=["add", "resolve", "list"]); p.add_argument("id", nargs="?")
    p.add_argument("--from", dest="frm"); p.add_argument("--question"); p.add_argument("--options")
    p.add_argument("--ref"); p.add_argument("--context"); p.add_argument("--answer")
    p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_inbox)
    p = sub.add_parser("verify", help="실험 증거 감사"); p.add_argument("id"); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("digest", help="지식 요약본 만들기"); p.set_defaults(fn=cmd_digest)
    p = sub.add_parser("pack-md", help="텍스트 파일들을 복원 가능한 md 하나로 묶기")
    p.add_argument("paths", nargs="+"); p.add_argument("--out", required=True); p.add_argument("--title")
    p.add_argument("--root", help="경로의 기준 폴더 (기본: 현재 폴더)"); p.set_defaults(fn=cmd_pack_md)
    p = sub.add_parser("unpack-md", help="pack-md로 만든 md에서 파일 복원")
    p.add_argument("md"); p.add_argument("--out", default="."); p.set_defaults(fn=cmd_unpack_md)

    p = sub.add_parser("campaign", help="자율 탐색 캠페인 (제안은 AI, 판정은 코드)")
    p.add_argument("op", choices=["init", "approve", "baseline", "begin", "run", "status", "confirm", "stop", "close"])
    p.add_argument("id", nargs="?")
    p.add_argument("--from", dest="src"); p.add_argument("--title"); p.add_argument("--slug"); p.add_argument("--tags")
    p.add_argument("--metric"); p.add_argument("--goal", choices=["min", "max"])
    p.add_argument("--run", help="학습(과 평가) 명령. 예: \"uv run python train.py\"")
    p.add_argument("--eval", help="수정 금지 평가 명령 (있으면 지표는 이 출력에서만 읽는다)")
    p.add_argument("--metric-regex", dest="metric_regex")
    p.add_argument("--editable"); p.add_argument("--protected")
    p.add_argument("--trial-minutes", dest="trial_minutes", type=float, default=5)
    p.add_argument("--max-trials", dest="max_trials", type=int, default=40)
    p.add_argument("--max-hours", dest="max_hours", type=float, default=8)
    p.add_argument("--patience", type=int, default=15)
    p.add_argument("--crash-limit", dest="crash_limit", type=int, default=5)
    p.add_argument("--min-delta", dest="min_delta", type=float, default=0.0)
    p.add_argument("--baseline-repeats", dest="baseline_repeats", type=int, default=3)
    p.add_argument("--confirm-seeds", dest="confirm_seeds", type=int, default=3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--desc"); p.add_argument("--note"); p.add_argument("--reason")
    p.add_argument("--reset", action="store_true"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_campaign)

    p = sub.add_parser("rank", help="쌍대 비교로 후보 순위 매기기 (Bradley-Terry)")
    p.add_argument("op", choices=["schedule", "score"])
    p.add_argument("items", nargs="*"); p.add_argument("--file"); p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_rank)

    p = sub.add_parser("lit", help="문헌 검색·조회·인용 확인 (arXiv, Semantic Scholar)")
    p.add_argument("op", choices=["search", "get", "check"]); p.add_argument("terms", nargs="*")
    p.add_argument("--limit", type=int, default=8); p.add_argument("--since", type=int)
    p.add_argument("--source", choices=["arxiv", "s2", "both"], default="both"); p.set_defaults(fn=cmd_lit)

    p = sub.add_parser("audit", help="실험/캠페인 감사: 검증 + 계획 대조 + 보고서 숫자 대조")
    p.add_argument("id", nargs="?"); p.add_argument("--report", help="숫자를 대조할 임의 문서 (논문 초안 등)")
    p.add_argument("--sources", help="--report 숫자의 출처 ID들, 쉼표로 구분"); p.set_defaults(fn=cmd_audit)
    p = sub.add_parser("lint", help="지식베이스 무결성 점검"); p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("doctor", help="실험 환경 진단"); p.add_argument("--torch", action="store_true")
    p.set_defaults(fn=cmd_doctor)
    p = sub.add_parser("map", help="연구 지도(mermaid) 만들기"); p.set_defaults(fn=cmd_map)
    p = sub.add_parser("report", help="HTML 리포트 (세션·실험·캠페인)")
    p.add_argument("target", nargs="*", help="세션 번호, EXP-id, CMP-id (비우면 가장 최근 세션)")
    p.add_argument("--open", action="store_true", help="만든 뒤 브라우저로 열기")
    p.add_argument("--auto", action="store_true", help="활동 뒤 자동 생성 (lab.config.json → report 설정을 따른다)")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("hardware", aliases=["hw"], help="이 PC의 하드웨어 탐색과 운영 제약")
    p.add_argument("--refresh", action="store_true", help="지금 다시 탐색"); p.set_defaults(fn=cmd_hardware)

    args = ap.parse_args()
    if getattr(args, "op", None) == "score" and not getattr(args, "file", None):
        ap.error("rank score 에는 --file 이 필요합니다")
    args.fn(args)


if __name__ == "__main__":
    main()
