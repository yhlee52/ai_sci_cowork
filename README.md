# AI Scientist Lab (`ai-lab` plugin)

[![테스트](https://github.com/yhlee52/ai_sci_cowork/actions/workflows/tests.yml/badge.svg)](https://github.com/yhlee52/ai_sci_cowork/actions/workflows/tests.yml)

ML/DL 연구를 하는 작은 AI 연구 그룹을 Claude Code의 agent, skill, hook으로 구성한 **재사용 가능한 환경**이다.
연구원들은 교수님(사용자)과 랩미팅으로 아이디어를 주고받고, 문헌을 조사하고, 실험을 구현·실행·분석하고, 서로 비판한다. 교수님이 자율 탐색을 시키면 승인한 범위 안에서 **스스로 실험을 반복**하기도 한다 (지금 바로, 또는 자리를 비운 사이나 밤새). 실험은 **이 PC를 자동으로 탐색해 건 하드웨어 제약** 안에서 설계된다. 중요한 결정은 반드시 교수님이 내리고, 결과가 좋아졌는지는 **코드가 판정**한다. 연구 지식은 **ID로 찾아 필요한 것만 읽을 수 있는 지식베이스**에 쌓인다.

- 이 저장소에는 **환경만** 들어 있다. 연구 결과물은 `/ai-lab:new-lab`으로 만드는 **별도 워크스페이스(별도 저장소)** 에 쌓인다.
- **모든 산출물은 한글이다.** ID, JSON 필드 이름, 상태 값, 태그 같은 기계용 표기만 영어로 둔다.

> 📖 **문서**
> - [처음 읽는 안내서](docs/처음_읽는_안내서.md): AI agent 개념, 이 환경의 구조, GitHub 관리 방법 (처음이라면 여기부터)
> - [사용설명서](docs/사용설명서.md): 설치, 첫 연구실, 첫 주기 따라 하기, 하드웨어 제약, 자율 탐색, 명령어 사전, 문제 해결
> - [설계 근거](docs/설계_근거.md): 다른 AI scientist 시스템과 그 실패 연구에서 배운 것, 그래서 이렇게 만든 이유

## 세 가지 원칙

1. **방향은 사람이, 숫자는 코드가 정한다.** AI는 제안하고 구현한다. 결과 비교(부트스트랩 신뢰구간), 캠페인의 채택/기각, 증거 감사는 코드가 한다. AI의 자기 평가는 개선이 없어도 개선됐다고 착각한다는 연구 결과가 있다.
2. **모든 주장은 추적 가능하다.** 주장 → 결과(F-) → 결과 파일 → 실행 기록, 인용 → 실존 확인된 논문(P-). 보고서의 숫자는 결과 파일과 자동 대조된다.
3. **정직한 실패도 성공이다.** 실패, 효과 없음, 부정적 결과도 지식으로 기록한다. 끝내야 한다는 압박을 없애야 날조가 줄어든다.

## 연구팀

| 이름 | 역할 | 구현 방식 |
|---|---|---|
| 교수님 | 사용자. 방향 설정과 중요 결정(C 등급) | — |
| 윤하진 | 수석연구원, 회의 진행 | 메인 세션 |
| 서도윤 | 이론·아이디어 | 메인 세션, 브레인스토밍 때 `ideator` |
| 민채원 | 문헌 조사(arXiv·Semantic Scholar API), 선행연구 충돌 확인, 인용 검증 | `scout` |
| 강태오 | 구현·실험 (재현 → 기준선 → 파일럿 → 본 실험 → 절제 → 조건 이동 점검), 자동 탐색한 하드웨어 제약 안에서 | `engineer` |
| 강태오 (자율 탐색) | 교수님이 시키면 언제든, 승인된 캠페인 안에서 시도를 반복 (판정은 `lab.py`) | `explorer` |
| 오세린 | 비평 (Reviewer 2): 코드·로그·감사 결과까지 확인, 쌍대 비교 판정 | `critic` (effort high) |
| 한유나 | 분석·보고서·논문 (모든 숫자와 인용이 추적 가능하게) | `writer` |
| 아이디어 발상가들 | 서로 다른 관점(lens)으로 독립적으로 아이디어 생성 | `ideator` × N (병렬) |
| 기록 담당 | 세션 기록을 지식베이스로 정리, 실패한 방향·실험 전략을 기억으로 증류 | `archivist` |

## 설치

아래 두 명령을 한 번만 실행한다. GitHub에서 바로 받아 오므로 어느 PC에서나 같다.

```
# 터미널 CLI 대화창
/plugin marketplace add yhlee52/ai_sci_cowork
/plugin install ai-lab@ai-sci-cowork

# VSCode 확장 사용 시: 채팅창은 /plugin 미지원 → VSCode 터미널에서
claude plugin marketplace add yhlee52/ai_sci_cowork
claude plugin install ai-lab@ai-sci-cowork
```

GitHub에 새 버전이 올라가면 `claude plugin marketplace update ai-sci-cowork` 후 `claude plugin update ai-lab@ai-sci-cowork`(CLI 대화창에서는 `/plugin marketplace update ai-sci-cowork`)로 받아 온다. `claude`가 PATH에 없으면 VSCode 확장에 들어 있는 `claude.exe`를 쓴다 ([사용설명서 3장](docs/사용설명서.md#3-설치하기)).

## 사용법

```
/ai-lab:new-lab D:\research\my-first-lab 작은 모델의 일반화 현상
```
→ 새 폴더(git 저장소)가 생긴다. **그 폴더를 열고 새 세션을 시작한 뒤, 처음 한 번 뜨는 신뢰(trust) 확인을 승인한다.** 세션 시작 hook이 장기·중기·단기 컨텍스트, 결정 대기 항목, 캠페인 상황, 점검 경고를 자동으로 불러온다.

| 명령 | 하는 일 |
|---|---|
| `/ai-lab:lab-meeting plan` | 주기 계획. 로드맵과 연구 지도를 보고 이번 주기의 목표, 약속, 성공·중단 기준, 예산을 교수님과 정한다 |
| `/ai-lab:lab-meeting progress` | 짧은 진행 점검 |
| `/ai-lab:lab-meeting review` | 결과 리뷰. 감사 결과와 리뷰를 보고 교수님이 확정·잠정·추가 실험·기각을 결정한다 |
| `/ai-lab:lab-meeting journal <P-/LIT id>` | 논문 읽기 모임 |
| `/ai-lab:lab-meeting retro` | 주기 회고. 교훈, 로드맵 변경 제안, **운영 방식 점검** |
| `/ai-lab:lab-meeting 1on1 <이름>` | 교수님과 연구원 한 명의 1:1 |
| `/ai-lab:brainstorm <주제>` | 병렬 독립 생성 → 선행연구 충돌 확인 → **쌍대 비교 순위** → 개선 → (파일럿 토너먼트) → 교수님 선택 |
| `/ai-lab:work [A-001 …]` | 할 일을 담당 agent에게 맡긴다. 파일럿은 자율, 본 실험과 결정은 교수님 |
| `/ai-lab:campaign [EXP-id] \| plan\|run\|status\|stop` | **자율 탐색 캠페인**: "자율 탐색해"라고 하면 계약 → 승인 → 바로 시작. 승인된 계약 안에서 시도 반복, 판정은 코드, 끝나면 새 시드 확인 실험 |
| `/ai-lab:paper <F-id들>` | 확정된 결과로 한글 논문·보고서 초안 → 숫자·인용 감사 → 학회식 리뷰 → 수정 |
| `/ai-lab:archive` | 세션 정리: 지식베이스·요약본·연구 지도 갱신, 점검, 인계 메모, 로컬 git 커밋 |
| `/ai-lab:release <F-/EXP-/CMP- id>` | 회사로 가져갈 **md 문서** (근거, 한계, 사용 방법, 선택적 코드 묶음) |
| `/ai-lab:lab-status` | 현재 상황을 싸게 요약한다 |

**운영 리듬:** 주기 = 세션 N개(기본 3). `plan 회의 → [세션마다: progress · brainstorm · work · campaign · review → archive] × N → retro 회의`

## 의사결정 규칙 (연구가 산으로 가지 않게)

| 등급 | 예 | 누가 |
|---|---|---|
| A. 자율 | 구현, 디버깅, 승인된 계획 안의 하이퍼파라미터, **파일럿**, 문헌 검색, **승인된 캠페인 안의 시도** | 담당 연구원 |
| B. 동료 협의 | 승인된 계획 안의 설계 변경, 애매한 결과 해석 | 연구원 + 다른 연구원(주로 비평가) |
| C. 교수님 결정 | 새 방향, **본 실험 착수**, **캠페인 계약**, 가설 폐기, **결과 확정**, 예산 초과, 로드맵 변경, 모순, 애매한 지시 | 교수님 |

C 등급은 선택지와 함께 바로 여쭙고 기다린다. 교수님이 자리에 없으면(또는 캠페인이 도는 중이면) 결정 대기함(`lab.py inbox`)에 올리고, 다음 세션 시작 때 가장 먼저 보여 드린다.

## 자율 탐색 (캠페인)

[Karpathy의 autoresearch](https://github.com/karpathy/autoresearch)처럼 고정 시간(기본 5분) 실험을 반복하되, 연구실의 안전장치를 붙였다. 시간대와 상관없이 교수님이 시키면 시작한다 (바로 돌려서 지켜보거나, 자리를 비운 사이·밤새 맡기거나).

- 교수님이 **계약**(지표, 수정 가능 파일, 예산, 멈춤 조건)을 승인한 범위 안에서만 자율.
- 평가 코드는 **해시로 보호**, 지표는 평가 출력에서만 읽음 → 학습 코드가 지표를 속일 수 없다.
- 채택 문턱 = 기준선 반복 측정의 잡음 × 2 → 우연한 개선을 채택하지 않는다. 같은 성능이면 더 짧은 코드를 채택한다.
- 모든 시도는 장부·패치·로그로 남고, `lab.py verify`가 **장부의 숫자와 판정을 로그에서 다시 계산**해 위조를 잡는다.
- 끝나면 **탐색에 쓰지 않은 새 시드**로 확인 실험 → 요약·리뷰 → 교수님 결정.
- 오래 맡길 때는 Claude Code의 `/goal`로 시작하면 사용 한도에 걸려도 풀린 뒤 자동으로 이어 간다.

## `lab.py` — 결정적 도구 (판정과 기록은 코드가)

| 명령 | 하는 일 |
|---|---|
| `status`, `find/show/context/history`, `digest`, `map` | 현황, ID 검색, 1쪽 지식 요약(실패한 방향·효과 없음 포함), 연구 지도(mermaid) |
| `audit <EXP/CMP>`, `audit --report <문서> --sources <ID들>` | 결과↔실행 기록 대조, 계획 준수, 보고서·논문의 숫자와 인용 대조 |
| `campaign init/baseline/approve/begin/run/status/confirm/stop/close` | 캠페인 엔진: 실행, 시간 제한, 지표 판독, 채택/기각, 확인 실험 |
| `rank schedule/score` | 쌍대 비교 순위 (Bradley-Terry) |
| `lit search/get/check` | arXiv·Semantic Scholar 검색, 논문 조회, 논문 항목 실존 확인 |
| `lint`, `doctor` | 지식베이스 무결성 점검, 실험 환경 진단 |
| `hardware` | 이 PC의 하드웨어(GPU, VRAM, RAM, CPU) 탐색 → 운영 제약(`compute.limits`) 자동 설정. PC가 바뀌면 세션 시작 때 다시 탐색 |
| `action`, `inbox`, `next`, `init`, `pack-md/unpack-md` | 할 일, 결정 대기함, ID 발급, 새 연구실, md 코드 묶음 |

## 장기·단기 컨텍스트와 지식베이스

| 층 | 파일 | 세션 시작 때 |
|---|---|---|
| 헌장 | `LAB.md` (원칙, 결정 규칙, 연구 생애주기) | 필요할 때만 |
| 장기 | `ROADMAP.md` (프로그램, 마일스톤) | 요약만 주입 |
| 중기 | `state/cycle.md` (주기 목표, 약속, 예산) | 주입 |
| 단기 | `state/lab_state.md` (인계 메모) | 주입 |
| 지식 | `kb/digest.md`, `kb/map.md` → `lab.py find/show/context/history` | 필요할 때 |

지식베이스는 [novel_project](https://github.com/yhlee52/novel_project)의 정본 관리 방식을 연구 지식에 적용했다: 사실 하나는 파일 하나가 소유, 현재 상태와 변화 기록(세션 로그) 분리, 작은 파일로 나누기, 색인은 캐시.

## 토큰 절약 설계

1. 회의는 한 컨텍스트에서 여러 관점으로 진행하고, 병렬 agent는 독립성이 품질을 올리는 곳(브레인스토밍, 깊은 리뷰)에만 쓴다.
2. 세션 시작 주입은 약 40줄, 나머지는 ID로 필요할 때만 읽는다. subagent는 40줄 이하의 brief만 읽고 10줄 이하로 보고한다.
3. 기계적인 일(ID, 검색, 감사, 캠페인 판정, 요약본, 지도)은 `lab.py`가 한다. 공용 코드 `labkit`을 재사용한다.
4. 예산 프로필(`economy`/`standard`/`deep`)로 회의 라운드, 리뷰 횟수, 병렬 agent 수, 브레인스토밍 인원, 파일럿 토너먼트, 캠페인 배치 크기가 함께 바뀐다.
5. agent와 skill의 내부 지시문만 영어로 쓴다(토큰이 적게 든다). 산출물은 모두 한글이다.

## 저장소 구조

```
.claude-plugin/     plugin.json, marketplace.json
agents/             scout, engineer, explorer, critic, writer, ideator, archivist
skills/             lab-meeting, brainstorm, work, campaign, paper, archive, release, lab-status, new-lab
hooks/hooks.json    SessionStart → lab.py status --hook
scripts/lab.py      연구실 도구 (Python 표준 라이브러리만 사용)
templates/workspace/  새 연구실 템플릿 (LAB.md, ROADMAP.md, team.md, state/, kb/, labkit/, research/)
tests/              lab.py·labkit 테스트 (python -m unittest discover -s tests)
.github/workflows/  GitHub Actions: Windows·Linux × Python 3.10·3.13 자동 테스트
docs/               처음 읽는 안내서, 사용설명서, 설계 근거
```

## 요구 사항
- Python 3.10 이상 (`python`이 PATH에 있어야 한다), git, [uv](https://docs.astral.sh/uv/)
- 실험용 torch는 첫 실험 때 engineer가 워크스페이스에 설치한다 (CUDA 12.8 wheel, Python 3.11–3.13)
- Claude Code v2.1.269 이상 권장 (`/goal`의 사용 한도 자동 재개)
