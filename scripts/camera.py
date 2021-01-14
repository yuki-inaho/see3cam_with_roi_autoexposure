from datetime import datetime
from threading import RLock
from typing import Optional

import cv2
import numpy as np
from attr import dataclass, fields
from scripts.see3cam_api import set_half_area_auto_exposure, get_hid_handle_from_device_id


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
        self._frame = Frame()
        self._hid_handle = get_hid_handle_from_device_id(camera_config.device_id)
        # self._hid_handle = get_see3cam_hid_handle()
        set_half_area_auto_exposure(camera_config.width, camera_config.height, self._hid_handle)

    def update(self) -> bool:
        ret, frame = self._cap.read()
        self._frame.data = frame
        return ret

    @property
    def image_timestamp(self):
        return self._frame.timestamp

    @property
    def image(self):
        return self._frame.data

    @property
    def remap_image(self):
        return cv2.remap(
            self._frame.data,
            self._map1,
            self._map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )