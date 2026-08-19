# -Hackintosh-One-Click-Assistant-
更简单的一体式软件
# 🍎 黑苹果一键辅助工具 (Hackintosh One-Click Assistant)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.11.2-green.svg)](https://pypi.org/project/PySide6/)

一个面向黑苹果玩家的**一站式图形化辅助工具**，集成了 EFI 生成、镜像下载、分区烧录三大核心功能。

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| ⚙️ **生成 EFI** | 调用 OpCore-Simplify，一键生成 OpenCore EFI 引导文件 |
| 📥 **下载镜像** | 列出各大网盘的 macOS 恢复版镜像链接，双击即可复制 |
| 📀 **烧录分区** | 将镜像烧录到**指定分区**（支持双系统，不影响其他分区） |
| 🛡️ **安全防护** | 确认 + 系统盘保护 + 管理员提权 + 取消烧录 |
| 🌐 **中英双语** | 所有界面中英双语显示，方便国内外用户 |

---

## 📦 下载与安装

### 方式一：下载源码运行（需要 Python 环境）

```bash
git clone https://github.com/你的用户名/HackintoshTool.git
cd HackintoshTool

# 安装依赖
pip install PySide6

# 运行
python main.py


🛠️ 使用说明
生成 EFI：点击卡片 → 自动打开 OpCore-Simplify，生成适合你硬件的 EFI

下载镜像：点击卡片 → 列出所有镜像网盘链接，双击复制

烧录分区：点击卡片 → 选择镜像文件 → 选择目标分区 → 三次确认后开始烧录

⚠️ 注意事项
烧录功能需要管理员权限

烧录前请备份目标分区的重要数据

系统分区（C盘）有额外警告，请仔细确认

📁 项目结构
text
HackintoshTool/
├── main.py              # 主程序
├── 启动工具.bat         # 一键启动脚本
├── bin/
│   └── dd.exe           # 烧录核心工具 (GPL v2)
└── tools/
    └── OpCore-Simplify/ # EFI 生成工具
🔧 开发环境
Python 3.8+

PySide6

Windows 10/11（理论上也支持 macOS/Linux，但烧录功能需要 Windows）

📜 许可证
本项目采用 MIT License，你可以自由使用、修改和分发。

但请注意：

bin/dd.exe 遵循 GPL v2 许可证

tools/OpCore-Simplify/ 遵循其作者指定的许可证

🤝 致谢
OpCore-Simplify - EFI 自动生成工具

dd for Windows - 磁盘写入工具

PySide6 - Qt for Python

⭐ Star 支持
如果这个工具对你有帮助，请给一个 ⭐ Star 支持一下！

📧 联系方式
提交 Issue：GitHub Issues

欢迎 PR 贡献代码

# 🍎 Hackintosh One-Click Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.11.2-green.svg)](https://pypi.org/project/PySide6/)

A **one-stop graphical assistant** for Hackintosh users, integrating **EFI generation**, **image downloading**, and **partition burning** into a single modern UI.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| ⚙️ **Generate EFI** | Launches OpCore-Simplify to auto-generate OpenCore EFI bootloader |
| 📥 **Download Image** | Lists macOS recovery image links from major cloud drives, double-click to copy |
| 📀 **Burn Partition** | Writes image to a **selected partition** (supports dual-boot, leaves other partitions untouched) |
| 🛡️ **Safety First** | Triple confirmation + system disk protection + admin elevation + burn cancellation |
| 🌐 **Bilingual UI** | All interface texts displayed in both Chinese and English (main + subtitle) |

---

## 🖥️ Preview

![Main Interface](screenshot.png)

---

## 📦 Installation & Usage

### Option 1: Run from source (Python required)

```bash
git clone https://github.com/your-username/HackintoshTool.git
cd HackintoshTool

# Install dependencies
pip install PySide6

# Run
python main.py
