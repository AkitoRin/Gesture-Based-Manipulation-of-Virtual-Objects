# =============================================================================
# 文件：gesture/hand_motion.py
# 职责：【识别层辅助 - 手部运动意图】
#       根据手部中心点和远近变化判断挥动、上滑、下滑、推近、拉远等动态手势
# =============================================================================

from collections import deque
import time


class HandMotionTracker:
    """
    手部运动追踪器
    用最近几帧的位置变化判断手是在横向挥动、上下移动，还是靠近/远离摄像头
    """

    def __init__(self, max_history=8, cooldown=0.55):
        """
        @function:
            初始化手部运动追踪器

        @params:
            max_history (int): 保留最近多少帧的位置历史
            cooldown (float): 同类运动命令的最小触发间隔，避免一挥手连续刷屏
        """
        self.history = deque(maxlen=max_history)
        self.cooldown = cooldown
        self.last_motion = "STILL"
        self.last_trigger_time = 0.0

    def reset(self):
        """
        @function:
            清空运动历史
        """
        self.history.clear()
        self.last_motion = "STILL"

    def update(self, features):
        """
        @function:
            更新手部位置历史，并返回当前动态意图

        @params:
            features (dict): get_hand_features() 返回的空间特征

        @returns:
            dict: 运动状态
                type = STILL / SWIPE_LEFT / SWIPE_RIGHT / RAISE_UP / MOVE_DOWN / PUSH_IN / PULL_OUT
                dx/dy/dscale = 最近窗口内的位置和远近变化
        """
        now = time.time()
        center = features.get("center_norm", [0.5, 0.5])
        depth = features.get("depth", {})
        scale = float(depth.get("scale", 0.0))

        sample = {
            "t": now,
            "x": float(center[0]),
            "y": float(center[1]),
            "scale": scale,
        }
        self.history.append(sample)

        if len(self.history) < 4:
            return self._build_motion("STILL", 0.0, 0.0, 0.0)

        first = self.history[0]
        last = self.history[-1]
        dt = max(0.001, last["t"] - first["t"])
        dx = last["x"] - first["x"]
        dy = last["y"] - first["y"]
        dscale = last["scale"] - first["scale"]

        motion_type = "STILL"
        if abs(dx) > 0.16 and abs(dx) > abs(dy) * 1.25:
            motion_type = "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
        elif abs(dy) > 0.14 and abs(dy) > abs(dx) * 1.2:
            motion_type = "MOVE_DOWN" if dy > 0 else "RAISE_UP"
        elif abs(dscale) > 0.10:
            motion_type = "PUSH_IN" if dscale > 0 else "PULL_OUT"

        # 动作意图需要冷却，否则同一次挥手会连续触发很多次
        if motion_type != "STILL":
            if now - self.last_trigger_time < self.cooldown:
                motion_type = "STILL"
            else:
                self.last_trigger_time = now
                self.history.clear()

        self.last_motion = motion_type
        return self._build_motion(motion_type, dx, dy, dscale, dt)

    def _build_motion(self, motion_type, dx, dy, dscale, dt=0.0):
        """
        @function:
            构建统一的运动状态字典
        """
        return {
            "type": motion_type,
            "dx": round(dx, 3),
            "dy": round(dy, 3),
            "dscale": round(dscale, 3),
            "dt": round(dt, 3),
        }
