# =============================================================================
# 文件：tools/udp_receiver_test.py
# 职责：【开发工具 - UDP 接收测试器】
#       用来验证 HandPilot 主程序是否真的把手势命令通过 UDP 发出来了
#
# 使用方式：
#   1. 在 config/settings.py 中设置 COMMUNICATION_ENABLED = True
#   2. 打开一个终端运行：python -m tools.udp_receiver_test
#   3. 再打开另一个终端运行：python main.py
#   4. 做手势，如果通信正常，这个终端会打印收到的 JSON 数据包
#
# 可选用法：
#   python -m tools.udp_receiver_test --host 127.0.0.1 --port 5005
#   python -m tools.udp_receiver_test --raw
# =============================================================================

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any


# 允许这个文件既可以通过 python -m tools.udp_receiver_test 运行，
# 也可以在某些 IDE 里直接运行。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.settings import COMM_HOST, COMM_PORT
except ImportError as exc:
    raise RuntimeError(
        "无法导入 config.settings。请确认你是在 HandPilot 项目根目录下运行：\n"
        "  python -m tools.udp_receiver_test"
    ) from exc


REQUIRED_FIELDS = {
    "version",
    "type",
    "source",
    "gesture",
    "command",
    "hand",
    "hands",
    "timestamp",
}


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    默认使用 config/settings.py 中的 COMM_HOST 和 COMM_PORT。
    如果临时想监听其他端口，也可以通过 --host / --port 覆盖。
    """
    parser = argparse.ArgumentParser(
        description="HandPilot UDP 接收测试工具，用于调试通信层是否正常发包"
    )

    parser.add_argument(
        "--host",
        default=COMM_HOST,
        help=f"监听地址，默认读取 settings.py：{COMM_HOST}",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=COMM_PORT,
        help=f"监听端口，默认读取 settings.py：{COMM_PORT}",
    )

    parser.add_argument(
        "--buffer-size",
        type=int,
        default=8192,
        help="单个 UDP 数据包最大读取字节数，默认 8192",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="只打印原始文本，不做 JSON 格式化与协议检查",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=0.5,
        help="socket 等待超时时间，默认 0.5 秒；用于让 Ctrl+C 更容易生效",
    )

    return parser.parse_args()


def create_udp_socket(host: str, port: int) -> socket.socket:
    """
    创建并绑定 UDP socket。

    UDP 接收端需要 bind 到一个地址和端口。
    如果这个端口已经被其他程序占用，比如 bridge 或另一个 receiver，
    bind 会失败。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind((host, port))
    except OSError as exc:
        sock.close()
        print("\n[启动失败] UDP 端口绑定失败。")
        print(f"监听地址：{host}:{port}")
        print("\n常见原因：")
        print("1. 你已经启动了另一个 UDP 接收器。")
        print("2. 你已经启动了 bridge/udp_to_ws.js。")
        print("3. COMM_PORT 配置和其他程序冲突。")
        print("\n解决方式：")
        print("1. 关闭占用该端口的程序。")
        print("2. 或者换一个端口，例如：")
        print("   python -m tools.udp_receiver_test --port 5006")
        raise SystemExit(1) from exc

    return sock


def decode_packet(data: bytes) -> str:
    """
    将 UDP bytes 数据解码为字符串。

    正常情况下，HandPilot 发出的应该是 UTF-8 JSON。
    如果有异常字符，用 replacement 替代，避免程序直接崩溃。
    """
    return data.decode("utf-8", errors="replace")


def try_parse_json(text: str) -> dict[str, Any] | None:
    """
    尝试把字符串解析为 JSON 对象。

    如果不是合法 JSON，或者 JSON 顶层不是对象，则返回 None。
    """
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(value, dict):
        return None

    return value


