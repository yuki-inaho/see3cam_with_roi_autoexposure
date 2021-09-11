import os
import re
import errno
from select import select
from time import sleep

# WARNING: LGPL
import pyudev

# If you would like to know the detail of See3CAM CU20's RoI based Autoexposure function, see below code lines
# https://github.com/econsysqtcam/qtcam/blob/master/src/see3cam_cu20.cpp#L436-L489

# If you would like to know the detail of See3CAM CU20's HID settings, see below scripts
# https://github.com/econsystems/opencv/blob/master/Source/PythonScript/hid.py

BUFFER_LENGTH = 65
READ_FIRMWARE_VERSION = 0x40
CAMERA_CONTROL_CU20 = 0x86

GET_AE_ROI_MODE_CU20 = 0x05
SET_AE_ROI_MODE_CU20 = 0x06

AutoExpCentered = 0x01
AutoExpManual = 0x02
AutoExpDisabled = 0x03

FAIL = 0x00
SUCCESS = 0x01


def hid_write(hid_handle: int, input_buffer: bytearray):
    """Writes the input buffer on to the hid handle"""

    if input_buffer is not None:
        retry_count = 0
        bytes_written = 0
        while retry_count < 3:
            try:
                bytes_written = os.write(hid_handle, input_buffer)
                retry_count += 1
            except IOError as e:
                if e.errno == errno.EPIPE:
                    sleep(0.1)
            else:
                break
        if bytes_written != len(input_buffer):
            raise IOError(errno.EIO, "Written %d bytes out of expected %d" % (bytes_written, len(input_buffer)))


def hid_read(hid_handle):
    """Reads data from the hid handle of the device"""
    output_buffer = None
    timeout = 2000.0
    rlist, wlist, xlist = select([hid_handle], [], [hid_handle], timeout)

    if xlist:
        if xlist == [hid_handle]:
            raise IOError(errno.EIO, "exception on file descriptor %d" % hid_handle)

    if rlist:
        if rlist == [hid_handle]:
            output_buffer = os.read(hid_handle, BUFFER_LENGTH)
            if output_buffer is None:
                return b""
    return output_buffer


def get_hid_handle_from_device_id(device_id):
    context = pyudev.Context()
    video_device = pyudev.Devices.from_device_file(context, device_id)
    assert "ID_SERIAL" in video_device.properties

    serial_sequence = video_device.properties.get("ID_SERIAL")
    # serial_id is alphanumeric like "180B0204"
    serial_id = re.search(r"e-con_Systems_See3CAM_CU20_([A-Z0-9]*)", serial_sequence).group(1)

    for device in pyudev.Context().list_devices(subsystem="hidraw"):
        usb_device = device.find_parent("usb", "usb_device")
        if usb_device:
            vendor_id = usb_device.get("ID_VENDOR_ID")
            product_id = usb_device.get("ID_MODEL_ID")
            if vendor_id == "2560" and product_id == "c120":  # Detect See3CAM CU20 device
                hid_device = device.parent
                if serial_id == hid_device.get("HID_UNIQ"):
                    hid_device_path = hid_device.children.__next__().device_node
                    break

    hid_handle = os.open(hid_device_path, os.O_RDWR, os.O_NONBLOCK)
    return hid_handle


def enable_centered_auto_exposure(image_width, image_height, hid_handle, win_size=8):
    """ Set Centered auto exposure to camera """
    input_buffer = bytearray([0] * BUFFER_LENGTH)
    input_buffer[1] = CAMERA_CONTROL_CU20
    input_buffer[2] = SET_AE_ROI_MODE_CU20
    input_buffer[3] = AutoExpCentered
    input_buffer[6] = win_size

    hid_write(hid_handle, input_buffer)
    output_buffer = hid_read(hid_handle)

    if output_buffer[6] == 0x00:
        print("\nEnabling AutoExposure(centered) is failed\n")
        return False
    elif (
        output_buffer[0] == CAMERA_CONTROL_CU20
        and output_buffer[1] == SET_AE_ROI_MODE_CU20
        and output_buffer[6] == SUCCESS
    ):
        print("\nAutoExposure(centered) is enabled\n")
        return True


