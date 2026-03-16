import cv2 as cv
import numpy as np


def fit_frame_to_window(frame, window_width, window_height, bg_color):
    """
    将图像按比例缩放，并居中放到窗口画布中
    :param frame: 帧
    :param window_width: 窗口宽度
    :param window_height: 窗口高度
    :param bg_color: 背景颜色
    :return:
    """
    if frame is None:
        return None

    h, w = frame.shape[:2]
    scale = min(window_width / w, window_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    if scale >= 1:
        interpolation = cv.INTER_CUBIC
    else:
        interpolation = cv.INTER_AREA

    resized = cv.resize(frame, (new_w, new_h), interpolation=interpolation)

    canvas = np.full((window_height, window_width, 3), bg_color, dtype=np.uint8)

    x_offset = (window_width - new_w) // 2
    y_offset = (window_height - new_h) // 2

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas
