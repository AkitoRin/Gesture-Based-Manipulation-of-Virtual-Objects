// =============================================================================
// 文件：web/app.js
// 职责：【Live2D 前端控制器】
//       加载 Haru 模型，连接 Bridge WebSocket，接收 HandPilot 手势命令并驱动动作、表情、语言和舞台反馈
// =============================================================================

import { init as initL2D } from "./vendor/l2d/index.js";
import {
  COMMAND_ALIASES,
  MODEL_PROFILE,
  RESPONSE_MAP,
  TEST_GROUPS,
} from "./live2d_profiles/haru.js";

const CONFIG = {
  reconnectDelay: 1800,
  // 同一命令最短重播间隔。仅用于"本地测试按钮连点"这种边缘情况防抖；
  // 真实手势的重复抑制由 executeResponse 里"相同命令不重播"逻辑负责。
  minRetriggerGap: 250,
  // 【全局动作间隔】任意两个动作之间至少间隔这么久（毫秒）。
  // 这是解决"动作鬼畜 / 台词没说完就被打断 / 头不跟手"的关键：
  //   你大幅移动手时会同时触发一堆不同命令（静态手势+挥手+摸头），
  //   若每个都立刻播动作，角色就一直在播动作、一直被动作带着头转、台词全被打断。
  //   强制间隔后，动作变成偶发点缀，大段空隙里头部追踪才能真正跟手，台词也能完整播完。
  globalMotionGap: 2500,
};

const dom = {
  stage: document.querySelector(".stage"),
  canvas: document.getElementById("live2d-canvas"),
  trackingOrb: document.getElementById("tracking-orb"),
  loadingCard: document.getElementById("loading-card"),
  loadingDetail: document.getElementById("loading-detail"),
  loadingBar: document.querySelector("#loading-bar i"),
  speechBubble: document.getElementById("speech-bubble"),
  wsLight: document.getElementById("ws-light"),
  wsState: document.getElementById("ws-state"),
  gesture: document.getElementById("current-gesture"),
  command: document.getElementById("current-command"),
  response: document.getElementById("current-response"),
  latency: document.getElementById("current-latency"),
  handsList: document.getElementById("hands-list"),
  costumeState: document.getElementById("costume-state"),
  enableAudio: document.getElementById("enable-audio"),
  testButtons: document.getElementById("test-buttons"),
};

const state = {
  l2d: null,
  modelReady: false,
  socket: null,
  reconnectTimer: null,
  lastCommand: "",
  lastCommandAt: 0,
  lastMotion: "",
  charTimer: null,
  mouthTimer: null,
  mouthRaf: null,
  speaking: false,
  currentMouth: 0,
  targetMouth: 0,
  mouthOpen: false,
  audioEnabled: false,
  costumeEnergy: 0.25,
  tracking: {
    currentX: 0,
    currentY: 0,
    currentZ: 0,
    targetX: 0,
    targetY: 0,
    targetZ: 0,
    targetScale: 0,
    lastSeenAt: 0,
  },
  burst: {
    activeUntil: 0,
    params: {},
  },
};

