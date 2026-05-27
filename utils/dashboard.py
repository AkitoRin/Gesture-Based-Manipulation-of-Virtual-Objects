# =============================================================================
# 文件：utils/dashboard.py
# 职责：【工具层 - 调试面板渲染】
#       将 FPS、UDP 状态、手势和命令等信息放到摄像头画面右侧的独立面板中。
#       这样不会遮挡手部画面，也能保持清爽、易读的监控界面风格。
# =============================================================================

import cv2 as cv
import numpy as np

from config.settings import DASHBOARD_WIDTH


FONT_TITLE = cv.FONT_HERSHEY_DUPLEX
FONT_BODY = cv.FONT_HERSHEY_DUPLEX
FONT_MONO = cv.FONT_HERSHEY_SIMPLEX


# OpenCV 使用 BGR 色值。这里采用偏暖浅色系，接近纸张/奶油白背景。
COLOR_BG = (242, 239, 231)
COLOR_BG_SOFT = (248, 246, 240)
COLOR_CARD = (255, 253, 247)
COLOR_TEXT = (48, 45, 39)
COLOR_TEXT_SOFT = (105, 100, 91)
COLOR_MUTED = (145, 138, 126)
COLOR_LINE = (216, 208, 194)
COLOR_GREEN = (86, 174, 91)
COLOR_GREEN_SOFT = (190, 226, 194)
COLOR_BLUE = (150, 112, 64)
COLOR_GOLD = (44, 149, 213)
COLOR_SECTION = (92, 142, 92)
COLOR_OFF = (150, 150, 150)
COLOR_SHADOW = (205, 199, 188)
COLOR_VIDEO_BORDER = (232, 224, 210)


