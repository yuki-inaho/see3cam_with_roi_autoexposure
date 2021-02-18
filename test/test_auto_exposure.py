import sys
import time
from pathlib import Path
from enum import IntEnum

import cv2
import pytest

CURRENT_DIR = str(Path(".").resolve())
SCRIPTS_DIR = str(Path(CURRENT_DIR).resolve())
CONFIG_FILE_PATH = str(Path(f"{CURRENT_DIR}/cfg/camera_parameter.toml").resolve())

sys.path.append(SCRIPTS_DIR)
from scripts.camera import Camera, AutoExposureMode
from scripts.camera_config import get_config


class CVAutoExposure(IntEnum):
    AUTO = 0
    MANUAL = 1


@pytest.fixture
def fixture_camera(scope="session"):
    camera = Camera(get_config(CONFIG_FILE_PATH))
    return camera


def test_camera_is_activated(fixture_camera):
    camera = fixture_camera
    print(camera)


def test_auto_exposure_mode_setting(fixture_camera):
    camera = fixture_camera
    for ae_mode, inner_expected_mode, ae_window_size in zip(["centered", "roi", "disabled"], ["Centered", "Manual", "Disable"], [8, 4, None]):
        if ae_mode == "disabled":
            # When without below process (call only camera.set_auto_exposure_mode("disabled")),
            # "aquired_auto_exposure_mode" will set "Manual"
            camera._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, CVAutoExposure.MANUAL)
            for _mode in ["centered", "disabled"]:
                camera.set_auto_exposure_mode(_mode)
                aquired_auto_exposure_mode, _ = camera.auto_exposure_setting
                assert inner_expected_mode == [mode.name for mode in AutoExposureMode if aquired_auto_exposure_mode == mode.value][0]

            camera._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, CVAutoExposure.AUTO)
            camera.set_auto_exposure_mode("disabled")
            aquired_auto_exposure_mode, _ = camera.auto_exposure_setting
            assert inner_expected_mode == "Disable"
        else:
            camera._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, CVAutoExposure.AUTO)
            camera.set_auto_exposure_mode(ae_mode)
            aquired_auto_exposure_mode, aquired_ae_window_size = camera.auto_exposure_setting
            assert inner_expected_mode == [mode.name for mode in AutoExposureMode if aquired_auto_exposure_mode == mode.value][0]
            assert ae_window_size == aquired_ae_window_size