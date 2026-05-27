// =============================================================================
// 文件：bridge/udp_to_ws.js
// 职责：【桥接层 - UDP 转 WebSocket + 静态网页服务】
//       接收 Python 端发来的 UDP JSON，再转发给浏览器里的 Live2D 页面
//       同时提供 http://127.0.0.1:8765 用于打开 web/index.html
// =============================================================================

const dgram = require("dgram");
const fs = require("fs");
const http = require("http");
const path = require("path");
const { WebSocket, WebSocketServer } = require("ws");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const WEB_ROOT = path.resolve(PROJECT_ROOT, "web");

const UDP_HOST = process.env.HANDPILOT_UDP_HOST || "127.0.0.1";
const UDP_PORT = Number(process.env.HANDPILOT_UDP_PORT || 5005);
const WEB_HOST = process.env.HANDPILOT_WEB_HOST || "127.0.0.1";
const WEB_PORT = Number(process.env.HANDPILOT_WEB_PORT || 8765);

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".wav": "audio/wav",
  ".moc3": "application/octet-stream",
  ".model3": "application/json; charset=utf-8",
  ".physics3": "application/json; charset=utf-8",
  ".pose3": "application/json; charset=utf-8",
  ".exp3": "application/json; charset=utf-8",
  ".motion3": "application/json; charset=utf-8",
  ".userdata3": "application/json; charset=utf-8",
  ".cdi3": "application/json; charset=utf-8",
};

let wsClientCount = 0;
let udpPacketCount = 0;

function log(message) {
  const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  console.log(`[${time}] ${message}`);
}

function resolveWebFile(requestUrl) {
  const url = new URL(requestUrl, `http://${WEB_HOST}:${WEB_PORT}`);
  const pathname = decodeURIComponent(url.pathname);
  const relativePath = pathname === "/" ? "index.html" : pathname.slice(1);
  const candidate = path.resolve(WEB_ROOT, relativePath);

  // 防止通过 ../ 访问 web 目录之外的文件
  if (candidate !== WEB_ROOT && !candidate.startsWith(WEB_ROOT + path.sep)) {
    return null;
  }

  return candidate;
}

function sendFile(response, filePath) {
  fs.readFile(filePath, (error, data) => {
    if (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("404 Not Found");
      return;
    }

    const ext = path.extname(filePath);
    const type = MIME_TYPES[ext] || "application/octet-stream";
    response.writeHead(200, {
      "Content-Type": type,
      "Cache-Control": "no-cache",
    });
    response.end(data);
  });
}

function createHttpServer() {
  return http.createServer((request, response) => {
    const filePath = resolveWebFile(request.url);
    if (!filePath) {
      response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("403 Forbidden");
      return;
    }

    sendFile(response, filePath);
  });
}

function createWebSocketServer(httpServer) {
  const wss = new WebSocketServer({ server: httpServer, path: "/ws" });

  wss.on("connection", (socket) => {
    wsClientCount += 1;
    log(`WebSocket 客户端已连接，当前 ${wsClientCount} 个`);

    socket.send(JSON.stringify({
      type: "bridge_status",
      source: "HandPilotBridge",
      message: "connected",
      udpTarget: `${UDP_HOST}:${UDP_PORT}`,
    }));

    socket.on("close", () => {
      wsClientCount = Math.max(0, wsClientCount - 1);
      log(`WebSocket 客户端已断开，当前 ${wsClientCount} 个`);
    });
  });

  return wss;
}

function broadcast(wss, payload) {
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  }
}

function createUdpServer(wss) {
  const udp = dgram.createSocket("udp4");

  udp.on("message", (buffer, remote) => {
    const text = buffer.toString("utf8");
    udpPacketCount += 1;

    try {
      const message = JSON.parse(text);
      broadcast(wss, JSON.stringify(message));

      const command = message.command || "UNKNOWN";
      const gesture = message.gesture || "UNKNOWN";
      const handsCount = Array.isArray(message.hands) ? message.hands.length : 0;
      log(
        `UDP #${udpPacketCount} ${remote.address}:${remote.port} ` +
        `gesture=${gesture} command=${command} hands=${handsCount}`,
      );
    } catch (error) {
      log(`收到非 JSON UDP 数据，已忽略：${error.message}`);
    }
  });

  udp.on("error", (error) => {
    if (error.code === "EADDRINUSE") {
      log(`UDP 端口已被占用：${UDP_HOST}:${UDP_PORT}`);
      log("请先关闭 tools/udp_receiver_test.py 或另一个 Bridge");
    } else {
      log(`UDP 服务错误：${error.message}`);
    }
    udp.close();
  });

  udp.bind(UDP_PORT, UDP_HOST, () => {
    log(`UDP 监听已启动：${UDP_HOST}:${UDP_PORT}`);
  });

  return udp;
}

function main() {
  const httpServer = createHttpServer();
  const wss = createWebSocketServer(httpServer);
  const udp = createUdpServer(wss);

  httpServer.on("error", (error) => {
    if (error.code === "EADDRINUSE") {
      log(`HTTP/WebSocket 端口已被占用：${WEB_HOST}:${WEB_PORT}`);
      log("请先关闭另一个 Bridge，或修改 HANDPILOT_WEB_PORT");
    } else {
      log(`HTTP 服务错误：${error.message}`);
    }

    udp.close();
    wss.close();
    process.exit(1);
  });

  httpServer.listen(WEB_PORT, WEB_HOST, () => {
    log(`Live2D 页面：http://${WEB_HOST}:${WEB_PORT}`);
    log(`WebSocket：ws://${WEB_HOST}:${WEB_PORT}/ws`);
    log("按 Ctrl+C 退出桥接服务");
  });

  process.on("SIGINT", () => {
    log("正在关闭桥接服务");
    udp.close();
    wss.close();
    httpServer.close(() => process.exit(0));
  });
}

main();
