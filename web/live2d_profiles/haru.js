// =============================================================================
// 文件：web/live2d_profiles/haru.js
// 职责：【Live2D 模型适配层 - Haru】
//       只保存 Haru 模型的路径、动作、表情、测试命令和命令响应映射
//       以后更换模型时优先复制这个文件做新 profile，而不是改 app.js 主控制器
// =============================================================================

export const MODEL_PROFILE = {
  id: "haru",
  name: "Haru",
  modelPath: "./models/Haru/Haru.model3.json",
  fallbackModelPath: "https://model.hacxy.cn/Haru/Haru.model3.json",
  modelScale: 0.92,
  modelPosition: [0, -0.1],
};

export const COMMAND_ALIASES = {
  CMD_START: "CMD_WAVE",
  CMD_STOP: "CMD_IDLE",
  CMD_FORWARD: "CMD_ATTENTION",
  CMD_MODE_SWITCH: "CMD_HAPPY_POSE",
  CMD_SPEED_UP: "CMD_PRAISE",
  CMD_SPEED_DOWN: "CMD_DISAPPOINTED",
  CMD_CALL: "CMD_TALK",
  CMD_THREE: "CMD_SURPRISE",
  CMD_FOUR: "CMD_CHEER",
  CMD_FOUR_THUMB: "CMD_SHY",
  CMD_PINKY: "CMD_PROMISE",
  CMD_LOOK_LEFT: "CMD_LOOK_LEFT",
  CMD_LOOK_RIGHT: "CMD_LOOK_RIGHT",
  CMD_JUMP_SURPRISE: "CMD_JUMP_SURPRISE",
  CMD_BOW: "CMD_BOW",
  CMD_COME_CLOSER: "CMD_COME_CLOSER",
  CMD_STEP_BACK: "CMD_STEP_BACK",
};

// 说明：之前大量命令都指向 TapBody 组，而 Haru 的 TapBody 组只有 4 个相似动作，
// 所以无论做什么手势看起来都在重复那几下。这里把每个命令改成指向 26 个 haru_g_mXX
// 动作中各不相同的一个（motionFile 直接按文件名播放），并保留 fallbackMotion 作为兜底，
// 让每种手势都有自己独特的动作表现。
export const RESPONSE_MAP = {
  CMD_WAVE: {
    label: "挥手回应",
    expression: "F05",
    motionFile: "motions/haru_g_m05.motion3.json",
    fallbackMotion: { group: "TapBody", index: 0, priority: 3 },
    speech: "你好呀，我看到你的手势啦",
    costume: "soft",
  },
  CMD_LOOK_LEFT: {
    label: "向左追踪",
    expression: "F01",
    motionFile: "motions/haru_g_m03.motion3.json",
    motionPriority: 3,
    speech: null,
    costume: "focus",
    burst: { ParamAngleX: -28, ParamBodyAngleX: -9, ParamBodyAngleZ: 6 },
  },
  CMD_LOOK_RIGHT: {
    label: "向右追踪",
    expression: "F01",
    motionFile: "motions/haru_g_m04.motion3.json",
    motionPriority: 3,
    speech: null,
    costume: "focus",
    burst: { ParamAngleX: 28, ParamBodyAngleX: 9, ParamBodyAngleZ: -6 },
  },
  CMD_JUMP_SURPRISE: {
    label: "抬手惊喜",
    expression: "F02",
    motionFile: "motions/haru_g_m12.motion3.json",
    motionPriority: 4,
    speech: "欸？手突然抬起来了",
    costume: "spark",
    burst: { ParamAngleY: 22, ParamBodyAngleY: 10, ParamEyeBallY: 1 },
  },
  CMD_BOW: {
    label: "低头回应",
    expression: "F01",
    motionFile: "motions/haru_g_m14.motion3.json",
    motionPriority: 3,
    speech: null,
    costume: "calm",
    burst: { ParamAngleY: -18, ParamBodyAngleY: -8 },
  },
  CMD_COME_CLOSER: {
    label: "靠近观察",
    expression: "F06",
    motionFile: "motions/haru_g_m18.motion3.json",
    motionPriority: 4,
    speech: "你靠近了，我看得更清楚啦",
    costume: "focus",
    burst: { ParamFaceForm: 0.7, ParamBodyUpper: 0.9, ParamEyeBallForm: -0.45 },
  },
  CMD_STEP_BACK: {
    label: "后退留白",
    expression: "F08",
    motionFile: "motions/haru_g_m19.motion3.json",
    motionPriority: 3,
    speech: null,
    costume: "calm",
    burst: { ParamFaceForm: -0.3, ParamBodyUpper: -0.55 },
  },
  CMD_IDLE: {
    label: "安静待机",
    expression: "F01",
    motion: { group: "Idle", index: 0, priority: 1 },
    speech: "好，我先安静一下",
    costume: "calm",
  },
  CMD_ATTENTION: {
    label: "认真听你说",
    expression: "F02",
    motionFile: "motions/haru_g_m06.motion3.json",
    fallbackMotion: { group: "TapBody", index: 1, priority: 3 },
    speech: "嗯，我在听，请继续",
    costume: "soft",
  },
  CMD_HAPPY_POSE: {
    label: "开心合影",
    expression: "F05",
    motionFile: "motions/haru_g_m26.motion3.json",
    fallbackMotion: { group: "TapBody", index: 0, priority: 3 },
    speech: "耶，这个手势很适合拍照",
    costume: "soft",
  },
  CMD_PRAISE: {
    label: "被夸奖",
    expression: "F05",
    motionFile: "motions/haru_g_m08.motion3.json",
    fallbackMotion: { group: "TapBody", index: 2, priority: 3 },
    speech: "谢谢夸奖，我会继续加油",
    costume: "soft",
  },
  CMD_DISAPPOINTED: {
    label: "有点委屈",
    expression: "F08",
    motionFile: "motions/haru_g_m13.motion3.json",
    fallbackMotion: { group: "TapBody", index: 3, priority: 3 },
    speech: "我会再调整一下，不要失望嘛",
    costume: "calm",
  },
  CMD_DANCE: {
    label: "舞台活跃",
    expression: "F05",
    motionFile: "motions/haru_g_m10.motion3.json",
    fallbackMotion: { group: "TapBody", index: 2, priority: 3 },
    speech: "节奏来了，进入舞台模式",
    costume: "dance",
  },
  CMD_TALK: {
    label: "通话回应",
    expression: "F01",
    motionFile: "motions/haru_g_m07.motion3.json",
    fallbackMotion: { group: "TapBody", index: 3, priority: 3 },
    speech: "喂喂，HandPilot 通信正常",
    costume: "soft",
  },
  CMD_SURPRISE: {
    label: "惊讶反应",
    expression: "F02",
    motionFile: "motions/haru_g_m11.motion3.json",
    fallbackMotion: { group: "TapBody", index: 1, priority: 3 },
    speech: "哇，三根手指触发了惊喜",
    costume: "soft",
  },
  CMD_CHEER: {
    label: "应援鼓励",
    expression: "F05",
    motionFile: "motions/haru_g_m24.motion3.json",
    fallbackMotion: { group: "TapBody", index: 0, priority: 3 },
    speech: "收到四指信号，给你加油",
    costume: "dance",
  },
  CMD_SHY: {
    label: "害羞回应",
    expression: "F07",
    motionFile: "motions/haru_g_m17.motion3.json",
    fallbackMotion: { group: "TapBody", index: 2, priority: 3 },
    speech: "这个手势有点可爱，我有点害羞",
    costume: "blush",
  },
  CMD_PROMISE: {
    label: "拉钩约定",
    expression: "F07",
    motionFile: "motions/haru_g_m16.motion3.json",
    fallbackMotion: { group: "TapBody", index: 2, priority: 3 },
    speech: "勾一下小指，这是我们的约定哦",
    costume: "blush",
  },
  CMD_PET_HEAD: {
    label: "摸头害羞",
    expression: "F07",
    motionFile: "motions/haru_g_m22.motion3.json",
    fallbackMotion: { group: "TapBody", index: 2, priority: 4 },
    speech: "唔，被摸头了，有点害羞",
    costume: "blush",
    burst: { ParamTere: 1, ParamAngleY: 12, ParamEyeBallY: 0.8 },
  },
  CMD_DOUBLE_CHEER: {
    label: "双手应援",
    expression: "F05",
    motionFile: "motions/haru_g_m21.motion3.json",
    fallbackMotion: { group: "TapBody", index: 0, priority: 4 },
    speech: "双手同步，能量满格",
    costume: "dance",
  },
  CMD_NONE: {
    label: "等待手势",
    costume: "calm",
  },
};

