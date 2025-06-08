# BBDown-Remote-GUI

一个基于 PyQt5 开发的 BBDown 远程 GUI 客户端，用于通过图形界面管理 BBDown 下载任务。

## 📖 项目简介

BBDown-Remote-GUI 是 [BBDown](https://github.com/nilaoda/BBDown) 的远程图形用户界面客户端。它通过 HTTP API 与 BBDown 服务器通信，提供了一个直观易用的图形界面来管理 B站视频下载任务。

## ✨ 主要功能

### 🎯 任务管理
- **实时任务监控**: 查看正在运行和已完成的下载任务
- **任务仪表盘**: 直观显示任务进度、下载速度、文件大小等信息
- **批量操作**: 支持批量移除已完成或失败的任务
- **任务详情**: 查看单个任务的详细信息

### 🛠️ 下载配置
- **基本选项**: URL输入、仅显示信息、交互模式等
- **API选择**: 支持TV API、App API、国际版API
- **内容选择**: 视频质量、音频质量、字幕下载等
- **下载控制**: 多线程下载、重试次数、超时设置
- **文件命名**: 自定义文件名格式和路径
- **网络设置**: 代理配置、User-Agent设置
- **高级选项**: 音视频编码、合并选项等

### 🎨 用户界面
- **现代化界面**: 基于 PyQt5 的美观界面设计
- **选项卡布局**: 任务仪表盘、添加任务、任务管理三个主要功能区
- **可折叠选项组**: 整洁的选项分类和展示
- **实时刷新**: 自动刷新任务状态和进度

## 🚀 快速开始

### 环境要求

- Python 3.7+
- PyQt5
- requests
- BBDown 服务器（需要启用 HTTP API）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python bbdown_gui.py
```

## 📦 构建可执行文件

### Windows

```bash
pyinstaller --onefile --windowed --name BBDown_GUI --icon bbdown_icon.ico bbdown_gui.py
```

### macOS

```bash
pyinstaller --windowed --name BBDown_GUI --icon bbdown_icon.icns bbdown_gui.py
```

## 🔧 配置说明

### BBDown 服务器配置

在使用本 GUI 客户端之前，需要确保 BBDown 服务器已启用 HTTP API 功能。

1. 启动 BBDown 服务器时添加 `serve -l http://0.0.0.0:{port}` 参数
2. 在 GUI 中配置正确的服务器地址和端口

### 连接设置

- **主机地址**: 默认为 `localhost`
- **端口**: 默认为 `58682`
- **超时**: 网络请求超时时间

## 📋 功能详解

### 任务仪表盘

- 显示所有正在运行的下载任务
- 显示已完成的任务历史
- 实时更新任务进度和状态
- 支持查看任务详情和移除任务

### 添加任务

支持多种下载选项配置：

#### 基本选项
- 视频 URL 或 BV/AV 号输入
- 仅显示信息模式
- 交互式选择模式
- 区域和语言设置

#### API 选项
- TV API（默认）
- App API
- 国际版 API
- 自定义 TV API 主机

#### 内容选择
- 视频质量选择
- 音频质量选择
- 字幕语言选择
- 仅下载音频/视频

#### 下载控制
- 多线程下载数量
- 重试次数设置
- 下载超时时间
- 跳过已存在文件

### 任务管理

- 批量移除所有已完成任务
- 批量移除所有失败任务
- 按 AID 移除特定任务

## 🎨 界面预览

程序采用现代化的选项卡式界面设计：

1. **任务仪表盘**: 分为运行中任务和已完成任务两个区域
2. **添加任务**: 可折叠的选项组，包含所有下载配置
3. **任务管理**: 批量操作和单个任务管理功能

## 🔄 自动化构建

项目配置了 GitHub Actions 自动构建：

- **Windows**: 构建 `.exe` 可执行文件
- **macOS**: 构建 `.app` 应用程序包

构建产物会自动上传为 GitHub Actions 的 artifacts。

## 📝 开发说明

### 项目结构

```
BBDown-Remote-GUI/
├── bbdown_gui.py          # 主程序文件
├── requirements.txt       # Python 依赖
├── BBDown-GUI.spec       # PyInstaller 配置
├── bbdown_icon.*         # 应用图标文件
├── .github/workflows/    # GitHub Actions 配置
├── hooks/                # PyInstaller 钩子
├── build/                # 构建临时文件
└── dist/                 # 构建输出目录
```

### 主要组件

- `BBDownAPIClient`: BBDown API 客户端
- `APITaskThread`: 异步 API 请求线程
- `OptionsForm`: 下载选项配置表单
- `BBDownGUI`: 主窗口和界面逻辑

### 性能优化

- 使用多线程处理 API 请求，避免界面卡顿
- 优化表格更新逻辑，减少不必要的 UI 刷新
- 实现选项组的折叠功能，提升界面响应速度

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目！

### 开发环境设置

1. Fork 本仓库
2. 克隆到本地
3. 安装依赖：`pip install -r requirements.txt`
4. 进行开发和测试
5. 提交 Pull Request

## 📄 许可证

本项目采用开源许可证，具体请查看 LICENSE 文件。

## 🙏 致谢

- [BBDown](https://github.com/nilaoda/BBDown) - 优秀的 B站视频下载工具
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - 强大的 Python GUI 框架

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发起 Pull Request
- 在项目讨论区交流

---

**注意**: 使用本工具下载视频时，请遵守相关网站的服务条款和版权法律法规。