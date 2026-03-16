# =========================
# 摄像头参数 Camera (IN camera.py)
# =========================
CAMERA_INDEX = 0          # 默认摄像头编号，0 表示第一个摄像头
FLIP_IMAGE = True         # 是否左右翻转画面


# =========================
# 窗口参数 Window (IN main.py)
# =========================
WINDOW_NAME = "Camera Preview"  # 窗口标题

# 窗口初始大小
WINDOW_INI_WIDTH = 960
WINDOW_INI_HEIGHT = 720

# 窗口背景色（当图像按比例缩放后，四周留白区域的颜色）
WINDOW_BG_COLOR = (30, 30, 30)


# =========================
# 手部检测参数 HandDetector (IN hand_detector.py)
# =========================
# 是否把输入当成“静态图片模式” - False 表示视频流模式;True 表示静态图片模式
HAND_STATIC_IMAGE_MODE = False

HAND_MAX_NUM_HANDS = 2                  # 最多检测的手的数量
HAND_MIN_DETECTION_CONFIDENCE = 0.7     # 最小检测置信度
HAND_MIN_TRACKING_CONFIDENCE = 0.7      # 最小跟踪置信度


# =========================
# FPS 显示参数
# =========================
SHOW_FPS = True                         # 是否在画面左上角显示 FPS

FPS_TEXT_PREFIX = "FPS: "               # FPS 文字前缀
FPS_TEXT_POS = (20, 35)                 # FPS 文本左下角位置 (x, y)
FPS_FONT = 0                            # 对应 cv.FONT_HERSHEY_SIMPLEX
FPS_FONT_SCALE = 0.8                    # 字体大小
FPS_COLOR = (0, 255, 0)                 # 字体颜色（绿色，BGR）
FPS_THICKNESS = 2                       # 字体线宽

FPS_SMOOTH_ALPHA = 0.9                  # FPS 平滑系数，越大越稳定，越小越灵敏
