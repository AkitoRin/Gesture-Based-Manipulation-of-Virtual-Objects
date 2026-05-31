# =============================================================================
# 文件：docs/diagrams/generate_handpilot_diagrams.py
# 职责：【文档工具 - HandPilot 图表资产生成器】
#       使用 Python 标准库统一生成项目文档中的 SVG 图表和 Draw.io 可编辑源文件
#       图表内容发生变化时，只需要修改本文件并重新运行生成命令
#
# 使用方式：
#   在项目根目录执行：
#   python docs/diagrams/generate_handpilot_diagrams.py
#
# 输出文件：
#   1. handpilot_system_architecture.svg  系统总体架构图
#   2. handpilot_frame_pipeline.svg       Python 单帧处理流水线
#   3. handpilot_realtime_link.svg        UDP 与 WebSocket 实时通信链路
#   4. handpilot_architecture.drawio      包含上述三类图表的三页 Draw.io 可编辑源文件
#
# Draw.io 页签：
#   1. 01 System Architecture  系统总体架构
#   2. 02 Frame Pipeline       单帧处理流程
#   3. 03 Realtime Link        实时通信链路
#
# 设计说明：
#   SVG 用于 README 和 Markdown 文档中的直接预览
#   Draw.io 用于后续拖拽编辑、补充节点和重新导出
#   两类资产由同一个脚本生成，避免文档中的图片与可编辑源文件长期不一致
# =============================================================================

from __future__ import annotations

# Python 标准库，用于转义 SVG 中的特殊字符
from html import escape
# Python 标准库，用于定位当前脚本所在目录
from pathlib import Path
# Python 标准库，用于构建 Draw.io 使用的 XML 文件
from xml.etree import ElementTree as ET


# 所有生成文件都保存到当前 docs/diagrams/ 目录
OUTPUT_DIR = Path(__file__).resolve().parent

# 统一维护图表配色
# 每组颜色依次表示：背景色、边框色、强调文字色
PALETTES = {
    "green": ("#E8F6EF", "#248B68", "#176B51"),
    "blue": ("#EAF3FF", "#3B79C9", "#255A99"),
    "orange": ("#FFF1E6", "#D77635", "#A94F1C"),
    "purple": ("#F0EEFF", "#7564CD", "#5142A6"),
    "rose": ("#FCEBF1", "#C65B83", "#983C60"),
    "gold": ("#FFF7DF", "#C28B22", "#906412"),
    "slate": ("#F2F4F7", "#7A8793", "#4E5964"),
}


def text(
    x: int,
    y: int,
    value: str,
    *,
    size: int = 15,
    weight: int = 500,
    fill: str = "#24313A",
    anchor: str = "start",
    family: str = "Segoe UI, Microsoft YaHei, sans-serif",
) -> str:
    """
    @function:
        生成一段 SVG 文本标签

    @params:
        x (int): 文本起点的横坐标
        y (int): 文本起点的纵坐标
        value (str): 需要显示的文字
        size (int): 字号
        weight (int): 字体粗细
        fill (str): 字体颜色
        anchor (str): 文本对齐方式
        family (str): 字体列表

    @returns:
        str: 可以拼接到 SVG 文件中的 <text> 标签字符串
    """
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}">{escape(value)}</text>'
    )


