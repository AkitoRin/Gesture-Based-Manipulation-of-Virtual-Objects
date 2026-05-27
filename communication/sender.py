# =============================================================================
# 文件：communication/sender.py
# 职责：【通信层 - UDP 命令发送器】
#       把识别到的手势和命令，通过 UDP 网络协议发送给接收端
#
# 设计原因：为什么用 UDP 而不是 TCP？
#   TCP 保证数据一定送达，但每次传输有握手开销，延迟较高
#   UDP 不保证送达，但速度快、延迟低，适合实时控制场景
#   手势控制对"延迟"敏感，偶尔丢一个包问题不大（下一秒还会重发），所以选 UDP 更合适
#
# 发送策略：（避免发送过多或过少）
#   1. 节流（Throttle）：两次发送之间至少要间隔 min_interval 秒，防止过度发送；
#   2. 变化即发（Changed）：手势/命令/左右手变化时立刻发送一次，保证接收端快速响应；
#   3. 周期重发（Repeat）：手势持续不变时，每隔 repeat_interval 秒重发一次，防止 UDP 丢包导致接收端没收到任何命令；
#   4. CMD_NONE 只发一次：没有手势时（CMD_NONE）只在刚变成无手势时发一次，之后不重复发送，避免无用流量。
# =============================================================================

# Python 标准库，用于输出日志
import logging  
# Python 标准库，用于网络通信
import socket   
# Python 标准库，用于时间计算
import time  
# 本项目中的消息构建工具   
from communication.protocol import build_message, serialize 
# 从配置文件导入所需参数 
from config.settings import (
    COMM_HOST,
    COMM_PORT, 
    COMM_MIN_INTERVAL,
    COMM_REPEAT_INTERVAL
)

# 获取一个专属于这个模块的日志记录器（logger）
# 日志记录器名称 "HandPilot.UDP" 会出现在每条日志的前面，方便区分是哪个模块输出的
log = logging.getLogger("HandPilot.UDP")

