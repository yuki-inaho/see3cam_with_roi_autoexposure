from datetime import datetime
from threading import RLock
from typing import Optional

import cv2
import numpy as np
from enum import Enum
from attr import dataclass, fields
from scripts.see3cam_api import (
    enable_centered_auto_exposure,
    enable_lower_center_roi_auto_exposure,
    enable_roi_auto_exposure,
    disable_auto_exposure,
    get_hid_handle_from_device_id,
    get_auto_exposure_property,
)


class AutoExposureMode(Enum):
    Centered = 0x01
    Manual = 0x02
    Disable = 0x03


class FromDict:
    @classmethod
    def from_dict(cls, _dict):
        init_kwargs = {}
        for field in fields(cls):
            field_value = _dict[field.name] if field.name in _dict.keys() else None
            init_kwargs[field.name] = field_value
        return cls(**init_kwargs)


@dataclass
class CameraConfig(FromDict):
    device_id: str
    width: int
    height: int
    fps: int
    fx: float
    fy: float
    cx: float
    cy: float
    k1: float
    k2: float
    k3: float
    k4: float
    auto_exposure: Optional[str]
    roi_size: Optional[int]


def confirm_prop(cap, prop_id, value_arg):
    value_act = cap.get(prop_id)
    if value_act != value_arg:
        raise RuntimeError("failed to set property. arg: {}, act: {}".format(value_arg, value_act))


def fisheye_undistort_rectify_map(cfg: CameraConfig):
    camera_mat = np.array([[cfg.fx, 0.0, cfg.cx], [0.0, cfg.fy, cfg.cy], [0.0, 0.0, 1.0]])
    dist_coef = np.array([[cfg.k1, cfg.k2, cfg.k3, cfg.k4]])
    projection_camera_mat = cv2.getOptimalNewCameraMatrix(camera_mat, dist_coef, (cfg.width, cfg.height), 0)[0]
    DIM = (cfg.width, cfg.height)
    return cv2.fisheye.initUndistortRectifyMap(camera_mat, dist_coef, np.eye(3), projection_camera_mat, DIM, cv2.CV_16SC2)


def get_cv2_video(cfg: CameraConfig) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(cfg.device_id)
    if not cap.isOpened():
        raise RuntimeError("failed to open camera. device id : {} ".format(cfg.device_id))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
    cap.set(cv2.CAP_PROP_FPS, cfg.fps)
    confirm_prop(cap, cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
    confirm_prop(cap, cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
    confirm_prop(cap, cv2.CAP_PROP_FPS, cfg.fps)
    return cap


class Frame(object):
    def __init__(self):
        self._data: np.ndarray = []
        self._timestamp: Optional[datetime] = None
        self._lock: RLock = RLock()

    @property
    def timestamp(self) -> Optional[datetime]:
        with self._lock:
            return self._timestamp

    @property
    def data(self) -> np.ndarray:
        with self._lock:
            return self._data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        with self._lock:
            self._timestamp = datetime.now()
            self._data = value


class Camera:
    def __init__(self, camera_config: CameraConfig):
        self._cap = get_cv2_video(camera_config)
        self._map1, self._map2 = fisheye_undistort_rectify_map(camera_config)
        self._image_width = camera_config.width
        self._image_height = camera_config.height
        self._roi_size = camera_config.roi_size if camera_config.roi_size is not None else 4
        self._frame = Frame()

        self._initialize_auto_exposure_mode(camera_config)

    def __str__(self):
        aquired_auto_exposure_mode, ae_window_size = self.auto_exposure_setting
        aquired_auto_exposure_str = [mode.name for mode in AutoExposureMode if aquired_auto_exposure_mode == mode.value]
        assert len(aquired_auto_exposure_str) > 0

        aquired_auto_exposure_str = aquired_auto_exposure_str[0]

        return (
            f"<< Auto Exposure Setting Information >>\n"
            f"Auto Exposure Mode (Expected): {self.auto_exposure_mode}\n"
            f"Auto Exposure Setting (Actual): \n"
            f"  Auto Exposure Mode: {aquired_auto_exposure_str} \n"
            f"  Window Size: {ae_window_size}"
        )

    def _initialize_auto_exposure_mode(self, camera_config: CameraConfig):
        self._hid_handle = get_hid_handle_from_device_id(camera_config.device_id)
        if camera_config.auto_exposure is None:
            self.set_auto_exposure_mode("centered")
        else:
            self.set_auto_exposure_mode(camera_config.auto_exposure)
        self._auto_exposure_mode = camera_config.auto_exposure

    def set_auto_exposure_mode(self, requested_auto_exposure_mode: str):
        if not requested_auto_exposure_mode in ["centered", "roi", "lower_center", "disabled"]:
            raise ValueError(f"\nNo such auto-exposure mode {requested_auto_exposure_mode}. Choose [centered, roi, disabled, lower_center]")

        if requested_auto_exposure_mode == "centered":
            self._ae_status = enable_centered_auto_exposure(self.image_width, self.image_height, self._hid_handle)
        elif requested_auto_exposure_mode == "roi":
            self._ae_status = enable_roi_auto_exposure(
                self.image_width // 2, self.image_height // 2, self.image_width, self.image_height, self._hid_handle
            )
        elif requested_auto_exposure_mode == "lower_center":
            self._ae_status = enable_lower_center_roi_auto_exposure(self.image_width, self.image_height, self._hid_handle)
        elif requested_auto_exposure_mode == "disabled":
            self._ae_status = disable_auto_exposure(self.image_width, self.image_height, self._hid_handle)
        assert self._ae_status

    def update(self) -> bool:
        ret, frame = self._cap.read()
        self._frame.data = frame
        return ret

    def set_roi_properties(self, xcord, ycord, win_size=4):
        self._ae_status = enable_roi_auto_exposure(xcord, ycord, self.image_width, self.image_height, self._hid_handle, win_size=win_size)

    @property
    def image_timestamp(self):
        return self._frame.timestamp

    @property
    def image(self):
        return self._frame.data

    @property
    def image_width(self):
        return self._image_width

    @property
    def image_height(self):
        return self._image_height

    @property
    def remap_image(self):
        return cv2.remap(
            self._frame.data,
            self._map1,
            self._map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )

    @property
    def auto_exposure_setting(self):
        status, roi_mode, window_size = get_auto_exposure_property(self._hid_handle)
        if not status:
            print("Getting auto exposure setting is failed")
        return roi_mode, window_size

    @property
    def auto_exposure_mode(self) -> str:
        if self._auto_exposure_mode is None:
            return "centered"
        else:
            return self._auto_exposure_mode
