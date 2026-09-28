# AI Scientist Lab (`ai-lab` plugin)

ML/DL 연구를 하는 작은 AI 연구 그룹을 Claude Code의 agent, skill, hook으로 구성한 **재사용 가능한 환경**이다.
연구원들은 교수님(사용자)과 랩미팅으로 아이디어를 주고받고, 문헌을 조사하고, 실험을 구현·실행·분석하고, 서로 비판한다. 중요한 결정은 반드시 교수님과 대화로 정한다. 연구 지식은 **ID로 찾아 필요한 것만 읽을 수 있는 지식베이스**에 쌓인다.

- 이 저장소에는 **환경만** 들어 있다. 연구 결과물은 `/ai-lab:new-lab`으로 만드는 **별도 워크스페이스(별도 저장소)** 에 쌓인다.
- Claude Code plugin 형식이라서 어느 워크스페이스에서든 그대로 재사용할 수 있다.
- **모든 산출물은 한글이다.** 회의록, 과업 지시서, 실험 계획, 보고서, 지식베이스 문장, 코드 주석과 메시지, 그림 글자, `lab.py` 출력까지 한글로 만든다. ID, JSON 필드 이름, 상태 값, 태그 같은 기계용 표기만 영어로 둔다.

> 📖 **자세한 사용법은 [docs/사용설명서.md](docs/사용설명서.md)** 에 있다. 설치, 첫 연구실 만들기, 첫 주기 따라 하기, 명령어 사전, 문제 해결까지 순서대로 설명한다.

## 운영 방식: 회사 밖에서 연구하고, 회사 안에서는 결과물만 쓴다

```
[회사 밖] ai-lab 연구실 (Claude API, 공개 데이터만)
     │  /ai-lab:release  → REL-xxx.zip (코드 + 보고서 + 근거 + 한계 + 오프라인 설치법)
     ▼
[회사 안] Claude 없이, 인터넷 없이 릴리스만 설치해서 사용
```

- 연구실에서 읽는 모든 내용은 API로 전송되므로 **회사 데이터, 사내 코드와 문서, 사내 수치는 연구실에 넣지 않는다.** 회사 문제는 기밀이 아닌 일반화된 형태로 설명한다.
- 회사로 가져갈 결과물의 범위, 미확정 결과의 포함 여부, 라이선스(회사 사용 가능 여부)는 교수님이 확인하고 승인한다.

## 연구팀

| 이름 | 역할 | 구현 방식 |
|---|---|---|
| 교수님 | 사용자. 방향 설정과 중요 결정(C 등급) | — |
| 윤하진 | 수석연구원, 회의 진행 | 메인 세션 |
| 서도윤 | 이론·아이디어 | 메인 세션, 브레인스토밍 때 `ideator` |
| 민채원 | 문헌 조사, novelty 검증, 논문 항목 관리 | `scout` |
| 강태오 | 구현·실험 실행 (GPU) | `engineer` |
| 오세린 | 비평 (Reviewer 2), 코드와 로그까지 감사 | `critic` (effort high) |
| 한유나 | 분석·보고서·논문 | `writer` |
| 아이디어 발상가들 | 서로 다른 관점(lens)으로 독립적으로 아이디어 생성 | `ideator` × N (병렬) |
| 기록 담당 | 세션 기록을 지식베이스로 정리 | `archivist` |

실무 agent들은 `memory: project`로 **각자의 전문 기억**을 쌓는다(환경 문제, 검색 요령, 반복되는 결함 등).

## 설치

Claude Code 채팅창에서 아래 두 줄을 한 번만 실행한다. GitHub에서 바로 받아 오므로 어느 PC에서나 같다.

```
/plugin marketplace add yhlee52/ai_sci_cowork
/plugin install ai-lab@ai-sci-cowork
```

GitHub에 새 버전이 올라가면 `/plugin marketplace update ai-sci-cowork`로 받아 온다.
AI agent가 처음이라면 [docs/처음_읽는_안내서.md](docs/처음_읽는_안내서.md)부터 읽는다. 환경을 고치고 GitHub에 올리는 방법도 거기에 있다.

## 사용법

```
/ai-lab:new-lab D:\research\my-first-lab 작은 모델의 일반화 현상
```
→ 새 폴더(git 저장소)가 생긴다. **그 폴더를 열고 새 세션을 시작한 뒤, 처음 한 번 뜨는 신뢰(trust) 확인을 승인한다.** 그러면 세션 시작 hook이 장기·중기·단기 컨텍스트와 결정 대기 항목을 자동으로 불러오고, `lab.py` 조회는 권한 확인 없이 실행된다. 실험 실행(`uv run`)은 매번 승인을 묻는다. 번거로우면 `.claude/settings.json`의 `allow`에 `"Bash(uv run *)"`를 추가한다.

