# =============================================================================
# 文件：main.py
# 职责：【程序总入口 - 主循环调度器】
#       HandPilot 的启动入口和主循环
#       它不自己处理任何具体逻辑，而是把所有模块"串联"起来，按正确的顺序调用各个模块，形成一个完整的处理流水线。
#
# 整体数据流（每一帧图像走过的路）：
#
#   摄像头读取一帧图像
#       ↓
#   MediaPipe 检测手部、画骨架、提取 21 个关键点像素坐标和 z 深度
#       ↓
#   对每只手：
#     finger_state → 判断五指伸屈状态 [0/1, 0/1, 0/1, 0/1, 0/1]
#       ↓
#     gesture_classifier → 匹配手势名称 "FIST" / "V_SIGN" / ...
#       ↓
#     gesture_smoother → 多帧投票过滤抖动，输出稳定手势名称
#       ↓
#     command_mapper → 把手势名映射为 Live2D 控制命令 "CMD_WAVE" / "CMD_IDLE" / ...
#       ↓
#     hand_motion → 结合最近几帧位置判断挥手、靠近、远离等动态意图
#       ↓
#     live2d_interaction → 结合手部位置和动态意图生成摸头、双手应援等互动命令
#       ↓
#   （如果通信已启用）sender.send() → UDP 发给接收端
#       ↓
#   在画面上叠加显示手势名、命令名、FPS 等信息
#       ↓
#   将画面适配到当前窗口大小（保持比例，加边框）
#       ↓
#   显示最终画面，等待下一帧
#
# 按 ESC 键退出程序，释放所有资源
# =============================================================================

# Python 日志库，用于输出运行信息
import logging   
# Python 标准库，用于控制 FPS 显示文字的刷新节奏
import time
# OpenCV 库，用于窗口管理和文字绘制   
import cv2 as cv    
# 从各个模块导入需要用的类和函数
from vision.camera           import Camera
from vision.hand_detector    import HandDetector
from utils.fps               import FPSCounter
from utils.display           import fit_frame_to_window
from utils.dashboard          import render_dashboard
from utils.image_enhance      import enhance_preview_frame
from gesture.finger_state    import get_finger_state
from gesture.gesture_classifier import classify_gesture
from gesture.gesture_smoother   import GestureSmoother
from gesture.command_mapper     import map_gesture_to_command
from gesture.hand_features      import get_hand_features, get_interaction_zone
from gesture.hand_motion        import HandMotionTracker
from gesture.live2d_interaction import derive_live2d_command, derive_scene_command
from communication.sender       import CommandSender
# 从配置文件导入所需参数
from config.settings import (
    WINDOW_NAME, WINDOW_INI_WIDTH, WINDOW_INI_HEIGHT, WINDOW_BG_COLOR,
    DISPLAY_FIT_MODE, ENHANCE_PREVIEW_IMAGE,
    HAND_MAX_NUM_HANDS,
    SHOW_FPS, FPS_TEXT_PREFIX, FPS_TEXT_POS,
    FPS_FONT, FPS_FONT_SCALE, FPS_COLOR, FPS_THICKNESS,
    FPS_SMOOTH_ALPHA, FPS_DISPLAY_UPDATE_INTERVAL,
    SHOW_DASHBOARD,
    SMOOTHER_WINDOW_SIZE, SMOOTHER_CONFIRM_THRESHOLD,
    COMMUNICATION_ENABLED, COMM_HOST, COMM_PORT,
    COMM_MIN_INTERVAL, COMM_REPEAT_INTERVAL,
)

# 配置日志系统：
#   level=DEBUG     → 输出所有级别的日志（DEBUG/INFO/WARNING/ERROR）
#   format          → 日志格式：时间 [级别] 模块名 | 消息内容
#   datefmt         → 时间显示格式：时:分:秒
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
# 获取这个文件专属的日志记录器，输出日志时会显示 "HandPilot" 作为来源名称
log = logging.getLogger("HandPilot")


