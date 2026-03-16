import cv2 as cv
from config.settings import CAMERA_INDEX, FLIP_IMAGE


class Camera:
    def __init__(self, camera_index=CAMERA_INDEX, flip=FLIP_IMAGE):
        """
        摄像头模块
        :param camera_index: 摄像头编号，默认0 表示系统默认摄像头（电脑摄像头）
        :param flip: 是否进行左右的镜像翻转
        """
        self.camera_index = camera_index
        self.flip = flip
        # VideoCapture返回设定序号的摄像头对象
        self.capture = cv.VideoCapture(self.camera_index)

        if not self.capture.isOpened():
            raise RuntimeError(f"无法打开摄像头: index={self.camera_index}")

    def read(self):
        """
        读取一帧图像
        :return: frame（BGR格式图像）
        """
        # frame：当前图像帧，本质上是一个 NumPy 数组
        success, frame = self.capture.read()  # 返回是否读取成功以及当前图像帧
        if not success:
            raise RuntimeError("摄像头读取数据失败")

        if self.flip:
            frame = cv.flip(frame, 1)

        return frame

    def release(self):
        """
        释放摄像头资源
        """
        if self.capture:
            self.capture.release()
