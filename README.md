# HandPilot

HandPilot 是一个基于摄像头手势识别的 Live2D 实时交互系统。Python 端使用
OpenCV 与 MediaPipe Hands 提取手部关键点、识别手势并判断空间运动；Node.js
Bridge 将 UDP 数据包转发为 WebSocket 消息；浏览器端驱动 Live2D 模型播放动作、
切换表情、执行头眼追踪并按需播报语音。

## 功能概览

- 识别单手与双手画面，提取每只手的 21 个关键点和相对 Z 轴深度
- 支持静态手势、多帧投票平滑、连续运动、头部区域抚摸和双手组合动作
- 使用 UDP 将 Python 识别结果传给 Bridge，再通过 WebSocket 推送到浏览器
- 使用 Live2D Profile 隔离通用命令与具体模型资源，便于后续替换模型
- 提供 OpenCV 本地仪表盘、UDP 接收测试器和 Web 页面 Local Test 调试入口

## 系统架构

![HandPilot 系统架构](docs/diagrams/handpilot_system_architecture.svg)

[查看可缩放 SVG](docs/diagrams/handpilot_system_architecture.svg) |
[打开 Draw.io 可编辑源文件](docs/diagrams/handpilot_architecture.drawio) |
[查看全部图表](docs/diagrams/README.md)

## 快速启动

### 环境要求

- Python `3.12`
- Node.js 与 npm
- 可用摄像头

当前项目虚拟环境已使用 Python `3.12.10` 验证。Windows 系统如果同时安装了多个
Python 版本，应使用 `py -3.12` 创建环境，避免误用默认版本。

### 1. 安装 Python 依赖

在项目根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 安装并启动 Node.js Bridge

新开一个终端执行：

```powershell
cd bridge
npm install
npm start
```

启动成功后，Bridge 会监听：

```text
UDP:       127.0.0.1:5005
Web page:  http://127.0.0.1:8765
WebSocket: ws://127.0.0.1:8765/ws
```

### 3. 启动手势识别端

再新开一个终端，在项目根目录执行：

```powershell
python main.py
```

程序会打开摄像头预览窗口。按 `Esc` 可正常退出并释放摄像头、UDP Socket 和
OpenCV 窗口资源。

### 4. 打开 Live2D 页面

浏览器访问：

```text
http://127.0.0.1:8765
```

页面右侧显示 WebSocket 状态、当前命令、双手信息和 Local Test 按钮。Local Test
可绕过摄像头，直接验证模型动作、表情和语音响应。

## 快速验证

完整链路推荐按以下顺序排查：

1. 启动 `npm start`，确认终端显示 UDP `5005` 和 HTTP `8765`
2. 打开 `http://127.0.0.1:8765`，确认页面显示 WebSocket 已连接
3. 运行 `python main.py`，确认摄像头窗口可见，仪表盘显示 UDP `ON`
4. 做出张开手掌等手势，确认页面收到 `CMD_WAVE` 并播放对应响应
5. 如果只想检查 UDP 发包，先关闭 Bridge，再运行 `python -m tools.udp_receiver_test`

> `tools.udp_receiver_test` 与 Bridge 都需要绑定 UDP `5005`，二者不能同时运行。

## 项目目录

