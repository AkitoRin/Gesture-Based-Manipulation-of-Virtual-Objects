# =============================================================================
# 文件：gesture/gesture_smoother.py
# 职责：【识别层第三步 - 手势去抖动】
#       通过滑动窗口投票机制，过滤掉因手轻微抖动或摄像头噪声导致的手势识别跳变
#
# 设计原因：
#   每一帧的手势识别结果可能因为手轻微抖动或摄像头噪声而跳变，
#   例如明明在做 FIST，但某帧突然被识别成了 UNKNOWN 又变回 FIST；
#   GestureSmoother 通过"多数表决"机制过滤掉这些偶发性错误识别，
#   只有当一个手势在最近多帧中持续出现时，才对外输出这个手势。
#
# 工作原理（滑动窗口投票）：
#   维护一个"最近 N 帧"的识别结果队列（窗口）
#   每收到新的一帧结果，就加入队列（队列满了就挤出最老的）
#   统计队列里每种手势出现的次数
#   如果某手势出现次数 >= 确认阈值，就把它设为"稳定输出"
#   否则，保持上一个稳定输出不变（宁可慢点确认，也不随便跳变）
#
# 举例（window_size=12, confirm_threshold=8）：
#   最近 12 帧：FIST×10, UNKNOWN×2  → FIST 出现 10 次 ≥ 8 → 输出 FIST
#   最近 12 帧：FIST×5, V_SIGN×5, UNKNOWN×2 → 都没达到 8 → 保持上一个稳定输出
# =============================================================================

# Python 标准库，用于提供高性能的容器数据类型
# deque  = 双端队列，一种特殊的列表，支持从两端高效添加/删除元素；可以设置最大长度，满了自动弹出旧数据
# Counter = 计数器，传入一个列表，自动统计每个元素出现的次数
from collections import deque, Counter
# 从配置文件导入所需参数
from config.settings import (
    SMOOTHER_WINDOW_SIZE,
    SMOOTHER_CONFIRM_THRESHOLD,
    SMOOTHER_IGNORE_UNKNOWN,
)

class GestureSmoother:
    """
    滑动窗口投票平滑器
    对逐帧的手势识别结果进行时间维度上的稳定化处理
    每只手需要单独创建一个 GestureSmoother 实例
    """

    def __init__(self, window_size = SMOOTHER_WINDOW_SIZE, 
                 confirm_threshold = SMOOTHER_CONFIRM_THRESHOLD,
                 ignore_unknown = SMOOTHER_IGNORE_UNKNOWN):
        """
        @function:   
            初始化平滑器

        @params：
            window_size (int): 滑动窗口大小，即"记住最近多少帧"
                越大 → 稳定性越好，但响应延迟越高（手势切换需要等更多帧才被确认）
                越小 → 响应更快，但更容易因抖动而误输出

            confirm_threshold (int): 确认阈值，窗口内某手势出现多少次才算"确认"
                必须 <= window_size
                confirm_threshold / window_size 的比例越高 → 判断越严格
                例如：12 帧窗口内需要 8 帧同意（约67%）才确认输出该手势
            ignore_unknown (bool): 是否忽略短暂的 UNKNOWN 抖动
                True = 已经有稳定手势时，UNKNOWN 不会立刻覆盖稳定输出
        """
        if window_size <= 0:
            raise ValueError("window_size 必须大于 0")
        if confirm_threshold <= 0:
            raise ValueError("confirm_threshold 必须大于 0")
        if confirm_threshold > window_size:
            raise ValueError("confirm_threshold 不能大于 window_size")

        # deque(maxlen=window_size) = 创建一个最大长度为 window_size 的双端队列
        # 当队列已满时，新加入的元素会自动把最早的元素挤出去，始终保持 window_size 个元素
        self.window = deque(maxlen = window_size)

        self.confirm_threshold = confirm_threshold  # 投票通过的最低票数
        self.ignore_unknown = ignore_unknown        # 是否忽略短暂 UNKNOWN

        # 当前稳定输出的手势名称，初始状态为 "UNKNOWN"（还没有稳定手势）
        self.stable_gesture = "UNKNOWN"

    def update(self, gesture):
        """
        @function:
            接收新一帧的手势识别结果，更新投票窗口，返回当前稳定手势

        @params：
            gesture (str): 这一帧识别到的手势名称，例如 "FIST", "V_SIGN"
                由 gesture_classifier.py 的 classify_gesture() 生成

        @returns：
            stable_gesture (str): 当前的稳定手势名称
                - 如果窗口内某手势达到阈值 → 返回该手势（可能和上次不同）
                - 否则 → 返回上一次的稳定手势（保持不变）
        """
        # 如果已经有稳定手势，短暂 UNKNOWN 通常只是识别抖动
        # 此时保持当前稳定手势，可以减少画面和 UDP 命令来回跳变
        if self.ignore_unknown and gesture == "UNKNOWN" and self.stable_gesture != "UNKNOWN":
            return self.stable_gesture

        # 把这帧的识别结果加入窗口队列
        # 如果队列已满（已有 window_size 个元素），最旧的那个会自动被弹出
        self.window.append(gesture)

        # Counter(self.window) 统计窗口内每个手势出现的次数
        # 例如 Counter(["FIST","FIST","UNKNOWN","FIST"]) → Counter({"FIST":3, "UNKNOWN":1})
        counts = Counter(self.window)

        # most_common(1) 返回出现次数最多的那一个，数据格式是 [(手势名, 出现次数)]
        # [0] 取列表里的第一个（唯一一个）元素：(手势名, 次数)
        # 再解包成 most_common（手势名）和 count（次数）两个变量
        most_common, count = counts.most_common(1)[0]

        # 如果出现次数最多的手势达到了确认阈值，就把它设为新的稳定手势
        if count >= self.confirm_threshold:
            self.stable_gesture = most_common

        return self.stable_gesture

    def reset(self):
        """
        @function:
            重置平滑器状态
            当手从摄像头画面中消失时调用，清空历史记录，回到初始状态
            避免下次手出现时，窗口里还残留着上次的旧数据，导致误判
        """
        self.window.clear()                   # 清空窗口队列
        self.stable_gesture = "UNKNOWN"       # 重置稳定手势为默认值
