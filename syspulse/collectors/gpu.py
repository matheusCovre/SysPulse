"""
SysPulse — GPU Collector
Auto-detects and supports: NVIDIA (via NVML), AMD (via sysfs), Intel integrated (via sysfs).
Graceful fallback when no GPU is available.
"""

import os
import glob
from typing import Dict, Any, List, Optional

# Try to import NVIDIA ML
_NVML_AVAILABLE = False
try:
    import pynvml
    pynvml.nvmlInit()
    _NVML_AVAILABLE = True
except Exception:
    pass


def _get_nvidia_gpus() -> List[Dict[str, Any]]:
    """Collect info from NVIDIA GPUs via NVML."""
    gpus = []
    if not _NVML_AVAILABLE:
        return gpus

    try:
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)

            # Name
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            # Memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            # Utilization
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = util.gpu
                mem_util = util.memory
            except Exception:
                gpu_util = None
                mem_util = None

            # Temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None

            # Power
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle)  # milliwatts
            except Exception:
                power = None

            try:
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle)
            except Exception:
                power_limit = None

            # Clocks
            try:
                clock_gpu = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
            except Exception:
                clock_gpu = None

            try:
                clock_mem = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
            except Exception:
                clock_mem = None

            # Fan
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
            except Exception:
                fan_speed = None

            # Driver
            try:
                driver = pynvml.nvmlSystemGetDriverVersion()
                if isinstance(driver, bytes):
                    driver = driver.decode("utf-8")
            except Exception:
                driver = "N/A"

            gpus.append({
                "type": "NVIDIA",
                "index": i,
                "name": name,
                "driver": driver,
                "vram_total": mem_info.total,
                "vram_used": mem_info.used,
                "vram_free": mem_info.free,
                "vram_percent": (mem_info.used / mem_info.total * 100) if mem_info.total > 0 else 0,
                "gpu_util": gpu_util,
                "mem_util": mem_util,
                "temperature": temp,
                "power_draw": power,       # milliwatts
                "power_limit": power_limit, # milliwatts
                "clock_gpu": clock_gpu,     # MHz
                "clock_mem": clock_mem,     # MHz
                "fan_speed": fan_speed,     # percentage
            })
    except Exception:
        pass

    return gpus