def card(
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    lines: list[str],
    *,
    palette: str = "blue",
    subtitle: str | None = None,
    title_size: int = 19,
    body_size: int = 14,
    compact: bool = False,
) -> str:
    """
    @function:
        生成一张带圆角、阴影、标题和正文的 SVG 信息卡片

    @params:
        x/y (int): 卡片左上角坐标
        width/height (int): 卡片宽度和高度
        title (str): 卡片标题
        lines (list[str]): 卡片正文，每个元素显示为一行
        palette (str): 使用 PALETTES 中的配色名称
        subtitle (str | None): 可选副标题
        title_size/body_size (int): 标题和正文字号
        compact (bool): 是否使用更紧凑的正文行距

    @returns:
        str: 卡片对应的 SVG 标签字符串
    """
    fill, stroke, strong = PALETTES[palette]
    body: list[str] = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="20" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" filter="url(#shadow)"/>',
        text(x + 22, y + 35, title, size=title_size, weight=700, fill=strong),
    ]
    cursor = y + 58
    if subtitle:
        body.append(text(x + 22, cursor, subtitle, size=12, weight=600, fill=stroke))
        cursor += 25
    else:
        cursor += 4
    step = 21 if compact else 25
    for line in lines:
        body.append(text(x + 22, cursor, line, size=body_size, weight=500))
        cursor += step
    return "\n".join(body)


def arrow(
    points: list[tuple[int, int]],
    *,
    label: str | None = None,
    label_x: int | None = None,
    label_y: int | None = None,
    color: str = "#667085",
    dashed: bool = False,
) -> str:
    """
    @function:
        生成一条 SVG 箭头连线

    @params:
        points (list[tuple[int, int]]): 箭头依次经过的坐标点
        label (str | None): 可选的箭头说明文字
        label_x/label_y (int | None): 说明文字坐标
        color (str): 箭头颜色
        dashed (bool): 是否使用虚线

    @returns:
        str: 箭头和可选说明文字对应的 SVG 标签字符串
    """
    commands = [f"M {points[0][0]} {points[0][1]}"]
    commands.extend(f"L {x} {y}" for x, y in points[1:])
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    body = [
        f'<path d="{" ".join(commands)}" fill="none" stroke="{color}" '
        f'stroke-width="2"{dash} marker-end="url(#arrow)"/>'
    ]
    if label and label_x is not None and label_y is not None:
        body.append(
            f'<rect x="{label_x - 7}" y="{label_y - 17}" '
            f'width="{len(label) * 8 + 14}" height="23" rx="11" '
            f'fill="#FCFBF8" opacity="0.96"/>'
        )
        body.append(text(label_x, label_y, label, size=12, weight=700, fill=color))
    return "\n".join(body)


def page(
    width: int,
    height: int,
    title_value: str,
    subtitle: str,
    body: str,
) -> str:
    """
    @function:
        把图表主体包装成完整的 SVG 页面

    @params:
        width/height (int): SVG 页面尺寸
        title_value (str): 页面标题
        subtitle (str): 页面副标题
        body (str): 已经拼接完成的卡片、箭头和文字标签

    @returns:
        str: 完整的 SVG XML 文本
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>{escape(title_value)}</title>
  <desc>{escape(subtitle)}</desc>
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#59636E" flood-opacity="0.10"/>
    </filter>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#667085"/>
    </marker>
  </defs>
  <rect width="{width}" height="{height}" fill="#FCFBF8"/>
  <rect x="24" y="22" width="{width - 48}" height="{height - 44}" rx="26" fill="#FFFFFF" stroke="#E6E9ED"/>
  {text(58, 76, title_value, size=30, weight=750)}
  {text(58, 105, subtitle, size=14, weight=500, fill="#667085")}
  <line x1="58" y1="128" x2="{width - 58}" y2="128" stroke="#E1E6EA"/>
  {body}
</svg>
"""


def write_svg(name: str, width: int, height: int, title_value: str, subtitle: str, body: str) -> None:
    """
    @function:
        将完整 SVG 文本保存到 docs/diagrams/ 目录

    @params:
        name (str): 输出文件名
        width/height (int): SVG 页面尺寸
        title_value (str): 页面标题
        subtitle (str): 页面副标题
        body (str): 图表主体标签

    @returns:
        None
    """
    (OUTPUT_DIR / name).write_text(
        page(width, height, title_value, subtitle, body),
        encoding="utf-8",
    )


# =============================================================================
# SVG 图表内容
# 以下三个函数分别生成三张适合在 Markdown 中直接预览的 SVG 图表
# =============================================================================

