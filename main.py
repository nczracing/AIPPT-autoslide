# -*- coding: utf-8 -*-
"""
AutoSlide - AI自动化PPT制作系统
主入口文件

设计要点（针对"双击 exe 闪退且无日志"问题）：
1. 日志系统在「任何项目模块 import 之前」建立，并写入 exe 同级 logs/，
   保证即使是 import 阶段崩溃也能落盘，不再静默消失。
2. 安装 sys.excepthook，捕获一切未捕获异常并写入日志，必要时弹窗提示。
3. qt_message_handler 使用 PyQt6 正确的 QtMsgType 枚举（旧代码误用
   Qt.MessageType，该属性在 PyQt6 已被移除，会导致首次 Qt 消息即崩溃）。
"""
import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------------------------------
# 1) 早期日志：必须在任何项目 import 之前完成，保证崩溃可诊断
# ----------------------------------------------------------------------------
def _app_dir() -> Path:
    """程序所在目录：exe 模式取 exe 同级，源码模式取脚本同级。"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _init_log() -> Path:
    """建立早期日志，返回日志文件路径。

    策略：
    1. exe模式：写入项目根目录logs/（通过exe上级目录推断）
    2. 源码模式：写入脚本同级logs/
    3. 兜底：写入TEMP/AutoSlide_logs/
    """
    app_dir = _app_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 尝试多个候选目录
    candidates = []

    if getattr(sys, 'frozen', False):
        # exe模式：尝试推断项目根目录
        project_root = app_dir  # 初始为exe所在目录

        # 如果exe在dist目录，向上推断项目根
        if app_dir.name == "dist" and app_dir.parent.exists():
            project_root = app_dir.parent
            candidates.append(project_root / "logs")

        # 备选：exe同级目录
        candidates.append(app_dir / "logs")
    else:
        # 源码模式：脚本所在目录（项目根）
        candidates.append(app_dir / "logs")

    # 系统临时目录（兜底）
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        candidates.append(Path(temp) / "AutoSlide_logs")

    # 当前工作目录（兼容从其他位置运行）
    candidates.append(Path.cwd() / "logs")

    log_dir = None
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            probe = c / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            log_dir = c
            break
        except Exception:
            continue

    if log_dir is None:
        # 最终兜底：确保app_dir/logs存在
        log_dir = app_dir / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    log_file = log_dir / f"autoslide_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # 清除已存在的handler（避免重复）
    root.handlers.clear()

    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        pass

    # stderr输出（调试时用）
    try:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        root.addHandler(sh)
    except Exception:
        pass

    return log_file


LOG_FILE = _init_log()
logger = logging.getLogger("autoslide")


# ----------------------------------------------------------------------------
# 2) 全局未捕获异常钩子：任何崩溃都写入日志，必要时弹窗
# ----------------------------------------------------------------------------
def _global_excepthook(exc_type, exc_value, exc_tb):
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        logging.getLogger().error("未捕获异常(全局):\n" + tb_text)
    except Exception:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("未捕获异常(全局):\n" + tb_text)
        except Exception:
            pass
    # 尽力弹出错误提示，帮助用户定位
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(
                None,
                "AutoSlide 致命错误",
                f"程序异常退出：\n{exc_value}\n\n详细日志：\n{LOG_FILE}",
            )
    except Exception:
        pass


sys.excepthook = _global_excepthook


# ----------------------------------------------------------------------------
# 3) 项目模块导入（失败也会被上面钩子记录，不再静默闪退）
# ----------------------------------------------------------------------------
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
    from utils.logger import setup_logger  # 保留兼容；本文件使用 bootstrap 根日志
    from ui.main_window import MainWindow
    from ui.theme import apply_theme
except Exception as e:
    logger.error("模块导入失败: %s", e, exc_info=True)
    raise


# ----------------------------------------------------------------------------
# 4) Qt 消息转发（使用正确的 QtMsgType 枚举）
# ----------------------------------------------------------------------------
def qt_message_handler(msg_type, context, msg):
    """将 Qt 日志转发到 Python logging。"""
    level = logging.DEBUG
    try:
        if msg_type == QtMsgType.WarningMsg:
            level = logging.WARNING
        elif msg_type in (QtMsgType.CriticalMsg, QtMsgType.FatalMsg):
            level = logging.ERROR
        elif msg_type == QtMsgType.InfoMsg:
            level = logging.INFO
    except Exception:
        level = logging.WARNING
    logger.log(level, f"[Qt] {msg}")


qInstallMessageHandler(qt_message_handler)


# ----------------------------------------------------------------------------
# 5) 主流程
# ----------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("AutoSlide 启动")
    logger.info(f"运行模式: {'exe' if getattr(sys, 'frozen', False) else 'source'}")
    logger.info(f"程序目录: {_app_dir()}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("=" * 60)

    app = QApplication(sys.argv)
    # 加载用户保存的主题偏好
    try:
        from settings_module import get_settings
        _ui_settings = get_settings().get_ui_config()
        _theme_mode = _ui_settings.get('theme', 'light')
    except Exception:
        _theme_mode = 'light'
    apply_theme(app, _theme_mode)

    logger.info("创建主窗口...")
    window = MainWindow()
    logger.info("显示主窗口...")
    window.show()

    logger.info("进入事件循环...")
    exit_code = app.exec()
    logger.info(f"程序退出，代码: {exit_code}")
    return exit_code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        logger.error("主流程异常退出", exc_info=True)
        raise
