# labkit — 연구실 공용 실험 코드

새 코드를 짜기 전에 여기서 먼저 찾아 쓴다. 두 번째 실험에서도 필요해진 코드는 여기로 옮기고, 지식베이스에 방법(`M-`)이나 데이터셋(`DS-`)으로 등록한다.

| 모듈 | 제공하는 것 |
|---|---|
| `run.py` | `Run` — 실행 하나당 폴더 하나: `config.json`(설정, 시드, git 커밋, 환경), `train.log`, `metrics.jsonl`, `metrics.json`(최종 지표) |
| `results.py` | `collect_results(exp_dir, exp_id, hypothesis, setup, goal=…)` → 실행 기록에서 `results.json`을 만든다. 조건별 평균·표준편차·개수, 그리고 기준선(`baseline`) 대비 **개선량과 95% 신뢰구간**(`comparisons`). 파일럿은 제외한다 |
| `stats.py` | `compare(treat, base, goal)` 부트스트랩 신뢰구간 비교 (판정: 개선 / 악화 / 판단 불가), `bootstrap_ci`, `summarize` |
| `leakage.py` | `check_overlap(train, test)` — 평가 데이터가 학습 데이터와 겹치는지 (결과가 너무 좋을 때 가장 먼저) |
| `train.py` | `fit(...)` — AMP, 기울기 자르기, 평가, 시간 예산, 체크포인트 이어하기를 갖춘 PyTorch 학습 루프 |
| `limits.py` | `lab_limits()` — `lab.py hardware`가 이 PC를 탐색해 건 운영 제약(장치, 정밀도, VRAM 예산, 모델 크기, DataLoader workers). `Run`과 `get_device()`가 VRAM 예산을 자동으로 걸고, `Run`이 최대 VRAM 사용량(`peak_vram_gb`)을 기록한다 |
| `repro.py` | `seed_everything`, `get_device`(운영 제약의 장치), `git_commit`, `env_info`, `seed_from_env`(캠페인이 주는 시드), `report_metric`(캠페인이 읽는 `LAB_METRIC 이름=값` 출력) |
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

res = collect_results(EXP_DIR, "EXP-001", hypothesis="가중치 감쇠가 일반화 시점을 앞당긴다",
                      setup={"데이터셋": "모듈러 덧셈", "모델": "2층 트랜스포머"},
                      goal={"val_acc": "max"})
print(res["comparisons"]["ours"]["val_acc"]["verdict"])   # 예: "개선 (95% 신뢰구간이 0보다 큼)"
```

그다음 `lab.py audit EXP-001`로 결과 파일이 실행 기록과 같은지, 계획대로 했는지, 보고서의 숫자가 결과 파일에 있는지 확인한다.

## 하드웨어 제약 지키기

- 모델, 배치 크기, 정밀도는 `lab_limits()`에 맞춘다. 하드웨어를 짐작해서 가정하지 않는다.
- DataLoader는 `num_workers=lab_limits().get("dataloader_workers", 0)`.
- 파일럿의 `최대 VRAM`(실행 끝 줄, `metrics.json`의 `peak_vram_gb`)을 보고 본 실험 크기를 정한다. 예산을 넘으면 메모리 부족 오류로 멈추므로, 배치를 줄이거나 기울기 누적을 쓴다.

## 캠페인(자율 탐색)용 코드

- `train.py` = 캠페인이 바꿔 볼 수 있는 파일. 시드는 `seed_from_env()`, 데이터 경로는 환경 변수 `LAB_ROOT` 기준.
- `evaluate.py` = **수정 금지** 평가 코드. 마지막에 `report_metric("val_loss", 값)`을 부른다. 지표를 여기서만 읽기 때문에 학습 코드가 지표를 속일 수 없다.
- 한 번의 실행이 캠페인의 시도 예산(기본 5분, 최대 7분) 안에 끝나야 한다.

## 규칙

- 조건 이름과 지표 이름(예: `baseline`, `val_acc`)은 코드 식별자라서 영어로 쓴다. 설명 문장, 주석, 로그 메시지, 그림 글자는 한글로 쓴다.
- 기준 조건의 이름은 `baseline`으로 한다 (그래야 비교가 자동으로 계산된다).
- 파일럿 실행은 조건 이름을 `pilot-`으로 시작한다. `collect_results`가 자동으로 제외한다.
- 공용 데이터 로더는 `labkit/data_<이름>.py`, 모델은 `labkit/models/<이름>.py`에 둔다.