def build_system_architecture() -> None:
    """
    @function:
        生成系统总体架构图

    @returns:
        None

    @outputs:
        输出 handpilot_system_architecture.svg
        用于说明视觉采集、Python 决策、Node Bridge 和 Web Live2D 之间的关系
    """
    body = "\n".join(
        [
            card(
                58,
                176,
                232,
                190,
                "01 视觉采集",
                [
                    "OpenCV Camera",
                    "1280 x 720 摄像头画面",
                    "镜像翻转与清晰度增强",
                    "MediaPipe Hands",
                    "21 个关键点 + 相对 Z 深度",
                ],
                palette="green",
            ),
            card(
                58,
                430,
                232,
                156,
                "本地预览",
                [
                    "OpenCV 可视化窗口",
                    "手部骨架与关键点",
                    "FPS / UDP / 双手状态",
                    "Esc 安全退出",
                ],
                palette="slate",
            ),
            card(
                345,
                158,
                490,
                458,
                "02 Python HandPilot",
                [],
                palette="orange",
                subtitle="识别、稳定化、空间语义与命令决策",
                title_size=22,
            ),
            card(
                375,
                250,
                200,
                118,
                "感知层",
                ["finger_state.py", "gesture_classifier.py", "静态手势规则识别"],
                palette="green",
                body_size=13,
                compact=True,
            ),
            card(
                600,
                250,
                200,
                118,
                "稳定层",
                ["gesture_smoother.py", "7 帧窗口 / 4 票确认", "降低短时抖动误判"],
                palette="blue",
                body_size=13,
                compact=True,
            ),
            card(
                375,
                397,
                200,
                134,
                "交互层",
                ["hand_features.py", "中心位置 / Z 轴 / 尺度", "区域与连续运动判断", "双手场景组合"],
                palette="purple",
                body_size=13,
                compact=True,
            ),
            card(
                600,
                397,
                200,
                134,
                "输出层",
                ["command_mapper.py", "live2d_interaction.py", "protocol.py / sender.py", "UDP JSON 数据包"],
                palette="gold",
                body_size=13,
                compact=True,
            ),
            card(
                900,
                176,
                302,
                174,
                "03 Node.js Bridge",
                [
                    "udp_to_ws.js",
                    "接收 UDP 127.0.0.1:5005",
                    "推送 WebSocket /ws",
                    "托管静态页面 127.0.0.1:8765",
                ],
                palette="blue",
            ),
            card(
                900,
                408,
                302,
                198,
                "04 Web Live2D",
                [
                    "app.js + Live2D Profile",
                    "动作文件与表情联动",
                    "头部 / 眼睛跟随手部移动",
                    "浏览器 SpeechSynthesis 语音",
                    "Local Test 独立验证模型响应",
                ],
                palette="rose",
            ),
            arrow([(290, 270), (345, 270)], label="frame", label_x=302, label_y=257),
            arrow([(290, 500), (322, 500), (322, 570), (345, 570)], dashed=True),
            arrow([(835, 500), (868, 500), (868, 265), (900, 265)], label="UDP JSON", label_x=844, label_y=485),
            arrow([(1050, 350), (1050, 408)], label="WebSocket", label_x=1062, label_y=389),
            text(58, 668, "核心原则：摄像头采集、手势决策、网络转发与模型表现保持模块解耦，可分别调试和替换", size=15, weight=650, fill="#4E5964"),
        ]
    )
    write_svg(
        "handpilot_system_architecture.svg",
        1260,
        720,
        "HandPilot 系统架构",
        "从摄像头手部画面到 Live2D 动作、表情和追踪反馈的完整链路",
        body,
    )


