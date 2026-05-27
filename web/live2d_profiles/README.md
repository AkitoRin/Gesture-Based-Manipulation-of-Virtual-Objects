# Live2D Profiles

这个目录是模型适配层，用来把 HandPilot 的通用命令映射到某个具体 Live2D 模型的动作、表情和参数效果。

## 为什么要有 profile

HandPilot Python 端只负责输出稳定命令，例如：

```text
CMD_WAVE
CMD_PET_HEAD
CMD_LOOK_LEFT
CMD_COME_CLOSER
```

具体某个模型要播放哪个 `.motion3.json`、切换哪个表情、说哪句话，应该放在 profile 中，而不是写死在 `web/app.js` 主控制器里。

这样以后换模型时，尽量只需要：

1. 把新模型放进 `web/models/新模型名/`
2. 复制 `haru.js` 为 `新模型名.js`
3. 修改 `MODEL_PROFILE.modelPath`
4. 根据新模型的 `model3.json` 修改 `RESPONSE_MAP`
5. 在 `web/app.js` 顶部把 import 改到新 profile

## profile 需要导出什么

```javascript
export const MODEL_PROFILE = {}
export const COMMAND_ALIASES = {}
export const RESPONSE_MAP = {}
export const TEST_COMMANDS = []
```

## 哪些内容属于模型相关

- `modelPath`
- `modelScale`
- `modelPosition`
- `expression`
- `motion`
- `motionFile`
- `fallbackMotion`
- 角色说话文案
- 某个模型独有的参数 burst

## 哪些内容不应该放到 profile

- WebSocket 连接逻辑
- UDP 协议解析
- 头眼追踪主循环
- DOM 面板渲染
- 通用的 `setParams()` 调用封装
