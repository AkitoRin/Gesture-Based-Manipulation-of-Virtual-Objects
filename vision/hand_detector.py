# =============================================================================
# 文件：vision/hand_detector.py
# 职责：【感知层 - 手部检测与关键点提取】
#       使用 Google 的 MediaPipe Hands 模型，在图像中找到手，
#       画出手部骨架，并提取每只手的 21 个关键点的像素坐标和 z 深度
# 
# 说明：
#   关键点编号（每只手 21 个点）：
#   0        = 手腕
#   1,2,3,4  = 拇指
#   5,6,7,8  = 食指
#   9,10,11,12 = 中指
#   13,14,15,16 = 无名指
#   17,18,19,20 = 小指
#
#   编号顺序：从根部到指尖
#   - 指尖：4（拇指）、8（食指）、12（中指）、16（无名指）、20（小指）
#   - 指根关节 PIP：1（拇指）、6（食指）、10（中指）、14（无名指）、18（小指）
# =============================================================================

# OpenCV库，用于图像操作和绘制文字
import cv2 as cv          
# Google MediaPipe，提供手部检测 AI 模型 
import mediapipe as mp     
# Python 类型提示，Any 表示"任意类型"
from typing import Any     
# 从配置文件导入所需参数
from config.settings import (
    HAND_STATIC_IMAGE_MODE,
    HAND_MAX_NUM_HANDS,
    HAND_MIN_DETECTION_CONFIDENCE,
    HAND_MIN_TRACKING_CONFIDENCE,
)


