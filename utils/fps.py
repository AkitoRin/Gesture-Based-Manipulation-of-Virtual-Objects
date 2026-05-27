# =============================================================================
# 文件：utils/fps.py
# 职责：【工具层 - FPS 计数器】
#       实时计算并平滑输出视频的帧率（FPS = Frames Per Second，每秒处理多少帧）
#
# 为什么需要平滑？
#   每帧处理时间不完全一样，直接显示瞬时 FPS 会导致数字一直跳动（比如：29→31→28→30...）
#   使用指数移动平均（EMA）平滑后，数字会缓慢平稳地变化，更易读
#
# EMA 公式：平滑FPS = alpha × 上一次平滑FPS + (1 - alpha) × 这一帧的瞬时FPS
#   alpha 越接近 1 → 平滑效果越强，但反应越迟钝
#   alpha 越接近 0 → 反应越灵敏，但数字越跳动
# =============================================================================

# Python 标准库，提供时间相关函数
import time  


class FPSCounter:
    """
    FPS 计数器，每次调用 update() 返回当前的平滑帧率
    """

    def __init__(self, alpha):
        """
        初始化 FPS 计数器

        @params：
            alpha (float): EMA 平滑系数，范围 0.0 ~ 1.0
                0.9 = 强平滑，数字变化缓慢稳定（适合显示用）
                0.5 = 中等平滑
                0.1 = 弱平滑，数字跟随实际帧率快速变化
                来自 config/settings.py 的 FPS_SMOOTH_ALPHA
        """
        # time.time() = 获取当前时间（Unix时间戳，单位秒，精确到微秒级）
        # 例如：1714000000.123456（代表从1970年1月1日到现在的秒数）
        self.prev_time = time.time()  # 记录上一次调用 update() 的时间

        self.fps = 0       # 当前的平滑 FPS（初始为 0，等第一帧更新后才有值）
        self.alpha = alpha # 保存平滑系数

    def update(self):
        """
        更新帧率计算，每处理完一帧图像就调用一次

        工作流程：
            1. 记录当前时间
            2. 计算距上次调用经过了多少时间（delta）
            3. 用 1/delta 得到这一帧的瞬时 FPS
            4. 用 EMA 公式把瞬时 FPS 融合进平滑 FPS
            5. 更新时间记录，为下一帧做准备

        @returns：
            float: 当前的平滑 FPS 值
                调用者通常把这个值取整后显示在画面上：int(fps_counter.update())
        """
        curr_time = time.time()  # 记录现在的时间

        # delta = 距离上一次 update() 调用经过的时间，单位秒
        # 例如：0.033 秒 ≈ 30 FPS
        delta = curr_time - self.prev_time

        # delta > 0 的判断是为了防止极端情况下两次调用时间完全相同（delta=0）导致除零错误
        if delta > 0:
            # 瞬时 FPS = 1 秒 / 这一帧耗时
            # 例如：delta=0.033秒 → 瞬时FPS = 1/0.033 ≈ 30.3
            instant_fps = 1.0 / delta

            if self.fps == 0:
                # 第一帧时还没有历史数据，直接用瞬时 FPS 作为初始值（不做平滑）
                self.fps = instant_fps
            else:
                # EMA 平滑公式：
                # 新平滑FPS = alpha × 旧平滑FPS + (1-alpha) × 瞬时FPS
                # alpha=0.9 时：90%来自历史，10%来自新数据 → 变化很平稳
                self.fps = self.alpha * self.fps + (1 - self.alpha) * instant_fps

        self.prev_time = curr_time  # 把"现在"变成"上一次"，为下一帧做准备

        return self.fps
