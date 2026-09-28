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

연구실 루트 = 현재 폴더에서 위로 올라가며 lab.config.json이 있는 첫 폴더
(--lab 경로 또는 환경 변수 AI_LAB_DIR로 지정 가능).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
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
}
DIR_SUMMARY = ("plan.md", "summary.md", "report.md", "README.md")
ID_RE = re.compile(r"\b(?:IDEA|LIT|EXP|REV|TASK|ASK|REL|BS|DS|H|F|Q|D|P|M|A|L)-\d{3,}\b")
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
    "release": "릴리스", "session": "세션",
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
    "logged": "기록됨",
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


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def alloc(lab: Path, kind: str) -> str:
    path = lab / "state" / "counters.json"
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
    save_json(lab / "kb" / "index.json",
              {"generated": today(), "note": "자동 생성 캐시입니다. 권위는 개별 파일에 있습니다. 직접 고치지 마세요.",
               "entries": rows})
    return rows


def get_index(lab: Path) -> list[dict]:
    return write_index(lab)  # 연구실 규모에서는 매번 새로 만들어도 충분히 빠르다


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
    acts = [a for a in load_json(lab / "state" / "actions.json", []) if a.get("status") == "open"]
    if acts:
        out.append(f"\n## 남은 할 일 ({len(acts)}건)")
        out += [f"- {a['id']} [{a['owner']}] {a['title']}" for a in acts[:15]]
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
        out.append(f'\n연구실 도구 (필요한 것만 읽기): python "{SELF}" find|show|context|history|digest|verify|inbox ...')
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
    """실험 하나의 증거를 결정적으로 감사한다: 사전 등록, results.json ↔ 실행 기록."""
    lab = need_lab(args)
    d = exp_dir(lab, args.id)
    if d is None:
        sys.exit(f"오류: {args.id} 실험 폴더가 없습니다")
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
    fails = sum(1 for lvl, _ in issues if lvl == "실패")
    for lvl, msg in issues:
        print(f"[{lvl}] {msg}")
    print(f"검증 {args.id}: {'실패' if fails else '통과'} (실패 {fails}건)")
    if fails:
        sys.exit(1)


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

    lines = ["# 연구실 지식 요약본",
             f"> {today()}에 `lab.py digest`가 자동 생성함 — 직접 고치지 마세요. 권위는 개별 항목에 있습니다."]
    lines += block("확정된 결과", by("finding", "accepted"), conf)
    lines += block("잠정 결과 (아직 확정 전)", by("finding", "provisional"), conf)
    lines += block("검증 중인 가설", by("hypothesis", "testing"))
    lines += block("제안된 가설", by("hypothesis", "proposed"))
    lines += block("결론이 난 가설", by("hypothesis", "supported", "refuted", "inconclusive"),
                   lambda r: f" [{ko_status(r['status'])}]")
    lines += block("열린 연구 질문", by("question", "open", "narrowed"))
    lines += block("유효한 결정", by("decision", "in_force"))
    lines += block("교훈 (운영 노하우)", by("lesson", "active"))
    lines += block("핵심 논문", by("paper", "key"))
    lines += block("재사용할 방법과 데이터셋", by("method", "implemented", "baseline") + by("dataset", "in_use"))
    lines += block("회사에 가져간 릴리스", by("release"))
    if len(lines) == 2:
        lines.append("\n(아직 쌓인 지식이 없습니다)")
    (lab / "kb").mkdir(exist_ok=True)
    (lab / "kb" / "digest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"kb/digest.md를 만들었습니다 ({len(lines)}줄)")


def cmd_action(args) -> None:
    lab = need_lab(args)
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

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