| 명령 | 하는 일 |
|---|---|
| `/ai-lab:lab-meeting plan` | 주기 계획. 로드맵을 보고 이번 주기의 목표, 약속, 성공·중단 기준, 예산을 교수님과 정한다 |
| `/ai-lab:lab-meeting progress` | 짧은 진행 점검 |
| `/ai-lab:lab-meeting review` | 결과 리뷰. 결과를 확정할지 교수님이 결정한다 |
| `/ai-lab:lab-meeting journal <P-/LIT id>` | 논문 읽기 모임 |
| `/ai-lab:lab-meeting retro` | 주기 회고. 교훈을 남기고 로드맵 변경을 제안한다 |
| `/ai-lab:lab-meeting 1on1 <이름>` | 교수님과 연구원 한 명의 1:1 |
| `/ai-lab:lab-meeting [안건]` | 일반 회의 |
| `/ai-lab:brainstorm <주제>` | 여러 `ideator`가 병렬로 아이디어를 내고, 합치고, 비평하고, 다듬어서 교수님께 후보를 올린다 |
| `/ai-lab:work [A-001 …]` | action item을 담당 agent에게 맡긴다. 파일럿은 자율로 하고, 본 실험과 결정 사항은 교수님께 여쭙는다 |
| `/ai-lab:archive` | 세션을 지식베이스로 정리하고, 요약본과 인계 메모를 갱신하고, 세션을 닫는다 |
| `/ai-lab:release <F-/EXP- id>` | 확정된 결과를 회사에서 쓸 수 있는 **독립 실행 패키지**로 만든다 (오프라인 설치, 근거와 한계, 라이선스, 재현 정보 포함). 포함 범위는 교수님이 승인한다 |
| `/ai-lab:lab-status` | 현재 상황을 싸게 요약한다 |

**운영 리듬:** 주기 = 세션 N개(기본 3).
`plan 회의 → [세션마다: progress · brainstorm · work · review → archive] × N → retro 회의`

## 의사결정 규칙 (연구가 산으로 가지 않게)

| 등급 | 예 | 누가 |
|---|---|---|
| A. 자율 | 구현, 디버깅, 승인된 계획 안의 하이퍼파라미터, **파일럿(2분, 1시드)**, 문헌 검색 | 담당 연구원 |
| B. 동료 협의 | 승인된 계획 안의 설계 변경, 애매한 결과 해석 | 연구원 + 다른 연구원(주로 비평가) |
| C. 교수님 결정 | 새 방향, **본 실험 착수**, 가설 폐기, **결과 확정**, 예산 초과, 로드맵 변경, 모순, 애매한 지시 | 교수님 |

C 등급은 대화로 바로 여쭙고 기다린다. 교수님이 자리에 없으면 결정 대기함(`lab.py inbox`)에 올리고, 다음 세션 시작 때 가장 먼저 보여 드린다. 판단이 애매하면 한 단계 위로 취급한다.

연구 생애주기: `아이디어 → 파일럿[A] → 사전 등록 승인[C] → 본 실험 → 리뷰[B] → 결과 확정[C] → 보고`

## 장기·단기 컨텍스트

| 층 | 파일 | 변하는 속도 | 세션 시작 때 |
|---|---|---|---|
| 헌장 | `LAB.md` | 거의 안 바뀜 | 필요할 때만 |
| 장기 | `ROADMAP.md` (프로그램, 마일스톤) | 주기마다 | 요약만 주입 |
| 중기 | `state/cycle.md` (이번 주기 목표, 약속, 예산) | 주기 안에서 | 주입 |
| 단기 | `state/lab_state.md` (인계 메모, 진행 중) | 매 단계 | 주입 |
| 지식 | `kb/digest.md` (연구실이 아는 것 1쪽) → `lab.py find/show/context/history` | archive마다 | 필요할 때 |
| 과업 | `briefs/TASK-*` | 과업마다 | agent만 |

모든 과업과 실험은 **목적의 사슬** `MS-n → Q- → H- → EXP- → TASK-`를 적는다. 그래서 담당 agent도 "이 일이 왜 중요한지"를 알고 판단할 수 있다.

## 지식베이스 (novel_project의 정본 관리 방식 적용)

- **사실 하나는 파일 하나가 소유한다.** 다른 곳에서는 ID로만 참조한다.
- **현재 상태와 변화 기록을 분리한다.** 항목은 현재 상태만 갖고, 언제 왜 바뀌었는지는 세션 로그가 소유한다.
- **작은 파일로 나눈다.** 필요한 항목만 골라 읽는다. 색인(`kb/index.json`)과 요약본(`kb/digest.md`)은 스크립트가 만든다.

| novel_project | 연구 워크스페이스 |
|---|---|
| `project/source_of_truth.md` | `kb/README.md` (소유권 표와 스키마) |
| `series_bible.md` | `LAB.md` (헌장) + `ROADMAP.md` (장기 계획) |
| `events/chapters/` | `kb/log/session_NNN.json` (모든 상태 변화의 근거) |
| `knowledge/facts/` | `kb/findings/F-` (증거 경로 필수, 확정은 교수님만) |
| `foreshadowing/` | `kb/hypotheses/H-`, `kb/questions/Q-` |
| `project/canon_decisions/` | `kb/decisions/D-` (등급, 이유, 이견) |
| 정의 카탈로그 | `kb/papers/P-`, `kb/datasets/DS-`, `kb/methods/M-`, `kb/lessons/L-` |
| `chapter_summaries/` | 각 항목의 한 줄 `summary`, `kb/digest.md` |
| context package | `briefs/TASK-NNN.md` |

