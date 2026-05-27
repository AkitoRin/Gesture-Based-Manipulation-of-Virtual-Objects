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
  TEST_COMMANDS,
} from "./live2d_profiles/haru.js";

const CONFIG = {
  reconnectDelay: 1800,
  duplicateCooldown: 700,
  motionCooldown: 420,
  petCooldown: 1200,
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

function tryPlayMotion(response) {
  if (!state.modelReady || !state.l2d || !response) {
    return;
  }

  const signature = response.motionFile ||
    (response.motion ? `${response.motion.group}:${response.motion.index}` : "");

  if (signature && signature === state.lastMotion && response.label !== "摸头害羞") {
    return;
  }

  try {
    if (response.motionFile && typeof state.l2d.playMotionByFile === "function") {
      state.l2d.playMotionByFile(response.motionFile, response.motionPriority || 3);
      state.lastMotion = signature;
      return;
    }

    if (response.motion) {
      const { group, index, priority } = response.motion;
      state.l2d.playMotion(group, index, priority);
      state.lastMotion = signature;
    }
  } catch (error) {
    console.warn("动作播放失败，尝试 fallback", error);
    if (response.fallbackMotion) {
      const { group, index, priority } = response.fallbackMotion;
      state.l2d.playMotion(group, index, priority);
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
  const isMotionCommand = command.startsWith("CMD_LOOK_") ||
    ["CMD_JUMP_SURPRISE", "CMD_BOW", "CMD_COME_CLOSER", "CMD_STEP_BACK"].includes(command);
  const cooldown = command === "CMD_PET_HEAD"
    ? CONFIG.petCooldown
    : isMotionCommand
      ? CONFIG.motionCooldown
      : CONFIG.duplicateCooldown;

  dom.response.textContent = response.label;
  setCostumeEffect(response.costume);

  if (command === "CMD_NONE") {
    return;
  }

  if (command === state.lastCommand && now - state.lastCommandAt < cooldown) {
    return;
  }

  state.lastCommand = command;
  state.lastCommandAt = now;

  trySetExpression(response.expression);
  tryPlayMotion(response);
  applyBurst(response.burst);
  speak(response.speech);

  if (packet && packet.source === "LocalTest") {
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
  state.tracking.targetX = clamp((center[0] - 0.5) * 58, -32, 32);
  state.tracking.targetY = clamp((0.5 - center[1]) * 42, -24, 24);
  state.tracking.targetZ = clamp((scale - 0.34) * 3.2, -0.75, 0.9);
  state.tracking.targetScale = scale;
  state.tracking.lastSeenAt = performance.now();

  dom.trackingOrb.style.left = `${clamp(center[0] * 100, 4, 96)}%`;
  dom.trackingOrb.style.top = `${clamp(center[1] * 100, 4, 96)}%`;
  dom.trackingOrb.title = `tracking ${motion}`;
  dom.trackingOrb.classList.add("is-visible");
}

function animationLoop() {
  const t = performance.now() / 1000;
  const now = performance.now();
  const trackingFresh = now - state.tracking.lastSeenAt < 900;
  const followSpeed = trackingFresh ? 0.14 : 0.06;

  if (!trackingFresh) {
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

function createTestButtons() {
  dom.testButtons.innerHTML = TEST_COMMANDS.map((command) => (
    `<button type="button" data-command="${command}">${command.replace("CMD_", "")}</button>`
  )).join("");

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
  if (!state.l2d || typeof state.l2d.setVolume !== "function") {
    return;
  }

  state.l2d.setVolume(0.85);
  state.audioEnabled = true;
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