// 本地测试面板的分组定义。
// 每个 item 的 command 必须存在于上面的 RESPONSE_MAP；gesture 是触发它的真实手势说明，
// 这样测试面板同时也是一份"手势 → 动作"对照清单，方便演示和讲解。
// app.js 会在启动时自动检查：RESPONSE_MAP 里除 CMD_NONE 外的每个命令都必须出现在这里，
// 漏了会在浏览器控制台警告，避免"加了新动作却忘了加测试按钮"。
export const TEST_GROUPS = [
  {
    title: "静态手势",
    items: [
      { command: "CMD_WAVE",        gesture: "张开手掌" },
      { command: "CMD_IDLE",        gesture: "握拳" },
      { command: "CMD_ATTENTION",   gesture: "食指朝上" },
      { command: "CMD_HAPPY_POSE",  gesture: "剪刀手 V" },
      { command: "CMD_PRAISE",      gesture: "拇指朝上" },
      { command: "CMD_DISAPPOINTED",gesture: "拇指朝下" },
      { command: "CMD_DANCE",       gesture: "摇滚手势" },
      { command: "CMD_TALK",        gesture: "打电话手势" },
      { command: "CMD_SURPRISE",    gesture: "三根手指" },
      { command: "CMD_CHEER",       gesture: "四根手指" },
      { command: "CMD_SHY",         gesture: "拇指+三指" },
      { command: "CMD_PROMISE",     gesture: "只伸小指" },
    ],
  },
  {
    title: "动态挥动",
    items: [
      { command: "CMD_LOOK_LEFT",     gesture: "手向左挥" },
      { command: "CMD_LOOK_RIGHT",    gesture: "手向右挥" },
      { command: "CMD_JUMP_SURPRISE", gesture: "手快速上抬" },
      { command: "CMD_BOW",           gesture: "手快速下移" },
      { command: "CMD_COME_CLOSER",   gesture: "手推近镜头" },
      { command: "CMD_STEP_BACK",     gesture: "手拉远镜头" },
    ],
  },
  {
    title: "空间 / 双手",
    items: [
      { command: "CMD_PET_HEAD",    gesture: "手掌放到头部" },
      { command: "CMD_DOUBLE_CHEER",gesture: "双手同时张开" },
    ],
  },
];
