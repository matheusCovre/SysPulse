"""
SysPulse — Energy Collector
Reads power consumption from Intel RAPL (via powercap sysfs) and GPU (via NVML).
Graceful fallback when unavailable (RISC-V, no permissions, etc.).
"""

import os
import time
import glob
from typing import Dict, Any, List, Optional

# RAPL state for delta calculation
_rapl_prev = {}
_rapl_prev_time = None


def _read_sysfs(path: str) -> Optional[str]:
    """Read a sysfs file, return None on failure."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _discover_rapl_domains() -> List[Dict[str, str]]:
    """
    Discover available Intel RAPL domains.
    Returns list of dicts with 'name', 'energy_path', 'max_energy_path'.
    """
    domains = []
    base = "/sys/class/powercap"

    if not os.path.exists(base):
        return domains

    # Find all intel-rapl domains
    for entry in sorted(glob.glob(os.path.join(base, "intel-rapl:*"))):
        name = _read_sysfs(os.path.join(entry, "name")) or os.path.basename(entry)
        energy_path = os.path.join(entry, "energy_uj")
        max_energy_path = os.path.join(entry, "max_energy_range_uj")

        if os.path.exists(energy_path):
            domains.append({
                "id": os.path.basename(entry),
                "name": name,
                "energy_path": energy_path,
                "max_energy_path": max_energy_path,
            })

        # Check sub-domains (e.g., intel-rapl:0:0 for cores, intel-rapl:0:1 for uncore)
        for sub_entry in sorted(glob.glob(os.path.join(entry, "intel-rapl:*"))):
            sub_name = _read_sysfs(os.path.join(sub_entry, "name")) or os.path.basename(sub_entry)
            sub_energy_path = os.path.join(sub_entry, "energy_uj")
            if os.path.exists(sub_energy_path):
                domains.append({
                    "id": os.path.basename(sub_entry),
                    "name": sub_name,
                    "energy_path": sub_energy_path,
                    "max_energy_path": os.path.join(sub_entry, "max_energy_range_uj"),
                })

    return domains


def get_cpu_power() -> Dict[str, Any]:
    """
    Read CPU power consumption from Intel RAPL.
    Returns watts for each domain (package, core, uncore, dram).
    Uses delta calculation between readings.
    """
    global _rapl_prev, _rapl_prev_time

    result = {
        "available": False,
        "domains": {},
        "total_watts": None,
    }

    domains = _discover_rapl_domains()
    if not domains:
        return result

    current_time = time.time()
    current_readings = {}
    power_readings = {}

    for domain in domains:
        energy_str = _read_sysfs(domain["energy_path"])
        if energy_str is None:
            continue

        energy_uj = int(energy_str)  # microjoules
        current_readings[domain["id"]] = energy_uj

        # Calculate watts from delta
        if domain["id"] in _rapl_prev and _rapl_prev_time is not None:
            dt = current_time - _rapl_prev_time
            if dt > 0:
                prev_energy = _rapl_prev[domain["id"]]
                delta_energy = energy_uj - prev_energy

                # Handle counter wrap-around
                if delta_energy < 0:
                    max_range_str = _read_sysfs(domain["max_energy_path"])
                    if max_range_str:
                        delta_energy += int(max_range_str)

                watts = (delta_energy / 1_000_000) / dt  # microjoules to joules, divide by seconds
                power_readings[domain["name"]] = round(watts, 2)

    _rapl_prev = current_readings
    _rapl_prev_time = current_time

    if power_readings:
        result["available"] = True
        result["domains"] = power_readings
        # Total = sum of top-level packages (avoid double counting subdomains)
        package_watts = [v for k, v in power_readings.items() if "package" in k.lower() or "psys" in k.lower()]
        if package_watts:
            result["total_watts"] = sum(package_watts)
        else:
            result["total_watts"] = sum(power_readings.values())

    return result


def get_gpu_power() -> Dict[str, Any]:
    """
    Get GPU power consumption.
    Uses NVML for NVIDIA, sysfs for AMD.
    """
    result = {
        "available": False,
        "gpus": [],
    }

    # NVIDIA via NVML
    try:
        import pynvml
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle)  # milliwatts
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                result["gpus"].append({
                    "name": name,
                    "watts": round(power / 1000, 2),
                })
                result["available"] = True
            except Exception:
                pass
    except Exception:
        pass

    # AMD via sysfs
    for hwmon in glob.glob("/sys/class/drm/card*/device/hwmon/hwmon*"):
        device_dir = os.path.dirname(os.path.dirname(hwmon))
        vendor = _read_sysfs(os.path.join(device_dir, "vendor"))
        if vendor == "0x1002":
            power_val = _read_sysfs(os.path.join(hwmon, "power1_average"))
            if power_val:
                watts = int(power_val) / 1_000_000  # microwatts to watts
                result["gpus"].append({
                    "name": "AMD GPU",
                    "watts": round(watts, 2),
                })
                result["available"] = True

    return result


def get_arm_power() -> Dict[str, float]:
    """
    Attempt to read power consumption on ARM boards (like Firefly RK3588)
    via /sys/class/power_supply or generic hwmon.
    """
    power_readings = {}
    
    # 1. Try power_supply (e.g. PMIC like RK808, RK818, battery)
    ps_dir = "/sys/class/power_supply"
    if os.path.exists(ps_dir):
        for ps in os.listdir(ps_dir):
            ps_path = os.path.join(ps_dir, ps)
            try:
                curr_str = _read_sysfs(os.path.join(ps_path, "current_now"))
                volt_str = _read_sysfs(os.path.join(ps_path, "voltage_now"))
                if curr_str and volt_str:
                    curr = abs(int(curr_str)) / 1_000_000  # A
                    volt = int(volt_str) / 1_000_000  # V
                    watts = curr * volt
                    if watts > 0:
                        power_readings[ps] = round(watts, 2)
            except Exception:
                continue

    # 2. Try generic hwmon power sensors (power*_input in microwatts)
    hwmon_dir = "/sys/class/hwmon"
    if os.path.exists(hwmon_dir):
        for hwmon in os.listdir(hwmon_dir):
            hwmon_path = os.path.join(hwmon_dir, hwmon)
            try:
                name = _read_sysfs(os.path.join(hwmon_path, "name")) or hwmon
                for file in os.listdir(hwmon_path):
                    if file.startswith("power") and file.endswith("_input"):
                        val = _read_sysfs(os.path.join(hwmon_path, file))
                        if val:
                            watts = int(val) / 1_000_000
                            power_readings[f"{name}_{file.split('_')[0]}"] = round(watts, 2)
            except Exception:
                continue

    return power_readings


def get_total_power() -> Dict[str, Any]:
    """
    Get estimated total system power consumption.
    Combines CPU (RAPL) + GPU (NVML/sysfs) readings + ARM PMIC.
    """
    cpu = get_cpu_power()
    gpu = get_gpu_power()
    arm = get_arm_power()

    total = 0.0
    breakdown = {}

    if cpu["available"] and cpu["total_watts"] is not None:
        total += cpu["total_watts"]
        breakdown["CPU (RAPL)"] = cpu["total_watts"]
        for domain, watts in cpu["domains"].items():
            breakdown[f"  {domain}"] = watts
    elif arm:
        # Use ARM readings if Intel RAPL is not available
        arm_total = sum(arm.values())
        total += arm_total
        breakdown["SoC/Placa (ARM)"] = round(arm_total, 2)
        for domain, watts in arm.items():
            breakdown[f"  {domain}"] = watts

    if gpu["available"]:
        for g in gpu["gpus"]:
            total += g["watts"]
            breakdown[g["name"]] = g["watts"]

    # If no real sensor found at all, estimate from CPU usage
    # Common ARM SoC TDPs: RK3568 ~4W, RK3588 ~10W
    has_real_data = cpu["available"] or gpu["available"] or bool(arm)
    if not has_real_data:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            # Detect SoC to pick TDP estimate
            soc_tdp = 4.0  # Default for RK3568
            try:
                with open("/proc/device-tree/compatible", "rb") as f:
                    compat = f.read().decode("utf-8", errors="ignore").lower()
                if "rk3588" in compat:
                    soc_tdp = 10.0
                elif "rk3399" in compat:
                    soc_tdp = 6.0
                elif "rk3566" in compat or "rk3568" in compat:
                    soc_tdp = 4.0
            except Exception:
                pass

            estimated_watts = round(soc_tdp * (cpu_percent / 100.0) * 0.7 + soc_tdp * 0.3, 2)
            total = estimated_watts
            breakdown["CPU SoC (estimado)"] = estimated_watts
            has_real_data = True
        except Exception:
            pass

    return {
        "total_watts": round(total, 2) if has_real_data else None,
        "breakdown": breakdown,
        "cpu": cpu,
        "gpu": gpu,
    }
