# =============================================================================
# 文件：communication/protocol.py
# 职责：【通信层 - 消息协议定义】
#       定义 Python 端发送给接收端的消息格式，并提供把消息字典序列化成网络传输用的字节串的工具函数
# 
# 设计原则：
#   协议格式是发送端和接收端共同约定的"语言"，这个协议/消息格式需要单独定义在一个文件里，方便维护和升级
#
# 消息格式（JSON）：
#   {
#     "version":   1,                   ← 协议版本，方便以后升级消息格式
#     "type":      "gesture_command",   ← 消息类型，方便接收端区分不同数据
#     "source":    "HandPilot",         ← 消息来源
#     "gesture":   "FIST",              ← 原始手势名称
#     "command":   "CMD_IDLE",          ← 对应的控制命令
#     "hand":      "Right",             ← 哪只手（MediaPipe视角的Left/Right）
#     "hands":     [...],               ← 所有手的信息列表，包含手势、命令、空间区域、运动意图和手部位置
#     "timestamp": 1714000000.123       ← 发送时刻的 Unix 时间戳（精确到毫秒）
#   }
# =============================================================================

# Python 标准库，用于把字典转换成 JSON 字符串
import json   
# Python 标准库，用于获取当前时间戳
import time   

PROTOCOL_VERSION = 1
MESSAGE_TYPE = "gesture_command"
MESSAGE_SOURCE = "HandPilot"


def build_message(gesture: str, command: str, hand: str = "Unknown", hands=None) -> dict:
    """
    @function:
    构建一条完整的消息字典

    @params:
        gesture (str): 手势名称，例如 "FIST", "OPEN_HAND"
            来自 gesture_smoother.py 的稳定输出
        command (str): 控制命令，例如 "CMD_IDLE", "CMD_WAVE"
            来自 command_mapper.py 的映射结果
        hand (str): 哪只手发出的手势，"Left", "Right" 或 "Unknown"
            注意：这里用的是 MediaPipe 视角的左右，镜像后和用户实际的手是相反的！
        hands (list): 当前帧所有手的信息列表
            用于双手控制场景，接收端可以从这里读取每只手的手势、命令、交互区域、运动意图和位置特征

    @returns:
        dict: 包含完整消息内容的字典
    """
    return {
        "version":   PROTOCOL_VERSION,
        "type":      MESSAGE_TYPE,
        "source":    MESSAGE_SOURCE,
        "gesture":   gesture,
        "command":   command,
        "hand":      hand,
        "hands":     hands or [],
        # round(time.time(), 3) = 当前 Unix 时间戳，保留 3 位小数。例如：1714000000.123（代表2024年某个时刻）
        # 接收端可以用这个时间戳检测消息延迟，或者按时间顺序处理消息
        "timestamp": round(time.time(), 3),
    }


def serialize(message: dict) -> bytes:
    """
    @function:
        把消息字典序列化成可以通过网络发送的字节串

    @params:
        message (dict): 由 build_message() 创建的消息字典

    @returns:
        bytes: UTF-8 编码的 JSON 字节串，可以直接通过 socket 发送
        例如：b'{"version": 1, "type": "gesture_command", "gesture": "FIST", "command": "CMD_IDLE"}'

    原理：
        网络传输只能传"字节"（bytes），不能传 Python 的字典对象
        json.dumps(dict) = 把字典转成 JSON 格式的字符串（str）
        .encode("utf-8") = 把字符串转成 UTF-8 编码的字节串（bytes）
        ensure_ascii=False = 允许 JSON 中包含中文等非 ASCII 字符（否则会被转义成 \\uXXXX）
    """
    return json.dumps(message, ensure_ascii=False).encode("utf-8")