def validate_protocol(message: dict[str, Any]) -> list[str]:
    """
    检查收到的 JSON 是否符合 HandPilot 通信协议的基本字段要求。

    注意：
    这里只做“基础字段检查”，不负责深度校验每个字段的业务含义。
    """
    warnings: list[str] = []

    missing_fields = REQUIRED_FIELDS - set(message.keys())
    if missing_fields:
        warnings.append(f"缺少字段：{', '.join(sorted(missing_fields))}")

    if message.get("type") != "gesture_command":
        warnings.append(
            f"type 字段不是 gesture_command，当前为：{message.get('type')!r}"
        )

    if message.get("source") != "HandPilot":
        warnings.append(
            f"source 字段不是 HandPilot，当前为：{message.get('source')!r}"
        )

    if "hands" in message and not isinstance(message.get("hands"), list):
        warnings.append("hands 字段应为 list，用于携带当前帧所有手的信息")

    return warnings


def calculate_latency_ms(message: dict[str, Any]) -> float | None:
    """
    根据 message['timestamp'] 估算从发送到接收的延迟。

    约定：
    - 如果 timestamp 是 time.time() 风格的秒级时间戳，直接计算。
    - 如果 timestamp 是毫秒级时间戳，自动转换为秒。
    """
    timestamp = message.get("timestamp")

    if not isinstance(timestamp, (int, float)):
        return None

    send_time = float(timestamp)

    # 兼容毫秒级时间戳，例如 1714000000123。
    if send_time > 10_000_000_000:
        send_time = send_time / 1000

    latency_ms = (time.time() - send_time) * 1000

    # 如果时间明显不合理，就不显示，避免误导。
    if latency_ms < 0 or latency_ms > 60_000:
        return None

    return latency_ms


def print_message(
    count: int,
    address: tuple[str, int],
    text: str,
    message: dict[str, Any] | None,
    raw: bool,
) -> None:
    """
    打印收到的数据包。
    """
    receive_time = time.strftime("%H:%M:%S")

    print("\n" + "=" * 72)
    print(f"包序号：#{count}")
    print(f"接收时间：{receive_time}")
    print(f"来源地址：{address[0]}:{address[1]}")

    if raw or message is None:
        print("\n原始内容：")
        print(text)
        return

    latency_ms = calculate_latency_ms(message)
    warnings = validate_protocol(message)

    gesture = message.get("gesture", "UNKNOWN")
    command = message.get("command", "UNKNOWN")
    hand = message.get("hand", "UNKNOWN")
    hands = message.get("hands", [])

    print("\n摘要：")
    summary = f"gesture={gesture} | command={command} | hand={hand}"
    if latency_ms is not None:
        summary += f" | latency={latency_ms:.2f} ms"
    print(summary)
    print(f"hands_count={len(hands) if isinstance(hands, list) else 'INVALID'}")

    if warnings:
        print("\n协议检查：")
        for warning in warnings:
            print(f"- [警告] {warning}")
    else:
        print("\n协议检查：通过")

    print("\nJSON 内容：")
    print(json.dumps(message, ensure_ascii=False, indent=2))


def main() -> None:
    """
    启动 UDP 接收测试工具。
    """
    args = parse_args()

    sock = create_udp_socket(args.host, args.port)
    # 不让 recvfrom 永久阻塞。每隔 timeout 秒醒一次，
    # 这样 Windows / VS Code 终端里按 Ctrl+C 时能更稳定地退出。
    sock.settimeout(args.timeout)
    packet_count = 0

    print("=" * 72)
    print("HandPilot UDP 接收测试工具已启动")
    print("=" * 72)
    print(f"监听地址：{args.host}:{args.port}")
    print("等待 HandPilot 数据包...")
    print("按 Ctrl+C 退出")
    print("\n提示：")
    print("1. 请确认 config/settings.py 中 COMMUNICATION_ENABLED = True")
    print("2. 请确认 main.py 的发送端口和这里的监听端口一致")
    print("3. 如果要启动 bridge，请先关闭本接收器，因为二者不能同时占用同一端口")

    try:
        while True:
            try:
                data, address = sock.recvfrom(args.buffer_size)
            except socket.timeout:
                continue

            packet_count += 1

            text = decode_packet(data)
            message = try_parse_json(text)

            print_message(
                count=packet_count,
                address=address,
                text=text,
                message=message,
                raw=args.raw,
            )

    except KeyboardInterrupt:
        print("\n\nUDP 接收测试已退出。")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
