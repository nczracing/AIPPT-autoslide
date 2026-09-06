"""
File operation utilities
"""
import os
from pathlib import Path


class FileHelper:
    """File operation utility class"""

    @staticmethod
    def browse_directory(initial_path: str = "") -> str:
        """Open directory selection dialog (requires UI integration)"""
        return initial_path

    @staticmethod
    def browse_file(
        initial_path: str = "",
        file_types: str = "All Files (*.*)",
    ) -> str:
        """Open file selection dialog (requires UI integration)"""
        return initial_path

    @staticmethod
    def save_file(
        initial_filename: str = "",
        file_types: str = "PPTX Files (*.pptx)",
    ) -> str:
        """Open save dialog (requires UI integration)"""
        return initial_filename

    @staticmethod
    def read_file(path: str, encoding: str = "utf-8") -> str:
        """Read file content"""
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    @staticmethod
    def write_file(path: str, content: str, encoding: str = "utf-8"):
        """Write file content"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def get_default_save_dir() -> str:
        """Get default save directory"""
        home = Path.home()
        return str(home / "Documents" / "AutoSlide")
