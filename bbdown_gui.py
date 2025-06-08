import sys
import os
import json
import requests
import ctypes
import subprocess
import platform
import zipfile
import tarfile
from datetime import datetime
from urllib.parse import urlparse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTextEdit, QSplitter, QGroupBox, 
    QCheckBox, QComboBox, QGridLayout, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QBrush, QColor, QIcon, QIntValidator

# 优化事件循环设置
if sys.platform == "win32":
    # 设置Windows进程优先级为高
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00008000)
    except:
        pass

class BBDownAPIClient:
    def __init__(self, host="localhost", port=58682):
        self.base_url = f"http://{host}:{port}"
    
    def get_tasks(self):
        try:
            response = requests.get(f"{self.base_url}/get-tasks/", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"获取任务失败: {str(e)}")
            return None
    
    def get_running_tasks(self):
        try:
            response = requests.get(f"{self.base_url}/get-tasks/running", timeout=5)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"获取运行中任务失败: {str(e)}")
            return []
    
    def get_finished_tasks(self):
        try:
            response = requests.get(f"{self.base_url}/get-tasks/finished", timeout=5)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"获取已完成任务失败: {str(e)}")
            return []
    
    def get_task(self, aid):
        try:
            response = requests.get(f"{self.base_url}/get-tasks/{aid}", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"获取任务详情失败: {str(e)}")
            return None
    
    def add_task(self, url, options=None):
        data = {"Url": url}
        if options:
            data.update(options)
        try:
            response = requests.post(
                f"{self.base_url}/add-task",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"添加任务失败: {str(e)}")
            return False
    
    def remove_finished_tasks(self):
        try:
            response = requests.get(f"{self.base_url}/remove-finished", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"移除已完成任务失败: {str(e)}")
            return False
    
    def remove_failed_tasks(self):
        try:
            response = requests.get(f"{self.base_url}/remove-finished/failed", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"移除失败任务失败: {str(e)}")
            return False
    
    def remove_task(self, aid):
        try:
            response = requests.get(f"{self.base_url}/remove-finished/{aid}", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"移除特定任务失败: {str(e)}")
            return False

# 网络请求线程
class APITaskThread(QThread):
    finished = pyqtSignal(object)
    
    def __init__(self, api_client, task_type, *args, **kwargs):
        super().__init__()
        self.api_client = api_client
        self.task_type = task_type
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            if self.task_type == "get_tasks":
                result = self.api_client.get_tasks()
            elif self.task_type == "get_running_tasks":
                result = self.api_client.get_running_tasks()
            elif self.task_type == "get_finished_tasks":
                result = self.api_client.get_finished_tasks()
            elif self.task_type == "get_task":
                result = self.api_client.get_task(*self.args)
            elif self.task_type == "add_task":
                result = self.api_client.add_task(*self.args, **self.kwargs)
            elif self.task_type == "remove_finished_tasks":
                result = self.api_client.remove_finished_tasks()
            elif self.task_type == "remove_failed_tasks":
                result = self.api_client.remove_failed_tasks()
            elif self.task_type == "remove_task":
                result = self.api_client.remove_task(*self.args)
            else:
                result = None
                
            self.finished.emit(result)
        except Exception as e:
            print(f"API线程错误: {str(e)}")
            self.finished.emit(None)

