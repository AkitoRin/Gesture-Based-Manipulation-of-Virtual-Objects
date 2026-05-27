# =============================================================================
# 文件：gesture/hand_features.py
# 职责：【识别层辅助 - 手部空间特征】
#       把一只手的 21 个关键点整理成中心点、边界框、z 深度、手掌朝向等信息
#       这些信息会跟随 UDP 数据包发给 Live2D 前端，用于判断手是否靠近角色头部、身体等区域
# =============================================================================

import math


_TIP_INDEXES = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}


_PALM_INDEXES = [0, 5, 9, 13, 17]


def _clamp(value, minimum=0.0, maximum=1.0):
    """
    @function:
        把数值限制在指定范围内
    """
    return max(minimum, min(maximum, value))


def _normalize_point(x, y, frame_width, frame_height):
    """
    @function:
        将像素坐标转换为 0~1 的归一化坐标
    """
    if frame_width <= 0 or frame_height <= 0:
        return [0.0, 0.0]

    return [
        round(_clamp(x / frame_width), 3),
        round(_clamp(y / frame_height), 3),
    ]


def _point_3d(hand, idx, frame_width, frame_height):
    """
    @function:
        把关键点转换成近似 3D 坐标，x/y 归一化，z 保留 MediaPipe 相对深度
    """
    point = hand[idx]
    z = point[3] if len(point) > 3 else 0.0
    return [
        point[1] / frame_width if frame_width else 0.0,
        point[2] / frame_height if frame_height else 0.0,
        z,
    ]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _normalize_vector(vector):
    """
    @function:
        将向量归一化，避免不同手掌大小导致方向值不可比
    """
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 0:
        return [0.0, 0.0, 0.0]

    return [round(value / length, 3) for value in vector]


def _get_palm_normal(hand, frame_width, frame_height):
    """
    @function:
        使用手腕、食指根部、小指根部估算手掌法线方向
    """
    wrist = _point_3d(hand, 0, frame_width, frame_height)
    index_mcp = _point_3d(hand, 5, frame_width, frame_height)
    pinky_mcp = _point_3d(hand, 17, frame_width, frame_height)

    index_vec = _sub(index_mcp, wrist)
    pinky_vec = _sub(pinky_mcp, wrist)
    return _normalize_vector(_cross(index_vec, pinky_vec))


def _get_depth_level(scale):
    """
    @function:
        根据手部在画面中的占比估计远近级别
    """
    if scale >= 0.46:
        return "near"
    if scale <= 0.24:
        return "far"
    return "mid"


def get_hand_features(hand, frame_width, frame_height):
    """
    @function:
        根据 21 个关键点计算手部空间特征

    @params:
        hand (list): 一只手的 21 个关键点，格式为 [[id, x, y], ...]
        frame_width (int): 当前摄像头画面宽度
        frame_height (int): 当前摄像头画面高度

    @returns:
        dict: 手部空间特征
            bbox = 手部边界框
            center = 手部中心点像素坐标
            center_norm = 手部中心点归一化坐标
            center_3d = 手部中心点的近似 3D 坐标
            depth = z 深度和画面占比估计
            palm_normal = 手掌朝向估计
            tips = 五个指尖的像素坐标
            tips_norm = 五个指尖的归一化坐标
    """
    if not hand:
        return {
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "center": [0, 0],
            "center_norm": [0.0, 0.0],
            "center_3d": [0.0, 0.0, 0.0],
            "depth": {"z": 0.0, "scale": 0.0, "level": "mid"},
            "palm_normal": [0.0, 0.0, 0.0],
            "tips": {},
            "tips_norm": {},
        }

    xs = [point[1] for point in hand]
    ys = [point[2] for point in hand]

    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)
    center_x = int((x_min + x_max) / 2)
    center_y = int((y_min + y_max) / 2)
    z_values = [point[3] for point in hand if len(point) > 3]
    palm_z_values = [hand[idx][3] for idx in _PALM_INDEXES if len(hand[idx]) > 3]
    center_z = sum(z_values) / len(z_values) if z_values else 0.0
    palm_z = sum(palm_z_values) / len(palm_z_values) if palm_z_values else center_z

    bbox_w = x_max - x_min
    bbox_h = y_max - y_min
    hand_scale = max(
        bbox_w / frame_width if frame_width else 0.0,
        bbox_h / frame_height if frame_height else 0.0,
    )

    tips = {}
    tips_norm = {}
    for name, idx in _TIP_INDEXES.items():
        point = hand[idx]
        tips[name] = [point[1], point[2]]
        tips_norm[name] = _normalize_point(point[1], point[2], frame_width, frame_height)

    return {
        "bbox": {
            "x": x_min,
            "y": y_min,
            "w": bbox_w,
            "h": bbox_h,
        },
        "center": [center_x, center_y],
        "center_norm": _normalize_point(center_x, center_y, frame_width, frame_height),
        "center_3d": [
            round(_clamp(center_x / frame_width), 3) if frame_width else 0.0,
            round(_clamp(center_y / frame_height), 3) if frame_height else 0.0,
            round(center_z, 5),
        ],
        "depth": {
            "z": round(center_z, 5),
            "palm_z": round(palm_z, 5),
            "scale": round(hand_scale, 3),
            "level": _get_depth_level(hand_scale),
        },
        "palm_normal": _get_palm_normal(hand, frame_width, frame_height),
        "tips": tips,
        "tips_norm": tips_norm,
    }


def get_interaction_zone(features):
    """
    @function:
        根据手部归一化位置判断它更像在角色哪个交互区域

    @params:
        features (dict): get_hand_features() 返回的空间特征

    @returns:
        str: "head"、"body" 或 "free"
    """
    center_x, center_y = features.get("center_norm", [0.0, 0.0])

    # 画面上方中间区域近似映射为 Live2D 角色头部互动区
    if 0.30 <= center_x <= 0.70 and center_y <= 0.44:
        return "head"

    # 画面中间区域近似映射为 Live2D 角色身体互动区
    if 0.24 <= center_x <= 0.76 and 0.44 < center_y <= 0.78:
        return "body"

    return "free"