class CommandSender:
    """
    UDP 命令发送器
    创建一个持续复用的 UDP socket，按策略把手势命令发送给接收端
    """

    def __init__(self, host: str = COMM_HOST, 
                 port: int = COMM_PORT,
                 min_interval: float = COMM_MIN_INTERVAL,
                 repeat_interval: float = COMM_REPEAT_INTERVAL):
        """
        @function:
            初始化发送器，创建 UDP socket

        @params:
            host (str): 接收端的 IP 地址
                "127.0.0.1" = 本机
                 其他 IP    = 局域网内另一台电脑上的接收端
            port (int): 接收端监听的 UDP 端口号 
                发送端和接收端必须一致
            min_interval (float): 最小发送间隔（秒）==> 0.05秒=最多每秒发20次
                防止发送太频繁，保护网络和接收端
            repeat_interval (float): 重复发送间隔（秒）
                手势不变时每隔这么久重发一次，对抗 UDP 丢包
        """

        self.host = host
        self.port = port
        self.min_interval = min_interval
        self.repeat_interval = repeat_interval

        # 创建 UDP socket：
        #   socket.AF_INET   = 使用 IPv4 地址（最常见的网络地址格式）
        #   socket.SOCK_DGRAM = 使用 UDP 协议（数据报协议，无连接）
        # 这个 socket 会被复用（不会每次发送都新建），效率更高
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 记录上一次发送的核心状态（用于判断手势/命令/左右手是否改变）
        # 只比较 command 不够，因为不同手势可能映射到同一个命令，左右手也可能影响接收端表现
        self._last_message_key = None
        self._last_send_time = 0.0   # 记录上一次发送的时间戳（用于节流和重发判断）

    def send(self, gesture: str, command: str, hand: str = "Unknown", hands=None):
        """
        @function:
            尝试发送一条手势命令消息，根据发送策略决定是否真正发送

        @params：
            gesture (str): 当前稳定手势名称，例如 "FIST"
            command (str): 对应的控制命令，例如 "CMD_IDLE"
            hand (str):    手势来自哪只手，"Left"/"Right"/"Unknown"
            hands (list):   当前帧所有手的信息，用于双手控制

        @returns：
            None（无返回值，发送结果通过日志输出）
        """
        now = time.time()  # 当前时间戳
        hands = hands or []

        # -----------------------------------------------------------------------
        # 判断是否应该发送（三条规则）
        # -----------------------------------------------------------------------

        # 规则1：节流检查 - 距上次发送不足 min_interval 秒，直接跳过，避免发送太频繁
        # 本次消息的核心状态（手势/命令/左右手）
        hand_keys = tuple(
            (
                item.get("index"),
                item.get("hand"),
                item.get("gesture"),
                item.get("command"),
                item.get("zone"),
                _get_position_bucket(item),
            )
            for item in hands
        )
        message_key = (gesture, command, hand, hand_keys)
        # 核心状态是否改变了 
        changed     = (message_key != self._last_message_key) 
        # 是否过了最小间隔  
        throttle_ok = (now - self._last_send_time) >= self.min_interval   
        # 是否到了重发时间
        repeat_due  = (now - self._last_send_time) >= self.repeat_interval 

        if not throttle_ok:
            return  # 发送太快，本次跳过

        # 规则2：CMD_NONE 只发一次 - 如果命令是"无操作"且命令没有变化，不重复发送
        if command == "CMD_NONE" and not changed:
            return

        # 规则3：未变化且未到重发时间 - 命令没变且距上次发送还没到 repeat_interval，跳过
        if not changed and not repeat_due:
            return

        # -----------------------------------------------------------------------
        # 通过了所有检查，执行发送
        # -----------------------------------------------------------------------

        # 1. 构建消息字典（包含手势、命令、手、时间戳）
        msg = build_message(gesture, command, hand, hands)

        # 2. 序列化成字节串（JSON 格式的 UTF-8 字节）
        payload = serialize(msg)

        try:
            # 3. 通过 UDP socket 发送字节串到目标地址
            # sendto(数据, (IP地址, 端口)) = 把数据发送到指定的 IP:端口

            # -----------------------------------------------------------------------
            # 数据发送
            # -----------------------------------------------------------------------
            self.sock.sendto(payload, (self.host, self.port))

            # 4. 更新发送记录
            self._last_message_key = message_key  # 记录这次发送的核心状态，供下次比较
            self._last_send_time = now            # 记录这次发送的时间，供下次节流判断

            # 5. 输出日志（CHANGED=命令改变了，REPEAT=持续重发）
            reason = "CHANGED" if changed else "REPEAT"
            log.info(f"[{reason}] → {self.host}:{self.port}  {payload.decode()}")

        except OSError as e:
            # 发送失败（例如网络断开、端口不可达等）
            # 用 warning 级别记录（不用 error，因为丢包是 UDP 正常情况，不算严重错误）
            log.warning(f"UDP 发送失败: {e}")

    def close(self):
        """
        @function:
            关闭 UDP socket，释放网络资源
        """
        self.sock.close()


def _get_position_bucket(hand_state):
    """
    @function:
        把手部位置压缩成粗略网格，避免手轻微抖动时每帧都触发 UDP 发送

    @params:
        hand_state (dict): hand_states 中的一项

    @returns:
        tuple: 归一化位置的粗略网格坐标
    """
    features = hand_state.get("features") or {}
    center_norm = features.get("center_norm") or [0.0, 0.0]
    if len(center_norm) < 2:
        return (0, 0)

    depth = features.get("depth") or {}
    scale = float(depth.get("scale", 0.0))

    # 使用较细网格，让 Live2D 头眼追踪能更顺滑地收到位置变化
    return (
        int(float(center_norm[0]) * 30),
        int(float(center_norm[1]) * 30),
        int(scale * 20),
    )
