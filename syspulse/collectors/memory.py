"""
SysPulse — Memory Collector
Collects RAM and Swap information.
"""

import psutil
from typing import Dict, Any


def get_memory_info() -> Dict[str, Any]:
    """Collect RAM and Swap memory information."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "ram": {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "free": vm.free,
            "percent": vm.percent,
            "cached": getattr(vm, "cached", 0),
            "buffers": getattr(vm, "buffers", 0),
            "shared": getattr(vm, "shared", 0),
            "active": getattr(vm, "active", 0),
            "inactive": getattr(vm, "inactive", 0),
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
            "sin": swap.sin,
            "sout": swap.sout,
        },
    }
