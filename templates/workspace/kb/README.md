# 지식베이스 — 정본 규칙과 형식

연구실에 쌓인 연구 지식을 모아 두는 곳이다. **사실 하나는 파일 하나가 소유한다.** 작은 파일로 나누고 모든 것에 ID를 붙여서, 어떤 작업이든 필요한 항목만 골라 읽을 수 있게 한다.

## 원칙

- **정의·현재 상태와 변화 기록을 분리한다.** 가설, 결과, 논문 같은 항목에는 *현재* 상태만 둔다. *언제, 왜* 바뀌었는지는 세션 로그(`kb/log/session_NNN.json`)가 소유한다.
- 현재 상태는 덮어쓴다. 이력은 지우지 않는다 (로그에 남아 있다). 항목 안에 이력을 쌓지 않는다.
- 다른 곳에서는 ID로만 참조한다. 사실의 문장을 다른 파일에 복사하지 않는다.
- 실제로 일어난 일, 실제로 내린 결정만 기록한다. 계획은 `state/actions.json`이나 `proposed` 상태로 둔다.
- 모든 결과(F-)는 증거를 적는다 (`EXP-xxx/results.json#summary`, `REV-xxx`, `P-xxx`).
- `kb/index.json`과 `kb/digest.md`는 `lab.py`가 만드는 캐시다. 권위는 개별 파일에 있다.

## 언어

- 사람이 읽는 모든 값(제목, 요약, 설명, 근거, 교훈)은 **한글**로 쓴다.
- ID, JSON 필드 이름, 상태 값, 태그는 기계가 읽는 표기라서 영어 소문자로 쓴다. 화면에는 `lab.py`가 한글로 바꿔 보여 준다.
- 논문 제목은 원제를 그대로 두고, `summary`와 `takeaway`는 한글로 쓴다.

## 찾아 읽기 (최소한만 읽는다)

먼저 `kb/digest.md`(1쪽)를 본다. 그다음은 이 순서로 좁혀 간다.

| 명령 | 보여 주는 것 |
|---|---|
| `lab.py find <검색어> [--type 종류 --status 상태 --tag 태그]` | 찾은 항목을 한 줄씩 |
| `lab.py show <ID>` | 항목 하나 |
| `lab.py context <ID>` | 항목 하나와, 그것이 참조하거나 그것을 참조하는 항목의 한 줄 요약 |
| `lab.py history <ID>` | 세션별로 어떻게 바뀌었는지 |

폴더를 통째로 읽지 않는다.

## 소유권 표

| 사실 | 소유 파일 | ID |
|---|---|---|
| 사명, 연구 방향, 원칙, 의사결정 규칙 | `LAB.md` | — |
| 팀의 역할과 관점 | `team.md` | — |
| 장기 계획: 연구 프로그램, 마일스톤 | `ROADMAP.md` | PR-n, MS-n |
| 이번 주기의 목표, 약속, 예산 | `state/cycle.md` | — |
| 지금 상태와 인계 메모 | `state/lab_state.md` (40줄 이하) | — |
| 교수님 결정을 기다리는 질문 | `state/inbox.json` (`lab.py inbox`) | ASK- |
| 세션에서 일어난 일과 모든 상태 변화 | `kb/log/session_NNN.json` | S-NNN |
| 세션의 논의 원본 | `meetings/session_NNN.md` | — |
| 연구 질문 | `kb/questions/Q-NNN.json` | Q- |
| 검증할 가설과 그 상태 | `kb/hypotheses/H-NNN.json` | H- |
| 연구 결과 | `kb/findings/F-NNN.json` | F- |
| 결정과 그 이유 | `kb/decisions/D-NNN.json` | D- |
| 논문 정보와 한 줄 요점 (중복 없이 하나씩) | `kb/papers/P-NNN.json` | P- |
| 데이터셋 정의 (출처, 분할, 로더) | `kb/datasets/DS-NNN.json` | DS- |
| 방법·모델 정의 (구현 경로, 검증된 하이퍼파라미터) | `kb/methods/M-NNN.json` | M- |
| 운영 노하우: 함정, 환경 문제, 다시 하지 말 것 | `kb/lessons/L-NNN.json` | L- |
| 연구실이 아는 것 1쪽 요약 (자동 생성) | `kb/digest.md` (`lab.py digest`) | — |
| 아이디어 제안 | `research/ideas/IDEA-NNN-*.md` | IDEA- |
| 문헌 조사 노트 | `research/literature/LIT-NNN-*.md` | LIT- |
| 브레인스토밍 (관점별 아이디어, 점수, 최종 후보) | `research/brainstorms/BS-NNN/` (summary.md) | BS- |
| 실험 (계획, 코드, 결과, 보고서) | `research/experiments/EXP-NNN-*/` | EXP- |
| 리뷰 | `research/reviews/REV-NNN.md` | REV- |
| 과업 지시서 | `briefs/TASK-NNN.md` | TASK- |
| 회사에서 쓸 릴리스 (독립 실행, 오프라인) | `research/releases/REL-NNN-*/` (README.md) | REL- |

