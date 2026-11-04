# AI Scientist Lab (`ai-lab` plugin)

[![테스트](https://github.com/yhlee52/ai_sci_cowork/actions/workflows/tests.yml/badge.svg)](https://github.com/yhlee52/ai_sci_cowork/actions/workflows/tests.yml)

ML/DL 연구를 하는 작은 AI 연구 그룹을 Claude Code의 agent, skill, hook으로 구성한 **재사용 가능한 환경**이다. 연구원들은 교수님(사용자)과 랩미팅으로 아이디어를 주고받고, 문헌을 조사하고, 실험을 구현·실행하고, 결과를 정리한다. 중요한 결정은 교수님이 내리고, 결과가 좋아졌는지는 **코드가 판정**한다.

- 이 저장소에는 **환경만** 들어 있다. 연구 결과물은 `/ai-lab:new-lab`으로 만드는 **별도 연구실 폴더(별도 저장소)** 에 쌓인다.
- **모든 산출물은 한글이다.** ID, JSON 필드 이름, 상태 값, 태그 같은 기계용 표기만 영어로 둔다.

## 원칙

1. **방향은 사람이, 숫자는 코드가 정한다.** 결과 비교(Welch t 신뢰구간), 캠페인의 채택·기각, 사전 등록 지키기, 보고서 숫자 감사는 코드가 한다.
2. **모든 주장은 추적 가능하다.** 주장 → 결과(F-) → 결과 파일, 인용 → 실존 확인된 논문(P-).
3. **정직한 실패도 성공이다.** 실패와 효과 없음도 지식으로 기록한다.
4. **검증은 기본은 가볍게, 필요할 때 깊게.** 코드 감사는 늘 하고(토큰이 들지 않는다), AI 연구원의 검토는 교수님이 요청할 때만 한다 (`/ai-lab:review`).

## 설치

```
# 터미널 CLI 대화창
/plugin marketplace add yhlee52/ai_sci_cowork
/plugin install ai-lab@ai-sci-cowork

# VSCode 확장 사용 시: 채팅창은 /plugin 미지원 → VSCode 터미널에서
claude plugin marketplace add yhlee52/ai_sci_cowork
claude plugin install ai-lab@ai-sci-cowork
```

새 버전은 `claude plugin marketplace update ai-sci-cowork` 후 `claude plugin update ai-lab@ai-sci-cowork`로 받는다. 자세한 것은 [사용설명서 3장](docs/사용설명서.md#3-설치하기).

## 빠른 시작

1. `/ai-lab:new-lab D:\research\my-lab 작은 모델의 일반화` → 새 연구실 폴더가 생긴다.
2. 그 폴더를 열고 새 세션을 시작한다 (처음 한 번 뜨는 신뢰 확인을 승인). 연구실 상태가 자동으로 불러와진다.
3. `/ai-lab:lab-meeting plan` → 교수님과 연구 방향과 첫 목표를 정한다.
4. 그다음은 **말로 시키면 된다** ("EXP-001 파일럿 돌려 줘", "관련 논문 찾아 줘"). 정해 둔 할 일을 한꺼번에 맡길 때는 `/ai-lab:work`.
5. 세션을 마칠 때 `/ai-lab:archive`.

## 명령

| 명령 | 하는 일 |
|---|---|
| `/ai-lab:lab-meeting [plan\|review\|journal\|retro\|1on1]` | 랩미팅: 방향 정하기, 결과 리뷰, 논문 읽기, 회고, 1:1 |
| `/ai-lab:work [A-id…]` | 할 일을 담당 연구원에게 맡긴다. 파일럿은 자율, 본 실험과 결과 확정은 교수님 |
| `/ai-lab:review <ID> [초점]` | **엄격 검증** (요청할 때만): 코드를 직접 돌려 보는 검증, 설계·통계·주장 비평, 메커니즘 분석 |
| `/ai-lab:brainstorm <주제>` | 여러 관점의 독립 아이디어 → 선행연구 확인 → 쌍대 비교 순위 → 교수님 선택 |
| `/ai-lab:campaign [EXP-id]` | 자율 탐색: 교수님이 승인한 범위 안에서 시도 반복, 판정은 코드, 끝나면 새 시드 확인 실험 |
| `/ai-lab:paper <F-id…>` | 확정된 결과로 한글 논문·보고서 초안, 숫자·인용 감사 |
| `/ai-lab:summarize <대상>` | 논문 깊이 읽기, 실험·세션의 한 쪽 요약 |
| `/ai-lab:release <ID…>` | 회사로 가져갈 **md 문서** (근거, 한계, 사용 방법, 선택적 코드 묶음) |
| `/ai-lab:archive` | 세션 정리: 지식베이스, 인계 메모, 점검, HTML 리포트, 로컬 git 커밋 |
| `/ai-lab:lab-status` | 지금 상황 요약 |
| `/ai-lab:new-lab <경로> [주제]` | 새 연구실 만들기 |

## 문서

- [사용설명서](docs/사용설명서.md): 설치, 첫 연구실, 따라 하기, 명령어 사전, 결정 규칙, 실험과 검증, 자율 탐색, 릴리스, 설정, 문제 해결
- [처음 읽는 안내서](docs/처음_읽는_안내서.md): AI agent가 처음인 분을 위한 개념 설명과 GitHub 관리 방법
- [설계 근거](docs/설계_근거.md): 다른 AI scientist 시스템과 그 실패 연구에서 배운 것, 그래서 이렇게 만든 이유
- [변경 이력](CHANGELOG.md)

## 저장소 구조

```
.claude-plugin/       plugin.json, marketplace.json
agents/               연구원 10명 (scout, engineer, explorer, verifier, theorist, critic, writer, summarizer, ideator, archivist)
skills/               명령 11개 (위 표)
hooks/hooks.json      세션 시작 → lab.py status --hook
scripts/lab.py        연구실 도구 (Python 표준 라이브러리만 사용)
templates/workspace/  새 연구실 템플릿 (LAB.md, ROADMAP.md, team.md, state/, kb/, labkit/, research/)
tests/                lab.py·labkit 테스트 (python -m unittest discover -s tests)
docs/                 사용설명서, 처음 읽는 안내서, 설계 근거
```

## 요구 사항
- Python 3.10 이상 (`python`이 PATH에 있어야 한다), git, [uv](https://docs.astral.sh/uv/)
- 실험용 torch는 첫 실험 때 연구 엔지니어가 연구실에 설치한다 (CUDA 12.8 wheel, Python 3.11–3.13)
- Claude Code v2.1.269 이상 권장 (`/goal`의 사용 한도 자동 재개)
