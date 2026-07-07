# Pi5 Dashboard — 树莓派5 设备监控面板

一套运行在 **树莓派5 (8GB RAM)** 上的全屏设备监控仪表盘，集成系统监控、实时新闻、AI 沟通记录和猎聘自动投递功能。

> 适配 Waveshare 3.5寸 DPI LCD 显示屏（803×602），基于 labwc Wayland 合成器。

![Dashboard](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red?logo=raspberrypi)
![Display](https://img.shields.io/badge/Display-3.5%22%20DPI%20LCD-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 功能模块

| 模块 | 说明 |
|------|------|
| 🔥 **实时新闻** | 百度热搜 + 微博热搜 + BBC/Guardian 国际新闻，每10分钟自动刷新 |
| ⚽ **世界杯赛区** | 跑马灯滚动展示当日比赛信息 |
| 📊 **系统监控** | CPU/内存/磁盘/网络实时统计卡片 + 环形仪表盘 |
| 📋 **进程管理** | TOP 8 高负载进程表格，按 CPU 着色 |
| 💼 **猎聘自动投递** | 可视化控制台，支持定时/循环/手动投递 |
| 💬 **沟通记录** | 从 Hermes Agent DB 同步多平台聊天记录 + AI 思考过程 |
| 🌡️ **温度传感器** | CPU/GPU/PMIC/环境 四路温度监控 |
| 🖥️ **系统信息** | 主机名、内核、运行时间等基础信息 |

---

## 🏗️ 架构

```
labwc (Wayland)  Ctrl+Alt+D
        │
        ▼
dashboard-toggle.sh  （总开关脚本）
   ├── 启动 → Chromium 全屏 (X11 + xdotool F11)
   ├── 启动 → dashboard-news-fetcher.py (后台抓取新闻)
   ├── 启动 → liepin_dashboard_server.py (HTTP API)
   └── 切换 → 检测运行则 kill，否则启动
```

### 数据流

```
dashboard-news-fetcher.py  →  /tmp/world-news-dashboard.js      ⤶
dashboard-comm-writer.py   →  /tmp/dashboard-comm.js            ⤷  2秒刷新
liepin_dashboard_server.py →  /tmp/liepin-dashboard.js          ⤶  HTML 动态加载
系统数据 (JS 模拟)          →  内置 JavaScript                   ⤷
```

---

## 📦 文件说明

| 文件 | 说明 |
|------|------|
| `device-monitor-dashboard.html` | 主仪表盘 — 单文件 Web 应用 (1588行, 60KB) |
| `scripts/dashboard-toggle.sh` | 切换脚本 — 总开关 + 后台服务管理 |
| `scripts/dashboard-news-fetcher.py` | 新闻抓取 — RSS + 热搜爬虫 (236行) |
| `scripts/dashboard-comm-writer.py` | 沟通日志 — 从 Hermes DB 提取消息 |
| `scripts/liepin_dashboard_server.py` | 猎聘 API — HTTP 控制服务 (333行, 端口8787) |
| `scripts/chromium-fullscreen.sh` | 备用全屏启动脚本 |
| `config/labwc-rc.xml` | labwc 窗口管理器配置参考（快捷键绑定） |

---

## 🚀 部署指南

### 环境要求

- 树莓派5 (8GB) / Raspberry Pi OS
- labwc (Wayland 合成器)
- Chromium 浏览器
- Python 3.11+
- xdotool (X11 工具)
- grim (Wayland 截图工具)

### 快速部署

```bash
# 1. 安装依赖
sudo apt install chromium xdotool grim

# 2. 克隆仓库
git clone https://github.com/Supergodgg/Pi5-dashboard.git
cd Pi5-dashboard

# 3. 复制文件到系统路径
cp device-monitor-dashboard.html /home/pi/
cp scripts/* /home/pi/.local/bin/
chmod +x /home/pi/.local/bin/dashboard-toggle.sh

# 4. 配置 labwc 快捷键 (Ctrl+Alt+D)
# 将 config/labwc-rc.xml 中的 keybind 合并到 ~/.config/labwc/rc.xml

# 5. 重启 labwc 使配置生效
```

### 使用

- **Ctrl+Alt+D** — 显示/隐藏仪表盘
- 仪表盘每 **2 秒**自动刷新系统数据
- 新闻每 **10 分钟**自动更新
- 猎聘面板可通过 UI 按钮控制投递

---

## 🎨 设计

- **Apple / Notion 浅色简约风格**
- 液态玻璃效果 (`backdrop-filter: blur(18px)`)
- Inter 字体，柔和阴影，圆角卡片
- 响应式布局，适配 803×602 小屏
- CPU/内存面板在所有断点保持并排

---

## 📄 License

MIT © Supergodgg