class HandDetector:
    """
    手部检测器类
    封装了 MediaPipe Hands 的初始化、检测、骨架绘制和关键点提取功能
    """

    def __init__(
            self,
            static_image_mode=HAND_STATIC_IMAGE_MODE,
            max_num_hands=HAND_MAX_NUM_HANDS,
            min_detection_confidence=HAND_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_MIN_TRACKING_CONFIDENCE
    ):
        """
        @function:
            初始化手部检测器

        @params：
            static_image_mode (bool):
                False = 视频流模式（推荐用于实时摄像头）
                        MediaPipe 会在检测到手后切换为"跟踪模式"，速度更快
                True  = 静态图片模式
                        每帧都重新检测，适合处理单张图片，但实时性差
            max_num_hands (int): 最多同时检测几只手
            min_detection_confidence (float): 检测置信度阈值 (0~1)
                MediaPipe 认为"这里有手"的信心要高于这个值才会输出结果
            min_tracking_confidence (float): 跟踪置信度阈值 (0~1)
                视频流模式下，跟踪置信度低于这个值时会重新触发检测
        """
        # mp.solutions.hands = MediaPipe 的"手部模块"，后续用它创建检测器和获取连接信息
        self.mp_hands = mp.solutions.hands

        # mp.solutions.drawing_utils = MediaPipe 的"绘图工具"，用来在图像上画骨架线
        self.mp_draw = mp.solutions.drawing_utils

        # 创建手部检测器（这个对象会加载 AI 模型到内存）
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # results = None，用来暂存每帧的检测结果
        # process() 函数会把新结果存在这里，find_positions() 再从这里读取
        self.results = None

    def process(self, frame):
        """
        @function:
            对图像帧进行手部检测，并在原图上绘制手部骨架

        工作流程：
            1. 把图像从 OpenCV 默认的 BGR 转成 MediaPipe 需求的 RGB
            2. 把 RGB 图像送给 MediaPipe Hands 检测
            3. 检测结果保存到 self.results 供后续使用
            4. 如果检测到手，在图像上画出骨架（关键点 + 连线）
            5. 返回画好骨架的图像

        @params:
            frame (numpy.ndarray): 从摄像头读取的原始图像（BGR格式）

        @returns:
            frame (numpy.ndarray): 在上面画了手部骨架的图像（BGR格式）
                如果没有检测到手，图像不会有变化，原样返回
        """
        # MediaPipe 要求输入 RGB 格式，但 OpenCV 读取的是 BGR 格式，需要转换
        # cv.cvtColor(图像, 转换方式) = 颜色空间转换
        # cv.COLOR_BGR2RGB = 把 BGR 转成 RGB（就是把 R 和 B 两个通道顺序对调）
        rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        # 把 RGB 图像送进 MediaPipe 检测器，得到检测结果（结果中包含：所有手的关键点坐标、左右手标签等信息）
        self.results: Any = self.hands.process(rgb_frame)

        # 从检测结果里取出"所有手的关键点信息"
        # getattr(对象, 属性名, 默认值) = 安全地读取属性，如果属性不存在就返回默认值 None
        # multi_hand_landmarks = 一个列表，每个元素代表一只手的 21 个关键点
        # 如果没检测到手，multi_hand_landmarks 会是 None，所以要安全读取
        landmarks_list = getattr(self.results, "multi_hand_landmarks", None)

        # 如果检测到了手（landmarks_list 不为 None）
        if landmarks_list:
            # 遍历每只手的关键点，给每只手都画上骨架
            for hand_landmarks in landmarks_list:
                self.mp_draw.draw_landmarks(
                    frame,                           # 在这张图上画
                    hand_landmarks,                  # 这只手的 21 个关键点数据
                    self.mp_hands.HAND_CONNECTIONS   # 关键点之间的连线定义（哪两个点之间画线）
                )

        return frame

    def find_positions(self, frame, draw=False):
        """
        @function:
            从上一次 process() 的结果中，提取所有手的关键点像素坐标和左右手标签

        坐标系说明：
            MediaPipe 原始关键点坐标是"归一化坐标"（范围 0~1）
            表示该点在图像中的比例位置（x=0.5 就是水平正中间）
            这个函数把它转换成"像素坐标"（整数，单位像素）
            例如 x=320 表示距离图像左边界 320 个像素
            lm.z 是 MediaPipe 给出的相对深度，通常越小表示越靠近摄像头

        @params:
            frame (numpy.ndarray): 当前图像帧（用来获取图像的宽高，以便坐标转换）
            draw (bool): 是否在图像上显示每个关键点的编号（0~20）
                True  = 在每个关键点旁边画上数字编号，适合调试时看清楚哪个点是哪个
                False = 不画编号（默认），画面更干净

        @returns:
            (all_hands, all_handedness)，这是一个元组，包含两个列表：

            all_hands (list): 所有手的关键点数据，结构如下：
                [
                    [  # 第 0 只手
                        [0, x0, y0, z0],   # 第 0 个关键点：[编号, x像素坐标, y像素坐标, z相对深度]
                        [1, x1, y1],
                        ...
                        [20, x20, y20]
                    ],
                    [  # 第 1 只手（如果有）
                        [0, x0, y0],
                        ...
                    ]
                ]
                如果没有检测到手，返回空列表 []

            all_handedness (list): 对应每只手的左右手标签，例如 ["Left", "Right"]
                注意：这里的 "Left"/"Right" 是 MediaPipe 从摄像头角度看的判断
                因为画面做了镜像翻转，MediaPipe 说 "Left" 实际上是用户的右手！
        """
        all_hands = []       # 存放所有手的关键点列表
        all_handedness = []  # 存放所有手的左右手标签

        # 取出这一帧的检测结果（process() 已经把结果保存在 self.results 里了）
        landmarks_list  = getattr(self.results, "multi_hand_landmarks", None)
        handedness_list = getattr(self.results, "multi_handedness", None)

        # 如果没有检测到手，直接返回两个空列表
        if not landmarks_list:
            return all_hands, all_handedness

        # 获取图像的高度 h 和宽度 w（用于把归一化坐标转换成像素坐标）
        # frame.shape 返回 (高, 宽, 通道数)，所以 h=shape[0], w=shape[1]；下划线 _ 表示"我不需要第三个值（通道数 3）"
        h, w, _ = frame.shape

        # 遍历每只检测到的手（i = 手的编号：0, 1, ...）
        for i, hand_landmarks in enumerate(landmarks_list):
            lm_list = []  # 存放这只手的 21 个关键点

            # 遍历这只手的每个关键点（共 21 个，idx = 0~20）
            for idx, lm in enumerate(hand_landmarks.landmark):
                # lm.x 和 lm.y 是归一化坐标（0~1 之间的浮点数）
                # lm.z 是相对深度值，后续会用于 Live2D 的头眼追踪和前后运动判断
                # 乘以图像宽度/高度，再取整，就得到了像素坐标（整数）
                # 例如：lm.x=0.5, w=640  →  x = int(0.5 * 640) = 320
                x = int(lm.x * w)
                y = int(lm.y * h)
                z = round(lm.z, 5)

                # 把 [编号, x坐标, y坐标, z深度] 加入这只手的列表
                # 旧代码只读取 [1] 和 [2]，所以增加 z 不会破坏原有手势判断
                lm_list.append([idx, x, y, z])

                # 如果需要在图像上显示关键点编号（调试用）
                if draw:
                    cv.putText(frame, str(idx), (x + 5, y - 5),
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            all_hands.append(lm_list)  # 把这只手的 21 个关键点加入总列表

            # 获取这只手的左右手标签（"Left" 或 "Right"）
            if handedness_list and i < len(handedness_list):
                # classification[0].label = 取第一个分类结果的标签字符串
                label = handedness_list[i].classification[0].label
            else:
                label = "Unknown"
            all_handedness.append(label)

        return all_hands, all_handedness

    def close(self):
        """
        @function:
            释放 MediaPipe Hands 检测器内部资源
        """
        self.hands.close()