def enable_lower_center_roi_auto_exposure(image_width, image_height, hid_handle, win_size=4):
    """ Set ROI auto exposure to camera """
    outputLow = 0
    outputHigh = 255

    # Convert RoI center position to 0-255 value
    inputXLow = 0
    inputXHigh = image_width - 1
    inputXCord = int(image_width / 2)
    outputXCord = int(((inputXCord - inputXLow) / (inputXHigh - inputXLow)) * (outputHigh - outputLow) + outputLow)

    inputYLow = 0
    inputYHigh = image_height - 1
    inputYCord = int(image_height * 3 / 4)
    outputYCord = int(((inputYCord - inputYLow) / (inputYHigh - inputYLow)) * (outputHigh - outputLow) + outputLow)

    input_buffer = bytearray([0] * BUFFER_LENGTH)
    input_buffer[1] = CAMERA_CONTROL_CU20
    input_buffer[2] = SET_AE_ROI_MODE_CU20
    input_buffer[3] = AutoExpManual
    input_buffer[4] = outputXCord
    input_buffer[5] = outputYCord
    input_buffer[6] = win_size

    hid_write(hid_handle, input_buffer)
    output_buffer = hid_read(hid_handle)

    if output_buffer[6] == 0x00:
        print("\nEnabling AutoExposure(RoI based) is failed\n")
        return False
    elif (
        output_buffer[0] == CAMERA_CONTROL_CU20
        and output_buffer[1] == SET_AE_ROI_MODE_CU20
        and output_buffer[6] == SUCCESS
    ):
        print("\nAutoExposure(RoI based) is enabled\n")
        return True


def enable_roi_auto_exposure(xcord, ycord, image_width, image_height, hid_handle, win_size=4):
    """ Set ROI auto exposure to camera """
    outputLow = 0
    outputHigh = 255

    # Convert RoI center position to 0-255 value
    inputXLow = 0
    inputXHigh = image_width - 1
    inputXCord = xcord
    outputXCord = int(((inputXCord - inputXLow) / (inputXHigh - inputXLow)) * (outputHigh - outputLow) + outputLow)

    inputYLow = 0
    inputYHigh = image_height - 1
    inputYCord = ycord
    outputYCord = int(((inputYCord - inputYLow) / (inputYHigh - inputYLow)) * (outputHigh - outputLow) + outputLow)

    input_buffer = bytearray([0] * BUFFER_LENGTH)
    input_buffer[1] = CAMERA_CONTROL_CU20
    input_buffer[2] = SET_AE_ROI_MODE_CU20
    input_buffer[3] = AutoExpManual
    input_buffer[4] = outputXCord
    input_buffer[5] = outputYCord
    input_buffer[6] = win_size

    hid_write(hid_handle, input_buffer)
    output_buffer = hid_read(hid_handle)

    if output_buffer[6] == 0x00:
        print("\nEnabling AutoExposure(RoI based) is failed\n")
        return False
    elif (
        output_buffer[0] == CAMERA_CONTROL_CU20
        and output_buffer[1] == SET_AE_ROI_MODE_CU20
        and output_buffer[6] == SUCCESS
    ):
        print("\nAutoExposure(RoI based) is enabled\n")
        return True


def disable_auto_exposure(image_width, image_height, hid_handle, win_size=8):
    input_buffer = bytearray([0] * BUFFER_LENGTH)
    input_buffer[1] = CAMERA_CONTROL_CU20
    input_buffer[2] = SET_AE_ROI_MODE_CU20
    input_buffer[3] = AutoExpDisabled

    hid_write(hid_handle, input_buffer)
    output_buffer = hid_read(hid_handle)

    if output_buffer[6] == 0x00:
        print("\nDisabling AutoExposure(centered) failed\n")
        return False
    elif (
        output_buffer[0] == CAMERA_CONTROL_CU20
        and output_buffer[1] == SET_AE_ROI_MODE_CU20
        and output_buffer[6] == SUCCESS
    ):
        print("\nAutoExposure(centered) is disabled\n")
        return True


def get_auto_exposure_property(hid_handle):
    """ Get auto exposure setting property"""
    input_buffer = bytearray([0] * BUFFER_LENGTH)
    input_buffer[1] = CAMERA_CONTROL_CU20
    input_buffer[2] = GET_AE_ROI_MODE_CU20

    hid_write(hid_handle, input_buffer)
    output_buffer = hid_read(hid_handle)

    if output_buffer[6] == 0x00:
        print("\nGetting AutoExposure Setting is failed\n")
        return False, None, None
    elif (
        output_buffer[0] == CAMERA_CONTROL_CU20
        and output_buffer[1] == GET_AE_ROI_MODE_CU20
        and output_buffer[6] == SUCCESS
    ):
        roi_mode = output_buffer[2]
        window_size = output_buffer[5]
        return True, roi_mode, window_size
