"""
SysPulse — Process Collector
Ranks processes by resource consumption to identify bottlenecks.
"""

import psutil
from typing import Dict, Any, List


def get_top_processes(n: int = 15, sort_by: str = "cpu") -> List[Dict[str, Any]]:
    """
    Get top N processes sorted by CPU or memory usage.

    Args:
        n: Number of top processes to return
        sort_by: 'cpu' or 'mem'

    Returns:
        List of process dicts with PID, name, user, cpu%, mem%, status, threads, etc.
    """
    processes = []

    attrs = [
        "pid", "name", "username", "cpu_percent", "memory_percent",
        "status", "num_threads", "create_time", "cmdline",
        "memory_info",
    ]

    for proc in psutil.process_iter(attrs=attrs, ad_value=None):
        try:
            info = proc.info
            if info["pid"] == 0:
                continue

            # Get command line (truncated)
            cmdline = ""
            if info["cmdline"]:
                cmdline = " ".join(info["cmdline"])
                if len(cmdline) > 60:
                    cmdline = cmdline[:57] + "..."

            # Memory in bytes
            rss = 0
            vms = 0
            if info["memory_info"]:
                rss = info["memory_info"].rss
                vms = info["memory_info"].vms

            # IO counters (may not be available without root)
            io_read = None
            io_write = None
            try:
                io = proc.io_counters()
                io_read = io.read_bytes
                io_write = io.write_bytes
            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                pass

            processes.append({
                "pid": info["pid"],
                "name": info["name"] or "?",
                "user": info["username"] or "?",
                "cpu_percent": info["cpu_percent"] or 0.0,
                "mem_percent": info["memory_percent"] or 0.0,
                "status": info["status"] or "?",
                "threads": info["num_threads"] or 0,
                "rss": rss,
                "vms": vms,
                "cmdline": cmdline,
                "io_read": io_read,
                "io_write": io_write,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort
    if sort_by == "cpu":
        processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
    elif sort_by == "mem":
        processes.sort(key=lambda p: p["mem_percent"], reverse=True)

    return processes[:n]


def get_process_summary() -> Dict[str, Any]:
    """Get a summary of all running processes."""
    total = 0
    running = 0
    sleeping = 0
    zombie = 0
    stopped = 0

    for proc in psutil.process_iter(["status"]):
        try:
            total += 1
            status = proc.info["status"]
            if status == psutil.STATUS_RUNNING:
                running += 1
            elif status == psutil.STATUS_SLEEPING:
                sleeping += 1
            elif status == psutil.STATUS_ZOMBIE:
                zombie += 1
            elif status == psutil.STATUS_STOPPED:
                stopped += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "total": total,
        "running": running,
        "sleeping": sleeping,
        "zombie": zombie,
        "stopped": stopped,
    }