def build_frame_pipeline() -> None:
    """
    @function:
        生成 Python 单帧处理流水线

    @returns:
        None

    @outputs:
        输出 handpilot_frame_pipeline.svg
        用于说明 main.py 每读取一帧画面后依次执行的处理步骤
    """
    body = "\n".join(
        [
            text(74, 168, "每帧循环", size=18, weight=750, fill="#176B51"),
            card(74, 194, 184, 94, "1 读取画面", ["Camera.read()", "翻转 / 图像增强"], palette="green", body_size=13, compact=True),
            card(287, 194, 184, 94, "2 检测手部", ["HandDetector.process()", "MediaPipe Hands"], palette="green", body_size=13, compact=True),
            card(500, 194, 184, 94, "3 提取关键点", ["find_positions()", "[id, x, y, z]"], palette="green", body_size=13, compact=True),
            card(713, 194, 184, 94, "4 遍历双手", ["hand_landmarks", "handedness"], palette="green", body_size=13, compact=True),
            arrow([(258, 241), (287, 241)]),
            arrow([(471, 241), (500, 241)]),
            arrow([(684, 241), (713, 241)]),
            arrow([(805, 288), (805, 328), (164, 328), (164, 367)]),
            text(74, 347, "单手识别与空间交互", size=18, weight=750, fill="#255A99"),
            card(74, 367, 184, 106, "5 手指状态", ["get_finger_state()", "五指伸展数组"], palette="blue", body_size=13, compact=True),
            card(287, 367, 184, 106, "6 静态分类", ["classify_gesture()", "手势规则匹配"], palette="blue", body_size=13, compact=True),
            card(500, 367, 184, 106, "7 多帧平滑", ["GestureSmoother", "7 帧窗口 / 4 票确认"], palette="blue", body_size=13, compact=True),
            card(713, 367, 184, 106, "8 空间与运动", ["hand_features.py", "hand_motion.py"], palette="purple", body_size=13, compact=True),
            card(926, 367, 246, 106, "9 决策优先级", ["动态运动 > 摸头 > 静态手势", "derive_live2d_command()"], palette="gold", body_size=13, compact=True),
            arrow([(258, 420), (287, 420)]),
            arrow([(471, 420), (500, 420)]),
            arrow([(684, 420), (713, 420)]),
            arrow([(897, 420), (926, 420)]),
            text(74, 541, "场景汇总与输出", size=18, weight=750, fill="#A94F1C"),
            card(74, 562, 238, 92, "10 双手场景命令", ["derive_scene_command()", "双掌触发 DOUBLE_CHEER"], palette="orange", body_size=13, compact=True),
            card(355, 562, 238, 92, "11 UDP 发送", ["CommandSender.send()", "变化立即发送 / 状态节流"], palette="orange", body_size=13, compact=True),
            card(636, 562, 238, 92, "12 本地仪表盘", ["render_dashboard()", "骨架、FPS 与手势卡片"], palette="slate", body_size=13, compact=True),
            card(917, 562, 255, 92, "13 下一帧", ["cv2.imshow()", "Esc 退出，否则继续循环"], palette="slate", body_size=13, compact=True),
            arrow([(1049, 473), (1049, 522), (193, 522), (193, 562)]),
            arrow([(312, 608), (355, 608)]),
            arrow([(593, 608), (636, 608)]),
            arrow([(874, 608), (917, 608)]),
            arrow([(1172, 608), (1204, 608), (1204, 155), (166, 155), (166, 194)], dashed=True),
            text(74, 700, "说明：Z 轴为 MediaPipe 相对深度，用于判断 PUSH_IN / PULL_OUT 等趋势，不等同于真实厘米距离", size=14, weight=650, fill="#667085"),
        ]
    )
    write_svg(
        "handpilot_frame_pipeline.svg",
        1260,
        744,
        "HandPilot 单帧处理流水线",
        "main.py 每读取一帧画面后，依次完成识别、稳定化、空间交互、发包与本地展示",
        body,
    )


