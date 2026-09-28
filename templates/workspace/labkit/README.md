# labkit — 연구실 공용 실험 코드

새 코드를 짜기 전에 여기서 먼저 찾아 쓴다. 두 번째 실험에서도 필요해진 코드는 여기로 옮기고, 지식베이스에 방법(`M-`)이나 데이터셋(`DS-`)으로 등록한다.

| 모듈 | 제공하는 것 |
|---|---|
| `run.py` | `Run` — 실행 하나당 폴더 하나: `config.json`(설정, 시드, git 커밋, 환경), `train.log`, `metrics.jsonl`, `metrics.json`(최종 지표) |
| `results.py` | `collect_results(exp_dir, exp_id, hypothesis, setup)` → 실행 기록에서 `results.json`을 만든다 (조건별 평균, 표준편차, 개수). 파일럿은 제외한다 |
| `train.py` | `fit(...)` — AMP, 기울기 자르기, 평가, 시간 예산, 체크포인트 이어하기를 갖춘 PyTorch 학습 루프 |
| `repro.py` | `seed_everything`, `get_device`, `git_commit`, `env_info` |
| `plot.py` | `setup_korean_plot()` — 그림의 제목, 축, 범례를 한글로 쓸 수 있게 글꼴을 설정한다 |

## 전형적인 실험 코드

```python
from labkit import Run, collect_results, setup_korean_plot
from labkit.train import fit

for cond in ["baseline", "ours"]:
    for seed in range(3):
        with Run(EXP_DIR, cond, seed, config=cfg[cond], max_minutes=30) as run:
            best = fit(...)                 # 또는 직접 짠 루프에서 run.log(...)
            run.finish(**best)

collect_results(EXP_DIR, "EXP-001", hypothesis="가중치 감쇠가 일반화 시점을 앞당긴다",
                setup={"데이터셋": "모듈러 덧셈", "모델": "2층 트랜스포머"})
```

그다음 `lab.py verify EXP-001`로 `results.json`이 실행 기록과 일치하는지 확인한다.

## 규칙

- 조건 이름과 지표 이름(예: `baseline`, `val_acc`)은 코드 식별자라서 영어로 쓴다. 설명 문장, 주석, 로그 메시지, 그림 글자는 한글로 쓴다.
- 파일럿 실행은 조건 이름을 `pilot-`으로 시작한다. `collect_results`가 자동으로 제외한다.
- 공용 데이터 로더는 `labkit/data_<이름>.py`, 모델은 `labkit/models/<이름>.py`에 둔다.