## 실험 인프라 (`labkit`) 와 무결성

워크스페이스의 `labkit/`는 연구실의 공용 코드다. `Run`은 실행마다 설정, 시드, git commit, 로그, 지표를 남긴다. `collect_results`는 실행 기록에서 `results.json`을 만든다(파일럿은 제외한다). `fit`은 AMP, 시간 예산, 체크포인트 이어하기를 지원한다. engineer가 매번 새로 짜지 않으니 토큰이 절약되고 재현성도 확보된다.

`lab.py verify EXP-xxx`는 사전 등록 항목이 있는지, `results.json`의 모든 숫자가 실제 실행 기록과 일치하는지 결정적으로 검사한다. AI scientist 시스템에서 흔히 보고되는 실패(실패한 실행을 가짜 데이터로 메우기, 보고서와 코드의 불일치, 버그를 발견으로 포장하기, 검증하지 않은 범위로 일반화하기)를 막기 위한 장치다.

## 참고한 AI scientist 시스템

| 시스템 | 가져온 것 |
|---|---|
| [Virtual Lab](https://www.nature.com/articles/s41586-025-09442-9) (Stanford, Nature 2025) | PI가 이끄는 팀 회의와 1:1 회의, 매 라운드의 비평가, 같은 과제를 병렬로 여러 번 돌리고 사람이 고르기 |
| [AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) (Google) | 생성 → 비평 → 순위 → 개선 → 메타리뷰 흐름 (브레인스토밍에 축소 적용) |
| [Kosmos](https://arxiv.org/abs/2511.02824) (Edison Scientific) | 장기 기억 역할의 구조화된 world model (지식베이스) |
| [AI Scientist-v2](https://arxiv.org/abs/2504.08066) (Sakana) | 단계별 실험 관리(파일럿 → 본 실험) |
| [Agent Laboratory](https://arxiv.org/abs/2501.04227) | 단계마다 사람이 검토하는 co-pilot 모드 |
| [Can LLMs Generate Novel Research Ideas?](https://arxiv.org/abs/2409.04109) | LLM 아이디어는 다양성이 부족하다는 결과 → 서로 다른 lens로 독립 생성, 중복 제거 |
| [Hidden Pitfalls of AI Scientist Systems](https://arxiv.org/abs/2509.08713) | 보고서만이 아니라 코드와 로그까지 감사 |

## 토큰 절약 설계

1. **회의는 한 컨텍스트에서 진행한다.** 병렬 agent는 서로 달라야 가치가 있는 곳(브레인스토밍, 깊은 리뷰)에만 쓴다.
2. **컨텍스트를 층으로 나눈다.** 세션 시작 주입은 약 40줄이고, 나머지는 ID로 필요할 때만 읽는다.
3. **brief로 넘기고 파일로 돌려받는다.** subagent는 40줄 이하의 brief만 읽고 10줄 이하로 보고한다.
4. **기계적인 일은 스크립트가 한다.** ID, action, inbox, 색인, 검색, 요약본, 검증은 `lab.py`가 한다.
5. **공용 코드를 재사용한다.** `labkit`, 등록된 방법(M-)과 데이터셋(DS-), 교훈(L-)을 쓴다.
6. **예산 프로필을 둔다.** `economy`(기본) / `standard` / `deep`에 따라 회의 라운드, 발언자, 리뷰 횟수, 병렬 agent 수, 문헌 수, 브레인스토밍 인원이 바뀐다.
7. **모델을 나눠 쓴다.** 실무 agent는 sonnet을 쓴다. 더 아끼려면 `model: haiku` 또는 `CLAUDE_CODE_SUBAGENT_MODEL`을 쓴다.
8. **agent와 skill의 내부 지시문만 영어로 쓴다** (토큰이 적게 든다). 연구실이 만드는 모든 산출물은 한글이다.
9. **파일럿에서 신호가 없으면 멈춘다.** 쓸데없는 본 실험을 막는다.

## 저장소 구조

```
.claude-plugin/   plugin.json, marketplace.json
agents/           scout, engineer, critic, writer, ideator, archivist
skills/           lab-meeting, brainstorm, work, archive, release, lab-status, new-lab
hooks/hooks.json  SessionStart → lab.py status --hook
scripts/lab.py    워크스페이스 도구 (Python 표준 라이브러리만 사용)
templates/workspace/  새 연구실 템플릿 (LAB.md, ROADMAP.md, team.md, state/, kb/, labkit/, research/)
```

## 요구 사항
- Python 3.x (`python`이 PATH에 있어야 한다), git, [uv](https://docs.astral.sh/uv/)
- 실험용 torch는 첫 실험 때 engineer가 워크스페이스에 설치한다 (CUDA 12.8 wheel, Python 3.11–3.13)
