# =============================================================================
# 文件：gesture/command_mapper.py
# 职责：【识别层第四步 - 手势→命令映射】
#       把手势名称字符串（如 "FIST"）翻译成 Live2D 角色能理解的控制命令字符串
#
# 设计原因：
#   直接把手势名发给接收端也能工作，但这样做不够灵活：
#   - 以后如果想换一个手势来表示"停止"，接收端那边也要改
#   - 以后如果同一个命令可以由多个手势触发，直接传手势名就乱了
#   这一层的作用是"解耦"：让视觉识别层（gesture）和控制执行层（Live2D）各自只负责自己的事，中间通过统一的命令字符串沟通
#   如果想改"什么手势对应什么功能"，只需要修改这个文件里的字典，不需要动其他任何地方
# =============================================================================


_GESTURE_TO_COMMAND = {
    "OPEN_HAND":   "CMD_WAVE",          # 张开手掌 → 友好挥手/打招呼
    "FIST":        "CMD_IDLE",          # 握拳     → 收起动作，回到安静待机
    "INDEX_UP":    "CMD_ATTENTION",     # 食指朝上 → 引起注意/认真听你说
    "V_SIGN":      "CMD_HAPPY_POSE",    # 剪刀手   → 开心合影感，不做点头/摇头这种不自然响应
    "THUMBS_UP":   "CMD_PRAISE",        # 拇指朝上 → 夸奖/鼓励
    "THUMBS_DOWN": "CMD_DISAPPOINTED",  # 拇指朝下 → 失落/委屈
    "ROCK":        "CMD_DANCE",         # 摇滚手势 → 活跃舞台动作
    "CALL":        "CMD_TALK",          # 打电话   → 说话/呼叫回应
    "THREE":       "CMD_SURPRISE",      # 三根手指 → 惊讶反应
    "FOUR":        "CMD_CHEER",         # 四根手指 → 应援/鼓励
    "FOUR_THUMB":  "CMD_SHY",           # 拇指+三指 → 害羞/可爱反应
    "PINKY_UP":    "CMD_SHY",           # 小指朝上  → 害羞/约定感
    "UNKNOWN":     "CMD_NONE",          # 未知手势  → 无操作
}
"""
手势名称 → 系统命令 的映射字典
    键（key）  = 手势名称字符串（gesture_classifier.py 中规定的手势类型）
    值（value）= Live2D 控制命令字符串（发给接收端，接收端根据命令执行对应的动作、表情和语言效果）
"""


def map_gesture_to_command(gesture: str) -> str:
    """
    @function:
    把手势名称转换成对应的控制命令字符串

    @params：
        gesture (str): 手势名称，例如 "FIST", "OPEN_HAND", "V_SIGN"
            由 gesture_smoother.py 的 update() 返回的稳定手势名称

    @returns:
        str: 控制命令字符串，例如 "CMD_WAVE", "CMD_IDLE"
            注：如果手势名称不在映射字典中（意外情况），默认返回 "CMD_NONE"
    """
    # dict.get(key, 默认值) = 查字典：找到就返回对应值，找不到就返回默认值 "CMD_NONE"
    return _GESTURE_TO_COMMAND.get(gesture, "CMD_NONE")
