"""
SysPulse — USB Collector
Reads USB device information directly from /sys/bus/usb/devices/ (sysfs).
No external libraries required.
"""

import os
import glob
from typing import Dict, Any, List, Optional


def _read_sysfs(path: str) -> Optional[str]:
    """Read a sysfs file, return None on failure."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _get_usb_speed_label(speed: str) -> str:
    """Convert USB speed value to human-readable label."""
    speed_map = {
        "1.5": "USB 1.0 (Low Speed)",
        "12": "USB 1.1 (Full Speed)",
        "480": "USB 2.0 (High Speed)",
        "5000": "USB 3.0 (SuperSpeed)",
        "10000": "USB 3.1 (SuperSpeed+)",
        "20000": "USB 3.2 (SuperSpeed++)",
    }
    return speed_map.get(speed, f"USB ({speed} Mbps)")


def get_usb_devices() -> List[Dict[str, Any]]:
    """
    Collect information about connected USB devices.
    Reads directly from sysfs — no external libraries needed.
    """
    devices = []
    usb_path = "/sys/bus/usb/devices/"

    if not os.path.exists(usb_path):
        return devices

    for entry in sorted(os.listdir(usb_path)):
        device_dir = os.path.join(usb_path, entry)

        # Skip interfaces (contain ':') and non-directories
        if ":" in entry or not os.path.isdir(device_dir):
            continue

        # Read device attributes
        vendor_id = _read_sysfs(os.path.join(device_dir, "idVendor"))
        product_id = _read_sysfs(os.path.join(device_dir, "idProduct"))

        # Skip root hubs and devices without IDs
        if not vendor_id or not product_id:
            continue
        if vendor_id == "0000" and product_id == "0000":
            continue

        manufacturer = _read_sysfs(os.path.join(device_dir, "manufacturer")) or "Unknown"
        product = _read_sysfs(os.path.join(device_dir, "product")) or "Unknown Device"
        serial = _read_sysfs(os.path.join(device_dir, "serial"))
        speed = _read_sysfs(os.path.join(device_dir, "speed")) or "?"

        # Power info
        max_power = _read_sysfs(os.path.join(device_dir, "bMaxPower")) or "N/A"

        # Device class
        dev_class = _read_sysfs(os.path.join(device_dir, "bDeviceClass")) or "00"
        dev_subclass = _read_sysfs(os.path.join(device_dir, "bDeviceSubClass")) or "00"

        # USB version
        usb_version = _read_sysfs(os.path.join(device_dir, "version"))
        if usb_version:
            usb_version = usb_version.strip()

        # Bus and device numbers
        busnum = _read_sysfs(os.path.join(device_dir, "busnum"))
        devnum = _read_sysfs(os.path.join(device_dir, "devnum"))

        # Number of interfaces
        num_interfaces = _read_sysfs(os.path.join(device_dir, "bNumInterfaces"))

        # Determine device type based on class
        class_names = {
            "00": "Composite",
            "01": "Audio",
            "02": "CDC (Serial)",
            "03": "HID (Mouse/KB)",
            "05": "Physical",
            "06": "Image",
            "07": "Printer",
            "08": "Mass Storage",
            "09": "Hub",
            "0a": "CDC Data",
            "0b": "Smart Card",
            "0e": "Video",
            "0f": "Health",
            "10": "Audio/Video",
            "dc": "Diagnostic",
            "e0": "Wireless",
            "ef": "Misc",
            "fe": "App Specific",
            "ff": "Vendor Specific",
        }
        class_name = class_names.get(dev_class.lower(), "Unknown")

        devices.append({
            "bus_id": entry,
            "vendor_id": vendor_id,
            "product_id": product_id,
            "manufacturer": manufacturer,
            "product": product,
            "serial": serial,
            "speed": speed,
            "speed_label": _get_usb_speed_label(speed),
            "max_power": max_power,
            "device_class": dev_class,
            "class_name": class_name,
            "usb_version": usb_version,
            "bus_num": busnum,
            "dev_num": devnum,
            "num_interfaces": num_interfaces,
        })

    return devices
