import time


class FPSCounter:
    def __init__(self, alpha):
        self.prev_time = time.time()  # 对象创建的初始时间
        self.fps = 0
        self.alpha = alpha

    def update(self):
        curr_time = time.time()
        delta = curr_time - self.prev_time

        if delta > 0:
            instant_fps = 1.0 / delta

            if self.fps == 0:
                self.fps = instant_fps
            else:
                # 平滑处理 FPS
                self.fps = self.alpha * self.fps + (1 - self.alpha) * instant_fps

        self.prev_time = curr_time  # 更新时间
        return self.fps
