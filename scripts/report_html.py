"""HTML 리포트 렌더러 (표준 라이브러리만 사용). lab.py report가 모은 자료를 한 파일짜리 HTML로 만든다.

숫자와 문장은 모두 연구실 파일(회의록, 지식베이스, results.json, 장부)에서 온다. 여기서는 모양만 만든다.
외부 글꼴, 스크립트, 그림 파일을 쓰지 않아서 인터넷 없이도 열리고, 파일 하나만 옮기면 된다.
"""
from __future__ import annotations

import base64
import html
import math
import re

ID_PATTERN = re.compile(r"\b(?:IDEA|LIT|EXP|REV|TASK|ASK|REL|CMP|BS|DS|MS|H|F|Q|D|P|M|A|L|S)-\d{1,}\b")

CSS = """
:root{--bg:#f7f7f5;--card:#ffffff;--ink:#1f2328;--muted:#5f6670;--line:#e3e5e8;--accent:#2f6fde;
--good:#1f8a4c;--bad:#c0392b;--warn:#b7791f;--chip:#eef2f8;--code:#f2f3f5;--shadow:0 1px 2px rgba(0,0,0,.05)}
@media (prefers-color-scheme:dark){:root{--bg:#15171a;--card:#1d2024;--ink:#e6e8eb;--muted:#9aa3ad;--line:#2d3238;
--accent:#6ea0ff;--good:#4cc38a;--bad:#ff7b72;--warn:#e3b341;--chip:#262b33;--code:#23272d;--shadow:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 "Pretendard","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
header.top{margin-bottom:20px}
header.top .kicker{color:var(--muted);font-size:13px;letter-spacing:.02em}
header.top h1{font-size:26px;line-height:1.3;margin:4px 0 6px}
header.top .sub{color:var(--muted)}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0;box-shadow:var(--shadow)}
section>h2{font-size:18px;margin:0 0 12px;display:flex;gap:8px;align-items:center}
h3{font-size:16px;margin:18px 0 8px}
h4{font-size:14px;margin:14px 0 6px;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.stat{border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stat .v{font-size:22px;font-weight:700}
.stat .k{color:var(--muted);font-size:12px}
.chip{display:inline-block;background:var(--chip);border-radius:999px;padding:1px 9px;font-size:12px;margin:0 4px 4px 0;white-space:nowrap}
.id{font-family:ui-monospace,Consolas,monospace;font-size:.92em;color:var(--accent);white-space:nowrap}
.good{color:var(--good)}.bad{color:var(--bad)}.warn{color:var(--warn)}.muted{color:var(--muted)}
.badge{display:inline-block;border-radius:6px;padding:0 8px;font-size:12px;font-weight:600;border:1px solid currentColor}
.item{border-left:3px solid var(--line);padding:6px 0 6px 12px;margin:10px 0}
.item.decision{border-color:var(--accent)}.item.finding{border-color:var(--good)}
.item .meta{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:13px}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.scroll{overflow-x:auto}
pre{background:var(--code);border-radius:8px;padding:10px 12px;overflow-x:auto;font-size:13px}
code{background:var(--code);border-radius:4px;padding:0 4px;font-size:.92em}
pre code{background:none;padding:0}
blockquote{margin:8px 0;padding:4px 12px;border-left:3px solid var(--line);color:var(--muted)}
details{margin:10px 0}
summary{cursor:pointer;color:var(--accent)}
figure{margin:12px 0}
figure img{max-width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
figcaption{color:var(--muted);font-size:13px}
svg text{fill:var(--muted);font-size:11px}
.empty{color:var(--muted);font-style:italic}
footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
@media print{body{background:#fff}section{box-shadow:none;break-inside:avoid}details{display:block}}
"""


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def inline(s: str) -> str:
    """마크다운 한 줄의 굵게, 코드, 링크, ID 표시."""
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{esc(part[1:-1])}</code>")
            continue
        t = esc(part)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
        t = ID_PATTERN.sub(lambda m: f'<span class="id">{m.group(0)}</span>', t)
        out.append(t)
    return "".join(out)


def md_to_html(text: str) -> str:
    """회의록, 보고서 같은 연구실 마크다운을 HTML로 (제목, 목록, 표, 코드, 인용, 문단)."""
    lines = (text or "").splitlines()
    out: list[str] = []
    i = 0
    para: list[str] = []

    def flush_para():
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):
            flush_para()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre><code>" + esc("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            flush_para()
            level = min(6, len(m.group(1)) + 1)  # 문서 안의 제목은 한 단계 낮춘다
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush_para()
            head = [c.strip() for c in s.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append(table_html(head, [[inline(c) for c in r] for r in rows], raw=True))
            i = j
            continue
        if re.match(r"^([-*]|\d+[.)])\s+", s):
            flush_para()
            items = []
            ordered = bool(re.match(r"^\d+[.)]", s))
            while i < len(lines) and re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i]):
                body = re.sub(r"^\s*([-*]|\d+[.)])\s+", "", lines[i])
                indent = len(lines[i]) - len(lines[i].lstrip())
                items.append((indent, inline(body)))
                i += 1
            tag = "ol" if ordered else "ul"
            html_items = []
            for indent, body in items:
                style = f' style="margin-left:{min(indent, 8) * 6}px"' if indent else ""
                html_items.append(f"<li{style}>{body}</li>")
            out.append(f"<{tag}>" + "".join(html_items) + f"</{tag}>")
            continue
        if s.startswith(">"):
            flush_para()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote>" + "<br>".join(quote) + "</blockquote>")
            continue
        if not s:
            flush_para()
        else:
            para.append(s)
        i += 1
    flush_para()
    return "\n".join(out)