## 모든 항목의 공통 필드 (JSON)

```json
{"id": "H-001", "title": "짧은 제목", "summary": "한 줄 요약 — find 결과에 보인다",
 "status": "…", "tags": ["grokking", "mlp"], "refs": ["EXP-001", "P-003"],
 "created_session": "001", "updated_session": "002"}
```

## 종류별 필드와 상태 값

| 종류 | 추가 필드 | 상태 값 (화면 표시) |
|---|---|---|
| 질문 `Q-` | `question`, `motivation`, `scope` | `open`(열림), `narrowed`(좁혀짐), `answered`(답변됨), `dropped`(중단됨) |
| 가설 `H-` | `statement`(반증 가능한 문장), `prediction`(어떤 결과면 반박되는가), `question`(Q- id) | `proposed`(제안됨), `testing`(검증 중), `supported`(지지됨), `refuted`(반박됨), `inconclusive`(결론 없음), `abandoned`(폐기됨) |
| 결과 `F-` | `statement`, `evidence`[경로/ID], `conditions`(성립하는 조건), `scope_limits`(검증하지 않은 범위), `confidence` `low/medium/high`, `supports`/`refutes`[H id], `decided_by`(`accepted`는 반드시 `교수님`) | `provisional`(잠정), `accepted`(확정), `superseded`(대체됨, `superseded_by` 기록) |
| 결정 `D-` | `decision`, `reason`, `alternatives`, `dissent`[{who, view}], `class`(A/B/C), `decided_by` | `in_force`(유효), `revised`(수정됨), `revoked`(철회됨) |
| 논문 `P-` | `authors`, `year`, `venue`, `url`, `arxiv`, `takeaway`(한 줄), `relevance`, `license`(있다면), `cited_in`[LIT id] | `skimmed`(훑어봄), `read`(읽음), `key`(핵심) |
| 데이터셋 `DS-` | `source`, `url`, `size`, `splits`, `license`(회사 사용 가능 여부 포함), `loader`(코드 경로) | `candidate`(후보), `in_use`(사용 중), `retired`(사용 종료) |
| 방법 `M-` | `description`, `impl`(코드 경로), `known_good_hparams`, `paper`(P id), `license` | `candidate`(후보), `implemented`(구현됨), `baseline`(베이스라인), `retired`(사용 종료) |
| 교훈 `L-` | `lesson`(명령형 한 줄), `context`(무슨 일이 있었나), `applies_to`(예: engineer, 전체), `source`(EXP/REV/세션 id) | `active`(유효), `obsolete`(폐기됨) |

## 마크다운 산출물의 머리말

첫 줄은 `# <ID>: <제목>`, 둘째 줄은 색인이 읽는 메타 줄이다.

```
# EXP-001: 가중치 감쇠 스윕
> status: planned | tags: grokking, weight-decay | session: 001 | summary: H-001 검증을 위한 가중치 감쇠 비교
```

## 세션 로그 `kb/log/session_NNN.json`

```json
{"session": "001", "date": "YYYY-MM-DD", "title": "…", "summary": "3~5줄 요약", "tags": [],
 "events": [{"id": "E-001-01", "type": "meeting|literature|experiment|review|decision|finding|status_change|release",
   "summary": "…", "refs": ["EXP-001"],
   "changes": [{"target": "H-001", "change": "상태 proposed → testing"}]}]}
```
