# =============================================================================
# 文件：utils/image_enhance.py
# 职责：【工具层 - 预览画面增强】
#       对摄像头预览画面做轻量亮度、对比度、饱和度和锐化增强，
#       让画面看起来更清楚、更通透
# =============================================================================

import cv2 as cv
import numpy as np


def enhance_preview_frame(frame):
    """
    对预览画面做轻量增强。

    @params:
        frame (numpy.ndarray): BGR 图像

    @returns:
        numpy.ndarray: 增强后的 BGR 图像
    """
    if frame is None:
        return None

    # 轻微提升对比度和亮度，避免过曝区域被进一步拉爆。
    enhanced = cv.convertScaleAbs(frame, alpha=1.06, beta=4)

    # 在 HSV 空间中提升一点饱和度，让画面不那么灰。
    hsv = cv.cvtColor(enhanced, cv.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.08, 0, 255)
    enhanced = cv.cvtColor(hsv.astype(np.uint8), cv.COLOR_HSV2BGR)

    # 非锐化遮罩：让边缘更清晰，但强度保持很低，避免出现明显噪点。
    blurred = cv.GaussianBlur(enhanced, (0, 0), 1.0)
    enhanced = cv.addWeighted(enhanced, 1.18, blurred, -0.18, 0)

    return enhanced