# BBDown下载和管理线程
class BBDownManagerThread(QThread):
    progress = pyqtSignal(str)  # 进度信息
    finished = pyqtSignal(bool, str)  # 完成状态和消息
    
    def __init__(self, action="download", bbdown_path=None):
        super().__init__()
        self.action = action
        self.bbdown_path = bbdown_path
        
    def run(self):
        try:
            if self.action == "download":
                self.download_bbdown()
            elif self.action == "start":
                self.start_bbdown_server()
        except Exception as e:
            self.finished.emit(False, f"操作失败: {str(e)}")
    
    def download_bbdown(self):
        """下载最新版本的BBDown"""
        try:
            self.progress.emit("正在获取最新版本信息...")
            
            # 获取最新版本信息
            releases_url = "https://api.github.com/repos/nilaoda/BBDown/releases/latest"
            response = requests.get(releases_url, timeout=30)
            if response.status_code != 200:
                raise Exception("无法获取版本信息")
            
            release_data = response.json()
            tag_name = release_data["tag_name"]
            assets = release_data["assets"]
            
            # 确定当前系统和架构
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            # 映射系统和架构名称
            if system == "darwin":
                if machine in ["arm64", "aarch64"]:
                    target_name = "osx-arm64"
                else:
                    target_name = "osx-x64"
            elif system == "windows":
                if machine in ["amd64", "x86_64"]:
                    target_name = "win-x64"
                else:
                    target_name = "win-x86"
            elif system == "linux":
                if machine in ["aarch64", "arm64"]:
                    target_name = "linux-arm64"
                elif machine in ["amd64", "x86_64"]:
                    target_name = "linux-x64"
                else:
                    target_name = "linux-x86"
            else:
                raise Exception(f"不支持的系统: {system}")
            
            # 查找匹配的资源
            download_url = None
            for asset in assets:
                if target_name in asset["name"]:
                    download_url = asset["browser_download_url"]
                    break
            
            if not download_url:
                raise Exception(f"未找到适合 {system}-{machine} 的版本")
            
            self.progress.emit(f"正在下载 {tag_name} 版本...")
            
            # 创建BBDown目录
            bbdown_dir = os.path.join(os.path.expanduser("~"), ".bbdown")
            os.makedirs(bbdown_dir, exist_ok=True)
            
            # 下载文件
            filename = os.path.basename(urlparse(download_url).path)
            download_path = os.path.join(bbdown_dir, filename)
            
            response = requests.get(download_url, stream=True, timeout=60)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.progress.emit(f"下载进度: {progress:.1f}%")
            
            self.progress.emit("正在解压文件...")
            
            # 解压文件
            extract_dir = os.path.join(bbdown_dir, "current")
            if os.path.exists(extract_dir):
                import shutil
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            if filename.endswith('.zip'):
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif filename.endswith(('.tar.gz', '.tgz')):
                with tarfile.open(download_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # 查找BBDown可执行文件
            bbdown_exe = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().startswith('bbdown') and (file.endswith('.exe') or '.' not in file):
                        bbdown_exe = os.path.join(root, file)
                        break
                if bbdown_exe:
                    break
            
            if not bbdown_exe:
                raise Exception("未找到BBDown可执行文件")
            
            # 在macOS上设置可执行权限
            if system == "darwin":
                self.progress.emit("正在设置可执行权限...")
                try:
                    # 尝试直接设置权限
                    os.chmod(bbdown_exe, 0o755)
                except PermissionError:
                    # 如果权限不足，使用sudo
                    try:
                        subprocess.run(['sudo', 'chmod', '+x', bbdown_exe], check=True)
                    except subprocess.CalledProcessError:
                        # 如果sudo失败，尝试使用osascript请求管理员权限
                        script = f'do shell script "chmod +x {bbdown_exe}" with administrator privileges'
                        subprocess.run(['osascript', '-e', script], check=True)
            
            # 清理下载的压缩包
            os.remove(download_path)
            
            self.finished.emit(True, f"BBDown {tag_name} 下载完成: {bbdown_exe}")
            
        except Exception as e:
            self.finished.emit(False, f"下载失败: {str(e)}")
    
    def start_bbdown_server(self):
        """启动BBDown服务器"""
        try:
            if not self.bbdown_path or not os.path.exists(self.bbdown_path):
                raise Exception("BBDown可执行文件不存在")
            
            self.progress.emit("正在启动BBDown服务器...")
            
            # 启动BBDown服务器
            cmd = [self.bbdown_path, "serve", "-l", "http://0.0.0.0:58682"]
            
            # 在后台启动进程
            if platform.system() == "Windows":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(cmd)
            
            # 等待一下让服务器启动
            import time
            time.sleep(2)
            
            # 检查服务器是否启动成功
            try:
                response = requests.get("http://localhost:58682/get-tasks/", timeout=5)
                if response.status_code == 200:
                    self.finished.emit(True, "BBDown服务器启动成功")
                else:
                    self.finished.emit(False, "服务器启动失败")
            except:
                self.finished.emit(False, "无法连接到BBDown服务器")
                
        except Exception as e:
            self.finished.emit(False, f"启动失败: {str(e)}")

class OptionsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # 滚动区域的内容部件
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # 基本选项组
        basic_group = self.create_collapsible_group("基本选项", self.create_basic_options())
        content_layout.addWidget(basic_group)
        
        # API选项组
        api_group = self.create_collapsible_group("API选项", self.create_api_options())
        content_layout.addWidget(api_group)
        
        # 内容选择组
        content_group = self.create_collapsible_group("内容选择", self.create_content_options())
        content_layout.addWidget(content_group)
        
        # 下载控制组
        control_group = self.create_collapsible_group("下载控制", self.create_control_options())
        content_layout.addWidget(control_group)
        
        # 文件命名组
        file_group = self.create_collapsible_group("文件命名", self.create_file_options())
        content_layout.addWidget(file_group)
        
        # 路径设置组
        path_group = self.create_collapsible_group("路径设置", self.create_path_options())
        content_layout.addWidget(path_group)
        
        # 网络设置组
        network_group = self.create_collapsible_group("网络设置", self.create_network_options())
        content_layout.addWidget(network_group)
        
        # 高级设置组
        advanced_group = self.create_collapsible_group("高级设置", self.create_advanced_options())
        content_layout.addWidget(advanced_group)
        
        # 兼容性选项组
        compat_group = self.create_collapsible_group("兼容性选项", self.create_compat_options())
        content_layout.addWidget(compat_group)
        
        content_layout.addStretch()
        
        main_layout.addWidget(scroll_area)
    
    def create_collapsible_group(self, title, content_widget):
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(False)
        group.setStyleSheet("""
            QGroupBox::indicator {
                width: 15px;
                height: 15px;
            }
            QGroupBox {
                font-weight: bold;
            }
        """)
        
        # 设置折叠状态变化时的行为
        group.toggled.connect(lambda checked, w=content_widget: w.setVisible(checked))
        
        layout = QVBoxLayout(group)
        layout.addWidget(content_widget)
        content_widget.setVisible(False)
        
        return group
    
    def create_basic_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # URL输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入BV/av/ep/ss号或视频URL")
        layout.addWidget(QLabel("视频URL:"), 0, 0)
        layout.addWidget(self.url_input, 0, 1, 1, 2)
        
        # 仅显示信息
        self.only_show_info = QCheckBox("仅显示信息（不下载）")
        layout.addWidget(self.only_show_info, 1, 0, 1, 3)
        
        # 显示所有信息
        self.show_all = QCheckBox("显示所有信息（包括隐藏流）")
        layout.addWidget(self.show_all, 2, 0, 1, 3)
        
        # 交互模式
        self.interactive = QCheckBox("交互模式（手动选择）")
        layout.addWidget(self.interactive, 3, 0, 1, 3)
        
        # 区域设置
        layout.addWidget(QLabel("区域设置:"), 4, 0)
        self.area_combo = QComboBox()
        self.area_combo.addItems(["", "大陆", "港澳台", "泰国", "其他"])
        layout.addWidget(self.area_combo, 4, 1, 1, 2)
        
        # 语言设置
        layout.addWidget(QLabel("语言:"), 5, 0)
        self.language_input = QLineEdit()
        self.language_input.setPlaceholderText("如: zh-Hans")
        layout.addWidget(self.language_input, 5, 1, 1, 2)
        
        # 延迟
        layout.addWidget(QLabel("分页延迟(ms):"), 6, 0)
        self.delay_input = QLineEdit("0")
        self.delay_input.setValidator(QIntValidator(0, 10000, self))
        layout.addWidget(self.delay_input, 6, 1, 1, 2)
        
        return widget
    
    def create_api_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # API类型单选按钮
        self.api_tv = QCheckBox("使用TV API")
        self.api_app = QCheckBox("使用App API")
        self.api_intl = QCheckBox("使用国际版API")
        
        # 互斥逻辑
        self.api_tv.clicked.connect(lambda: self.handle_api_mutex(self.api_tv))
        self.api_app.clicked.connect(lambda: self.handle_api_mutex(self.api_app))
        self.api_intl.clicked.connect(lambda: self.handle_api_mutex(self.api_intl))
        
        layout.addWidget(self.api_tv, 0, 0, 1, 2)
        layout.addWidget(self.api_app, 1, 0, 1, 2)
        layout.addWidget(self.api_intl, 2, 0, 1, 2)
        
        # TV API主机
        layout.addWidget(QLabel("TV API主机:"), 3, 0)
        self.tv_host_input = QLineEdit("api.snm0516.aisee.tv")
        layout.addWidget(self.tv_host_input, 3, 1)
        
        return widget
    
    def handle_api_mutex(self, checkbox):
        """处理API类型选择的互斥逻辑"""
        if checkbox.isChecked():
            if checkbox == self.api_tv:
                self.api_app.setChecked(False)
                self.api_intl.setChecked(False)
            elif checkbox == self.api_app:
                self.api_tv.setChecked(False)
                self.api_intl.setChecked(False)
            elif checkbox == self.api_intl:
                self.api_tv.setChecked(False)
                self.api_app.setChecked(False)
    
    def create_content_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 内容类型选择
        self.video_only = QCheckBox("仅下载视频")
        self.audio_only = QCheckBox("仅下载音频")
        self.danmaku_only = QCheckBox("仅下载弹幕")
        self.cover_only = QCheckBox("仅下载封面")
        self.sub_only = QCheckBox("仅下载字幕")
        
        # 互斥逻辑
        self.video_only.clicked.connect(lambda: self.handle_content_mutex(self.video_only))
        self.audio_only.clicked.connect(lambda: self.handle_content_mutex(self.audio_only))
        
        layout.addWidget(self.video_only, 0, 0)
        layout.addWidget(self.audio_only, 0, 1)
        layout.addWidget(self.danmaku_only, 1, 0)
        layout.addWidget(self.cover_only, 1, 1)
        layout.addWidget(self.sub_only, 2, 0)
        
        # 下载弹幕
        self.download_danmaku = QCheckBox("下载弹幕")
        layout.addWidget(self.download_danmaku, 3, 0, 1, 2)
        
        # 弹幕格式
        layout.addWidget(QLabel("弹幕格式:"), 4, 0)
        self.danmaku_formats = QLineEdit()
        self.danmaku_formats.setPlaceholderText("如: xml,ass 用逗号分隔")
        layout.addWidget(self.danmaku_formats, 4, 1)
        
        # 跳过AI字幕
        self.skip_ai = QCheckBox("跳过AI生成字幕")
        self.skip_ai.setChecked(True)
        layout.addWidget(self.skip_ai, 5, 0, 1, 2)
        
        return widget
    
    def handle_content_mutex(self, checkbox):
        """处理内容选择的互斥逻辑"""
        if checkbox.isChecked():
            if checkbox == self.video_only:
                self.audio_only.setChecked(False)
            elif checkbox == self.audio_only:
                self.video_only.setChecked(False)
    
    def create_control_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 多线程下载
        self.multi_thread = QCheckBox("多线程下载")
        self.multi_thread.setChecked(True)
        layout.addWidget(self.multi_thread, 0, 0, 1, 2)
        
        # 使用MP4box
        self.use_mp4box = QCheckBox("使用MP4box封装")
        layout.addWidget(self.use_mp4box, 1, 0, 1, 2)
        
        # 使用aria2c
        self.use_aria2c = QCheckBox("使用aria2c下载")
        layout.addWidget(self.use_aria2c, 2, 0, 1, 2)
        
        # 简单混流
        self.simply_mux = QCheckBox("简单混流（减少处理）")
        layout.addWidget(self.simply_mux, 3, 0, 1, 2)
        
        # 跳过混流
        self.skip_mux = QCheckBox("跳过混流步骤")
        layout.addWidget(self.skip_mux, 4, 0, 1, 2)
        
        # 跳过字幕
        self.skip_subtitle = QCheckBox("跳过字幕下载")
        layout.addWidget(self.skip_subtitle, 5, 0, 1, 2)
        
        # 跳过封面
        self.skip_cover = QCheckBox("跳过封面下载")
        layout.addWidget(self.skip_cover, 6, 0, 1, 2)
        
        # 编码优先级
        layout.addWidget(QLabel("编码优先级:"), 7, 0)
        self.encoding_priority = QLineEdit()
        self.encoding_priority.setPlaceholderText("如: hevc,av1,avc")
        layout.addWidget(self.encoding_priority, 7, 1)
        
        # 画质优先级
        layout.addWidget(QLabel("画质优先级:"), 8, 0)
        self.dfn_priority = QLineEdit()
        self.dfn_priority.setPlaceholderText("如: 1080p,720p")
        layout.addWidget(self.dfn_priority, 8, 1)
        
        # 分页选择
        layout.addWidget(QLabel("分页选择:"), 9, 0)
        self.select_page = QLineEdit()
        self.select_page.setPlaceholderText("如: 1-5,8")
        layout.addWidget(self.select_page, 9, 1)
        
        return widget
    
    def create_file_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 文件命名模式
        layout.addWidget(QLabel("文件命名模式:"), 0, 0)
        self.file_pattern = QLineEdit()
        self.file_pattern.setPlaceholderText("如: <videoTitle>[<dfn>]")
        layout.addWidget(self.file_pattern, 0, 1)
        
        # 多P文件命名模式
        layout.addWidget(QLabel("多P文件命名:"), 1, 0)
        self.multi_file_pattern = QLineEdit()
        self.multi_file_pattern.setPlaceholderText("如: P<pageNumber>_<videoTitle>")
        layout.addWidget(self.multi_file_pattern, 1, 1)
        
        # 添加dfn后缀
        self.add_dfn_subfix = QCheckBox("添加画质后缀到文件名")
        layout.addWidget(self.add_dfn_subfix, 2, 0, 1, 2)
        
        # 不补零页码
        self.no_padding_page = QCheckBox("页码不补零")
        layout.addWidget(self.no_padding_page, 3, 0, 1, 2)
        
        return widget
    
    def create_path_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 工作目录
        layout.addWidget(QLabel("工作目录:"), 0, 0)
        self.work_dir = QLineEdit()
        self.work_dir.setPlaceholderText("下载文件保存路径")
        layout.addWidget(self.work_dir, 0, 1)
        
        # FFmpeg路径
        layout.addWidget(QLabel("FFmpeg路径:"), 1, 0)
        self.ffmpeg_path = QLineEdit()
        self.ffmpeg_path.setPlaceholderText("自定义FFmpeg路径")
        layout.addWidget(self.ffmpeg_path, 1, 1)
        
        # MP4box路径
        layout.addWidget(QLabel("MP4box路径:"), 2, 0)
        self.mp4box_path = QLineEdit()
        self.mp4box_path.setPlaceholderText("自定义MP4box路径")
        layout.addWidget(self.mp4box_path, 2, 1)
        
        # aria2c路径
        layout.addWidget(QLabel("aria2c路径:"), 3, 0)
        self.aria2c_path = QLineEdit()
        self.aria2c_path.setPlaceholderText("自定义aria2c路径")
        layout.addWidget(self.aria2c_path, 3, 1)
        
        return widget
    
    def create_network_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 用户代理
        layout.addWidget(QLabel("User-Agent:"), 0, 0)
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("自定义User-Agent")
        layout.addWidget(self.user_agent, 0, 1)
        
        # Cookie
        layout.addWidget(QLabel("Cookie:"), 1, 0)
        self.cookie = QLineEdit()
        self.cookie.setPlaceholderText("B站Cookie")
        layout.addWidget(self.cookie, 1, 1)
        
        # Access Token
        layout.addWidget(QLabel("Access Token:"), 2, 0)
        self.access_token = QLineEdit()
        self.access_token.setPlaceholderText("API访问令牌")
        layout.addWidget(self.access_token, 2, 1)
        
        # 主API主机
        layout.addWidget(QLabel("API主机:"), 3, 0)
        self.host_input = QLineEdit("api.bilibili.com")
        layout.addWidget(self.host_input, 3, 1)
        
        # EP API主机
        layout.addWidget(QLabel("EP API主机:"), 4, 0)
        self.ep_host_input = QLineEdit("api.bilibili.com")
        layout.addWidget(self.ep_host_input, 4, 1)
        
        # UPOS主机
        layout.addWidget(QLabel("UPOS主机:"), 5, 0)
        self.upos_host = QLineEdit()
        self.upos_host.setPlaceholderText("如: upos-sz-mirrorcos.bilivideo.com")
        layout.addWidget(self.upos_host, 5, 1)
        
        # aria2c参数
        layout.addWidget(QLabel("aria2c参数:"), 6, 0)
        self.aria2c_args = QLineEdit()
        self.aria2c_args.setPlaceholderText("自定义aria2c参数")
        layout.addWidget(self.aria2c_args, 6, 1)
        
        # aria2c代理
        layout.addWidget(QLabel("aria2c代理:"), 7, 0)
        self.aria2c_proxy = QLineEdit()
        self.aria2c_proxy.setPlaceholderText("代理服务器地址")
        layout.addWidget(self.aria2c_proxy, 7, 1)
        
        return widget
    
    def create_advanced_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 调试模式
        self.debug = QCheckBox("调试模式")
        layout.addWidget(self.debug, 0, 0, 1, 2)
        
        # 强制HTTP
        self.force_http = QCheckBox("强制使用HTTP")
        self.force_http.setChecked(True)
        layout.addWidget(self.force_http, 1, 0, 1, 2)
        
        # 允许PCDN
        self.allow_pcdn = QCheckBox("允许PCDN")
        layout.addWidget(self.allow_pcdn, 2, 0, 1, 2)
        
        # 强制替换主机
        self.force_replace_host = QCheckBox("强制替换主机")
        self.force_replace_host.setChecked(True)
        layout.addWidget(self.force_replace_host, 3, 0, 1, 2)
        
        # 保存存档到文件
        self.save_archives = QCheckBox("保存存档到文件")
        layout.addWidget(self.save_archives, 4, 0, 1, 2)
        
        # 视频升序
        self.video_asc = QCheckBox("视频质量升序选择")
        layout.addWidget(self.video_asc, 5, 0, 1, 2)
        
        # 音频升序
        self.audio_asc = QCheckBox("音频质量升序选择")
        layout.addWidget(self.audio_asc, 6, 0, 1, 2)
        
        # 带宽升序
        self.bandwidth_asc = QCheckBox("带宽升序选择")
        layout.addWidget(self.bandwidth_asc, 7, 0, 1, 2)
        
        return widget
    
    def create_compat_options(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setColumnStretch(1, 1)
        
        # 兼容性选项标签
        compat_label = QLabel("以下为兼容旧版本的选项，不建议使用:")
        compat_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(compat_label, 0, 0, 1, 2)
        
        # 仅HEVC
        self.only_hevc = QCheckBox("仅下载HEVC编码")
        layout.addWidget(self.only_hevc, 1, 0, 1, 2)
        
        # 仅AVC
        self.only_avc = QCheckBox("仅下载AVC编码")
        layout.addWidget(self.only_avc, 2, 0, 1, 2)
        
        # 仅AV1
        self.only_av1 = QCheckBox("仅下载AV1编码")
        layout.addWidget(self.only_av1, 3, 0, 1, 2)
        
        return widget
    
    def get_options(self):
        """收集所有选项并返回字典"""
        options = {}
        
        # 基本选项
        if self.url_input.text().strip():
            options["Url"] = self.url_input.text().strip()
        options["OnlyShowInfo"] = self.only_show_info.isChecked()
        options["ShowAll"] = self.show_all.isChecked()
        options["Interactive"] = self.interactive.isChecked()
        if self.area_combo.currentText():
            options["Area"] = self.area_combo.currentText()
        if self.language_input.text().strip():
            options["Language"] = self.language_input.text().strip()
        if self.delay_input.text().strip():
            options["DelayPerPage"] = self.delay_input.text().strip()
        
        # API选项
        options["UseTvApi"] = self.api_tv.isChecked()
        options["UseAppApi"] = self.api_app.isChecked()
        options["UseIntlApi"] = self.api_intl.isChecked()
        if self.tv_host_input.text().strip():
            options["TvHost"] = self.tv_host_input.text().strip()
        
        # 内容选择
        options["VideoOnly"] = self.video_only.isChecked()
        options["AudioOnly"] = self.audio_only.isChecked()
        options["DanmakuOnly"] = self.danmaku_only.isChecked()
        options["CoverOnly"] = self.cover_only.isChecked()
        options["SubOnly"] = self.sub_only.isChecked()
        options["DownloadDanmaku"] = self.download_danmaku.isChecked()
        if self.danmaku_formats.text().strip():
            options["DownloadDanmakuFormats"] = self.danmaku_formats.text().strip()
        options["SkipAi"] = self.skip_ai.isChecked()
        
        # 下载控制
        options["MultiThread"] = self.multi_thread.isChecked()
        options["UseMP4box"] = self.use_mp4box.isChecked()
        options["UseAria2c"] = self.use_aria2c.isChecked()
        options["SimplyMux"] = self.simply_mux.isChecked()
        options["SkipMux"] = self.skip_mux.isChecked()
        options["SkipSubtitle"] = self.skip_subtitle.isChecked()
        options["SkipCover"] = self.skip_cover.isChecked()
        if self.encoding_priority.text().strip():
            options["EncodingPriority"] = self.encoding_priority.text().strip()
        if self.dfn_priority.text().strip():
            options["DfnPriority"] = self.dfn_priority.text().strip()
        if self.select_page.text().strip():
            options["SelectPage"] = self.select_page.text().strip()
        
        # 文件命名
        if self.file_pattern.text().strip():
            options["FilePattern"] = self.file_pattern.text().strip()
        if self.multi_file_pattern.text().strip():
            options["MultiFilePattern"] = self.multi_file_pattern.text().strip()
        options["AddDfnSubfix"] = self.add_dfn_subfix.isChecked()
        options["NoPaddingPageNum"] = self.no_padding_page.isChecked()
        
        # 路径设置
        if self.work_dir.text().strip():
            options["WorkDir"] = self.work_dir.text().strip()
        if self.ffmpeg_path.text().strip():
            options["FFmpegPath"] = self.ffmpeg_path.text().strip()
        if self.mp4box_path.text().strip():
            options["Mp4boxPath"] = self.mp4box_path.text().strip()
        if self.aria2c_path.text().strip():
            options["Aria2cPath"] = self.aria2c_path.text().strip()
        
        # 网络设置
        if self.user_agent.text().strip():
            options["UserAgent"] = self.user_agent.text().strip()
        if self.cookie.text().strip():
            options["Cookie"] = self.cookie.text().strip()
        if self.access_token.text().strip():
            options["AccessToken"] = self.access_token.text().strip()
        if self.host_input.text().strip():
            options["Host"] = self.host_input.text().strip()
        if self.ep_host_input.text().strip():
            options["EpHost"] = self.ep_host_input.text().strip()
        if self.upos_host.text().strip():
            options["UposHost"] = self.upos_host.text().strip()
        if self.aria2c_args.text().strip():
            options["Aria2cArgs"] = self.aria2c_args.text().strip()
        if self.aria2c_proxy.text().strip():
            options["Aria2cProxy"] = self.aria2c_proxy.text().strip()
        
        # 高级设置
        options["Debug"] = self.debug.isChecked()
        options["ForceHttp"] = self.force_http.isChecked()
        options["AllowPcdn"] = self.allow_pcdn.isChecked()
        options["ForceReplaceHost"] = self.force_replace_host.isChecked()
        options["SaveArchivesToFile"] = self.save_archives.isChecked()
        options["VideoAscending"] = self.video_asc.isChecked()
        options["AudioAscending"] = self.audio_asc.isChecked()
        options["BandwithAscending"] = self.bandwidth_asc.isChecked()
        
        # 兼容性选项
        options["OnlyHevc"] = self.only_hevc.isChecked()
        options["OnlyAvc"] = self.only_avc.isChecked()
        options["OnlyAv1"] = self.only_av1.isChecked()
        
        # 清理空值
        options = {k: v for k, v in options.items() if v or isinstance(v, bool)}
        
        return options

class BBDownGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Windows 特定优化
        if sys.platform == "win32":
            # 禁用Windows视觉样式以提升性能
            try:
                os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
                os.environ["QT_SCALE_FACTOR"] = "1"
            except:
                pass
            
            # 设置Windows兼容模式
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BBDown.GUI")
            except:
                pass
        
        # 设置窗口标题和尺寸
        self.setWindowTitle("BBDown任务管理器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置应用图标
        try:
            self.setWindowIcon(QIcon("bbdown_icon.ico"))
        except:
            pass
        
        # 初始化API客户端
        self.api_client = BBDownAPIClient()
        
        # 创建主控件
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建顶部连接控制栏
        self.create_connection_controls()
        
        # 创建选项卡
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # 创建各个选项卡
        self.create_dashboard_tab()
        self.create_add_task_tab()
        self.create_manage_tab()
        
        # 设置定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.start_refresh_tasks)
        self.refresh_timer.start(10000)  # 每10秒刷新一次
        
        # 初始化数据
        self.last_tasks = {"Running": [], "Finished": []}
        self.start_refresh_tasks()
    
    def create_connection_controls(self):
        connection_group = QGroupBox("连接设置")
        layout = QHBoxLayout(connection_group)
        
        self.host_input = QLineEdit("localhost")
        self.port_input = QLineEdit("58682")
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setIcon(QIcon.fromTheme("network-connect"))
        self.connect_btn.clicked.connect(self.update_connection)
        
        layout.addWidget(QLabel("主机:"))
        layout.addWidget(self.host_input)
        layout.addWidget(QLabel("端口:"))
        layout.addWidget(self.port_input)
        layout.addWidget(self.connect_btn)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # BBDown管理按钮
        self.download_bbdown_btn = QPushButton("下载BBDown")
        self.download_bbdown_btn.setIcon(QIcon.fromTheme("document-save"))
        self.download_bbdown_btn.clicked.connect(self.download_bbdown)
        
        self.start_bbdown_btn = QPushButton("启动BBDown服务")
        self.start_bbdown_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_bbdown_btn.clicked.connect(self.start_bbdown_server)
        self.start_bbdown_btn.setEnabled(False)  # 初始禁用
        
        self.stop_bbdown_btn = QPushButton("停止BBDown服务")
        self.stop_bbdown_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_bbdown_btn.clicked.connect(self.stop_bbdown_server)
        self.stop_bbdown_btn.setEnabled(False)  # 初始禁用
        
        self.delete_bbdown_btn = QPushButton("删除BBDown文件")
        self.delete_bbdown_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_bbdown_btn.clicked.connect(self.delete_bbdown_files)
        self.delete_bbdown_btn.setEnabled(False)  # 初始禁用
        
        layout.addWidget(self.download_bbdown_btn)
        layout.addWidget(self.start_bbdown_btn)
        layout.addWidget(self.stop_bbdown_btn)
        layout.addWidget(self.delete_bbdown_btn)
        layout.addStretch()
        
        self.main_layout.addWidget(connection_group)
        
        # 检查是否已有BBDown
        self.check_existing_bbdown()
    
    def update_connection(self):
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        
        if not host or not port:
            QMessageBox.warning(self, "输入错误", "主机和端口不能为空")
            return
        
        try:
            port = int(port)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "输入错误", "端口必须是1-65535之间的整数")
            return
        
        self.api_client = BBDownAPIClient(host, port)
        QMessageBox.information(self, "成功", "连接设置已更新")
        self.start_refresh_tasks()
    
    def create_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新任务")
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_btn.clicked.connect(self.start_refresh_tasks)
        layout.addWidget(self.refresh_btn)
        
        # 分割视图
        splitter = QSplitter(Qt.Vertical)
        
        # 运行中任务表
        self.running_table = self.create_task_table()
        running_group = QGroupBox("运行中任务")
        running_layout = QVBoxLayout()
        running_layout.addWidget(self.running_table)
        running_group.setLayout(running_layout)
        
        # 已完成任务表
        self.finished_table = self.create_task_table()
        finished_group = QGroupBox("已完成任务")
        finished_layout = QVBoxLayout()
        finished_layout.addWidget(self.finished_table)
        finished_group.setLayout(finished_layout)
        
        splitter.addWidget(running_group)
        splitter.addWidget(finished_group)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        self.tabs.addTab(dashboard_tab, "任务仪表盘")
    
    def create_task_table(self):
        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "AID", "标题", "创建时间", "完成时间", "进度", 
            "速度", "大小", "状态", "操作"
        ])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table
    
    def create_add_task_tab(self):
        add_task_tab = QWidget()
        layout = QVBoxLayout(add_task_tab)
        
        # 创建选项表单
        self.options_form = OptionsForm()
        layout.addWidget(self.options_form)
        
        # 添加按钮
        self.add_btn = QPushButton("添加任务")
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_btn.clicked.connect(self.add_new_task)
        layout.addWidget(self.add_btn)
        
        self.tabs.addTab(add_task_tab, "添加任务")
    
    def create_manage_tab(self):
        manage_tab = QWidget()
        layout = QVBoxLayout(manage_tab)
        
        # 批量操作
        batch_layout = QHBoxLayout()
        self.remove_all_btn = QPushButton("移除所有已完成任务")
        self.remove_all_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_all_btn.clicked.connect(self.remove_all_finished)
        self.remove_failed_btn = QPushButton("移除所有失败任务")
        self.remove_failed_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_failed_btn.clicked.connect(self.remove_failed_tasks)
        
        batch_layout.addWidget(self.remove_all_btn)
        batch_layout.addWidget(self.remove_failed_btn)
        batch_layout.addStretch()
        
        # 按AID移除
        aid_layout = QHBoxLayout()
        self.aid_input = QLineEdit()
        self.aid_input.setPlaceholderText("输入要移除的任务AID")
        self.remove_by_aid_btn = QPushButton("移除任务")
        self.remove_by_aid_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_by_aid_btn.clicked.connect(self.remove_task_by_aid)
        
        aid_layout.addWidget(QLabel("按AID移除:"))
        aid_layout.addWidget(self.aid_input)
        aid_layout.addWidget(self.remove_by_aid_btn)
        
        layout.addLayout(batch_layout)
        layout.addLayout(aid_layout)
        layout.addStretch()
        
        self.tabs.addTab(manage_tab, "任务管理")
    
    def start_refresh_tasks(self):
        """使用线程启动任务刷新"""
        if hasattr(self, 'refresh_thread') and self.refresh_thread.isRunning():
            return
            
        self.refresh_thread = APITaskThread(self.api_client, "get_tasks")
        self.refresh_thread.finished.connect(self.handle_refresh_result)
        self.refresh_thread.start()
    
    def handle_refresh_result(self, tasks):
        """处理刷新结果"""
        if tasks is None:
            return
            
        # 优化UI更新 - 只在数据变化时更新
        if tasks != self.last_tasks:
            self.last_tasks = tasks
            running_tasks = tasks.get("Running", [])
            finished_tasks = tasks.get("Finished", [])
            
            # 更新运行中任务表
            self.update_task_table(self.running_table, running_tasks, False)
            
            # 更新已完成任务表
            self.update_task_table(self.finished_table, finished_tasks, True)
    
    def update_task_table(self, table, tasks, is_finished):
        """优化表格更新性能"""
        # 避免不必要的UI更新
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        
        current_row_count = table.rowCount()
        new_row_count = len(tasks)
        
        # 设置行数
        if new_row_count != current_row_count:
            table.setRowCount(new_row_count)
        
        # 批量更新单元格
        for row, task in enumerate(tasks):
            # 转换时间戳
            create_time = self.format_timestamp(task.get("TaskCreateTime"))
            finish_time = self.format_timestamp(task.get("TaskFinishTime"))
            
            # 格式化速度和大小
            speed = self.format_bytes(task.get("DownloadSpeed", 0))
            size = self.format_bytes(task.get("TotalDownloadedBytes", 0))
            
            # 状态和颜色
            status = "成功" if task.get("IsSuccessful", False) else "失败"
            status_color = QColor(0, 128, 0) if status == "成功" else QColor(220, 20, 60)
            
            # 填充表格
            table.setItem(row, 0, QTableWidgetItem(task.get("Aid", "")))
            table.setItem(row, 1, QTableWidgetItem(task.get("Title", "")))
            table.setItem(row, 2, QTableWidgetItem(create_time))
            table.setItem(row, 3, QTableWidgetItem(finish_time))
            
            # 进度条
            progress = task.get("Progress", 0)
            progress_item = QTableWidgetItem(f"{progress * 100:.2f}%")
            progress_item.setBackground(self.get_progress_color(progress))
            table.setItem(row, 4, progress_item)
            
            table.setItem(row, 5, QTableWidgetItem(speed))
            table.setItem(row, 6, QTableWidgetItem(size))
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(status_color))
            table.setItem(row, 7, status_item)
            
            # 操作按钮
            if is_finished:
                btn = QPushButton("移除")
                btn.setIcon(QIcon.fromTheme("edit-delete"))
                btn.clicked.connect(lambda _, aid=task.get("Aid"): self.remove_task(aid))
            else:
                btn = QPushButton("详情")
                btn.setIcon(QIcon.fromTheme("dialog-information"))
                btn.clicked.connect(lambda _, aid=task.get("Aid"): self.show_task_details(aid))
            
            # 将按钮添加到表格
            table.setCellWidget(row, 8, btn)
        
        # 启用UI更新
        table.blockSignals(False)
        table.setUpdatesEnabled(True)
        table.viewport().update()  # 强制重绘
    
    def get_progress_color(self, progress):
        """根据进度返回不同的背景颜色"""
        if progress < 0.3:
            return QColor(255, 200, 200)  # 浅红
        elif progress < 0.7:
            return QColor(255, 255, 200)  # 浅黄
        else:
            return QColor(200, 255, 200)  # 浅绿
    
    def format_timestamp(self, timestamp):
        """格式化时间戳"""
        if timestamp is None:
            return ""
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return ""
    
    def format_bytes(self, size):
        """格式化字节大小为更易读的格式"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024**2:
            return f"{size/1024:.2f} KB"
        elif size < 1024**3:
            return f"{size/(1024**2):.2f} MB"
        else:
            return f"{size/(1024**3):.2f} GB"
    
    def add_new_task(self):
        # 从表单获取选项
        options = self.options_form.get_options()
        
        if "Url" not in options or not options["Url"]:
            QMessageBox.warning(self, "输入错误", "URL不能为空")
            return
        
        # 使用线程添加任务
        self.add_task_thread = APITaskThread(self.api_client, "add_task", options["Url"], options)
        self.add_task_thread.finished.connect(self.handle_add_task_result)
        self.add_task_thread.start()
    
    def handle_add_task_result(self, success):
        """处理添加任务结果"""
        if success:
            QMessageBox.information(self, "成功", "任务已添加")
            self.start_refresh_tasks()
        else:
            QMessageBox.warning(self, "错误", "添加任务失败，请检查URL和参数")
    
    def remove_all_finished(self):
        # 使用线程移除任务
        self.remove_thread = APITaskThread(self.api_client, "remove_finished_tasks")
        self.remove_thread.finished.connect(self.handle_remove_finished)
        self.remove_thread.start()
    
    def handle_remove_finished(self, success):
        """处理移除完成的任务"""
        if success:
            QMessageBox.information(self, "成功", "已完成任务已全部移除")
            self.start_refresh_tasks()
        else:
            QMessageBox.critical(self, "错误", "移除任务失败")
    
    def remove_failed_tasks(self):
        # 使用线程移除失败任务
        self.remove_failed_thread = APITaskThread(self.api_client, "remove_failed_tasks")
        self.remove_failed_thread.finished.connect(self.handle_remove_failed)
        self.remove_failed_thread.start()
    
    def handle_remove_failed(self, success):
        """处理移除失败的任务"""
        if success:
            QMessageBox.information(self, "成功", "失败任务已全部移除")
            self.start_refresh_tasks()
        else:
            QMessageBox.critical(self, "错误", "移除任务失败")
    
    def remove_task_by_aid(self):
        aid = self.aid_input.text().strip()
        if not aid:
            QMessageBox.warning(self, "输入错误", "AID不能为空")
            return
        
        # 使用线程移除任务
        self.remove_task_thread = APITaskThread(self.api_client, "remove_task", aid)
        self.remove_task_thread.finished.connect(self.handle_remove_task)
        self.remove_task_thread.start()
    
    def handle_remove_task(self, success):
        """处理移除特定任务"""
        if success:
            QMessageBox.information(self, "成功", "任务已移除")
            self.aid_input.clear()
            self.start_refresh_tasks()
        else:
            QMessageBox.critical(self, "错误", "移除任务失败")
    
    def remove_task(self, aid):
        # 使用线程移除任务
        self.remove_task_thread = APITaskThread(self.api_client, "remove_task", aid)
        self.remove_task_thread.finished.connect(lambda success: self.handle_remove_task_by_aid(success, aid))
        self.remove_task_thread.start()
    
    def handle_remove_task_by_aid(self, success, aid):
        """处理移除特定任务的结果"""
        if success:
            QMessageBox.information(self, "成功", f"任务 {aid} 已移除")
            self.start_refresh_tasks()
        else:
            QMessageBox.critical(self, "错误", f"移除任务 {aid} 失败")
    
    def show_task_details(self, aid):
        # 使用线程获取任务详情
        self.task_detail_thread = APITaskThread(self.api_client, "get_task", aid)
        self.task_detail_thread.finished.connect(lambda task: self.handle_task_details(task, aid))
        self.task_detail_thread.start()
    
    def handle_task_details(self, task, aid):
        """显示任务详情"""
        if not task:
            QMessageBox.warning(self, "错误", f"找不到任务 {aid}")
            return
        
        # 创建详情对话框
        detail_dialog = QMessageBox(self)
        detail_dialog.setWindowTitle(f"任务详情 - {aid}")
        detail_dialog.setIcon(QMessageBox.Information)
        
        # 格式化任务信息
        details = [
            f"<b>AID:</b> {task.get('Aid', '')}",
            f"<b>标题:</b> {task.get('Title', '')}",
            f"<b>URL:</b> {task.get('Url', '')}",
            f"<b>创建时间:</b> {self.format_timestamp(task.get('TaskCreateTime'))}",
            f"<b>完成时间:</b> {self.format_timestamp(task.get('TaskFinishTime'))}",
            f"<b>进度:</b> {task.get('Progress', 0)*100:.2f}%",
            f"<b>下载速度:</b> {self.format_bytes(task.get('DownloadSpeed', 0))}/s",
            f"<b>已下载:</b> {self.format_bytes(task.get('TotalDownloadedBytes', 0))}",
            f"<b>状态:</b> {'成功' if task.get('IsSuccessful', False) else '失败'}"
        ]
        
        detail_dialog.setText("\n".join(details))
        detail_dialog.setStandardButtons(QMessageBox.Ok)
        detail_dialog.exec_()
    
    def check_existing_bbdown(self):
        """检查是否已存在BBDown可执行文件"""
        bbdown_dir = os.path.join(os.path.expanduser("~"), ".bbdown", "current")
        if os.path.exists(bbdown_dir):
            for root, dirs, files in os.walk(bbdown_dir):
                for file in files:
                    if file.lower().startswith('bbdown') and (file.endswith('.exe') or '.' not in file):
                        self.bbdown_path = os.path.join(root, file)
                        self.start_bbdown_btn.setEnabled(True)
                        self.delete_bbdown_btn.setEnabled(True)
                        self.download_bbdown_btn.setText("重新下载BBDown")
                        return
        
        self.bbdown_path = None
        self.start_bbdown_btn.setEnabled(False)
        self.stop_bbdown_btn.setEnabled(False)
        self.delete_bbdown_btn.setEnabled(False)
        self.download_bbdown_btn.setText("下载BBDown")
    
    def download_bbdown(self):
        """下载BBDown"""
        # 禁用按钮防止重复点击
        self.download_bbdown_btn.setEnabled(False)
        
        # 创建进度对话框
        from PyQt5.QtWidgets import QProgressDialog
        self.progress_dialog = QProgressDialog("正在下载BBDown...", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("下载BBDown")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        
        # 启动下载线程
        self.bbdown_manager_thread = BBDownManagerThread("download")
        self.bbdown_manager_thread.progress.connect(self.update_download_progress)
        self.bbdown_manager_thread.finished.connect(self.handle_download_finished)
        self.bbdown_manager_thread.start()
        
        # 连接取消按钮
        self.progress_dialog.canceled.connect(self.cancel_download)
    
    def update_download_progress(self, message):
        """更新下载进度"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setLabelText(message)
    
    def handle_download_finished(self, success, message):
        """处理下载完成"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            delattr(self, 'progress_dialog')
        
        # 重新启用按钮
        self.download_bbdown_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            # 重新检查BBDown状态
            self.check_existing_bbdown()
        else:
            QMessageBox.critical(self, "错误", message)
    
    def cancel_download(self):
        """取消下载"""
        if hasattr(self, 'bbdown_manager_thread') and self.bbdown_manager_thread.isRunning():
            self.bbdown_manager_thread.terminate()
            self.bbdown_manager_thread.wait()
        
        self.download_bbdown_btn.setEnabled(True)
    
    def start_bbdown_server(self):
        """启动BBDown服务器"""
        if not hasattr(self, 'bbdown_path') or not self.bbdown_path:
            QMessageBox.warning(self, "错误", "请先下载BBDown")
            return
        
        # 禁用按钮防止重复点击
        self.start_bbdown_btn.setEnabled(False)
        
        # 创建进度对话框
        from PyQt5.QtWidgets import QProgressDialog
        self.start_progress_dialog = QProgressDialog("正在启动BBDown服务器...", None, 0, 0, self)
        self.start_progress_dialog.setWindowTitle("启动服务器")
        self.start_progress_dialog.setModal(True)
        self.start_progress_dialog.show()
        
        # 启动服务器线程
        self.bbdown_start_thread = BBDownManagerThread("start", self.bbdown_path)
        self.bbdown_start_thread.progress.connect(self.update_start_progress)
        self.bbdown_start_thread.finished.connect(self.handle_start_finished)
        self.bbdown_start_thread.start()
    
    def update_start_progress(self, message):
        """更新启动进度"""
        if hasattr(self, 'start_progress_dialog'):
            self.start_progress_dialog.setLabelText(message)
    
    def handle_start_finished(self, success, message):
        """处理启动完成"""
        # 关闭进度对话框
        if hasattr(self, 'start_progress_dialog'):
            self.start_progress_dialog.close()
            delattr(self, 'start_progress_dialog')
        
        # 重新启用按钮
        self.start_bbdown_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            # 启动成功后启用停止按钮
            self.stop_bbdown_btn.setEnabled(True)
            # 自动刷新任务列表
            self.start_refresh_tasks()
        else:
            QMessageBox.critical(self, "错误", message)
    
    def stop_bbdown_server(self):
        """停止BBDown服务器"""
        reply = QMessageBox.question(
            self, "确认停止", 
            "确定要停止BBDown服务器吗？这将中断所有正在进行的下载任务。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 尝试通过API优雅关闭
            try:
                response = requests.post(f"{self.api_client.base_url}/shutdown", timeout=5)
                if response.status_code == 200:
                    QMessageBox.information(self, "成功", "BBDown服务器已停止")
                    self.stop_bbdown_btn.setEnabled(False)
                    return
            except:
                pass
            
            # 如果API关闭失败，尝试通过进程管理停止
            system = platform.system().lower()
            if system == "windows":
                # Windows系统使用taskkill
                subprocess.run(["taskkill", "/f", "/im", "BBDown.exe"], 
                             capture_output=True, text=True)
            else:
                # Unix系统使用pkill
                subprocess.run(["pkill", "-f", "BBDown"], 
                             capture_output=True, text=True)
            
            # 等待一下确保进程已停止
            import time
            time.sleep(2)
            
            # 检查服务器是否已停止
            try:
                response = requests.get(f"{self.api_client.base_url}/get-tasks/", timeout=2)
                if response.status_code == 200:
                    QMessageBox.warning(self, "警告", "服务器可能仍在运行，请手动检查")
                else:
                    QMessageBox.information(self, "成功", "BBDown服务器已停止")
                    self.stop_bbdown_btn.setEnabled(False)
            except:
                QMessageBox.information(self, "成功", "BBDown服务器已停止")
                self.stop_bbdown_btn.setEnabled(False)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止服务器失败: {str(e)}")
    
    def delete_bbdown_files(self):
        """删除BBDown服务端文件"""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除BBDown服务端文件吗？这将删除所有已下载的BBDown文件，操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 首先尝试停止服务器
            try:
                requests.post(f"{self.api_client.base_url}/shutdown", timeout=2)
            except:
                pass
            
            # 强制停止进程
            system = platform.system().lower()
            if system == "windows":
                subprocess.run(["taskkill", "/f", "/im", "BBDown.exe"], 
                             capture_output=True, text=True)
            else:
                subprocess.run(["pkill", "-f", "BBDown"], 
                             capture_output=True, text=True)
            
            # 等待进程完全停止
            import time
            time.sleep(2)
            
            # 删除BBDown目录
            bbdown_dir = os.path.join(os.path.expanduser("~"), ".bbdown")
            if os.path.exists(bbdown_dir):
                import shutil
                shutil.rmtree(bbdown_dir)
                QMessageBox.information(self, "成功", "BBDown文件已删除")
                
                # 重置按钮状态
                self.bbdown_path = None
                self.start_bbdown_btn.setEnabled(False)
                self.stop_bbdown_btn.setEnabled(False)
                self.delete_bbdown_btn.setEnabled(False)
                self.download_bbdown_btn.setText("下载BBDown")
            else:
                QMessageBox.information(self, "提示", "BBDown文件目录不存在")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除文件失败: {str(e)}")

# 应用启动优化
if __name__ == "__main__":
    # Windows特定优化
    if sys.platform == "win32":
        # 禁用DPI缩放
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 优化Windows渲染
    if sys.platform == "win32":
        # 使用更轻量的渲染引擎
        app.setAttribute(Qt.AA_UseSoftwareOpenGL)
        app.setAttribute(Qt.AA_DisableHighDpiScaling)
        
        # 设置字体
        font = QFont("Segoe UI", 9)
        app.setFont(font)
    else:
        # 其他平台使用默认设置
        font = QFont("Arial", 10)
        app.setFont(font)
    
    # 创建主窗口
    window = BBDownGUI()
    
    # 显示窗口
    window.show()
    
    # 启动应用
    sys.exit(app.exec_())