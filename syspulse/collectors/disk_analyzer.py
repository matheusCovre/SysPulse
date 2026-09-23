"""
SysPulse — Disk Analyzer Collector
Scans directories recursively to build a size tree for block visualization.
Like ncdu/WinDirStat but as data for our TUI.
"""

import os
import stat
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


def _get_dir_size_fast(path: str) -> int:
    """Get directory size using os.scandir (fast, no recursion limit issues)."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += _get_dir_size_fast(entry.path)
                except (PermissionError, OSError, FileNotFoundError):
                    continue
    except (PermissionError, OSError, FileNotFoundError):
        pass
    return total


def scan_directory(path: str, max_depth: int = 1, min_size_mb: float = 1.0) -> List[Dict[str, Any]]:
    """
    Scan a directory and return children sorted by size.

    Args:
        path: Root path to scan
        max_depth: How deep to scan (1 = immediate children only)
        min_size_mb: Minimum size in MB to include in results

    Returns:
        List of dicts with name, path, size, is_dir, children count
    """
    results = []
    min_size_bytes = int(min_size_mb * 1024 * 1024)

    try:
        entries = list(os.scandir(path))
    except (PermissionError, OSError):
        return results

    for entry in entries:
        try:
            if entry.name.startswith('.') and entry.is_dir(follow_symlinks=False):
                # Still include hidden dirs but don't recurse deep
                pass

            if entry.is_file(follow_symlinks=False):
                size = entry.stat(follow_symlinks=False).st_size
                if size >= min_size_bytes:
                    results.append({
                        "name": entry.name,
                        "path": entry.path,
                        "size": size,
                        "is_dir": False,
                        "children": [],
                        "child_count": 0,
                    })
            elif entry.is_dir(follow_symlinks=False):
                # Skip special directories
                if entry.name in ("proc", "sys", "dev", "run", "snap", "lost+found"):
                    continue

                size = _get_dir_size_fast(entry.path)
                if size >= min_size_bytes:
                    children = []
                    if max_depth > 1:
                        children = scan_directory(entry.path, max_depth - 1, min_size_mb)

                    # Count items in directory
                    try:
                        child_count = len(list(os.scandir(entry.path)))
                    except (PermissionError, OSError):
                        child_count = 0

                    results.append({
                        "name": entry.name,
                        "path": entry.path,
                        "size": size,
                        "is_dir": True,
                        "children": children,
                        "child_count": child_count,
                    })
        except (PermissionError, OSError, FileNotFoundError):
            continue

    # Sort by size descending
    results.sort(key=lambda x: x["size"], reverse=True)
    return results


def analyze_partition(mountpoint: str, max_items: int = 20) -> Dict[str, Any]:
    """
    Analyze a partition's top-level directory usage.
    Returns the largest directories/files for block visualization.

    Args:
        mountpoint: The mount point to analyze (e.g., '/', '/home/user/ssd')
        max_items: Maximum number of items to return
    """
    try:
        usage = os.statvfs(mountpoint)
        total = usage.f_frsize * usage.f_blocks
        free = usage.f_frsize * usage.f_bfree
        used = total - free
    except OSError:
        total = free = used = 0

    items = scan_directory(mountpoint, max_depth=1, min_size_mb=10.0)

    # Calculate "other" (used space not accounted for by scanned items)
    accounted = sum(item["size"] for item in items)
    other = max(0, used - accounted)

    return {
        "mountpoint": mountpoint,
        "total": total,
        "used": used,
        "free": free,
        "items": items[:max_items],
        "other_size": other,
    }


def get_disk_analysis(partitions: List[Dict[str, Any]], max_items: int = 20) -> List[Dict[str, Any]]:
    """
    Analyze multiple partitions in parallel.

    Args:
        partitions: List of partition dicts from disk.get_disk_info()
        max_items: Max items per partition
    """
    results = []

    # Filter to real partitions only
    skip_mounts = ("/boot/efi", "/boot")
    valid = [p for p in partitions if p["mountpoint"] not in skip_mounts and p.get("total")]

    for part in valid:
        analysis = analyze_partition(part["mountpoint"], max_items)
        analysis["device"] = part["device"]
        analysis["fstype"] = part["fstype"]
        results.append(analysis)

    return results
