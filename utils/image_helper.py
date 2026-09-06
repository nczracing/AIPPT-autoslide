"""
Image processing utilities
"""
from PIL import Image
from io import BytesIO
from pathlib import Path


class ImageHelper:
    """Image processing utility class"""

    @staticmethod
    def resize_image(image_path: str, max_width: int = 800, max_height: int = 600) -> str:
        """Resize image"""
        img = Image.open(image_path)
        img.thumbnail((max_width, max_height))

        output_path = Path(image_path).parent / f"_resized_{Path(image_path).name}"
        img.save(output_path)
        return str(output_path)

    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """Convert image to base64"""
        with open(image_path, "rb") as f:
            import base64
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def is_valid_image(path: str) -> bool:
        """Check if path is a valid image"""
        try:
            img = Image.open(path)
            img.verify()
            return True
        except Exception:
            return False
