"""데이터 누수 점검. 학습 데이터와 평가 데이터에 같은 샘플이 섞였는지 지문(해시)으로 확인한다.

    from labkit.leakage import check_overlap
    report = check_overlap(train_texts, test_texts)            # 문자열, 바이트, 숫자 튜플, numpy/torch 배열 지원
    report = check_overlap(train_ds, test_ds, key=lambda s: s[0])  # 샘플에서 입력만 비교할 때

결과가 "너무 좋아 보이면" 가장 먼저 돌려 볼 점검이다.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Iterable


def fingerprint(item: Any) -> str:
    """샘플 하나의 지문. 같은 내용이면 같은 값이 나온다."""
    if hasattr(item, "detach"):  # torch 텐서
        item = item.detach().cpu().numpy()
    if hasattr(item, "tobytes") and hasattr(item, "shape"):  # numpy 배열
        data = str(item.shape).encode() + item.tobytes()
    elif isinstance(item, bytes):
        data = item
    elif isinstance(item, str):
        data = item.strip().encode("utf-8")
    else:
        data = repr(item).encode("utf-8")
    return hashlib.sha1(data).hexdigest()


def check_overlap(train_items: Iterable[Any], test_items: Iterable[Any],
                  key: Callable[[Any], Any] | None = None, max_examples: int = 5, verbose: bool = True) -> dict:
    """평가 샘플 중 학습 데이터에도 있는 것의 개수와 비율."""
    pick = key or (lambda x: x)
    train_fp = {fingerprint(pick(x)) for x in train_items}
    overlap, total, examples = 0, 0, []
    for i, x in enumerate(test_items):
        total += 1
        if fingerprint(pick(x)) in train_fp:
            overlap += 1
            if len(examples) < max_examples:
                examples.append(i)
    ratio = overlap / total if total else 0.0
    report = {"overlap": overlap, "test_size": total, "ratio": ratio, "example_test_indices": examples}
    if verbose:
        if overlap:
            print(f"경고: 평가 샘플 {total}개 중 {overlap}개({ratio:.1%})가 학습 데이터에도 있습니다 (누수 의심). 예: {examples}")
        else:
            print(f"누수 점검 통과: 평가 샘플 {total}개 중 학습 데이터와 겹치는 것이 없습니다")
    return report
