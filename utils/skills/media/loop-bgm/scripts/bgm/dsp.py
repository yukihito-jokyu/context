"""通常版とゲームボーイ風で共有する処理。"""

import numpy as np

SR = 48000


def add_wrapped(buffer: np.ndarray, signal: np.ndarray, start: int) -> None:
    """曲末からはみ出した分を曲頭へ折り返して加算する。"""
    size = len(buffer)
    position = 0
    while position < len(signal):
        index = (start + position) % size
        count = min(size - index, len(signal) - position)
        buffer[index:index + count] += signal[position:position + count]
        position += count
