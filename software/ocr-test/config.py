"""
Centralized configuration for OCR Test.
Loads variables from .env and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).parent.resolve()
MODELS_DIR = BASE_DIR / "models"
TEST_IMAGES_DIR = BASE_DIR / "test_images"

# For future Metis integration
VOYAGER_SDK_DIR = BASE_DIR.parent / "voyager-sdk"
VOYAGER_BUILD_DIR = VOYAGER_SDK_DIR / "build"

# Load .env
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to voyager-sdk .env if local doesn't exist
    voyager_env = VOYAGER_SDK_DIR / ".env"
    if voyager_env.exists():
        load_dotenv(voyager_env)


class RTSPConfig:
    """RTSP camera configuration."""
    username: str = os.getenv("RTSP_USERNAME", "")
    password: str = os.getenv("RTSP_PASSWORD", "")
    ip: str = os.getenv("RTSP_IP", "192.168.1.1")
    port: str = os.getenv("RTSP_PORT", "554")
    path: str = os.getenv("RTSP_PATH", "/av_stream/ch0")

    @classmethod
    def get_url(cls) -> str:
        """Build complete RTSP URL."""
        if cls.username and cls.password:
            return f"rtsp://{cls.username}:{cls.password}@{cls.ip}:{cls.port}{cls.path}"
        return f"rtsp://{cls.ip}:{cls.port}{cls.path}"


class OCRConfig:
    """OCR configuration."""
    model: str = os.getenv("OCR_MODEL", "ppocr_v3")
    lang: str = os.getenv("OCR_LANG", "latin")

    # Input size for PP-OCRv3 recognition
    input_height: int = 48
    input_width: int = 320

    # Preprocessing
    mean: tuple = (127.5, 127.5, 127.5)
    std: tuple = (127.5, 127.5, 127.5)

    # Model paths
    det_model_path: Path = MODELS_DIR / "ch_PP-OCRv3_det_infer.onnx"
    rec_model_path: Path = MODELS_DIR / "latin_PP-OCRv3_rec_infer.onnx"
    rec_char_dict: Path = MODELS_DIR / "latin_dict.txt"


class AppConfig:
    """Application configuration."""
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    save_intermediate: bool = os.getenv("SAVE_INTERMEDIATE", "false").lower() == "true"

    # Display
    window_width: int = 1280
    window_height: int = 720


# Singleton instances
rtsp = RTSPConfig()
ocr = OCRConfig()
app = AppConfig()


def check_voyager_env() -> bool:
    """Check if Voyager SDK environment is active (for Metis mode)."""
    return os.environ.get('AXELERA_FRAMEWORK') is not None


def get_metis_model_path(model_name: str) -> Path:
    """Return path to compiled model in Voyager SDK build directory."""
    return VOYAGER_BUILD_DIR / model_name
