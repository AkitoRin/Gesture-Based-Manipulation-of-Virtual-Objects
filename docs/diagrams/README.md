# HandPilot 图表资产

本目录保存项目文档使用的 SVG 图表、Draw.io 可编辑源文件和生成脚本。

## 图表索引

| 文件 | 用途 |
| --- | --- |
| `handpilot_system_architecture.svg` | 系统全景：视觉采集、Python 决策、Bridge 与 Web Live2D |
| `handpilot_frame_pipeline.svg` | 单帧流水线：识别、平滑、空间交互、发包与下一帧循环 |
| `handpilot_realtime_link.svg` | 实时链路：UDP、WebSocket、数据包和调试边界 |
| `handpilot_architecture.drawio` | 上述三张图的 Draw.io 可编辑版本，每张图对应一个页面 |
| `generate_handpilot_diagrams.py` | SVG 与 Draw.io 资产生成脚本 |

## 查看与编辑

- SVG 可直接在浏览器或 VS Code 中打开，并通过缩放查看细节
- Draw.io 文件可使用 VS Code Draw.io 插件或 diagrams.net 打开
- Mermaid 适合简单流程，复杂图表使用 SVG 可避免 Markdown 预览中内容过小

## 重新生成

在项目根目录执行：

```powershell
python docs/diagrams/generate_handpilot_diagrams.py
```

生成脚本只依赖 Python 标准库。
