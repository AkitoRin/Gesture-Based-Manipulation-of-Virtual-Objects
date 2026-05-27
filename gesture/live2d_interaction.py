# =============================================================================
# 文件：gesture/live2d_interaction.py
# 职责：【识别层第五步 - Live2D 互动意图】
#       在基础手势命令之上叠加空间语义，例如手掌出现在头部区域时触发摸头回应
# =============================================================================


_PETTING_GESTURES = {"OPEN_HAND", "FOUR", "FOUR_THUMB"}

_MOTION_TO_COMMAND = {
    "SWIPE_LEFT": "CMD_LOOK_LEFT",
    "SWIPE_RIGHT": "CMD_LOOK_RIGHT",
    "RAISE_UP": "CMD_JUMP_SURPRISE",
    "MOVE_DOWN": "CMD_BOW",
    "PUSH_IN": "CMD_COME_CLOSER",
    "PULL_OUT": "CMD_STEP_BACK",
}


def derive_live2d_command(gesture, base_command, interaction_zone, motion=None):
    """
    @function:
        根据手势和空间区域推导更适合 Live2D 的互动命令

    @params:
        gesture (str): 当前稳定手势名称
        base_command (str): command_mapper.py 输出的基础命令
        interaction_zone (str): 手部所在区域，通常为 "head"、"body" 或 "free"
        motion (dict): HandMotionTracker 输出的运动意图

    @returns:
        str: 最终发送给 Live2D 前端的命令字符串
    """
    motion_type = (motion or {}).get("type", "STILL")

    # 明确的动态手势优先级最高，让角色对挥动、靠近、远离这类动作有清楚反馈
    if motion_type in _MOTION_TO_COMMAND:
        return _MOTION_TO_COMMAND[motion_type]

    # 张开手掌或四指靠近头部区域时，更像是在摸头而不是普通挥手
    if interaction_zone == "head" and gesture in _PETTING_GESTURES:
        return "CMD_PET_HEAD"

    return base_command


def derive_scene_command(hand_states):
    """
    @function:
        根据多只手的组合状态推导全局场景命令

    @params:
        hand_states (list): 当前帧所有手的状态列表

    @returns:
        str | None: 如果存在双手组合命令则返回命令，否则返回 None
    """
    if len(hand_states) < 2:
        return None

    open_hands = [
        item for item in hand_states
        if item.get("gesture") == "OPEN_HAND"
    ]

    # 双手同时张开时，角色进入更热烈的应援回应
    if len(open_hands) >= 2:
        return "CMD_DOUBLE_CHEER"

    return None
