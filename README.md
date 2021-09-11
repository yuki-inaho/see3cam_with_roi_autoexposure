# memo
- This code is implemented with [pyudev](https://github.com/pyudev/pyudev)
- If you get the following error, please try below processes.
```
PermissionError: [Errno 13] Permission denied: '/dev/hidraw0'
```
1. Create the file /etc/udev/rules.d/99-com.rules
```99-com.rules
KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"
```
2. Restart udev
```
sudo udevadm control --reload-rules && sudo udevadm trigger
```

![screenshot of demo_lower_center_roi.py](https://github.com/yuki-inaho/see3cam_with_roi_autoexposure/blob/main/Screenshot.png)