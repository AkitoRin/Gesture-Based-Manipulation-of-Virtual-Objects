import cv2 as cv
from vision.camera import Camera
from vision.hand_detector import HandDetector
from utils.fps import FPSCounter
from utils.display import fit_frame_to_window
from config.settings import (
    WINDOW_NAME, WINDOW_INI_WIDTH, WINDOW_INI_HEIGHT, WINDOW_BG_COLOR,
    SHOW_FPS, FPS_TEXT_PREFIX, FPS_TEXT_POS,
    FPS_FONT, FPS_FONT_SCALE, FPS_COLOR, FPS_THICKNESS,
    FPS_SMOOTH_ALPHA
)
from gesture.finger_state import get_finger_state
from gesture.gesture_classifier import classify_gesture


def main():
    camera = Camera()
    detector = HandDetector()
    fps_counter = FPSCounter(FPS_SMOOTH_ALPHA)

    # 创建窗口模式并初始化
    cv.namedWindow(WINDOW_NAME, cv.WINDOW_NORMAL)  # 该窗口允许用户手动调整窗口大小
    cv.resizeWindow(WINDOW_NAME, WINDOW_INI_WIDTH, WINDOW_INI_HEIGHT)
    while True:  # 循环读取图像帧并刷新 ——> 视频流
        frame = camera.read()
        frame = detector.process(frame)

        all_hands = detector.find_positions(frame)
        if all_hands:
            hand = all_hands[0]  # 先只处理第一只手

            fingers = get_finger_state(hand)
            gesture_name = classify_gesture(fingers)

            cv.putText(
                frame,
                gesture_name,
                (20, 70),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

        # 实时显示FPS
        fps = fps_counter.update()
        if SHOW_FPS:
            cv.putText(frame,
                       f"{FPS_TEXT_PREFIX}{int(fps)}",
                       FPS_TEXT_POS,
                       FPS_FONT,
                       FPS_FONT_SCALE,
                       FPS_COLOR,
                       FPS_THICKNESS)

        # 获取当前窗口位置和大小
        x, y, width, height = cv.getWindowImageRect(WINDOW_NAME)
        if width > 0 and height > 0:
            display_frame = fit_frame_to_window(frame, width, height, WINDOW_BG_COLOR)
        else:
            display_frame = frame

        # 显示画面
        cv.imshow(WINDOW_NAME, display_frame)

        # 刷新窗口（1ms）并等待键盘输入，按 ESC 退出
        key = cv.waitKey(1)
        if key == 27:
            break

    camera.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
