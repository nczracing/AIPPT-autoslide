"""
日志工具 - 增强版
支持文件日志和控制台日志
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "autoslide", log_file: str = None, log_dir: str = None) -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 日志目录 - 优先使用传入的参数，否则尝试从__file__推断
    if log_dir:
        log_path_obj = Path(log_dir)
    else:
        # 尝试多种方式确定日志目录
        _possible_dirs = [
            Path.cwd() / "logs",  # 当前工作目录
        ]
        # 如果是源码模式，也尝试从__file__推断
        import sys
        if not getattr(sys, 'frozen', False):
            _possible_dirs.append(Path(__file__).parent.parent / "logs")
        log_path_obj = next((d for d in _possible_dirs if d.exists()), Path.cwd() / "logs")

    # 确保目录存在
    log_path_obj.mkdir(parents=True, exist_ok=True)
    # 打印调试信息
    print(f"[DEBUG] 日志目录: {log_path_obj}", file=sys.stderr)

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件handler
    if log_file:
        log_path = Path(log_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_path_obj / f"{name}_{timestamp}.log"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        file_handler = logging.FileHandler(log_path, encoding="utf-8", mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.debug(f"日志文件已创建: {log_path}")
        # 立即刷新确保日志写入
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
    except Exception as e:
        print(f"日志文件创建失败: {e}", file=sys.stderr)

    return logger


# 默认日志实例（仅在模块直接运行时创建）
if __name__ == '__main__':
    logger = setup_logger()
else:
    # 作为模块导入时不创建默认实例，由调用方决定
    logger = None
