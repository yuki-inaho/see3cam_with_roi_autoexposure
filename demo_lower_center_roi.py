import sys
import cvui
import argparse
import cv2
import numpy as np

from pathlib import Path
from scripts.camera import Camera
from scripts.camera_config import get_config
from functools import partial


def parse_args():
    parser = argparse.ArgumentParser(description="")
    default_comm_path = str(Path(Path(__file__).parent, "cfg/camera_parameter.toml"))
    parser.add_argument("--camera-toml-path", "-c", type=str, default=default_comm_path)
    parser.add_argument("--enable-distortion-correction", "-d", action="store_true")
    return parser.parse_args()


def scaling_int(int_num, scale):
    return int(int_num * scale)


def main(camera_toml_path, enable_distortion_correction):
    camera_config = get_config(camera_toml_path)
    camera = Camera(camera_config)
    print(camera)
    scaling = partial(scaling_int, scale=2.0 / 3)
    if camera_config.roi_size != 4:
        sys.exit('This script is only supported on "camera_config.roi_size == 4" ')

    image_width = camera.image_width
    image_height = camera.image_height

    roi = cvui.Rect(0, 0, 0, 0)
    WINDOW_NAME = "Capture"
    cvui.init(WINDOW_NAME)
    while True:
        key = cv2.waitKey(10)
        frame = np.zeros((scaling(image_height), scaling(image_width), 3), np.uint8)
        frame[:] = (49, 52, 49)

        status = camera.update()
        if status:
            # WARNING:If distortion correction is enabled, the rectangle on windows doesn't indicate actual RoI area for auto exposure.
            see3cam_rgb_image = camera.remap_image if enable_distortion_correction else camera.image
            scaled_width = scaling(image_width)
            scaled_height = scaling(image_height)
            see3cam_rgb_image_resized = cv2.resize(see3cam_rgb_image, (scaled_width, scaled_height))
            frame[:scaled_height, :scaled_width, :] = see3cam_rgb_image_resized

            window_w = image_width // 2
            window_h = image_height // 2
            roi = cvui.Rect(scaling(window_w - image_width // 4), scaling(window_h), scaling(window_w), scaling(window_h))

            # Ensure ROI is within bounds
            roi.x = 0 if roi.x < 0 else roi.x
            roi.y = 0 if roi.y < 0 else roi.y
            roi.width = roi.width + scaled_width - (roi.x + roi.width) if roi.x + roi.width > scaled_width else roi.width
            roi.height = roi.height + scaled_height - (roi.y + roi.height) if roi.y + roi.height > scaled_height else roi.height

            cvui.rect(frame, roi.x, roi.y, roi.width, roi.height, 0xFF0000)

        if key == 27 or key == ord("q"):
            break

        cvui.update()
        cvui.imshow(WINDOW_NAME, frame)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    args = parse_args()
    main(args.camera_toml_path, args.enable_distortion_correction)