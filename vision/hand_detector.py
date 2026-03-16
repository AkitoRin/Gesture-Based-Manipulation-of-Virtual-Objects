import cv2 as cv  # 导入OpenCV
import mediapipe as mp  # 导入 MediaPipe
from typing import Any  # Any 忽略当前的返回类型


class HandDetector:
    def __init__(
            self,  # 当前这个对象自己（this）
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
    ):
        # 保存 MediaPipe 的手部模块入口
        self.mp_hands = mp.solutions.hands
        # 保存 MediaPipe 的绘图工具
        self.mp_draw = mp.solutions.drawing_utils
        # 创建手部检测器
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.results = None

    def process(self, frame):
        """
        处理并返回图像帧（手骨架）
        :param frame: 当前图像帧
        :return: 处理后的图像帧
        """
        rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        # 用手部检测器处理 RGB 图像帧并保存返回的信息
        self.results: Any = self.hands.process(rgb_frame)
        # 从保存的信息中获取 multi_hand_landmarks（手的关键点信息 <列表>）
        landmarks_list = getattr(self.results, "multi_hand_landmarks", None)

        if landmarks_list:
            for hand_landmarks in landmarks_list:  # 类似增强 for 循环
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

        return frame

    def find_positions(self, frame, draw=True):
        """
        提取所有手的21个关键点坐标
        :param frame: 当前图像帧
        :param draw: 是否绘制关键点编号
        :return: [[id, x, y], ...]
        """
        all_hands = []

        landmarks_list = getattr(self.results, "multi_hand_landmarks", None)
        if not landmarks_list:
            return all_hands

        # 图像数组的形状（高度，宽度，通道数）
        h, w, _ = frame.shape
        for hand_landmarks in landmarks_list:
            lm_list = []

            # 遍历取出手的关键点（编号idx，内容lm）
            for idx, lm in enumerate(hand_landmarks.landmark):
                # 归一化坐标 ——> 像素坐标
                x = int(lm.x * w)
                y = int(lm.y * h)
                lm_list.append([idx, x, y])

                if draw:
                    # 在图像帧上绘制文本
                    cv.putText(
                        frame,
                        str(idx),  # 绘制的文本内容（这里是编号）
                        (x + 5, y - 5),  # 文本位置（偏移关键点）
                        cv.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1
                    )

            all_hands.append(lm_list)

        return all_hands