def _draw_round_rect(canvas, x1, y1, x2, y2, color, radius=18, thickness=-1):
    """
    用 OpenCV 基础图形拼出圆角矩形。
    """
    if thickness == -1:
        cv.rectangle(canvas, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv.rectangle(canvas, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        cv.circle(canvas, (x1 + radius, y1 + radius), radius, color, -1)
        cv.circle(canvas, (x2 - radius, y1 + radius), radius, color, -1)
        cv.circle(canvas, (x1 + radius, y2 - radius), radius, color, -1)
        cv.circle(canvas, (x2 - radius, y2 - radius), radius, color, -1)
        return

    cv.line(canvas, (x1 + radius, y1), (x2 - radius, y1), color, thickness, cv.LINE_AA)
    cv.line(canvas, (x1 + radius, y2), (x2 - radius, y2), color, thickness, cv.LINE_AA)
    cv.line(canvas, (x1, y1 + radius), (x1, y2 - radius), color, thickness, cv.LINE_AA)
    cv.line(canvas, (x2, y1 + radius), (x2, y2 - radius), color, thickness, cv.LINE_AA)
    cv.ellipse(canvas, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness, cv.LINE_AA)
    cv.ellipse(canvas, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness, cv.LINE_AA)
    cv.ellipse(canvas, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness, cv.LINE_AA)
    cv.ellipse(canvas, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness, cv.LINE_AA)


def _put_text(canvas, text, pos, scale=0.62, color=COLOR_TEXT, thickness=1, font=FONT_BODY):
    """
    绘制抗锯齿文字。
    """
    cv.putText(canvas, text, pos, font, scale, color, thickness, cv.LINE_AA)


def _put_shadow_text(
    canvas,
    text,
    pos,
    scale=0.86,
    color=COLOR_TEXT,
    thickness=2,
    font=FONT_TITLE,
):
    """
    给标题文字加一个非常轻的阴影，让 OpenCV 字体看起来更有层次。
    """
    x, y = pos
    _put_text(canvas, text, (x + 2, y + 2), scale, COLOR_SHADOW, thickness, font)
    _put_text(canvas, text, pos, scale, color, thickness, font)


def _put_section(canvas, text, x, y):
    _put_text(canvas, text.upper(), (x, y), 0.54, COLOR_SECTION, 1, FONT_MONO)


def _draw_metric(canvas, label, value, x, y, value_color=COLOR_TEXT):
    """
    绘制一行系统指标。
    """
    _put_text(canvas, label, (x, y), 0.58, COLOR_TEXT_SOFT, 1, FONT_BODY)
    _put_text(canvas, str(value), (x + 150, y), 0.66, value_color, 2, FONT_BODY)


def _draw_status_dot(canvas, center, color):
    """
    绘制 UDP 状态圆点。
    """
    cv.circle(canvas, center, 11, COLOR_GREEN_SOFT, -1, cv.LINE_AA)
    cv.circle(canvas, center, 7, color, -1, cv.LINE_AA)
    cv.circle(canvas, center, 12, color, 1, cv.LINE_AA)


def _draw_empty_card(canvas, x, y, width):
    card_h = 92
    _draw_round_rect(canvas, x, y, x + width, y + card_h, COLOR_CARD, 18, -1)
    _draw_round_rect(canvas, x, y, x + width, y + card_h, COLOR_LINE, 18, 1)
    _put_text(canvas, "No hand detected", (x + 24, y + 56), 0.62, COLOR_MUTED, 1, FONT_BODY)
    return card_h


def _draw_hand_card(canvas, item, x, y, width):
    card_h = 140
    _draw_round_rect(canvas, x, y, x + width, y + card_h, COLOR_CARD, 20, -1)
    _draw_round_rect(canvas, x, y, x + width, y + card_h, COLOR_LINE, 20, 1)

    left = x + 24
    title_y = y + 28
    gesture_y = y + 68
    command_y = y + 98
    meta_y = y + 126

    _put_text(
        canvas,
        f"Hand {item['index']}  [{item['label']}]",
        (left, title_y),
        0.62,
        COLOR_TEXT_SOFT,
        1,
        FONT_BODY,
    )

    # 手势名本身已经足够醒目，这里不再加厚阴影，避免显得笨重。
    _put_text(
        canvas,
        item["gesture"],
        (left, gesture_y),
        0.78,
        COLOR_GOLD,
        2,
        FONT_TITLE,
    )
    _put_text(canvas, item["command"], (left, command_y), 0.56, COLOR_SECTION, 1, FONT_BODY)

    raw_text = f"raw={item['raw_gesture']}"
    fingers_value = str(item["fingers"])
    fingers_text = f"fingers={fingers_value}"
    meta_scale = 0.52
    meta_gap = 10

    # 自适应兜底：优先使用稍大的字号；如果完整 fingers=[...] 放不下，
    # 就逐步缩小一点，避免再次越出卡片边界。
    max_meta_w = width - 36
    while meta_scale >= 0.44:
        raw_w = cv.getTextSize(raw_text, FONT_MONO, meta_scale, 1)[0][0]
        fingers_w = cv.getTextSize(fingers_text, FONT_MONO, meta_scale, 1)[0][0]
        meta_w = raw_w + meta_gap + fingers_w
        if meta_w <= max_meta_w:
            break
        meta_scale -= 0.02

    meta_x = x + max(18, (width - meta_w) // 2)

    _put_text(
        canvas,
        raw_text,
        (meta_x, meta_y),
        meta_scale,
        COLOR_MUTED,
        1,
        FONT_MONO,
    )
    _put_text(
        canvas,
        fingers_text,
        (meta_x + raw_w + meta_gap, meta_y),
        meta_scale,
        COLOR_MUTED,
        1,
        FONT_MONO,
    )

    return card_h


def _draw_panel_background(height):
    """
    创建浅色背景面板，并加入非常淡的斜向装饰，让界面不显得单调。
    """
    panel = np.full((height, DASHBOARD_WIDTH, 3), COLOR_BG, dtype=np.uint8)

    # 柔和的装饰色块，不影响文字阅读。
    overlay = panel.copy()
    cv.rectangle(overlay, (DASHBOARD_WIDTH - 130, 0), (DASHBOARD_WIDTH, height), (235, 242, 238), -1)
    pts = np.array(
        [
            [DASHBOARD_WIDTH - 160, 0],
            [DASHBOARD_WIDTH, 0],
            [DASHBOARD_WIDTH - 72, height],
            [DASHBOARD_WIDTH - 232, height],
        ],
        np.int32,
    )
    cv.fillPoly(overlay, [pts], (230, 238, 235))
    panel = cv.addWeighted(overlay, 0.34, panel, 0.66, 0)

    return panel


def render_dashboard(frame, fps, hands, communication_enabled, host, port):
    """
    在视频帧右侧拼接一个独立调试面板。

    返回：
        numpy.ndarray: 摄像头画面 + 右侧信息面板。
    """
    height = frame.shape[0]
    panel = _draw_panel_background(height)

    x = 34
    y = 44
    inner_w = DASHBOARD_WIDTH - x * 2
    footer_y = height - 56

    _put_shadow_text(panel, "HandPilot", (x, y), 0.9, COLOR_TEXT, 2, FONT_TITLE)
    _put_text(panel, "Gesture Control Monitor", (x, y + 32), 0.52, COLOR_TEXT_SOFT, 1, FONT_BODY)
    cv.line(panel, (x, y + 56), (DASHBOARD_WIDTH - x, y + 56), COLOR_LINE, 1, cv.LINE_AA)

    y += 84
    _put_section(panel, "System", x, y)
    y += 34
    _draw_metric(panel, "FPS", fps, x, y, COLOR_GREEN)
    y += 31
    udp_state = "ON" if communication_enabled else "OFF"
    udp_color = COLOR_GREEN if communication_enabled else COLOR_OFF
    _draw_metric(panel, "UDP", udp_state, x, y, udp_color)
    _draw_status_dot(panel, (x + 212, y - 7), udp_color)
    y += 31
    _draw_metric(panel, "Target", f"{host}:{port}", x, y, COLOR_BLUE)

    y += 46
    _put_section(panel, "Hands", x, y)
    y += 22

    if not hands:
        _draw_empty_card(panel, x, y, inner_w)
    else:
        gap = 14
        hidden_count = 0

        for item in hands[:3]:
            card_h = 140
            if y + card_h > footer_y - 18:
                hidden_count += 1
                continue

            _draw_hand_card(panel, item, x, y, inner_w)
            y += card_h + gap

        hidden_count += max(0, len(hands) - 3)
        if hidden_count:
            _put_text(
                panel,
                f"+{hidden_count} more hand state",
                (x + 16, footer_y - 12),
                0.42,
                COLOR_MUTED,
                1,
                FONT_MONO,
            )

    cv.line(panel, (x, footer_y - 18), (DASHBOARD_WIDTH - x, footer_y - 18), COLOR_LINE, 1, cv.LINE_AA)
    _put_text(panel, "Esc to quit", (x, height - 30), 0.48, COLOR_MUTED, 1, FONT_MONO)

    # 给摄像头画面和面板之间加一条浅色分隔线，视觉上更干净。
    separator = np.full((height, 2, 3), COLOR_VIDEO_BORDER, dtype=np.uint8)
    return np.hstack((frame, separator, panel))
