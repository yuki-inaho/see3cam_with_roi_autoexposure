import pytest
import sys
import time
from pathlib import Path

CURRENT_DIR = str(Path(".").resolve())
SCRIPTS_DIR = str(Path(CURRENT_DIR).resolve())
CONFIG_FILE_PATH = str(Path(f"{CURRENT_DIR}/cfg/camera_parameter.toml").resolve())

sys.path.append(SCRIPTS_DIR)
from scripts.camera import Camera, AutoExposureMode
from scripts.camera_config import get_config


@pytest.fixture
def fixture_camera(scope="session"):
    camera = Camera(get_config(CONFIG_FILE_PATH))
    return camera


def test_camera_is_activated(fixture_camera):
    camera = fixture_camera
    print(camera)


def test_auto_exposure_mode_setting(fixture_camera):
    camera = fixture_camera
    for ae_mode, inner_expected_mode in zip(["centered", "roi", "disabled"], ["Centered", "Manual", "Disable"]):
        camera.set_auto_exposure_mode(ae_mode)
        aquired_auto_exposure_mode, _ = camera.auto_exposure_setting
        time.sleep(1.0)
        assert inner_expected_mode == [mode.name for mode in AutoExposureMode if aquired_auto_exposure_mode == mode.value][0]