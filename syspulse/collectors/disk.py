"""
SysPulse — Disk Collector
Collects disk partition info and I/O statistics.
"""

import time
import psutil
from typing import Dict, Any, List, Optional

# Previous I/O readings for delta calculation
_prev_disk_io = None
_prev_disk_time = None


def get_disk_info() -> Dict[str, Any]:
    """Collect disk partitions and usage information.
    Filters out snap, loop, tmpfs, and other virtual/noise filesystems.
    """
    # Filesystem types to skip
    skip_fstypes = {"squashfs", "tmpfs", "devtmpfs", "overlay", "fuse.portal"}
    # Mount prefixes to skip
    skip_mounts = ("/snap/", "/sys/", "/proc/", "/run/", "/dev/")

    partitions = []

    for part in psutil.disk_partitions(all=False):
        # Skip noise
        if part.fstype in skip_fstypes:
            continue
        if any(part.mountpoint.startswith(prefix) for prefix in skip_mounts):
            continue
        if part.device.startswith("/dev/loop"):
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
                "total": None,
                "used": None,
                "free": None,
                "percent": None,
            })

    return {"partitions": partitions}



def get_disk_io() -> Dict[str, Any]:
    """
    Collect disk I/O statistics with delta calculation.
    Returns read/write bytes per second for each disk.
    """
    global _prev_disk_io, _prev_disk_time

    current_io = psutil.disk_io_counters(perdisk=True)
    current_time = time.time()

    io_stats = {}

    if _prev_disk_io is not None and _prev_disk_time is not None:
        dt = current_time - _prev_disk_time
        if dt > 0:
            for disk_name, counters in current_io.items():
                if disk_name in _prev_disk_io:
                    prev = _prev_disk_io[disk_name]
                    io_stats[disk_name] = {
                        "read_bytes_sec": (counters.read_bytes - prev.read_bytes) / dt,
                        "write_bytes_sec": (counters.write_bytes - prev.write_bytes) / dt,
                        "read_count_sec": (counters.read_count - prev.read_count) / dt,
                        "write_count_sec": (counters.write_count - prev.write_count) / dt,
                        "read_bytes_total": counters.read_bytes,
                        "write_bytes_total": counters.write_bytes,
                    }
                else:
                    io_stats[disk_name] = {
                        "read_bytes_sec": 0,
                        "write_bytes_sec": 0,
                        "read_count_sec": 0,
                        "write_count_sec": 0,
                        "read_bytes_total": counters.read_bytes,
                        "write_bytes_total": counters.write_bytes,
                    }
    else:
        # First call, no delta available yet
        for disk_name, counters in current_io.items():
            io_stats[disk_name] = {
                "read_bytes_sec": 0,
                "write_bytes_sec": 0,
                "read_count_sec": 0,
                "write_count_sec": 0,
                "read_bytes_total": counters.read_bytes,
                "write_bytes_total": counters.write_bytes,
            }

    _prev_disk_io = current_io
    _prev_disk_time = current_time

    # Also get totals
    total = psutil.disk_io_counters()
    total_read_sec = sum(s["read_bytes_sec"] for s in io_stats.values())
    total_write_sec = sum(s["write_bytes_sec"] for s in io_stats.values())

    return {
        "per_disk": io_stats,
        "total_read_sec": total_read_sec,
        "total_write_sec": total_write_sec,
    }
