"""그림의 한글 표시 설정. 제목, 축 이름, 범례를 모두 한글로 쓰기 위해 그림을 그리기 전에 한 번 부른다.

    from labkit import setup_korean_plot
    setup_korean_plot()
"""
from __future__ import annotations

KOREAN_FONTS = ("Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic", "Noto Sans CJK KR", "Noto Sans KR")


def setup_korean_plot() -> str | None:
    """설치된 한글 글꼴을 찾아 matplotlib 기본 글꼴로 정한다. 찾은 글꼴 이름을 돌려준다."""
    import matplotlib
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((name for name in KOREAN_FONTS if name in installed), None)
    if chosen:
        matplotlib.rcParams["font.family"] = chosen
    else:
        print("경고: 한글 글꼴을 찾지 못했습니다. 그림의 한글이 깨질 수 있습니다 (예: 맑은 고딕, 나눔고딕 설치).")
    matplotlib.rcParams["axes.unicode_minus"] = False  # 한글 글꼴에서 음수 기호가 깨지는 문제 방지
    return chosen