function getWebSocketUrl() {
  if (location.host) {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${location.host}/ws`;
  }

  return "ws://127.0.0.1:8765/ws";
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = dom.canvas.getBoundingClientRect();
  dom.canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  dom.canvas.height = Math.max(1, Math.floor(rect.height * ratio));

  if (state.l2d && typeof state.l2d.resize === "function") {
    state.l2d.resize();
  }
}

function setLoading(percent, detail) {
  dom.loadingBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  dom.loadingDetail.textContent = detail;
}

function setConnection(connected, text) {
  dom.wsLight.classList.toggle("is-on", connected);
  dom.wsState.textContent = text;
}

function safeSetParams(params) {
  if (!state.modelReady || !state.l2d || typeof state.l2d.setParams !== "function") {
    return;
  }

  try {
    state.l2d.setParams(params);
  } catch (error) {
    console.warn("setParams 调用失败", error);
  }
}

function trySetExpression(expression) {
  if (!expression || !state.modelReady || !state.l2d) {
    return;
  }

  try {
    state.l2d.setExpression(expression);
  } catch (error) {
    console.warn("表情切换失败", expression, error);
  }
}

// 把 "motions/haru_g_mNN.motion3.json" 换算成 model3.json 里 "HandPilot" 动作组的索引。
// 该组按 m01..m26 顺序排列，所以 mNN 对应索引 NN-1。
// 这样可以走 playMotion(group, index) 这条已被 TapBody 动作验证可用的可靠路径，
// 而不依赖 playMotionByFile（黑盒渲染库里该接口不保证有效）。
function resolveHaruMotion(motionFile) {
  const matched = /haru_g_m(\d+)\.motion3\.json/.exec(motionFile || "");
  if (!matched) {
    return null;
  }
  return { group: "HandPilot", index: parseInt(matched[1], 10) - 1 };
}

function tryPlayMotion(response) {
  if (!state.modelReady || !state.l2d || !response) {
    return;
  }

  const signature = response.motionFile ||
    (response.motion ? `${response.motion.group}:${response.motion.index}` : "");

  if (signature && signature === state.lastMotion && response.label !== "摸头害羞") {
    return;
  }

  const priority = response.motionPriority || (response.motion && response.motion.priority) || 3;

  try {
    // 优先：把 motionFile 解析成 HandPilot 组索引，走可靠的 playMotion 路径
    const resolved = response.motionFile ? resolveHaruMotion(response.motionFile) : null;
    if (resolved) {
      state.l2d.playMotion(resolved.group, resolved.index, priority);
      state.lastMotion = signature;
      return;
    }

    // 其次：直接用 group/index 定义的动作（例如 Idle）
    if (response.motion) {
      const { group, index } = response.motion;
      state.l2d.playMotion(group, index, response.motion.priority || priority);
      state.lastMotion = signature;
      return;
    }

    // 再次：仍然保留 playMotionByFile 作为后备路径
    if (response.motionFile && typeof state.l2d.playMotionByFile === "function") {
      state.l2d.playMotionByFile(response.motionFile, priority);
      state.lastMotion = signature;
    }
  } catch (error) {
    console.warn("动作播放失败，尝试 fallback", error);
    if (response.fallbackMotion) {
      const { group, index, priority: fbPriority } = response.fallbackMotion;
      state.l2d.playMotion(group, index, fbPriority);
      state.lastMotion = `${group}:${index}`;
    }
  }
}

function setCostumeEffect(mode) {
  const normalized = mode || "soft";
  dom.stage.dataset.costume = normalized;

  const text = {
    soft: "制服柔光 · Soft Uniform",
    calm: "冷静浅蓝 · Calm Layer",
    blush: "害羞粉光 · Blush Layer",
    dance: "舞台暖光 · Dance Layer",
    focus: "追踪蓝光 · Tracking Focus",
    spark: "惊喜星光 · Spark Layer",
  }[normalized];

  dom.costumeState.textContent = text || "制服柔光 · Soft Uniform";
  state.costumeEnergy = normalized === "dance"
    ? 0.92
    : normalized === "blush"
      ? 0.72
      : normalized === "focus" || normalized === "spark"
        ? 0.58
        : 0.28;
}

function stopSpeechTimers() {
  if (state.charTimer !== null) {
    clearTimeout(state.charTimer);
    state.charTimer = null;
  }

  if (state.mouthTimer !== null) {
    clearTimeout(state.mouthTimer);
    state.mouthTimer = null;
  }

  if (state.mouthRaf !== null) {
    cancelAnimationFrame(state.mouthRaf);
    state.mouthRaf = null;
  }

  // 打断上一句还没念完的语音，避免多条台词叠在一起变成"模糊不清"的声音
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

// 用浏览器自带的语音合成（Web Speech API / TTS）把台词真正"读"出来。
// 这样每个命令都有清晰、可区分的中文语音，而不再依赖模型里仅有的几个日语 wav 片段。
// 需要用户先点过"开启角色声音"（浏览器要求有用户交互后才允许出声）。
function speakAloud(text) {
  if (!state.audioEnabled || !window.speechSynthesis) {
    return;
  }

  try {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "zh-CN";   // 中文发音
    utterance.rate = 1.05;      // 语速（1.0 为正常）
    utterance.pitch = 1.2;      // 音调略高，更接近角色声线

    // 如果系统里装了中文语音包，优先挑一个中文嗓音
    const voices = window.speechSynthesis.getVoices();
    const zhVoice = voices.find((v) => /zh|chinese|中文/i.test(`${v.lang} ${v.name}`));
    if (zhVoice) {
      utterance.voice = zhVoice;
    }

    window.speechSynthesis.speak(utterance);
  } catch (error) {
    console.warn("语音合成失败", error);
  }
}

function mouthLoop() {
  state.currentMouth += (state.targetMouth - state.currentMouth) * 0.2;
  safeSetParams({ ParamMouthOpenY: state.currentMouth });

  if (state.speaking || state.currentMouth > 0.02) {
    state.mouthRaf = requestAnimationFrame(mouthLoop);
  } else {
    state.mouthRaf = null;
    safeSetParams({ ParamMouthOpenY: 0 });
    dom.speechBubble.classList.remove("is-visible");
  }
}

function scheduleMouthFlip() {
  state.mouthOpen = !state.mouthOpen;
  state.targetMouth = state.mouthOpen
    ? 0.45 + Math.random() * 0.5
    : Math.random() * 0.18;

  state.mouthTimer = setTimeout(scheduleMouthFlip, 90 + Math.random() * 90);
}

function speak(text) {
  if (!text) {
    return;
  }

  stopSpeechTimers();

  // 真正发出中文语音（嘴型动画 + 字幕逐字显示依旧保留，三者同步）
  speakAloud(text);

  let charIndex = 0;
  state.currentMouth = 0;
  state.targetMouth = 0;
  state.mouthOpen = false;
  state.speaking = true;
  dom.speechBubble.textContent = "";
  dom.speechBubble.classList.add("is-visible");

  mouthLoop();
  scheduleMouthFlip();

  function showNextChar() {
    dom.speechBubble.textContent = text.slice(0, charIndex + 1);
    charIndex += 1;

    if (charIndex < text.length) {
      state.charTimer = setTimeout(showNextChar, 80);
      return;
    }

    if (state.mouthTimer !== null) {
      clearTimeout(state.mouthTimer);
      state.mouthTimer = null;
    }
    state.speaking = false;
    state.targetMouth = 0;
  }

  showNextChar();
}

function applyBurst(params) {
  if (!params) {
    return;
  }

  state.burst.params = { ...params };
  state.burst.activeUntil = performance.now() + 720;
}

function resolveCommand(packet) {
  const hands = Array.isArray(packet.hands) ? packet.hands : [];
  const petHand = hands.find((item) => item.command === "CMD_PET_HEAD");
  if (petHand) {
    return "CMD_PET_HEAD";
  }

  const openHands = hands.filter((item) => item.gesture === "OPEN_HAND");
  if (openHands.length >= 2) {
    return "CMD_DOUBLE_CHEER";
  }

  const command = packet.command || "CMD_NONE";
  return COMMAND_ALIASES[command] || command;
}

function executeResponse(command, packet) {
  const response = RESPONSE_MAP[command] || RESPONSE_MAP.CMD_NONE;
  const now = Date.now();
  const isLocalTest = packet && packet.source === "LocalTest";

  // 顶部状态文字和舞台灯光每帧都可以更新（轻量，不涉及重播动作）
  dom.response.textContent = response.label;
  setCostumeEffect(response.costume);

  if (command === "CMD_NONE") {
    // 无手势：不更新 lastCommand，这样手短暂离开/抖回来时不会被当成"新命令"重播
    return;
  }

  // 【修复1：相同命令持续时绝不重播动作】
  // 你保持同一个手势时，后端会按 COMM_REPEAT_INTERVAL 持续重发相同命令（用于维持头眼追踪的新鲜度），
  // 但动作只应该在"刚切换到这个手势"那一刻播一次。命令没变就只更新追踪、直接返回，不重播。
  // 例外：本地测试按钮（LocalTest）允许连点重播，方便逐个演示，但仍加一个很短的防抖。
  if (command === state.lastCommand) {
    if (!isLocalTest) {
      return;
    }
    if (now - state.lastCommandAt < CONFIG.minRetriggerGap) {
      return;
    }
  } else if (!isLocalTest) {
    // 【修复2：全局动作间隔——治本】
    // 命令变成了一个新值（你做了新手势，或手大幅移动触发了动态命令）。
    // 但若距上一次播放动作还不到 globalMotionGap，就先把这次变化"吞掉"不播：
    //   - 这样动作之间至少隔 2.5 秒，上一个动作和台词能完整播完，不会被打断；
    //   - 动作变少后，大段时间没有动作压制头部，头眼追踪才能真正跟手。
    // 注意：这里特意【不更新】state.lastCommand，等冷却结束后第一个新手势才真正触发，
    //       避免把冷却期里一闪而过的噪声命令记成"当前命令"。
    if (now - (state.lastMotionPlayedAt || 0) < CONFIG.globalMotionGap) {
      return;
    }
  }

  state.lastCommand = command;
  state.lastCommandAt = now;
  state.lastMotionPlayedAt = now;   // 记录"本次真正播放了动作"的时刻，供全局间隔判断

  trySetExpression(response.expression);
  tryPlayMotion(response);
  applyBurst(response.burst);
  speak(response.speech);

  if (isLocalTest) {
    console.info("本地测试命令", command);
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function applyHandTracking(hands) {
  if (!Array.isArray(hands) || hands.length === 0) {
    state.tracking.targetX = 0;
    state.tracking.targetY = 0;
    state.tracking.targetZ = 0;
    state.tracking.targetScale = 0;
    dom.trackingOrb.classList.remove("is-visible");
    return;
  }

  const activeHand = hands.find((item) => item.command && item.command !== "CMD_NONE") || hands[0];
  const features = activeHand.features || {};
  const center = features.center_3d || features.center_norm || [0.5, 0.5, 0];
  const depth = features.depth || {};
  const scale = Number(depth.scale || 0);
  const motion = activeHand.motion?.type || "STILL";

  // 头和眼睛追踪手部位置，幅度故意比普通鼠标跟随更明显
  state.tracking.targetX = clamp((center[0] - 0.5) * 64, -30, 30);
  state.tracking.targetY = clamp((0.5 - center[1]) * 48, -26, 26);
  state.tracking.targetZ = clamp((scale - 0.34) * 3.2, -0.75, 0.9);
  state.tracking.targetScale = scale;
  state.tracking.lastSeenAt = performance.now();

  dom.trackingOrb.style.left = `${clamp(center[0] * 100, 4, 96)}%`;
  dom.trackingOrb.style.top = `${clamp(center[1] * 100, 4, 96)}%`;
  dom.trackingOrb.title = `tracking ${motion}`;
  dom.trackingOrb.classList.add("is-visible");

  // 【诊断】每秒输出一次手部坐标和算出的头部目标角度。
  // 如果你做手势移动手时，这里的 center 和 目标X/Y 在变化，说明数据链路是通的。
  const nowMs = performance.now();
  if (!state._trackLogAt || nowMs - state._trackLogAt > 1000) {
    state._trackLogAt = nowMs;
    console.info(
      "[追踪] 手部中心 center=",
      center.map((n) => Number(n).toFixed(2)).join(", "),
      "→ 头部目标 X/Y=",
      state.tracking.targetX.toFixed(1),
      state.tracking.targetY.toFixed(1),
    );
  }
}

function animationLoop() {
  const t = performance.now() / 1000;
  const now = performance.now();
  // 新鲜度窗口必须 > 后端的重发间隔（COMM_REPEAT_INTERVAL=0.3s），
  // 否则手一静止就会被误判为"数据过期"，导致头部回弹到正中（这正是之前不跟手的根因）。
  // 1500ms 给足缓冲：只要手还在画面里，前端就持续把头朝向手；
  // 手真正离开时，后端会发一个空手数据包让 applyHandTracking 平滑归位，这里只是 UDP 丢包时的安全兜底。
  const trackingFresh = now - state.tracking.lastSeenAt < 1500;
  const followSpeed = trackingFresh ? 0.25 : 0.07;

  if (!trackingFresh) {
    // 仅当长时间收不到任何数据（疑似丢包）才缓慢回正，避免突兀
    state.tracking.targetX = 0;
    state.tracking.targetY = 0;
    state.tracking.targetZ = 0;
    dom.trackingOrb.classList.remove("is-visible");
  }

  state.tracking.currentX += (state.tracking.targetX - state.tracking.currentX) * followSpeed;
  state.tracking.currentY += (state.tracking.targetY - state.tracking.currentY) * followSpeed;
  state.tracking.currentZ += (state.tracking.targetZ - state.tracking.currentZ) * 0.1;

  const burstWeight = Math.max(0, Math.min(1, (state.burst.activeUntil - now) / 720));
  const burst = state.burst.params;
  const burstValue = (key) => (burst[key] || 0) * burstWeight;

  safeSetParams({
    ParamAngleX: clamp(state.tracking.currentX + burstValue("ParamAngleX"), -38, 38),
    ParamAngleY: clamp(state.tracking.currentY + burstValue("ParamAngleY"), -28, 28),
    ParamAngleZ: clamp(-state.tracking.currentX * 0.18, -10, 10),
    ParamEyeBallX: clamp(state.tracking.currentX / 26, -1, 1),
    ParamEyeBallY: clamp(state.tracking.currentY / 22 + burstValue("ParamEyeBallY"), -1, 1),
    ParamEyeBallForm: burstValue("ParamEyeBallForm"),
    ParamFaceForm: burstValue("ParamFaceForm"),
    ParamBodyAngleX: clamp(state.tracking.currentX * 0.42 + burstValue("ParamBodyAngleX"), -18, 18),
    ParamBodyAngleY: clamp(state.tracking.currentY * 0.28 + burstValue("ParamBodyAngleY"), -12, 12),
    ParamBodyAngleZ: clamp(-state.tracking.currentX * 0.2 + burstValue("ParamBodyAngleZ"), -12, 12),
    ParamBodyUpper: clamp(state.tracking.currentZ + burstValue("ParamBodyUpper"), -1, 1),
    ParamBreath: 0.55 + Math.sin(t * 1.8) * 0.32,
    ParamScarf: Math.sin(t * 4.2) * (state.costumeEnergy + Math.abs(state.tracking.currentX) / 45),
    ParamHairFront: Math.sin(t * 3.6) * state.costumeEnergy + state.tracking.currentX * 0.018,
    ParamHairSide: Math.cos(t * 3.2) * state.costumeEnergy - state.tracking.currentX * 0.014,
    ParamTere: burstValue("ParamTere"),
  });

  // 【诊断】每 1.5 秒对比一次"我想设的头部角度"和"模型实际生效的角度"。
  // 这是判断头不跟手的决定性证据：
  //   - 若 我设的 currentX 在变，但 模型实际 ParamAngleX 不变 → setParams 没生效（渲染库覆盖问题）
  //   - 若 两者都在变，但你肉眼觉得头没动 → 是幅度/视觉问题，继续加大即可
  //   - 若 我设的 currentX 一直≈0 → 没收到手部数据（看上面的 [追踪] 日志）
  if (state.modelReady && typeof state.l2d.getParams === "function") {
    if (!state._paramLogAt || now - state._paramLogAt > 1500) {
      state._paramLogAt = now;
      try {
        const params = state.l2d.getParams();
        const angleX = params.find((p) => p.id === "ParamAngleX");
        if (angleX) {
          console.info(
            "[模型] ParamAngleX 实际生效=",
            Number(angleX.value).toFixed(2),
            " | 我设的 currentX=",
            state.tracking.currentX.toFixed(2),
          );
        }
      } catch (error) {
        // getParams 偶发失败不影响渲染，忽略
      }
    }
  }

  requestAnimationFrame(animationLoop);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderHands(hands) {
  if (!Array.isArray(hands) || hands.length === 0) {
    dom.handsList.innerHTML = '<p class="empty">等待手势输入</p>';
    return;
  }

  dom.handsList.innerHTML = hands.map((item) => {
    const center = item.features?.center_norm || ["?", "?"];
    const depth = item.features?.depth || {};
    const motion = item.motion?.type || "STILL";
    return `
      <article class="hand-card">
        <span>Hand ${escapeHtml(item.index)} [${escapeHtml(item.label || "?")}] · zone=${escapeHtml(item.zone || "free")}</span>
        <strong>${escapeHtml(item.gesture || "UNKNOWN")}</strong>
        <span>${escapeHtml(item.command || "CMD_NONE")}</span>
        <span>pos=[${escapeHtml(center[0])}, ${escapeHtml(center[1])}] z=${escapeHtml(depth.z ?? "?")} scale=${escapeHtml(depth.scale ?? "?")}</span>
        <span>motion=${escapeHtml(motion)} fingers=${escapeHtml(JSON.stringify(item.fingers || []))}</span>
      </article>
    `;
  }).join("");
}

function updateMetrics(packet, command) {
  dom.gesture.textContent = packet.gesture || "UNKNOWN";
  dom.command.textContent = command;

  if (typeof packet.timestamp === "number") {
    const latency = Math.max(0, (Date.now() / 1000 - packet.timestamp) * 1000);
    dom.latency.textContent = `${latency.toFixed(1)} ms`;
  } else {
    dom.latency.textContent = "-- ms";
  }
}

function handleGesturePacket(packet) {
  if (!packet || packet.type !== "gesture_command") {
    return;
  }

  const command = resolveCommand(packet);
  const hands = Array.isArray(packet.hands) ? packet.hands : [];

  updateMetrics(packet, command);
  renderHands(hands);
  applyHandTracking(hands);
  executeResponse(command, packet);
}

function connectWebSocket() {
  if (state.socket) {
    state.socket.close();
  }

  const socket = new WebSocket(getWebSocketUrl());
  state.socket = socket;
  setConnection(false, "WebSocket 连接中");

  socket.addEventListener("open", () => {
    setConnection(true, "WebSocket 已连接");
  });

  socket.addEventListener("message", (event) => {
    try {
      const packet = JSON.parse(event.data);
      if (packet.type === "bridge_status") {
        return;
      }
      handleGesturePacket(packet);
    } catch (error) {
      console.warn("WebSocket 消息解析失败", error);
    }
  });

  socket.addEventListener("close", () => {
    setConnection(false, "WebSocket 已断开，准备重连");
    clearTimeout(state.reconnectTimer);
    state.reconnectTimer = setTimeout(connectWebSocket, CONFIG.reconnectDelay);
  });

  socket.addEventListener("error", () => {
    setConnection(false, "WebSocket 连接异常");
  });
}

// 完整性检查：RESPONSE_MAP 里除 CMD_NONE 外的每个命令，都应该出现在测试面板里。
// 漏掉的命令会在浏览器控制台用警告列出来，提醒你补测试按钮。
function warnMissingTestCommands() {
  const tested = new Set();
  for (const group of TEST_GROUPS) {
    for (const item of group.items) {
      tested.add(item.command);
    }
  }

  const missing = Object.keys(RESPONSE_MAP)
    .filter((command) => command !== "CMD_NONE")
    .filter((command) => !tested.has(command));

  if (missing.length > 0) {
    console.warn("以下命令在 RESPONSE_MAP 里有响应，但测试面板缺少按钮：", missing);
  }
}

function createTestButtons() {
  warnMissingTestCommands();

  // 按分组渲染：每组一个小标题，下面是该组的动作按钮。
  // 按钮上显示中文效果名（来自 RESPONSE_MAP.label）+ 触发手势，比纯英文命令名直观得多。
  dom.testButtons.innerHTML = TEST_GROUPS.map((group) => {
    const buttons = group.items.map((item) => {
      const response = RESPONSE_MAP[item.command];
      const label = (response && response.label) || item.command.replace("CMD_", "");
      return `
        <button type="button" data-command="${item.command}" title="${item.command}">
          <strong>${label}</strong>
          <span>${item.gesture}</span>
        </button>
      `;
    }).join("");

    return `
      <div class="test-group">
        <h4>${group.title}</h4>
        <div class="test-group-grid">${buttons}</div>
      </div>
    `;
  }).join("");

  dom.testButtons.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-command]");
    if (!button) {
      return;
    }

    const command = button.dataset.command;
    const testFeatureMap = {
      CMD_LOOK_LEFT: { center_3d: [0.22, 0.48, 0], center_norm: [0.22, 0.48], depth: { scale: 0.32 }, motion: "SWIPE_LEFT" },
      CMD_LOOK_RIGHT: { center_3d: [0.78, 0.48, 0], center_norm: [0.78, 0.48], depth: { scale: 0.32 }, motion: "SWIPE_RIGHT" },
      CMD_JUMP_SURPRISE: { center_3d: [0.52, 0.2, 0], center_norm: [0.52, 0.2], depth: { scale: 0.3 }, motion: "RAISE_UP" },
      CMD_BOW: { center_3d: [0.52, 0.75, 0], center_norm: [0.52, 0.75], depth: { scale: 0.3 }, motion: "MOVE_DOWN" },
      CMD_COME_CLOSER: { center_3d: [0.5, 0.5, -0.15], center_norm: [0.5, 0.5], depth: { scale: 0.56 }, motion: "PUSH_IN" },
      CMD_STEP_BACK: { center_3d: [0.5, 0.5, 0.08], center_norm: [0.5, 0.5], depth: { scale: 0.18 }, motion: "PULL_OUT" },
      CMD_PET_HEAD: { center_3d: [0.5, 0.28, -0.04], center_norm: [0.5, 0.28], depth: { scale: 0.4 }, motion: "STILL" },
    };
    const testFeature = testFeatureMap[command] || {
      center_3d: [0.56, 0.52, 0],
      center_norm: [0.56, 0.52],
      depth: { scale: 0.34 },
      motion: "STILL",
    };

    handleGesturePacket({
      version: 1,
      type: "gesture_command",
      source: "LocalTest",
      gesture: command.replace("CMD_", "TEST_"),
      command,
      hand: "Right",
      hands: [
        {
          index: 0,
          label: "R",
          hand: "Left",
          gesture: command.replace("CMD_", "TEST_"),
          command,
          fingers: [1, 1, 1, 1, 1],
          zone: command === "CMD_PET_HEAD" ? "head" : "body",
          motion: { type: testFeature.motion, dx: 0, dy: 0, dscale: 0 },
          features: testFeature,
        },
      ],
      timestamp: Date.now() / 1000,
    });
  });
}

function unlockAudio() {
  // 先解锁语音合成（TTS）：浏览器要求必须在用户点击等交互里首次调用才会允许出声，
  // 这里念一个空串相当于"预热"，之后命令台词才能正常发声。
  state.audioEnabled = true;
  if (window.speechSynthesis) {
    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
    } catch (error) {
      console.warn("语音预热失败", error);
    }
  }

  // 再解锁模型自带 wav 音量（部分动作带原声）。即使模型不支持也不影响 TTS。
  if (state.l2d && typeof state.l2d.setVolume === "function") {
    state.l2d.setVolume(0.85);
  }

  dom.enableAudio.textContent = "角色声音已开启";
  dom.enableAudio.classList.add("is-enabled");
}

async function loadModel(path, label) {
  setLoading(8, `加载 ${label}`);
  await state.l2d.load({
    path,
    scale: MODEL_PROFILE.modelScale,
    position: MODEL_PROFILE.modelPosition,
    volume: 0,
  });
}

async function initLive2D() {
  resizeCanvas();
  state.l2d = initL2D(dom.canvas);
  if (!state.l2d) {
    setLoading(100, "L2D 初始化失败，请检查 canvas 元素");
    return;
  }

  state.l2d.on("loadstart", (total) => {
    setLoading(12, `开始加载 ${total} 个模型文件`);
  });

  state.l2d.on("loadprogress", (loaded, total, file) => {
    const percent = total > 0 ? Math.round((loaded / total) * 80) + 12 : 24;
    setLoading(percent, `加载中 ${loaded}/${total} · ${file || ""}`);
  });

  state.l2d.on("loaded", () => {
    state.modelReady = true;
    setLoading(100, `${MODEL_PROFILE.name} 已就绪`);
    dom.loadingCard.classList.add("is-hidden");

    console.info("可用动作", state.l2d.getMotions?.());
    console.info("可用表情", state.l2d.getExpressions?.());
    tryPlayMotion(RESPONSE_MAP.CMD_IDLE);
  });

  state.l2d.on("motionstart", (group, index, duration, file) => {
    console.info("动作开始", group, index, duration, file);
  });

  state.l2d.on("expressionchange", (id) => {
    console.info("表情切换", id);
  });

  try {
    await loadModel(MODEL_PROFILE.modelPath, `本地 ${MODEL_PROFILE.name} 模型`);
  } catch (error) {
    console.warn("本地模型加载失败，尝试 CDN 模型", error);
    await loadModel(MODEL_PROFILE.fallbackModelPath, `CDN ${MODEL_PROFILE.name} 模型`);
  }
}

async function init() {
  createTestButtons();
  setCostumeEffect("soft");
  dom.enableAudio.addEventListener("click", unlockAudio);
  window.addEventListener("resize", resizeCanvas);

  await initLive2D();
  connectWebSocket();
  animationLoop();
}

init();