def _read_sysfs(path: str) -> Optional[str]:
    """Read a sysfs file, return None on failure."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _get_amd_gpus() -> List[Dict[str, Any]]:
    """Collect info from AMD GPUs via sysfs (amdgpu driver)."""
    gpus = []
    hwmon_dirs = glob.glob("/sys/class/drm/card*/device/hwmon/hwmon*")

    for idx, hwmon in enumerate(hwmon_dirs):
        device_dir = os.path.dirname(os.path.dirname(hwmon))
        vendor = _read_sysfs(os.path.join(device_dir, "vendor"))

        # AMD vendor ID is 0x1002
        if vendor != "0x1002":
            continue

        name = _read_sysfs(os.path.join(hwmon, "name")) or "AMD GPU"

        # Temperature
        temp_val = _read_sysfs(os.path.join(hwmon, "temp1_input"))
        temp = int(temp_val) / 1000 if temp_val else None

        # Power
        power_val = _read_sysfs(os.path.join(hwmon, "power1_average"))
        power = int(power_val) / 1000 if power_val else None  # microwatts to milliwatts

        # Fan
        fan_val = _read_sysfs(os.path.join(hwmon, "pwm1"))
        fan_max = _read_sysfs(os.path.join(hwmon, "pwm1_max"))
        fan_speed = None
        if fan_val and fan_max:
            fan_speed = int(fan_val) / int(fan_max) * 100

        # VRAM
        vram_total_val = _read_sysfs(os.path.join(device_dir, "mem_info_vram_total"))
        vram_used_val = _read_sysfs(os.path.join(device_dir, "mem_info_vram_used"))
        vram_total = int(vram_total_val) if vram_total_val else None
        vram_used = int(vram_used_val) if vram_used_val else None

        # GPU utilization
        gpu_busy = _read_sysfs(os.path.join(device_dir, "gpu_busy_percent"))
        gpu_util = int(gpu_busy) if gpu_busy else None

        # Clock
        clock_val = _read_sysfs(os.path.join(device_dir, "pp_dpm_sclk"))
        clock_gpu = None
        if clock_val:
            for line in clock_val.splitlines():
                if "*" in line:
                    # Format: "0: 300Mhz *"
                    parts = line.split()
                    for p in parts:
                        if "mhz" in p.lower():
                            clock_gpu = int(p.lower().replace("mhz", ""))
                            break

        gpus.append({
            "type": "AMD",
            "index": idx,
            "name": name,
            "driver": "amdgpu",
            "vram_total": vram_total,
            "vram_used": vram_used,
            "vram_free": (vram_total - vram_used) if vram_total and vram_used else None,
            "vram_percent": (vram_used / vram_total * 100) if vram_total and vram_used else None,
            "gpu_util": gpu_util,
            "mem_util": None,
            "temperature": temp,
            "power_draw": power,
            "power_limit": None,
            "clock_gpu": clock_gpu,
            "clock_mem": None,
            "fan_speed": fan_speed,
        })

    return gpus


def _get_intel_igpu() -> List[Dict[str, Any]]:
    """Collect basic info from Intel integrated GPU via sysfs."""
    gpus = []

    # Check if Intel GPU exists via DRM
    drm_cards = glob.glob("/sys/class/drm/card*/device/vendor")
    for vendor_path in drm_cards:
        vendor = _read_sysfs(vendor_path)
        if vendor != "0x8086":  # Intel vendor ID
            continue

        device_dir = os.path.dirname(vendor_path)
        card_dir = os.path.dirname(device_dir)

        # Try to get the GPU name from lspci-style info
        device_id = _read_sysfs(os.path.join(device_dir, "device")) or "Unknown"

        # Check if i915 driver
        driver_link = os.path.join(device_dir, "driver")
        driver_name = "i915"
        if os.path.islink(driver_link):
            driver_name = os.path.basename(os.readlink(driver_link))

        # Frequency from i915
        freq_cur = None
        freq_max = None
        gt_dir = glob.glob(os.path.join(card_dir, "gt/gt*"))
        if gt_dir:
            cur = _read_sysfs(os.path.join(gt_dir[0], "freq0/cur_freq"))
            max_f = _read_sysfs(os.path.join(gt_dir[0], "freq0/max_freq"))
            freq_cur = int(cur) if cur else None
            freq_max = int(max_f) if max_f else None

        # Alternative frequency path
        if freq_cur is None:
            cur = _read_sysfs(os.path.join(card_dir, "gt_cur_freq_mhz"))
            max_f = _read_sysfs(os.path.join(card_dir, "gt_max_freq_mhz"))
            freq_cur = int(cur) if cur else None
            freq_max = int(max_f) if max_f else None

        gpus.append({
            "type": "Intel",
            "index": 0,
            "name": f"Intel Integrated GPU ({device_id})",
            "driver": driver_name,
            "vram_total": None,   # Shared memory, not directly available
            "vram_used": None,
            "vram_free": None,
            "vram_percent": None,
            "gpu_util": None,
            "mem_util": None,
            "temperature": None,
            "power_draw": None,
            "power_limit": None,
            "clock_gpu": freq_cur,
            "clock_mem": None,
            "fan_speed": None,
        })
        break  # Only first Intel iGPU

    return gpus


def get_gpu_info() -> Dict[str, Any]:
    """
    Auto-detect and collect GPU information.
    Tries NVIDIA first, then AMD, then Intel integrated.
    Returns empty list if no GPU detected.
    """
    all_gpus = []

    # 1. Try NVIDIA
    nvidia_gpus = _get_nvidia_gpus()
    all_gpus.extend(nvidia_gpus)

    # 2. Try AMD
    amd_gpus = _get_amd_gpus()
    all_gpus.extend(amd_gpus)

    # 3. Try Intel integrated
    intel_gpus = _get_intel_igpu()
    all_gpus.extend(intel_gpus)

    return {
        "available": len(all_gpus) > 0,
        "count": len(all_gpus),
        "gpus": all_gpus,
    }


def shutdown_nvml():
    """Cleanup NVML on exit."""
    global _NVML_AVAILABLE
    if _NVML_AVAILABLE:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
        _NVML_AVAILABLE = False