```text
HandPilot/
├─ main.py                         # Python 主循环：采集、识别、决策、发包与本地展示
├─ requirements.txt                # Python 第三方依赖清单
│
├─ config/
│  └─ settings.py                  # 摄像头、检测器、平滑器、通信与仪表盘参数
│
├─ vision/
│  ├─ camera.py                    # OpenCV 摄像头初始化、读取和资源释放
│  └─ hand_detector.py             # MediaPipe Hands 封装与关键点提取
│
├─ gesture/
│  ├─ finger_state.py              # 根据关键点判断五根手指是否伸展
│  ├─ gesture_classifier.py        # 静态手势规则分类器
│  ├─ gesture_smoother.py          # 多帧投票平滑，抑制短时抖动和误判
│  ├─ command_mapper.py            # 静态手势到 Live2D 通用命令的映射
│  ├─ hand_features.py             # 中心坐标、Z 轴、尺度、区域等空间特征
│  ├─ hand_motion.py               # 滑动、上下移动、推近和拉远趋势识别
│  └─ live2d_interaction.py        # 单手空间交互和双手组合命令决策
│
├─ communication/
│  ├─ protocol.py                  # gesture_command UDP JSON 协议构造
│  └─ sender.py                    # UDP Socket 复用、变化检测与发送节流
│
├─ tools/
│  ├─ __init__.py
│  └─ udp_receiver_test.py         # 手动 UDP 接收测试器
│
├─ utils/
│  ├─ fps.py                       # FPS 计算与显示节流
│  ├─ display.py                   # 画面适配窗口尺寸
│  ├─ dashboard.py                 # OpenCV 侧边仪表盘渲染
│  └─ image_enhance.py             # 预览画面清晰度增强
│
├─ bridge/
│  ├─ udp_to_ws.js                 # UDP -> WebSocket Bridge 与静态文件服务器
│  ├─ package.json                 # Node.js 脚本与 ws 依赖
│  └─ package-lock.json
│
├─ web/
│  ├─ index.html                   # Live2D 展示页结构
│  ├─ style.css                    # 页面视觉样式与响应式布局
│  ├─ app.js                       # WebSocket、模型驱动、追踪、语音与测试面板
│  ├─ live2d_profiles/
│  │  ├─ README.md                 # 模型 Profile 适配规范
│  │  └─ haru.js                   # Haru 模型动作、表情和语音响应映射
│  ├─ models/
│  │  └─ Haru/                     # 当前 Live2D Cubism 3 模型资源
│  └─ vendor/
│     └─ l2d/                      # 本地 Live2D Web 渲染库
│
└─ docs/
   ├─ HandPilot_Project_Description.md  # 系统设计与实现说明
   ├─ Live2D_Integration_Delivery.md    # Live2D 集成交付与调试手册
   └─ diagrams/
      ├─ README.md                      # 图表索引与使用方式
      ├─ handpilot_system_architecture.svg
      ├─ handpilot_frame_pipeline.svg
      ├─ handpilot_realtime_link.svg
      ├─ handpilot_architecture.drawio  # 三页可编辑架构图
      └─ generate_handpilot_diagrams.py # 图表生成脚本
```

## 关键配置

主要配置位于 `config/settings.py`：

| 配置项 | 当前值 | 作用 |
| --- | --- | --- |
| `CAMERA_FRAME_WIDTH` / `CAMERA_FRAME_HEIGHT` | `1280` / `720` | 摄像头期望分辨率 |
| `HAND_MAX_NUM_HANDS` | `2` | 最大识别手数 |
| `SMOOTHER_WINDOW_SIZE` | `7` | 平滑器投票窗口长度 |
| `SMOOTHER_CONFIRM_THRESHOLD` | `4` | 手势确认所需最少票数 |
| `COMMUNICATION_ENABLED` | `True` | 是否启用 UDP 发送 |
| `COMM_HOST` / `COMM_PORT` | `127.0.0.1` / `5005` | Bridge UDP 监听地址 |
| `COMM_MIN_INTERVAL` | `0.05` | 变化消息最小发送间隔 |
| `COMM_REPEAT_INTERVAL` | `0.3` | 相同状态重复发送间隔 |

## 文档

- [系统设计与实现说明](docs/HandPilot_Project_Description.md)
- [Live2D 集成交付与调试手册](docs/Live2D_Integration_Delivery.md)
- [架构图资产索引](docs/diagrams/README.md)

## 常见问题

### Bridge 启动时报端口占用

确认没有同时运行 `python -m tools.udp_receiver_test`，也没有启动第二个 Bridge。

### 页面能够打开，但模型没有收到手势

依次检查 Python 仪表盘 UDP 状态、Bridge 终端是否收到消息、页面是否显示 WebSocket
已连接。也可以先用 Local Test 验证模型端，再用 UDP 接收测试器验证 Python 端。

### 预览窗口退出后摄像头仍被占用

正常退出方式是聚焦 OpenCV 预览窗口并按 `Esc`。如果程序被强制终止，需要确认旧的
Python 进程已经结束。
