# =============================================================================
# 文件：utils/display.py
# 职责：【工具层 - 图像显示适配】
#       把摄像头图像按比例缩放并放进窗口画布中。
#       支持 contain（完整显示，可能留白）和 cover（填满窗口，可能裁剪）两种模式。
#
# 解决的问题：
#   摄像头图像的宽高比（例如 16:9）不一定和窗口大小完全匹配
#   如果直接拉伸图像填满窗口，画面会变形（人脸变宽或变高）
#   这个函数保持图像原始比例，不会把人脸拉宽或拉高。
#   如果使用 contain，会像视频播放器一样出现黑边（Letterbox / Pillarbox）。
#   如果使用 cover，会尽量填满窗口，减少黑边，但可能裁掉少量画面边缘。
#
# 示意：
#   ┌─────────────────┐  ← 窗口
#   │░░░░░░░░░░░░░░░░░│  ← 背景色上边框
#   │░░┌───────────┐░░│
#   │░░│           │░░│  ← 等比例缩放后的图像
#   │░░│ 摄像头画面 │░░│
#   │░░│           │░░│
#   │░░└───────────┘░░│
#   │░░░░░░░░░░░░░░░░░│  ← 背景色下边框
#   └─────────────────┘
# =============================================================================

import cv2 as cv    # OpenCV，用于图像缩放
import numpy as np  # NumPy，用于创建画布数组


def fit_frame_to_window(frame, window_width, window_height, bg_color, fit_mode="contain"):
    """
    @function:
        将图像按比例缩放并居中放置在指定尺寸的画布上

    @params:
        frame (numpy.ndarray): 要显示的图像，BGR 格式，形状为 (高, 宽, 3)
        window_width (int):  当前窗口的宽度（像素）
        window_height (int): 当前窗口的高度（像素）
        bg_color (tuple):    背景色，BGR 格式，例如 (30, 30, 30) 是深灰色
        fit_mode (str):      "contain" 完整显示并允许留白；"cover" 填满窗口并允许裁剪少量边缘

    @returns:
        canvas (numpy.ndarray): 大小为 (window_height, window_width, 3) 的图像，
            图像被居中放置，周围用 bg_color 填充
        None: 如果输入图像为 None（异常情况），返回 None
    """
    # 安全检查：如果传入了空图像，直接返回 None 不做处理
    if frame is None:
        return None

    # 获取原始图像的高度和宽度
    # frame.shape = (高度, 宽度, 通道数)，[:2] = 只取前两个元素（高和宽），忽略通道数
    h, w = frame.shape[:2]

    # 计算缩放比例：
    # - contain：完整显示整张图，可能留白，适合“不想裁剪”的场景
    # - cover：填满整个窗口，可能裁掉少量边缘，适合“减少黑边”的预览场景
    width_scale = window_width / w
    height_scale = window_height / h
    if fit_mode == "cover":
        scale = max(width_scale, height_scale)
    else:
        scale = min(width_scale, height_scale)

    # 计算缩放后图像的实际宽高
    new_w = int(w * scale)
    new_h = int(h * scale)

    # 选择合适的插值方法（影响缩放质量）：
    #   放大图像（scale >= 1）→ INTER_CUBIC（双三次插值），放大时画质更平滑
    #   缩小图像（scale < 1）  → INTER_AREA（区域插值），缩小时效果最好，抗锯齿
    if scale >= 1:
        interpolation = cv.INTER_CUBIC
    else:
        interpolation = cv.INTER_AREA

    # 按计算出的新尺寸缩放图像
    resized = cv.resize(frame, (new_w, new_h), interpolation=interpolation)

    # 创建空白画布：大小等于窗口大小，用背景色填满
    # np.full(形状, 填充值, 数据类型) = 创建一个全部填充为指定值的数组
    # 形状 (window_height, window_width, 3)：高×宽×BGR三通道
    # dtype=np.uint8：每个像素通道的值是 0~255 的整数（图像标准格式）
    canvas = np.full((window_height, window_width, 3), bg_color, dtype=np.uint8)

    # 计算图像和画布的重叠区域。
    # cover 模式下 new_w/new_h 可能比窗口大，所以不能直接整张粘贴，要先裁剪。
    x_offset = (window_width - new_w) // 2
    y_offset = (window_height - new_h) // 2

    canvas_x1 = max(x_offset, 0)
    canvas_y1 = max(y_offset, 0)
    canvas_x2 = min(x_offset + new_w, window_width)
    canvas_y2 = min(y_offset + new_h, window_height)

    frame_x1 = max(-x_offset, 0)
    frame_y1 = max(-y_offset, 0)
    frame_x2 = frame_x1 + (canvas_x2 - canvas_x1)
    frame_y2 = frame_y1 + (canvas_y2 - canvas_y1)

    canvas[canvas_y1:canvas_y2, canvas_x1:canvas_x2] = resized[
        frame_y1:frame_y2,
        frame_x1:frame_x2,
    ]

    return canvas
