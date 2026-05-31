# Live2D Profile 适配规范

本目录是 HandPilot 的模型适配层。Python 端只输出模型无关的通用命令，例如
`CMD_WAVE`、`CMD_PET_HEAD` 和 `CMD_LOOK_LEFT`；Profile 决定具体模型使用哪个动作、
表情、参数变化和语音文案。

## 当前适配器

`haru.js` 是 Haru Cubism 3 模型的适配器，导出以下配置：

```javascript
export const MODEL_PROFILE = {}
export const COMMAND_ALIASES = {}
export const RESPONSE_MAP = {}
export const TEST_GROUPS = []
```

| 配置 | 职责 |
| --- | --- |
| `MODEL_PROFILE` | 模型路径、缩放、位置、追踪参数和默认状态 |
| `COMMAND_ALIASES` | 兼容旧命令名称，避免协议升级后立即失效 |
| `RESPONSE_MAP` | 通用命令到动作、表情、语音和参数效果的映射 |
| `TEST_GROUPS` | 页面 Local Test 按钮分组，同时用于响应映射完整性检查 |

## 更换模型

1. 将新模型资源放入 `web/models/<model-name>/`
2. 复制 `haru.js`，创建新的 Profile 文件
3. 修改 `MODEL_PROFILE.modelPath`、缩放、位置和追踪参数
4. 根据模型的 `.model3.json`、动作文件和表情文件重写 `RESPONSE_MAP`
5. 为所有可触发命令配置 `TEST_GROUPS`
6. 在 `web/app.js` 顶部切换 Profile import
7. 使用页面 Local Test 逐项验证动作、表情、参数和语音

## Profile 应包含的内容

- 模型资源路径、缩放和初始位置
- 动作分组、动作索引或 `.motion3.json` 文件路径
- 表情文件、参数 burst 和语音文案
- 模型独有的追踪参数名称与幅度
- Local Test 验证分组

## Profile 不应包含的内容

- WebSocket 连接和重连逻辑
- UDP 协议解析
- DOM 面板渲染
- 通用语音开关
- 通用的 `setParams()` 封装

通过 Profile 隔离后，更换 Live2D 模型通常不需要修改 Python 手势识别链路和
Node.js Bridge。
