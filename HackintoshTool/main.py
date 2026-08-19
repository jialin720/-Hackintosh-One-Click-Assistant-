# -*- coding: utf-8 -*-
"""
黑苹果一键辅助工具 (Hackintosh One-Click Assistant)
功能：生成 EFI、下载镜像、烧录镜像到分区
版本：1.0.2 (分区烧录版，修复变量名错误)
"""
import sys
import subprocess
import os
import re
import ctypes
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QTextEdit, QDialog, QFileDialog,
    QMessageBox, QComboBox, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor, QFont


# ============================================================
# 0. 路径工具
# ============================================================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()


# ============================================================
# 1. 双语辅助
# ============================================================
def tr(zh, en):
    return f"{zh}\n{en}"

def tr_html(zh, en):
    return f'<html><body><span style="font-size:12pt;">{zh}</span><br><span style="font-size:8pt;color:#888888;">{en}</span></body></html>'


def show_rich_messagebox(parent, title, text, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setTextFormat(Qt.RichText)
    msg.setIcon(icon)
    msg.setStandardButtons(buttons)
    return msg.exec()


# ============================================================
# 2. 日志
# ============================================================
class Logger:
    def __init__(self):
        self.log_file = os.path.join(BASE_DIR, "tool.log")
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                if len(f.readlines()) > 200:
                    os.remove(self.log_file)

    def log(self, msg, widget=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"[{timestamp}] {msg}"
        if widget:
            try:
                widget.append(full_msg)
            except AttributeError:
                try:
                    widget.insertPlainText(full_msg + '\n')
                except:
                    pass
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(full_msg + '\n')

logger = Logger()


# ============================================================
# 3. 管理员权限
# ============================================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ensure_admin_for_burn(parent=None):
    if is_admin():
        return True
    reply = show_rich_messagebox(
        parent,
        tr("权限提示", "Permission Required"),
        tr_html(
            "烧录功能需要管理员权限。\n请以管理员身份重新运行本工具。",
            "Burn function requires administrator privileges.\nPlease run as administrator."
        ),
        QMessageBox.Question,
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        script = os.path.abspath(sys.argv[0])
        args = ' '.join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {args}', None, 1
        )
        sys.exit(0)
    return False


# ============================================================
# 4. 获取系统盘符
# ============================================================
def get_system_drive():
    return os.environ.get('SystemDrive', 'C:').rstrip('\\')


# ============================================================
# 5. 烧录线程（分区写入）
# ============================================================
class BurnThread(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, image_path, target_partition):
        """
        target_partition: 盘符，如 "E:" 或 "D:"
        """
        super().__init__()
        self.image_path = image_path
        self.target_partition = target_partition
        self._cancelled = False
        self.process = None

    def cancel(self):
        self._cancelled = True
        if self.process:
            self.process.terminate()
            for _ in range(6):
                if self.process.poll() is not None:
                    break
                time.sleep(0.5)
            else:
                self.process.kill()

    def run(self):
        dd_path = os.path.join(BASE_DIR, "bin", "dd.exe")
        if not os.path.exists(dd_path):
            self.finished.emit(False, tr("未找到 dd.exe，请下载并放入 bin/ 目录", "dd.exe not found, please download and place in bin/"))
            return

        target_device = f"\\\\.\\{self.target_partition}"
        try:
            image_size = os.path.getsize(self.image_path)
        except:
            image_size = 0
            self.progress.emit(-1)

        cmd = [dd_path, f"if={self.image_path}", f"of={target_device}", "bs=4M", "--progress"]
        self.log.emit(tr(f"正在写入镜像到 {self.target_partition}...", f"Writing image to {self.target_partition}..."))

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            pattern = re.compile(r"(\d+)\+(\d+)\s+records in")
            total_records = None
            last_progress = 0

            for line in self.process.stdout:
                if self._cancelled:
                    self.finished.emit(False, tr("已取消", "Cancelled"))
                    return
                line = line.strip()
                if line:
                    m = pattern.search(line)
                    if m:
                        rec_in = int(m.group(1))
                        if image_size > 0 and total_records is None:
                            total_records = (image_size + 4*1024*1024 - 1) // (4*1024*1024)
                        if total_records and total_records > 0:
                            val = min(100, int(rec_in / total_records * 100))
                            if val > last_progress:
                                self.progress.emit(val)
                                last_progress = val

            self.process.wait()
            if self._cancelled:
                self.finished.emit(False, tr("已取消", "Cancelled"))
                return
            if self.process.returncode == 0:
                self.progress.emit(100)
                self.finished.emit(True, tr(f"烧录完成！({self.target_partition})", f"Burn completed! ({self.target_partition})"))
            else:
                self.finished.emit(False, tr(f"错误码 {self.process.returncode}", f"Error code {self.process.returncode}"))
        except Exception as e:
            self.finished.emit(False, tr(f"异常: {str(e)}", f"Exception: {str(e)}"))


# ============================================================
# 6. 烧录对话框（分区模式）
# ============================================================
class BurnDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("烧录镜像到分区", "Burn Image to Partition"))
        self.setMinimumWidth(650)
        self.setModal(True)
        self.image_path = None
        self.burn_thread = None
        self.system_drive = get_system_drive()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(14)

        h1 = QHBoxLayout()
        self.file_label = QLabel(tr("未选择镜像文件", "No image selected"))
        self.file_label.setStyleSheet("border: 1px solid #d0d0d0; border-radius: 4px; padding: 6px;")
        self.file_label.setMinimumWidth(300)
        self.btn_file = QPushButton(tr("选择文件", "Select"))
        self.btn_file.setFixedWidth(100)
        self.btn_file.clicked.connect(self.select_image)
        h1.addWidget(self.file_label)
        h1.addWidget(self.btn_file)
        layout.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel(tr("目标分区：", "Target partition:")))
        self.partition_combo = QComboBox()
        self.partition_combo.setMinimumWidth(350)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.refresh_partitions()
        h2.addWidget(self.partition_combo)
        self.btn_refresh = QPushButton(tr("刷新", "Refresh"))
        self.btn_refresh.setFixedWidth(80)
        self.btn_refresh.clicked.connect(self.refresh_partitions)
        h2.addWidget(self.btn_refresh)
        layout.addLayout(h2)

        info_label = QLabel(tr("提示：选择要烧录的分区（如 E:），程序只写入该分区，不影响其他分区。", "Hint: Select the partition to burn (e.g. E:). Only that partition will be written, others unaffected."))
        info_label.setStyleSheet("color: #555; font-size: 12px; padding: 4px 0;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.warn_label = QLabel(tr("⚠️ 目标分区上的所有数据将被清除！", "⚠️ All data on the target partition will be erased!"))
        self.warn_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        layout.addWidget(self.warn_label)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        layout.addWidget(self.log_text)

        h3 = QHBoxLayout()
        self.btn_start = QPushButton(tr("开始烧录", "Start Burn"))
        self.btn_start.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 4px; padding: 8px 20px;")
        self.btn_start.clicked.connect(self.start_burn)
        self.btn_cancel = QPushButton(tr("取消", "Cancel"))
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; border-radius: 4px; padding: 8px 20px;")
        self.btn_cancel.clicked.connect(self.cancel_burn)
        self.btn_close = QPushButton(tr("关闭", "Close"))
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; padding: 8px 20px;")
        h3.addWidget(self.btn_start)
        h3.addWidget(self.btn_cancel)
        h3.addWidget(self.btn_close)
        layout.addLayout(h3)

        self.setLayout(layout)

    def append_log(self, msg):
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.append(msg)
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("选择镜像文件", "Select Image"),
            os.path.expanduser("~"),
            tr("镜像文件 (*.dmg *.img *.rdr *.iso);;所有文件 (*.*)", "Image files (*.dmg *.img *.rdr *.iso);;All files (*.*)")
        )
        if path:
            self.image_path = path
            self.file_label.setText(tr(os.path.basename(path), os.path.basename(path)))
            self.file_label.setStyleSheet("border: 1px solid #4CAF50; border-radius: 4px; padding: 6px; background-color: #E8F5E9;")

    def refresh_partitions(self):
        self.partition_combo.clear()
        partitions = []

        try:
            result = subprocess.run(
                ["wmic", "logicaldisk", "get", "DeviceID,VolumeName,Size,FileSystem"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        dev_id = parts[0].strip()
                        fs = parts[1].strip()
                        size_str = parts[2].strip()
                        vol_name = ' '.join(parts[3:]).strip()
                        try:
                            size_bytes = int(size_str)
                            size_gb = size_bytes / (1024**3)
                        except:
                            size_gb = 0
                        if fs in ['CDFS', 'UDF']:
                            continue
                        if not dev_id or len(dev_id) < 2:
                            continue
                        is_system = (dev_id == self.system_drive)
                        label = f"{dev_id} ({vol_name if vol_name else '无卷标'}) {size_gb:.1f} GB - {fs}"
                        if is_system:
                            label += " ⚠️ " + tr("系统盘", "System Disk")
                        partitions.append((label, dev_id, is_system))
        except Exception as e:
            self.append_log(tr(f"枚举分区失败: {e}", f"Failed to enumerate partitions: {e}"))

        if not partitions:
            self.partition_combo.addItem(tr("未找到可写分区", "No writable partition found"), "")
            self.append_log(tr("⚠️ 枚举分区失败，请以管理员身份运行", "Failed to enumerate partitions, please run as administrator"))
            return

        for label, dev_id, is_sys in partitions:
            self.partition_combo.addItem(label, dev_id)

        if self.partition_combo.count() > 0:
            self.append_log(tr(f"✅ 找到 {self.partition_combo.count()} 个分区", f"Found {self.partition_combo.count()} partitions"))

    def start_burn(self):
        if not ensure_admin_for_burn(self):
            return

        if not self.image_path:
            show_rich_messagebox(self, tr("提示", "Hint"), tr_html("请先选择镜像文件", "Please select an image file first"), QMessageBox.Warning)
            return

        target = self.partition_combo.currentData()
        if not target or len(target) < 2:
            show_rich_messagebox(self, tr("提示", "Hint"), tr_html("请选择有效的目标分区", "Please select a valid target partition"), QMessageBox.Warning)
            return

        if target == self.system_drive:
            reply = show_rich_messagebox(
                self,
                tr("⚠️ 严重警告", "Critical Warning"),
                tr_html(
                    f"您选择了系统分区 {target}！\n烧录将永久清除系统分区上的所有数据！\n确定继续？",
                    f"You selected the system partition {target}!\nBurning will permanently erase all data on it!\nContinue?"
                ),
                QMessageBox.Critical,
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        reply = show_rich_messagebox(
            self,
            tr("确认烧录", "Confirm Burn"),
            tr_html(
                f"即将把镜像写入分区：{self.partition_combo.currentText()}\n该分区上的所有数据将被永久清除！\n请再次确认。",
                f"About to write image to partition: {self.partition_combo.currentText()}\nAll data on this partition will be permanently erased!\nPlease confirm again."
            ),
            QMessageBox.Question,
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("最终确认", "Final Confirmation"))
        dlg.setMinimumWidth(400)
        dlg.setModal(True)
        v = QVBoxLayout()
        v.addWidget(QLabel(tr("请输入 '确认清除' 以继续：", "Please type 'confirm erase' to continue:")))
        inp = QLineEdit()
        inp.setPlaceholderText(tr("确认清除", "confirm erase"))
        v.addWidget(inp)
        h = QHBoxLayout()
        ok_btn = QPushButton(tr("确认", "Confirm"))
        ok_btn.setEnabled(False)
        def check(t):
            ok_btn.setEnabled(t == "确认清除")
        inp.textChanged.connect(check)
        def do_ok():
            dlg.accept()
        ok_btn.clicked.connect(do_ok)
        cancel_btn = QPushButton(tr("取消", "Cancel"))
        cancel_btn.clicked.connect(dlg.reject)
        h.addWidget(ok_btn)
        h.addWidget(cancel_btn)
        v.addLayout(h)
        dlg.setLayout(v)
        if dlg.exec() != QDialog.Accepted:
            self.append_log(tr("烧录已取消", "Burn cancelled"))
            return

        self.append_log(tr(f"✅ 已通过全部安全确认，开始烧录到 {target}...", f"All security confirmations passed, starting burn to {target}..."))
        self.btn_start.setEnabled(False)
        self.btn_file.setEnabled(False)
        self.partition_combo.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.progress.setValue(0)
        self.log_text.clear()

        self.burn_thread = BurnThread(self.image_path, target)
        self.burn_thread.progress.connect(self.on_progress)
        self.burn_thread.log.connect(self.append_log)
        self.burn_thread.finished.connect(self.on_finished)
        self.burn_thread.start()

    def on_progress(self, val):
        if val == -1:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(val)

    def cancel_burn(self):
        if self.burn_thread and self.burn_thread.isRunning():
            reply = show_rich_messagebox(
                self,
                tr("确认取消", "Confirm Cancel"),
                tr_html(
                    "烧录正在进行，取消可能会损坏分区。确定要取消吗？",
                    "Burn is in progress, cancelling may damage the partition. Confirm?"
                ),
                QMessageBox.Question,
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.append_log(tr("正在取消烧录...", "Cancelling burn..."))
                self.burn_thread.cancel()
                self.btn_cancel.setEnabled(False)

    def on_finished(self, success, msg):
        self.btn_start.setEnabled(True)
        self.btn_file.setEnabled(True)
        self.partition_combo.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.btn_close.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setRange(0, 100)

        if self.burn_thread:
            self.burn_thread.deleteLater()
            self.burn_thread = None

        if success:
            show_rich_messagebox(self, tr("完成", "Done"), tr_html(msg, msg), QMessageBox.Information)
            self.close()
        else:
            show_rich_messagebox(self, tr("错误", "Error"), tr_html(msg, msg), QMessageBox.Critical)

    def closeEvent(self, event):
        if self.burn_thread and self.burn_thread.isRunning():
            reply = show_rich_messagebox(
                self,
                tr("确认取消", "Confirm Cancel"),
                tr_html(
                    "烧录进行中，取消可能会损坏分区。确定要退出吗？",
                    "Burn is in progress, cancelling may damage the partition. Confirm exit?"
                ),
                QMessageBox.Question,
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.burn_thread.cancel()
                self.burn_thread.wait()
                self.burn_thread.deleteLater()
                self.burn_thread = None
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ============================================================
# 7. 下载对话框
# ============================================================
MIRRORS = [
    ("百度网盘", "https://pan.baidu.com/s/11TebZUgDHnJru_-KxtCC-Q?pwd=hpdt", "hpdt"),
    ("天翼网盘", "https://cloud.189.cn/t/rAFrAzbiaeEv", "9zuj"),
    ("夸克网盘", "https://pan.quark.cn/s/1d1386e45627", "YCQ2"),
    ("123网盘", "https://www.123865.com/s/vGEiVv-7YxpH?pwd=RLxH#", "RLxH"),
    ("115网盘", "https://115cdn.com/s/sws798s36vd?password=jd86", "jd86"),
    ("阿里云盘", "https://www.alipan.com/s/Ea2fmYf8t5Y", "qj71 (RDR密码: hackintosh.club)"),
]

class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("下载镜像", "Download Image"))
        self.setMinimumWidth(720)
        self.setMinimumHeight(400)
        self.setModal(True)
        self.move(200, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        info_label = QLabel(tr("双击任意链接可复制到剪贴板", "Double-click any link to copy to clipboard"))
        info_label.setStyleSheet("color: #555; padding: 8px 0;")
        layout.addWidget(info_label)

        for name, url, code in MIRRORS:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background: #fafafa;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 6px 10px;
                    margin: 3px 0;
                }
                QFrame:hover {
                    background: #f0f0f0;
                    border-color: #b0b0b0;
                }
            """)
            h = QHBoxLayout(frame)
            h.setContentsMargins(8, 4, 8, 4)
            name_label = QLabel(f"<b>{name}</b>")
            name_label.setStyleSheet("min-width: 80px;")
            h.addWidget(name_label)

            url_label = QLabel(url)
            url_label.setStyleSheet("color: #1976D2;")
            url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)   # 直接设置，不进行位或操作
            url_label.mouseDoubleClickEvent = lambda e, u=url: self.copy(u)
            h.addWidget(url_label)

            if code:
                code_label = QLabel(f"🔑 {code}")
                code_label.setStyleSheet("color: #666; font-size: 11px; min-width: 100px;")
                h.addWidget(code_label)

            layout.addWidget(frame)

        close_btn = QPushButton(tr("关闭", "Close"))
        close_btn.setStyleSheet("background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 8px 24px;")
        close_btn.clicked.connect(self.close)
        h_btn = QHBoxLayout()
        h_btn.addStretch()
        h_btn.addWidget(close_btn)
        layout.addLayout(h_btn)

        self.setLayout(layout)

    def copy(self, url):
        QApplication.clipboard().setText(url)
        show_rich_messagebox(self, tr("已复制", "Copied"), tr_html(f"链接已复制到剪贴板：\n{url}", f"Link copied to clipboard:\n{url}"), QMessageBox.Information)


# ============================================================
# 8. 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("黑苹果一键辅助工具", "Hackintosh One-Click Assistant"))
        self.setGeometry(200, 200, 820, 500)

        font = QFont("SF Pro Display", 12)
        QApplication.setFont(font)

        cw = QWidget()
        self.setCentralWidget(cw)
        layout = QVBoxLayout(cw)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(28)

        title = QLabel(tr("黑苹果一键辅助工具", "Hackintosh One-Click Assistant"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 300; color: #2c3e50; letter-spacing: 1px;")
        layout.addWidget(title)

        subtitle = QLabel(tr("生成 EFI · 下载镜像 · 烧录分区", "Generate EFI · Download Image · Burn Partition"))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        layout.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(30)

        self.card1 = self._create_card("⚙️", tr("生成 EFI", "Generate EFI"), tr("调用 OpCore-Simplify", "Call OpCore-Simplify"))
        self.card1.clicked.connect(self.run_efi)
        cards.addWidget(self.card1)

        self.card2 = self._create_card("📥", tr("下载镜像", "Download Image"), tr("复制链接至浏览器", "Copy link to browser"))
        self.card2.clicked.connect(self.run_download)
        cards.addWidget(self.card2)

        self.card3 = self._create_card("📀", tr("烧录分区", "Burn Partition"), tr("写入指定分区", "Write to partition"))
        self.card3.clicked.connect(self.run_burn)
        cards.addWidget(self.card3)

        layout.addLayout(cards)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(130)
        self.output.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                font-family: 'SF Mono', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.output)

        status = QLabel(tr("就绪 — 点击卡片开始操作", "Ready — Click a card to start"))
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #95a5a6; font-size: 13px;")
        layout.addWidget(status)

        if not is_admin():
            self.append_log(tr("⚠️ 当前未以管理员身份运行，烧录功能可能失败。建议以管理员身份重新启动。",
                               "Not running as administrator, burn function may fail. Please restart as administrator."))

    def _create_card(self, icon, title, desc):
        btn = QPushButton()
        btn.setFixedSize(200, 180)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ffffff, stop:1 #f5f7fa);
                border: 1px solid #d0d7dd;
                border-radius: 16px;
                color: #2c3e50;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #f8f9fa, stop:1 #e9ecef);
                border-color: #b0b8c0;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #e9ecef, stop:1 #dee2e6);
            }
        """)
        layout = QVBoxLayout(btn)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 42px;")
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 17px; font-weight: 500;")
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(desc_label)

        return btn

    def append_log(self, msg):
        self.output.append(msg)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)

    # ---- 三个核心功能 ----
    def run_efi(self):
        self.append_log(tr("⚙️ 正在启动 EFI 生成工具...", "Starting EFI generator..."))
        possible_paths = [
            os.path.join(BASE_DIR, "tools", "OpCore-Simplify", "OpCore-Simplify.bat"),
            os.path.join(BASE_DIR, "tools", "OpCore-Simplify-main", "OpCore-Simplify.bat"),
        ]
        bat_path = None
        for p in possible_paths:
            if os.path.exists(p):
                bat_path = p
                break
        if bat_path is None:
            self.append_log(tr("❌ 未找到 OpCore-Simplify，请确认 tools/OpCore-Simplify/ 目录存在",
                               "OpCore-Simplify not found, please ensure tools/OpCore-Simplify/ exists"))
            return
        try:
            subprocess.Popen(
                ['cmd', '/c', 'start', '', bat_path],
                shell=False,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.append_log(tr("✅ OpCore-Simplify 已启动，请在新窗口中操作", "OpCore-Simplify started, please operate in the new window"))
        except Exception as e:
            self.append_log(tr(f"❌ 启动失败: {e}", f"Failed to start: {e}"))

    def run_download(self):
        self.append_log(tr("📥 正在打开下载列表...", "Opening download list..."))
        dlg = DownloadDialog(self)
        dlg.exec()
        self.append_log(tr("✅ 下载列表已关闭", "Download list closed"))

    def run_burn(self):
        self.append_log(tr("📀 正在打开烧录工具...", "Opening burn tool..."))
        dlg = BurnDialog(self)
        dlg.exec()
        self.append_log(tr("✅ 烧录工具已关闭", "Burn tool closed"))


# ============================================================
# 9. 程序入口
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QMainWindow {
            background: #f5f6f8;
        }
        QDialog {
            background: #f5f6f8;
        }
        QPushButton {
            font-size: 13px;
            border-radius: 6px;
            padding: 6px 14px;
        }
        QLabel {
            font-size: 13px;
        }
        QComboBox {
            padding: 4px 8px;
            border: 1px solid #d0d7dd;
            border-radius: 6px;
            background: white;
        }
        QProgressBar {
            border: 1px solid #d0d7dd;
            border-radius: 6px;
            text-align: center;
            height: 20px;
        }
        QProgressBar::chunk {
            background: #4CAF50;
            border-radius: 6px;
        }
        QTextEdit {
            font-size: 13px;
        }
        QLineEdit {
            padding: 6px;
            border: 1px solid #d0d7dd;
            border-radius: 6px;
        }
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())