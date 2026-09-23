"""
SysPulse — Latency & System Performance Collector
Measures system responsiveness, scheduling latency, and "System FPS".
"""

import os
import time
import psutil
from typing import Dict, Any, Optional

# State for delta calculations
_prev_ctx_switches = None
_prev_interrupts = None
_prev_time = None
_prev_loop_time = None
_loop_times = []  # Rolling window of loop times


def _read_sysfs(path: str) -> Optional[str]:
    """Read a sysfs file, return None on failure."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _get_scheduler_latency() -> Optional[float]:
    """
    Read scheduler latency from /proc/schedstat.
    Returns average wait time in milliseconds.
    """
    try:
        with open("/proc/schedstat", "r") as f:
            lines = f.readlines()

        total_wait = 0
        total_switches = 0

        for line in lines:
            if line.startswith("cpu"):
                parts = line.split()
                if len(parts) >= 8:
                    # Format: cpuN yld_count ... sched_count run_time wait_time ...
                    # Positions vary by kernel version
                    try:
                        wait_time = int(parts[7])  # nanoseconds total wait
                        sched_count = int(parts[5])
                        total_wait += wait_time
                        total_switches += sched_count
                    except (IndexError, ValueError):
                        pass

        if total_switches > 0:
            avg_wait_ns = total_wait / total_switches
            return avg_wait_ns / 1_000_000  # Convert to milliseconds
    except Exception:
        pass

    return None


def _get_system_uptime() -> float:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            return float(f.read().split()[0])
    except Exception:
        return 0.0


def record_loop_time(loop_duration: float):
    """
    Record a loop iteration time for FPS calculation.
    Call this from the main loop to track responsiveness.
    """
    global _loop_times
    _loop_times.append(loop_duration)
    # Keep only last 60 samples
    if len(_loop_times) > 60:
        _loop_times = _loop_times[-60:]


def get_latency_info() -> Dict[str, Any]:
    """
    Collect system latency and performance metrics.
    - Load average (1, 5, 15 min)
    - Context switches per second
    - Interrupts per second
    - System "FPS" (based on main loop responsiveness)
    - Scheduler latency
    - System uptime
    - Bottleneck detection
    """
    global _prev_ctx_switches, _prev_interrupts, _prev_time

    current_time = time.time()
    cpu_stats = psutil.cpu_stats()
    load_avg = os.getloadavg()
    num_cpus = psutil.cpu_count() or 1

    # Delta calculations for per-second rates
    ctx_per_sec = 0
    int_per_sec = 0
    if _prev_time is not None:
        dt = current_time - _prev_time
        if dt > 0:
            if _prev_ctx_switches is not None:
                ctx_per_sec = (cpu_stats.ctx_switches - _prev_ctx_switches) / dt
            if _prev_interrupts is not None:
                int_per_sec = (cpu_stats.interrupts - _prev_interrupts) / dt

    _prev_ctx_switches = cpu_stats.ctx_switches
    _prev_interrupts = cpu_stats.interrupts
    _prev_time = current_time

    # System FPS based on loop times
    system_fps = 0.0
    avg_loop_time = 0.0
    jitter = 0.0
    if _loop_times:
        avg_loop_time = sum(_loop_times) / len(_loop_times)
        if avg_loop_time > 0:
            system_fps = 1.0 / avg_loop_time
        if len(_loop_times) > 1:
            mean = avg_loop_time
            variance = sum((t - mean) ** 2 for t in _loop_times) / len(_loop_times)
            jitter = variance ** 0.5  # standard deviation

    # Scheduler latency
    sched_latency = _get_scheduler_latency()

    # Bottleneck detection
    bottleneck = "Normal"
    bottleneck_color = "green"

    if load_avg[0] > num_cpus * 2:
        bottleneck = "CRÍTICO — Sistema muito sobrecarregado!"
        bottleneck_color = "red"
    elif load_avg[0] > num_cpus * 1.5:
        bottleneck = "ALTO — Carga acima da capacidade"
        bottleneck_color = "dark_orange"
    elif load_avg[0] > num_cpus:
        bottleneck = "ATENÇÃO — Carga igual à capacidade"
        bottleneck_color = "yellow"

    # Memory pressure check
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        bottleneck = "MEMÓRIA CRÍTICA — RAM quase cheia!"
        bottleneck_color = "red"
    elif mem.percent > 80:
        if bottleneck == "Normal":
            bottleneck = "ATENÇÃO — Memória alta"
            bottleneck_color = "yellow"

    return {
        "load_avg": {
            "1min": load_avg[0],
            "5min": load_avg[1],
            "15min": load_avg[2],
        },
        "num_cpus": num_cpus,
        "ctx_switches_sec": int(ctx_per_sec),
        "interrupts_sec": int(int_per_sec),
        "system_fps": round(system_fps, 1),
        "avg_loop_time_ms": round(avg_loop_time * 1000, 1),
        "jitter_ms": round(jitter * 1000, 2),
        "sched_latency_ms": round(sched_latency, 3) if sched_latency else None,
        "uptime_sec": _get_system_uptime(),
        "bottleneck": bottleneck,
        "bottleneck_color": bottleneck_color,
    }