def table_html(head: list[str], rows: list[list], raw: bool = False, num_cols: tuple = ()) -> str:
    th = "".join(f'<th{" class=num" if k in num_cols else ""}>{h if raw else esc(h)}</th>' for k, h in enumerate(head))
    body = []
    for r in rows:
        tds = []
        for k, c in enumerate(r):
            cls = ' class="num"' if k in num_cols else ""
            tds.append(f"<td{cls}>{c if raw else esc(c)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def fmt(v, nd: int = 4) -> str:
    if v is None or v == "":
        return "-"
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return str(v)
        return f"{v:.{nd}g}"
    return str(v)


def verdict_class(text: str) -> str:
    if not text:
        return "muted"
    if text.startswith(("개선", "통과", "채택")):
        return "good"
    if text.startswith(("악화", "실패", "기각")):
        return "bad"
    return "warn"


def audit_badge(verdict: str) -> str:
    return badge(f"감사 {verdict}", verdict_class(verdict))


def badge(text: str, cls: str | None = None) -> str:
    return f'<span class="badge {cls or verdict_class(text)}">{esc(text)}</span>'


def img_tag(data: bytes, name: str) -> str:
    mime = "image/svg+xml" if name.lower().endswith(".svg") else "image/png" if name.lower().endswith(".png") else "image/jpeg"
    b64 = base64.b64encode(data).decode("ascii")
    return f'<figure><img alt="{esc(name)}" src="data:{mime};base64,{b64}"><figcaption>{esc(name)}</figcaption></figure>'


def svg_bars(summary: dict, metric: str) -> str:
    """조건별 평균과 표준편차 막대 그림."""
    items = [(c, m[metric]) for c, m in summary.items() if metric in m]
    if not items:
        return ""
    w, h, pad_l, pad_b, pad_t = 640, 230, 56, 44, 16
    tops = [v["mean"] + v.get("std", 0) for _, v in items]
    lows = [min(0.0, v["mean"] - v.get("std", 0)) for _, v in items]
    ymax, ymin = max(tops) or 1.0, min(lows)
    span = (ymax - ymin) or 1.0
    bw = (w - pad_l - 20) / len(items)
    y = lambda val: pad_t + (h - pad_t - pad_b) * (1 - (val - ymin) / span)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(metric)} 조건별 평균">']
    parts.append(f'<line x1="{pad_l}" y1="{y(ymin):.1f}" x2="{w - 10}" y2="{y(ymin):.1f}" stroke="currentColor" opacity=".3"/>')
    for k in range(5):
        val = ymin + span * k / 4
        parts.append(f'<text x="{pad_l - 6}" y="{y(val) + 4:.1f}" text-anchor="end">{esc(fmt(val, 3))}</text>')
    for n, (cond, v) in enumerate(items):
        x0 = pad_l + n * bw + bw * 0.2
        bwid = bw * 0.6
        top, base = y(v["mean"]), y(max(ymin, 0.0) if ymin < 0 else ymin)
        color = "var(--muted)" if cond == "baseline" else "var(--accent)"
        parts.append(f'<rect x="{x0:.1f}" y="{min(top, base):.1f}" width="{bwid:.1f}" height="{abs(base - top):.1f}" fill="{color}" opacity=".85" rx="3"/>')
        sd = v.get("std", 0) or 0
        if sd:
            cx = x0 + bwid / 2
            parts.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(v["mean"] - sd):.1f}" y2="{y(v["mean"] + sd):.1f}" stroke="var(--ink)" stroke-width="1.5"/>')
        parts.append(f'<text x="{x0 + bwid / 2:.1f}" y="{h - pad_b + 16}" text-anchor="middle">{esc(cond)}</text>')
        parts.append(f'<text x="{x0 + bwid / 2:.1f}" y="{top - 6:.1f}" text-anchor="middle">{esc(fmt(v["mean"], 4))}</text>')
    parts.append(f'<text x="{pad_l}" y="{h - 6}">{esc(metric)} 평균 (세로선: 표준편차)</text></svg>')
    return "".join(parts)


