"""
SysPulse — CPU Collector
Supports Intel and RISC-V processors with automatic detection.
"""

import os
import psutil
from typing import Dict, Any, List, Optional


def _detect_arch() -> str:
    """Detect CPU architecture: 'intel', 'amd', 'riscv', or 'unknown'."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            content = f.read().lower()
        if "genuineintel" in content:
            return "intel"
        elif "authenticamd" in content:
            return "amd"
        elif "riscv" in content or "isa" in content and "rv" in content:
            return "riscv"
    except Exception:
        pass
    return "unknown"


def _get_cpu_model() -> str:
    """Get CPU model name from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
                # RISC-V uses 'isa' or 'uarch' fields
                if line.startswith("uarch"):
                    return line.split(":", 1)[1].strip()
        # Fallback for RISC-V — try 'isa' field
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("isa"):
                    return "RISC-V " + line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Unknown CPU"


def _get_cpu_flags() -> List[str]:
    """Get CPU flags/extensions."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("flags") or line.startswith("isa"):
                    return line.split(":", 1)[1].strip().split()
    except Exception:
        pass
    return []


def _get_temperatures() -> Dict[str, Optional[float]]:
    """Get CPU temperatures directly from sysfs to avoid psutil errors."""
    temps = {"package": None, "cores": []}
    try:
        hwmon_dir = '/sys/class/hwmon'
        if not os.path.exists(hwmon_dir):
            return temps
        
        for hwmon in os.listdir(hwmon_dir):
            hwmon_path = os.path.join(hwmon_dir, hwmon)
            try:
                with open(os.path.join(hwmon_path, 'name'), 'r') as f:
                    name = f.read().strip()
                # Focus on CPU core temps
                if name in ('coretemp', 'k10temp', 'cpu_thermal'):
                    for file in os.listdir(hwmon_path):
                        if file.startswith('temp') and file.endswith('_label'):
                            prefix = file.split('_')[0]
                            with open(os.path.join(hwmon_path, file), 'r') as f:
                                label = f.read().strip().lower()
                            with open(os.path.join(hwmon_path, prefix + '_input'), 'r') as f:
                                temp = int(f.read().strip()) / 1000.0
                                
                            if 'package' in label or 'tctl' in label or 'tdie' in label:
                                temps['package'] = temp
                            elif 'core' in label:
                                # Try to extract core number
                                core_num = -1
                                for part in label.split():
                                    if part.isdigit():
                                        core_num = int(part)
                                temps['cores'].append((core_num, temp))
            except Exception:
                continue
                
        # Fallback to thermal_zone for ARM/Rockchip boards
        if temps['package'] is None and not temps['cores']:
            thermal_dir = '/sys/class/thermal'
            if os.path.exists(thermal_dir):
                for tz in os.listdir(thermal_dir):
                    if tz.startswith('thermal_zone'):
                        tz_path = os.path.join(thermal_dir, tz)
                        try:
                            with open(os.path.join(tz_path, 'type'), 'r') as f:
                                t_type = f.read().strip().lower()
                            # Look for common ARM/Rockchip CPU thermal zones
                            if 'cpu' in t_type or 'soc' in t_type or 'big' in t_type or 'lit' in t_type or 'center' in t_type or 'core' in t_type:
                                with open(os.path.join(tz_path, 'temp'), 'r') as f:
                                    t_val = int(f.read().strip())
                                    # Some expose millidegrees, some just degrees.
                                    t_val = t_val / 1000.0 if t_val > 1000 else float(t_val)
                                    temps['cores'].append((-1, t_val))
                        except Exception:
                            continue
        
        # Sort cores by number if available
        if temps['cores']:
            temps['cores'].sort(key=lambda x: x[0])
            temps['cores'] = [t for _, t in temps['cores']]
            
        # Fallback if no package temp found
        if temps['package'] is None and temps['cores']:
            temps['package'] = max(temps['cores'])
            
    except Exception:
        pass
    return temps


def get_cpu_info() -> Dict[str, Any]:
    """
    Collect comprehensive CPU information.
    Works with Intel, AMD, and RISC-V processors.
    """
    arch = _detect_arch()
    model = _get_cpu_model()

    # Core counts
    physical_cores = psutil.cpu_count(logical=False) or 0
    logical_cores = psutil.cpu_count(logical=True) or 0

    # Usage per core
    per_cpu = psutil.cpu_percent(percpu=True)
    total_usage = psutil.cpu_percent()

    # Frequency
    freq = psutil.cpu_freq()
    freq_per_cpu = psutil.cpu_freq(percpu=True)
    freq_info = {
        "current": freq.current if freq else None,
        "min": freq.min if freq else None,
        "max": freq.max if freq else None,
        "per_cpu": [
            {"current": f.current, "min": f.min, "max": f.max}
            for f in freq_per_cpu
        ] if freq_per_cpu else [],
    }

    # Temperatures
    temps = _get_temperatures()

    # Context switches and interrupts
    ctx = psutil.cpu_stats()

    # Load average
    load_avg = os.getloadavg()

    return {
        "arch": arch,
        "model": model,
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "total_usage": total_usage,
        "per_cpu_usage": per_cpu,
        "frequency": freq_info,
        "temperature": temps,
        "ctx_switches": ctx.ctx_switches,
        "interrupts": ctx.interrupts,
        "soft_interrupts": ctx.soft_interrupts,
        "load_avg": {
            "1min": load_avg[0],
            "5min": load_avg[1],
            "15min": load_avg[2],
        },
    }
