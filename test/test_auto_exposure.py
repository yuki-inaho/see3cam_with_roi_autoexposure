import pytest
import sys
from pathlib import Path

CURRENT_DIR = str(Path(".").resolve())
SCRIPTS_DIR = str(Path(CURRENT_DIR).resolve())
CONFIG_FILE_PATH = str(Path(f"{CURRENT_DIR}/cfg/camera_parameter.toml").resolve())

sys.path.append(SCRIPTS_DIR)
from scripts.camera import Camera
from scripts.camera_config import get_config

@pytest.fixture
def fixture_camera(scope="session"):
    camera = Camera(get_config(CONFIG_FILE_PATH))
    return camera