def svg_campaign(rows: list[dict], baseline: float | None, goal: str, metric: str) -> str:
    """캠페인 시도별 지표, 채택 표시, 지금까지의 최고안 선."""
    pts = []
    for n, r in enumerate(rows, 1):
        try:
            pts.append((n, float(r["metric"]), r["status"]))
        except (ValueError, TypeError, KeyError):
            pts.append((n, None, r.get("status", "")))
    vals = [v for _, v, _ in pts if v is not None] + ([baseline] if baseline is not None else [])
    if not vals:
        return ""
    w, h, pad_l, pad_b, pad_t = 680, 260, 60, 40, 16
    # 기준선과 채택안 주변을 보여 준다. 크게 망한 시도 하나가 축을 늘려 나머지가 뭉개지지 않도록, 멀리 떨어진 점은 가장자리에 표시한다
    core = [v for _, v, s in pts if v is not None and s in ("keep", "keep-simpler")] + ([baseline] if baseline is not None else [])
    core = core or vals
    spread = (max(core) - min(core)) or (abs(max(core)) or 1.0) * 0.1
    allowed_lo, allowed_hi = min(core) - 2 * spread, max(core) + 2 * spread
    shown = [v for v in vals if allowed_lo <= v <= allowed_hi]
    lo, hi = min(shown), max(shown)
    span = (hi - lo) or spread
    lo, hi = lo - span * 0.08, hi + span * 0.08
    n_max = max(len(pts), 2)
    x = lambda n: pad_l + (w - pad_l - 16) * (n - 1) / (n_max - 1)  # noqa: E731
    y = lambda v: pad_t + (h - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="캠페인 진행">']
    for k in range(5):
        val = lo + (hi - lo) * k / 4
        parts.append(f'<line x1="{pad_l}" x2="{w - 16}" y1="{y(val):.1f}" y2="{y(val):.1f}" stroke="currentColor" opacity=".08"/>')
        parts.append(f'<text x="{pad_l - 6}" y="{y(val) + 4:.1f}" text-anchor="end">{esc(fmt(val, 4))}</text>')
    if baseline is not None:
        parts.append(f'<line x1="{pad_l}" x2="{w - 16}" y1="{y(baseline):.1f}" y2="{y(baseline):.1f}" stroke="var(--muted)" stroke-dasharray="5 4"/>')
        parts.append(f'<text x="{w - 18}" y="{y(baseline) - 5:.1f}" text-anchor="end">기준선</text>')
    best, path = baseline, []
    for n, v, stt in pts:
        if v is not None and stt in ("keep", "keep-simpler"):
            best = v
        if best is not None:
            path.append(f"{x(n):.1f},{y(best):.1f}")
    if path:
        parts.append(f'<polyline points="{" ".join(path)}" fill="none" stroke="var(--good)" stroke-width="2" opacity=".8"/>')
    for n, v, stt in pts:
        if v is None:
            parts.append(f'<text x="{x(n):.1f}" y="{h - pad_b - 4}" text-anchor="middle" fill="var(--bad)">×</text>')
            continue
        label = f'<title>{esc(rows[n - 1].get("trial", ""))} {esc(fmt(v, 6))}</title>'
        if v > hi or v < lo:  # 축 밖의 점: 가장자리에 빈 삼각형
            ey = pad_t + 4 if v > hi else h - pad_b - 4
            tip = ey - 5 if v > hi else ey + 5
            parts.append(f'<polygon points="{x(n) - 5:.1f},{ey:.1f} {x(n) + 5:.1f},{ey:.1f} {x(n):.1f},{tip:.1f}" fill="none" stroke="var(--muted)">{label}</polygon>')
            continue
        color = {"keep": "var(--good)", "keep-simpler": "var(--good)"}.get(stt, "var(--muted)")
        r = 5 if stt in ("keep", "keep-simpler") else 3.5
        parts.append(f'<circle cx="{x(n):.1f}" cy="{y(v):.1f}" r="{r}" fill="{color}">{label}</circle>')
    better = "낮을수록" if goal == "min" else "높을수록"
    parts.append(f'<text x="{pad_l}" y="{h - 8}">{esc(metric)} ({better} 좋음) · 초록 점: 채택 · 초록 선: 그때까지의 최고안 · △: 축 밖 · ×: 실행 실패</text></svg>')
    return "".join(parts)


def section(title: str, body: str, icon: str = "") -> str:
    return f"<section><h2>{icon}{esc(title)}</h2>{body}</section>"


def stats_grid(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="stat"><div class="v">{esc(v)}</div><div class="k">{esc(k)}</div></div>' for k, v in items)
    return f'<div class="stats">{cells}</div>'


def page(title: str, kicker: str, sub: str, body: str, generated: str) -> str:
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><main>"
        f'<header class="top"><div class="kicker">{esc(kicker)}</div><h1>{esc(title)}</h1>'
        f'<div class="sub">{esc(sub)}</div></header>{body}'
        f"<footer>{esc(generated)} · lab.py report가 연구실 파일에서 자동으로 만든 문서입니다. 숫자는 모두 결과 파일에서 가져왔습니다.</footer>"
        "</main></body></html>"
    )