# MediaPipe 返回的左右手标签 → 显示在屏幕上的简短标签
# 注意：因为画面已镜像，MediaPipe 的 "Left" 实际上是用户的右手，显示为 "R"
_HAND_LABEL = {"Left": "R", "Right": "L", "Unknown": "?"}

# 需要在日志里打印的特殊关键点（手腕 + 五指指尖）
# 格式：{关键点编号: 关键点名称}
_TIP_IDS = {0: "Wrist", 4: "Thumb", 8: "Index", 12: "Middle", 16: "Ring", 20: "Pinky"}


def _log_hand_detail(idx, handedness, hand, fingers, raw_gesture, stable_gesture):
    """
    @function:
        当稳定手势发生切换时，在日志里打印完整的调试信息。
    （以下划线开头的函数表示这是"私有函数"，只在本文件内部使用）

    @params:
        idx (int):            手的编号（0=第一只手，1=第二只手）
        handedness (str):     MediaPipe 的左右手标签 "Left"/"Right"/"Unknown"
        hand (list):          这只手的 21 个关键点 [[id,x,y], ...]
        fingers (list):       五指状态 [0/1, 0/1, 0/1, 0/1, 0/1]
        raw_gesture (str):    这一帧的原始手势名（未平滑）
        stable_gesture (str): 平滑后的稳定手势名（对外输出的）
    """
    label = _HAND_LABEL.get(handedness, "?")

    # 取出几个关键点的坐标，格式化成易读的字符串，方便对照画面调试
    tips = {name: (hand[i][1], hand[i][2]) for i, name in _TIP_IDS.items()}
    tips_str = "  ".join(f"{k}({v[0]},{v[1]})" for k, v in tips.items())

    log.info(
        f"手{idx}[{label}]  fingers={fingers}  raw={raw_gesture} → stable={stable_gesture}\n"
        f"          关键点: {tips_str}"
    )


