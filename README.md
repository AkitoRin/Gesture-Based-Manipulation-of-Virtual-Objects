# HandPilot

HandPilot 是一个基于 Python、OpenCV、MediaPipe 和 Live2D Web 前端的实时手势交互项目。

当前链路已经从单纯的摄像头手势识别，扩展为：

```text
摄像头画面
→ Python 手势识别
→ 手势平滑与动态意图判断
→ UDP JSON
→ Node Bridge
→ WebSocket
→ Web Live2D 页面
→ Haru 模型动作 / 表情 / 语言 / 追踪反馈
```

## 当前项目状态

```text
Python 端：负责摄像头读取、MediaPipe 检测、手势分类、平滑、空间特征、UDP 发送
Bridge 端：负责 UDP 转 WebSocket，并提供本地静态网页服务
Web 端：负责加载 Live2D 模型、接收命令、播放动作、表情、语言和舞台反馈
模型资源：当前接入 Haru model3 模型
```

详细交付说明见：

```text
docs/Live2D_Integration_Delivery.md
```

## 环境建议

当前 `requirements.txt` 使用了 OpenCV、MediaPipe 和 NumPy。建议使用 Python 3.11 或 Python 3.12 建立虚拟环境。

不建议直接使用 Python 3.14。当前终端体检时发现 Python 3.14 环境里没有安装 `cv2 / mediapipe / numpy`，会导致 `python main.py` 启动失败。

## 第一次安装

在项目根目录执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

安装 Bridge 依赖：

```powershell
cd bridge
npm install
```

## 快速启动

终端 1：启动 Bridge 和 Live2D 页面服务

```powershell
cd bridge
npm start
```

正常输出应包含：

```text
UDP 监听已启动：127.0.0.1:5005
Live2D 页面：http://127.0.0.1:8765
WebSocket：ws://127.0.0.1:8765/ws
```

浏览器打开：

```text
http://127.0.0.1:8765
```

终端 2：启动 Python 手势识别

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

## 如何判断启动成功

```text
1. OpenCV 摄像头窗口能打开
2. Live2D 页面显示 WebSocket 已连接
3. 摄像头前做手势后，Bridge 终端能看到 UDP 日志
4. Live2D 角色会跟随手部位置，并播放动作、表情或语言反馈
```

退出方式：

```text
Python 主程序：按 Esc
Bridge 服务：按 Ctrl+C
```

## 只测试 UDP

如果只想确认 Python 是否真的发出了 UDP 包，可以不启动 Bridge，改用测试接收器：

```powershell
python -m tools.udp_receiver_test
```

注意：`tools.udp_receiver_test` 和 Bridge 都会监听 `127.0.0.1:5005`，二者不能同时运行。

## 常见问题

| 问题 | 常见原因 | 处理方式 |
|---|---|---|
| `ModuleNotFoundError: No module named 'cv2'` | 当前 Python 环境没有安装依赖 | 激活 `.venv` 后执行 `pip install -r requirements.txt` |
| `mediapipe` 安装失败 | Python 版本过新或不兼容 | 优先使用 Python 3.11 / 3.12 |
| Bridge 启动失败 | 端口 `5005` 或 `8765` 被占用 | 关闭旧 Bridge 或 UDP 测试器 |
| Live2D 页面没反应 | Bridge 未启动或 WebSocket 未连接 | 先确认页面右侧连接状态 |
| 模型有动作但没声音 | 浏览器自动播放策略限制 | 点击页面中的“开启角色声音” |

## 主要目录

```text
main.py                         # Python 主入口
config/settings.py              # 全局配置
vision/                         # 摄像头和 MediaPipe 手部检测
gesture/                        # 手势识别、平滑、动态意图、Live2D 命令推导
communication/                  # UDP 协议和发送器
tools/                          # 手动调试工具
bridge/                         # UDP → WebSocket 桥接服务
web/                            # Live2D 页面和 Haru 模型资源
docs/                           # 交付说明和架构说明
```