def build_realtime_link() -> None:
    """
    @function:
        生成实时通信链路图

    @returns:
        None

    @outputs:
        输出 handpilot_realtime_link.svg
        用于说明 UDP、Node Bridge、WebSocket 和浏览器页面之间的数据传输关系
    """
    body = "\n".join(
        [
            card(62, 200, 214, 150, "Python Sender", ["main.py", "protocol.py", "sender.py", "序列化 gesture_command"], palette="green", body_size=13, compact=True),
            card(342, 200, 214, 150, "UDP 通道", ["127.0.0.1:5005", "低开销本机传输", "变化立即发送", "重复状态节流"], palette="orange", body_size=13, compact=True),
            card(622, 200, 214, 150, "Node Bridge", ["udp_to_ws.js", "接收 UDP JSON", "WebSocket 广播", "静态资源托管"], palette="blue", body_size=13, compact=True),
            card(902, 200, 292, 150, "Web Live2D", ["http://127.0.0.1:8765", "WebSocket /ws", "Haru Profile 解析命令", "动作 / 表情 / 追踪 / TTS"], palette="purple", body_size=13, compact=True),
            arrow([(276, 275), (342, 275)], label="JSON", label_x=294, label_y=261),
            arrow([(556, 275), (622, 275)], label="datagram", label_x=568, label_y=261),
            arrow([(836, 275), (902, 275)], label="WebSocket", label_x=845, label_y=261),
            card(
                62,
                422,
                514,
                166,
                "gesture_command 数据包",
                [
                    "version / type / source / timestamp",
                    "gesture / command / hand",
                    "hands[]：双手状态、中心坐标、Z 轴、尺度、区域与运动",
                    "浏览器既可消费离散命令，也可消费连续追踪参数",
                ],
                palette="rose",
                body_size=14,
            ),
            card(
                622,
                422,
                572,
                166,
                "调试与边界",
                [
                    "tools/udp_receiver_test.py 可单独验证 UDP 数据包",
                    "接收测试器与 Bridge 不可同时绑定 5005 端口",
                    "Web 页面 Local Test 可绕过摄像头，单独验证模型响应",
                    "三段链路可拆开排查：识别端、Bridge、浏览器端",
                ],
                palette="slate",
                body_size=14,
            ),
            text(62, 654, "推荐启动顺序：先启动 Node Bridge，再启动 Python main.py，最后访问浏览器页面", size=15, weight=700, fill="#4E5964"),
        ]
    )
    write_svg(
        "handpilot_realtime_link.svg",
        1260,
        704,
        "HandPilot 实时通信链路",
        "UDP 负责 Python 到 Bridge 的本机传输，WebSocket 负责 Bridge 到浏览器的实时推送",
        body,
    )


# =============================================================================
# Draw.io 可编辑源文件
# Draw.io 文件是一个 XML 文件，每个 diagram 节点对应一个可切换的页签
# =============================================================================

def drawio_style(palette: str, *, rounded: bool = True) -> str:
    """
    @function:
        根据配色名称生成 Draw.io 节点样式

    @params:
        palette (str): 使用 PALETTES 中的配色名称
        rounded (bool): 节点是否使用圆角

    @returns:
        str: Draw.io mxCell 节点使用的样式字符串
    """
    fill, stroke, strong = PALETTES[palette]
    rounded_value = "1" if rounded else "0"
    return (
        f"rounded={rounded_value};whiteSpace=wrap;html=1;arcSize=18;"
        f"fillColor={fill};strokeColor={stroke};fontColor={strong};"
        "fontSize=14;fontStyle=1;spacing=8;"
    )


