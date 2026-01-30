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

    # Preprocessing (applied to crops before recognition)
    enable_preprocessing: bool = True

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


def setup_voyager_env() -> bool:
    """Setup Voyager SDK environment for Metis access from ocr-test venv.

    Returns True if setup successful, False otherwise.
    """
    import sys

    # Check if already configured
    if os.environ.get('AXELERA_FRAMEWORK'):
        return True

    # Setup paths
    voyager_site_packages = VOYAGER_SDK_DIR / "venv" / "lib" / "python3.10" / "site-packages"

    if not voyager_site_packages.exists():
        return False

    # Add voyager-sdk site-packages to Python path
    site_pkg_str = str(voyager_site_packages)
    if site_pkg_str not in sys.path:
        sys.path.insert(0, site_pkg_str)

    # Set environment variables
    os.environ['AXELERA_FRAMEWORK'] = str(VOYAGER_SDK_DIR)

    # Add ax_models to path
    ax_models_path = str(VOYAGER_SDK_DIR / "ax_models")
    if ax_models_path not in sys.path:
        sys.path.insert(0, ax_models_path)

    return True


def check_voyager_env() -> bool:
    """Check if Voyager SDK environment is available (for Metis mode)."""
    # Try to setup if not already done
    if not os.environ.get('AXELERA_FRAMEWORK'):
        setup_voyager_env()
    return os.environ.get('AXELERA_FRAMEWORK') is not None


def get_metis_model_path(model_name: str) -> Path:
    """Return path to compiled model in Voyager SDK build directory."""
    return VOYAGER_BUILD_DIR / model_name
