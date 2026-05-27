# =============================================================================
# 文件：vision/camera.py
# 职责：【输入层 - 摄像头封装】
#       把 OpenCV 的摄像头操作包装成一个 Camera 类
#       负责打开摄像头、读取图像帧、释放摄像头资源等
# =============================================================================

# OpenCV 库，用于摄像头操作和图像处理
import cv2 as cv                          
# 从配置文件导入所需参数
from config.settings import (
    CAMERA_INDEX,
    FLIP_IMAGE,
    CAMERA_FRAME_WIDTH,
    CAMERA_FRAME_HEIGHT,
)  

class Camera:
    """
    摄像头封装类
    创建时自动打开摄像头，提供读取帧和释放资源的方法
    """

    def __init__(
            self,
            camera_index=CAMERA_INDEX,
            flip=FLIP_IMAGE,
            frame_width=CAMERA_FRAME_WIDTH,
            frame_height=CAMERA_FRAME_HEIGHT
    ):
        """
        @function:
            初始化摄像头

        @params:
            camera_index (int): 摄像头编号
            flip (bool): 是否左右翻转图像（镜像）
            frame_width (int): 请求的摄像头采集宽度
            frame_height (int): 请求的摄像头采集高度

        @returns:
            None
        
        @raises:
            该构造过程不会直接返回摄像头通道对象，而是将其作为成员属性 self.capture 挂到 Camera 实例上
        """
        self.camera_index = camera_index
        self.flip = flip
        self.frame_width = frame_width
        self.frame_height = frame_height

        # cv.VideoCapture(index) = 打开编号为 index 的摄像头，返回一个"摄像头对象"。这个对象本身不是图像，而是一个"连接到摄像头的通道"，之后每次调用 .read() 会从这个通道取出一张图像。
        self.capture = cv.VideoCapture(self.camera_index)

        # isOpened() 检查摄像头是否成功打开
        # 如果摄像头无法打开（例如设备不存在或被占用），会直接抛出错误
        if not self.capture.isOpened():
            raise RuntimeError(f"无法打开摄像头: index={self.camera_index}")

        # 请求摄像头使用指定采集分辨率。
        # 注意：这是"请求"而不是强制，最终是否生效取决于摄像头硬件和驱动支持。
        if self.frame_width:
            self.capture.set(cv.CAP_PROP_FRAME_WIDTH, self.frame_width)
        if self.frame_height:
            self.capture.set(cv.CAP_PROP_FRAME_HEIGHT, self.frame_height)

    def read(self):
        """
        @function:
            从摄像头读取一帧图像

        @params:
            None

        @returns:
            frame (numpy.ndarray): BGR 格式的图像，形状为 (高度, 宽度, 3)
                - 这是一个三维 NumPy 数组，每个像素有 B（蓝）、G（绿）、R（红）三个通道的值（0~255）
                - 注意 OpenCV 用的是 BGR 顺序，不是常见的 RGB！

        @raises:
            如果摄像头读取失败（例如摄像头断开），会抛出错误
        """
        # capture.read() 返回两个值：
        #   1. success: True/False，表示这次读取是否成功
        #   2. frame:   NumPy 数组，表示当前这一帧的图像
        success, frame = self.capture.read()

        if not success:
            raise RuntimeError("摄像头读取数据失败")

        # 如果需要镜像翻转：cv.flip(frame, 1) 沿竖轴（左右）翻转
        # @param 1 = 水平翻转；0 = 垂直翻转；-1 = 同时水平和垂直翻转
        if self.flip:
            frame = cv.flip(frame, 1)

        return frame

    def release(self):
        """
        @function:
            释放摄像头资源

        @raises:
            如果摄像头资源释放失败，会抛出错误
        """
        if self.capture:
            self.capture.release()
