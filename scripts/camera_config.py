import toml
from pathlib import Path
from cerberus import Validator
from scripts.camera import CameraConfig


_SCHEMA = {
    "device_id": {"type": "string", "required": True},
    "width": {"type": "integer", "required": True},
    "height": {"type": "integer", "required": True},
    "fps": {"type": "integer", "required": True},
    "fx": {"type": "float", "required": True},
    "fy": {"type": "float", "required": True},
    "cx": {"type": "float", "required": True},
    "cy": {"type": "float", "required": True},
    "k1": {"type": "float", "required": True},
    "k2": {"type": "float", "required": True},
    "k3": {"type": "float", "required": True},
    "k4": {"type": "float", "required": True},
    "k5": {"type": "float", "required": False},
    "k6": {"type": "float", "required": False},
    "auto_exposure": {"type": "string", "required": False}
}


def get_config(file: str) -> CameraConfig:
    f = Path(file)
    if not f.exists():
        raise FileNotFoundError("No such file or directory: {}".format(f))

    dict_toml = toml.load(f)
    config = dict_toml["Rgb"]

    v = Validator()
    if not v.validate(config, _SCHEMA):
        raise ValueError("Invalid param in config: {}".format(v.errors))

    return CameraConfig.from_dict(config)