def add_page(
    mxfile: ET.Element,
    name: str,
    width: int,
    height: int,
    nodes: list[tuple[str, str, int, int, int, int, str]],
    edges: list[tuple[str, str, str, str]],
) -> None:
    """
    @function:
        向 Draw.io 文件中增加一个可独立切换的页签

    @params:
        mxfile (ET.Element): Draw.io 文件的根节点
        name (str): 页签名称
        width/height (int): 画布尺寸
        nodes (list): 节点列表
            每个节点格式为：
            (节点ID, 显示内容, x, y, 宽度, 高度, 配色名称)
        edges (list): 连线列表
            每条连线格式为：
            (连线ID, 起点节点ID, 终点节点ID, 连线说明)

    @returns:
        None
    """
    diagram = ET.SubElement(mxfile, "diagram", {"id": name.lower().replace(" ", "-"), "name": name})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1280",
            "dy": "720",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(width),
            "pageHeight": str(height),
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for node_id, value, x, y, node_width, node_height, palette in nodes:
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node_id,
                "value": value,
                "style": drawio_style(palette),
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(x),
                "y": str(y),
                "width": str(node_width),
                "height": str(node_height),
                "as": "geometry",
            },
        )
    for edge_id, source, target, label in edges:
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": edge_id,
                "value": label,
                "style": (
                    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                    "jettySize=auto;html=1;endArrow=block;endFill=1;"
                    "strokeColor=#667085;fontColor=#4E5964;fontSize=12;"
                ),
                "edge": "1",
                "parent": "1",
                "source": source,
                "target": target,
            },
        )
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def build_drawio() -> None:
    """
    @function:
        生成包含三个页签的 Draw.io 可编辑源文件

    @returns:
        None

    @outputs:
        输出 handpilot_architecture.drawio
        页签 1：系统总体架构
        页签 2：Python 单帧处理流水线
        页签 3：UDP 与 WebSocket 实时通信链路
    """
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Electron",
            "modified": "2026-05-31T00:00:00.000Z",
            "agent": "HandPilot diagram generator",
            "version": "24.7.17",
            "type": "device",
        },
    )
    add_page(
        mxfile,
        "01 System Architecture",
        1400,
        900,
        [
            ("camera", "01 视觉采集&#xa;OpenCV Camera&#xa;MediaPipe Hands&#xa;21 点 + 相对 Z 深度", 40, 100, 220, 150, "green"),
            ("preview", "本地预览&#xa;骨架 / FPS / UDP / 双手卡片", 40, 340, 220, 100, "slate"),
            ("python", "02 Python HandPilot&#xa;识别、稳定化、空间语义与命令决策", 350, 80, 360, 100, "orange"),
            ("perception", "感知层&#xa;finger_state.py&#xa;gesture_classifier.py", 330, 240, 180, 100, "green"),
            ("smoother", "稳定层&#xa;gesture_smoother.py&#xa;7 帧窗口 / 4 票确认", 560, 240, 180, 100, "blue"),
            ("interaction", "交互层&#xa;hand_features.py&#xa;hand_motion.py", 330, 390, 180, 100, "purple"),
            ("sender", "输出层&#xa;command_mapper.py&#xa;protocol.py / sender.py", 560, 390, 180, 100, "gold"),
            ("bridge", "03 Node.js Bridge&#xa;UDP 5005 -&gt; WebSocket /ws&#xa;HTTP 8765", 840, 120, 240, 130, "blue"),
            ("web", "04 Web Live2D&#xa;动作 / 表情 / 追踪 / TTS&#xa;Local Test", 840, 360, 240, 130, "rose"),
        ],
        [
            ("a1", "camera", "python", "frame"),
            ("a2", "python", "perception", ""),
            ("a3", "perception", "smoother", ""),
            ("a4", "smoother", "interaction", ""),
            ("a5", "interaction", "sender", ""),
            ("a6", "sender", "bridge", "UDP JSON"),
            ("a7", "bridge", "web", "WebSocket"),
            ("a8", "camera", "preview", ""),
            ("a9", "sender", "preview", "state"),
        ],
    )
    add_page(
        mxfile,
        "02 Frame Pipeline",
        1700,
        900,
        [
            ("read", "1 读取画面&#xa;Camera.read()", 40, 80, 170, 80, "green"),
            ("detect", "2 检测手部&#xa;HandDetector.process()", 260, 80, 190, 80, "green"),
            ("position", "3 提取关键点&#xa;[id, x, y, z]", 500, 80, 190, 80, "green"),
            ("hands", "4 遍历双手", 740, 80, 170, 80, "green"),
            ("finger", "5 手指状态&#xa;get_finger_state()", 40, 260, 180, 80, "blue"),
            ("classify", "6 静态分类&#xa;classify_gesture()", 270, 260, 180, 80, "blue"),
            ("smooth", "7 多帧平滑&#xa;7 帧 / 4 票确认", 500, 260, 180, 80, "blue"),
            ("feature", "8 空间与运动&#xa;Z 轴 / 区域 / 趋势", 730, 260, 180, 80, "purple"),
            ("intent", "9 命令决策&#xa;动态运动 &gt; 摸头 &gt; 静态手势", 960, 260, 240, 80, "gold"),
            ("scene", "10 双手场景&#xa;derive_scene_command()", 40, 450, 210, 80, "orange"),
            ("send", "11 UDP 发送&#xa;CommandSender.send()", 300, 450, 210, 80, "orange"),
            ("dashboard", "12 本地仪表盘&#xa;render_dashboard()", 560, 450, 210, 80, "slate"),
            ("next", "13 下一帧&#xa;Esc 退出，否则继续", 820, 450, 210, 80, "slate"),
        ],
        [
            ("p1", "read", "detect", ""),
            ("p2", "detect", "position", ""),
            ("p3", "position", "hands", ""),
            ("p4", "hands", "finger", ""),
            ("p5", "finger", "classify", ""),
            ("p6", "classify", "smooth", ""),
            ("p7", "smooth", "feature", ""),
            ("p8", "feature", "intent", ""),
            ("p9", "intent", "scene", ""),
            ("p10", "scene", "send", ""),
            ("p11", "send", "dashboard", ""),
            ("p12", "dashboard", "next", ""),
            ("p13", "next", "read", "loop"),
        ],
    )
    add_page(
        mxfile,
        "03 Realtime Link",
        1400,
        900,
        [
            ("sender", "Python Sender&#xa;protocol.py / sender.py&#xa;gesture_command JSON", 40, 140, 220, 130, "green"),
            ("udp", "UDP 通道&#xa;127.0.0.1:5005&#xa;状态节流", 330, 140, 220, 130, "orange"),
            ("bridge", "Node Bridge&#xa;udp_to_ws.js&#xa;WebSocket 广播", 620, 140, 220, 130, "blue"),
            ("browser", "Web Live2D&#xa;127.0.0.1:8765&#xa;动作 / 表情 / 追踪 / TTS", 910, 140, 240, 130, "purple"),
            ("packet", "gesture_command 数据包&#xa;gesture / command / hand / hands[] / timestamp", 40, 380, 510, 100, "rose"),
            ("debug", "调试路径&#xa;UDP receiver 与 Bridge 不能同时绑定 5005&#xa;Local Test 可独立验证浏览器模型响应", 620, 380, 530, 100, "slate"),
        ],
        [
            ("r1", "sender", "udp", "JSON"),
            ("r2", "udp", "bridge", "datagram"),
            ("r3", "bridge", "browser", "WebSocket /ws"),
            ("r4", "sender", "packet", ""),
            ("r5", "bridge", "debug", ""),
        ],
    )
    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(
        OUTPUT_DIR / "handpilot_architecture.drawio",
        encoding="utf-8",
        xml_declaration=True,
    )


def main() -> None:
    """
    @function:
        依次生成三张 SVG 图表和一个三页 Draw.io 文件

    @returns:
        None
    """
    build_system_architecture()
    build_frame_pipeline()
    build_realtime_link()
    build_drawio()
    print("HandPilot diagrams generated")


if __name__ == "__main__":
    main()