def _draw_hand_info(frame, hand_idx, handedness, gesture, command):
    """
    在图像画面上叠加显示这只手的识别结果（手势名 + 命令名）

    @params:
        frame (numpy.ndarray): 要绘制文字的图像帧（会被直接修改）
        hand_idx (int):        手的编号（0或1），用于决定文字显示的纵向位置
        handedness (str):      左右手标签
        gesture (str):         稳定手势名称，例如 "FIST"
        command (str):         对应命令，例如 "CMD_IDLE"
    """
    label = _HAND_LABEL.get(handedness, "?")

    # 根据手的编号计算显示位置，防止多只手的信息重叠
    # 第 0 只手显示在 y=70，第 1 只手显示在 y=130（间隔 60 像素）
    y_base = 70 + hand_idx * 60

    # 在画面上绘制手势名称（青色文字）
    # cv.putText(图像, 文字, 左下角位置, 字体, 大小, 颜色BGR, 线宽)
    cv.putText(frame, f"[{label}] {gesture}",
               (20, y_base), cv.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)

    # 在手势名称下方绘制命令名称（橙色文字，小一点）
    cv.putText(frame, f"CMD: {command}",
               (20, y_base + 25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 1)


def main():
    """
    HandPilot 主函数，程序的入口
    完成初始化后进入主循环，每迭代一次处理一帧图像，直到按 ESC 退出。
    """

    # -----------------------------------------------------------------------
    # 初始化阶段（启动各个模块）
    # -----------------------------------------------------------------------

    log.info("=== HandPilot 启动 ===")
    log.info(f"平滑器: window={SMOOTHER_WINDOW_SIZE}, threshold={SMOOTHER_CONFIRM_THRESHOLD}")
    log.info(
        f"通信: {'启用 → ' + COMM_HOST + ':' + str(COMM_PORT) if COMMUNICATION_ENABLED else '禁用 (COMMUNICATION_ENABLED=False)'}"
    )

    # 打开摄像头（如果失败会直接报错退出）
    camera = Camera()
    log.info("摄像头已打开")

    # 初始化 MediaPipe 手部检测器
    detector = HandDetector()
    log.info("MediaPipe 手部检测器已初始化")
    log.info(f"手部检测: max_num_hands={HAND_MAX_NUM_HANDS}")

    # 初始化 FPS 计数器
    fps_counter = FPSCounter(FPS_SMOOTH_ALPHA)
    displayed_fps = 0
    last_fps_display_time = 0.0

    # 为每只手创建一个独立的手势平滑器（数量由 HAND_MAX_NUM_HANDS 配置决定）
    # 每只手都需要各自独立平滑，互不干扰
    smoothers = [
        GestureSmoother(SMOOTHER_WINDOW_SIZE, SMOOTHER_CONFIRM_THRESHOLD)
        for _ in range(HAND_MAX_NUM_HANDS)
    ]

    # 为每只手创建一个运动追踪器，用于判断横向挥动、上下移动、靠近/远离镜头
    motion_trackers = [
        HandMotionTracker()
        for _ in range(HAND_MAX_NUM_HANDS)
    ]

    # 如果通信功能已启用，创建 UDP 发送器；否则 sender 为 None（不发送）
    sender = CommandSender(COMM_HOST, COMM_PORT, COMM_MIN_INTERVAL, COMM_REPEAT_INTERVAL) \
        if COMMUNICATION_ENABLED else None

    # 记录每只手上一帧的稳定手势，用于判断手势是否发生了变化（变化时才打印详细日志）
    prev_gestures = [""] * HAND_MAX_NUM_HANDS

    # 创建显示窗口（WINDOW_NORMAL 允许用户手动拖拽改变窗口大小）
    cv.namedWindow(WINDOW_NAME, cv.WINDOW_NORMAL)
    cv.resizeWindow(WINDOW_NAME, WINDOW_INI_WIDTH, WINDOW_INI_HEIGHT)
    log.info("窗口已创建 | 按 ESC 退出")
    log.info("---------- 等待手势输入 ----------")

    # -----------------------------------------------------------------------
    # 主循环（每次循环 = 处理一帧图像）
    # -----------------------------------------------------------------------

    while True:

        # --- 步骤1：从摄像头读取一帧图像 ---
        frame = camera.read()
        # frame 现在是一张 BGR 图像（NumPy 数组），如果设置了镜像则已翻转

        # --- 步骤2：手部检测 + 画骨架 ---
        # detector.process() 做了两件事：
        #   1. 把图像送给 MediaPipe 检测，把结果保存在 detector.results 里
        #   2. 在图像上画出检测到的手部骨架（关键点 + 连线）
        # 返回的 frame 已经带有骨架画面
        frame = detector.process(frame)

        # --- 步骤3：提取所有手的关键点坐标 ---
        # all_hands:      [[[id,x,y,z],...×21], ...]  每只手21个关键点，z 为 MediaPipe 相对深度
        # all_handedness: ["Left"/"Right"/..., ...]  每只手的左右手标签
        all_hands, all_handedness = detector.find_positions(frame)
        frame_height, frame_width = frame.shape[:2]

        # 初始化本帧的"主要输出"变量（当没有检测到手时使用这些默认值）
        primary_gesture    = "UNKNOWN"
        primary_command    = "CMD_NONE"
        primary_handedness = "Unknown"
        hand_states = []

        # --- 步骤4：逐只手处理（手势识别流水线）---
        if all_hands:
            # 遍历检测到的每只手（idx=0 是第一只手，idx=1 是第二只手）
            for idx, hand in enumerate(all_hands):

                # 获取这只手的左右手标签（如果索引超出范围，用 "Unknown"）
                handedness = all_handedness[idx] if idx < len(all_handedness) else "Unknown"

                # 获取这只手对应的平滑器（如果检测结果超出配置上限，复用最后一个平滑器）
                smoother = smoothers[idx] if idx < len(smoothers) else smoothers[-1]

                # 步骤4a：判断五指状态
                # 输入：21个关键点 + 左右手标签
                # 输出：[拇指, 食指, 中指, 无名指, 小指]，各位 1=伸出 0=弯曲
                fingers = get_finger_state(hand, handedness)

                # 步骤4b：分类手势（单帧原始结果，可能抖动）
                # 输入：五指状态 + 原始关键点（用于判断拇指朝向）
                # 输出：手势名称字符串，例如 "FIST"
                raw_gesture = classify_gesture(fingers, hand)

                # 步骤4c：平滑去抖动（多帧投票）
                # 输入：这帧的原始手势名
                # 输出：稳定的手势名（可能和这帧的原始结果不同）
                stable_gesture = smoother.update(raw_gesture)

                # 步骤4d：映射控制命令
                # 输入：稳定手势名
                # 输出：控制命令字符串，例如 "CMD_WAVE"
                base_command = map_gesture_to_command(stable_gesture)
                label = _HAND_LABEL.get(handedness, "?")

                # 步骤4e：提取手部空间特征
                # Live2D 端不仅需要知道"是什么手势"，还需要知道"手大概在哪里"
                # 例如张开的手掌出现在头部区域时，会被解释为摸头互动
                features = get_hand_features(hand, frame_width, frame_height)
                interaction_zone = get_interaction_zone(features)
                motion_tracker = motion_trackers[idx] if idx < len(motion_trackers) else motion_trackers[-1]
                motion = motion_tracker.update(features)
                command = derive_live2d_command(
                    stable_gesture,
                    base_command,
                    interaction_zone,
                    motion,
                )

                # 记录这只手的状态。这个列表既用于右侧面板显示，也会被放进 UDP 数据包。
                hand_states.append({
                    "index": idx,
                    "hand": handedness,
                    "label": label,
                    "raw_gesture": raw_gesture,
                    "gesture": stable_gesture,
                    "base_command": base_command,
                    "command": command,
                    "fingers": fingers,
                    "zone": interaction_zone,
                    "motion": motion,
                    "features": features,
                })

                # 步骤4f：只在手势切换时打印详细日志（避免每帧都刷屏）
                prev_gesture = prev_gestures[idx] if idx < len(prev_gestures) else prev_gestures[-1]

                if stable_gesture != prev_gesture:
                    _log_hand_detail(idx, handedness, hand, fingers, raw_gesture, stable_gesture)
                    if idx < len(prev_gestures):
                        prev_gestures[idx] = stable_gesture  # 更新记录
                    else:
                        prev_gestures[-1] = stable_gesture

                # 步骤4g：显示策略
                # 右侧调试面板开启时，手势/命令文字会交给外侧面板显示，
                # 避免直接画在摄像头主体区域上。
                # 如果关闭面板，则回退到直接画在视频画面上。
                if not SHOW_DASHBOARD:
                    _draw_hand_info(frame, idx, handedness, stable_gesture, command)

                # 步骤4h：第一只手（idx=0）作为"主要手"，其结果用于发送
                if idx == 0:
                    primary_gesture    = stable_gesture
                    primary_command    = command
                    primary_handedness = handedness

            # 双手组合命令优先级高于单手命令，用于 Live2D 的全局舞台回应
            scene_command = derive_scene_command(hand_states)
            if scene_command is not None:
                primary_gesture = "DOUBLE_OPEN_HAND"
                primary_command = scene_command
                primary_handedness = "Both"

        else:
            # 当前帧没有检测到任何手
            # 重置所有平滑器状态（清空历史数据），防止下次手出现时残留旧数据
            for i, s in enumerate(smoothers):
                if prev_gestures[i]:  # 如果之前有手势记录，说明手刚离开
                    log.debug(f"手{i} 离开画面，平滑器重置")
                    prev_gestures[i] = ""
                s.reset()
                if i < len(motion_trackers):
                    motion_trackers[i].reset()

        # --- 步骤5：发送命令（如果通信已启用）---
        # sender 为 None 时（COMMUNICATION_ENABLED=False），跳过不发送
        if sender is not None:
            sender.send(primary_gesture, primary_command, primary_handedness, hand_states)

        # --- 步骤6：绘制 FPS ---
        fps = fps_counter.update()  # 更新并获取当前平滑帧率
        if SHOW_FPS:
            now = time.time()
            # FPS 每帧都计算，但屏幕上的数字按固定间隔刷新，避免数字跳动太快
            if now - last_fps_display_time >= FPS_DISPLAY_UPDATE_INTERVAL:
                displayed_fps = int(fps)
                last_fps_display_time = now

            if not SHOW_DASHBOARD:
                cv.putText(frame, f"{FPS_TEXT_PREFIX}{displayed_fps}",
                           FPS_TEXT_POS, FPS_FONT, FPS_FONT_SCALE, FPS_COLOR, FPS_THICKNESS)

        # --- 步骤7：显示通信状态（如果通信已启用）---
        if COMMUNICATION_ENABLED and not SHOW_DASHBOARD:
            w = frame.shape[1]  # 图像宽度（用于把文字放在右上角）
            # OpenCV 默认字体不支持 Unicode 箭头，所以这里使用 ASCII 的 "->"。
            cv.putText(frame, f"UDP -> {COMM_HOST}:{COMM_PORT}",
                       (w - 260, 25), cv.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 255), 1)

        if ENHANCE_PREVIEW_IMAGE:
            frame = enhance_preview_frame(frame)

        if SHOW_DASHBOARD:
            frame = render_dashboard(
                frame,
                displayed_fps,
                hand_states,
                COMMUNICATION_ENABLED,
                COMM_HOST,
                COMM_PORT,
            )

        # --- 步骤8：把图像按比例适配到当前窗口大小 ---
        # cv.getWindowImageRect() 获取当前窗口的实际大小（用户可能已拖拽改变了窗口大小）
        # 返回 (x, y, width, height)，我们只需要 width 和 height
        _, _, width, height = cv.getWindowImageRect(WINDOW_NAME)

        # 如果窗口有有效大小（width>0 避免窗口最小化时的异常）
        if width > 0 and height > 0:
            # 外置调试面板是信息区域，不能被 cover 模式裁掉；
            # 所以面板开启时强制完整显示整张合成画面。
            fit_mode = "contain" if SHOW_DASHBOARD else DISPLAY_FIT_MODE
            display_frame = fit_frame_to_window(
                frame,
                width,
                height,
                WINDOW_BG_COLOR,
                fit_mode,
            )
        else:
            display_frame = frame  # 窗口大小异常时直接显示原图

        # --- 步骤9：在窗口中显示最终画面 ---
        cv.imshow(WINDOW_NAME, display_frame)

        # --- 步骤10：检测键盘输入 ---
        # cv.waitKey(1) = 等待最多 1 毫秒的键盘输入，返回按键的 ASCII 码
        # 没有按键时返回 -1；按 ESC 时返回 27
        # 这行也是让画面实际刷新的关键调用（没有 waitKey，窗口不会更新）
        if cv.waitKey(1) == 27:  # 27 = ESC 键的 ASCII 码
            break  # 跳出主循环，进入退出流程

    # -----------------------------------------------------------------------
    # 退出阶段（释放所有资源）
    # -----------------------------------------------------------------------

    log.info("=== HandPilot 退出 ===")

    if sender is not None:
        sender.close()    # 关闭 UDP socket，释放网络资源
    detector.close()       # 释放 MediaPipe Hands 内部资源
    camera.release()      # 释放摄像头，让其他程序可以使用
    cv.destroyAllWindows()  # 关闭所有 OpenCV 窗口


if __name__ == "__main__":
    """
    当这个文件被直接运行（而不是被其他文件 import）时，才执行 main()
    如果其他文件 import main.py，这行以下的代码不会执行
    """
    main()
