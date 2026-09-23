"""
SysPulse — Utility helpers for formatting values.
"""


def format_bytes(nbytes: float, suffix: str = "B") -> str:
    """Convert bytes to human-readable format (KB, MB, GB, TB)."""
    if nbytes is None:
        return "N/A"
    for unit in ("", "K", "M", "G", "T", "P"):
        if abs(nbytes) < 1024.0:
            return f"{nbytes:.1f} {unit}{suffix}"
        nbytes /= 1024.0
    return f"{nbytes:.1f} E{suffix}"


def format_bytes_speed(nbytes_per_sec: float) -> str:
    """Convert bytes/s to human-readable speed."""
    return format_bytes(nbytes_per_sec, suffix="B/s")


def format_watts(milliwatts: float) -> str:
    """Convert milliwatts to watts string."""
    if milliwatts is None:
        return "N/A"
    return f"{milliwatts / 1000.0:.1f} W"


def format_frequency(mhz: float) -> str:
    """Convert MHz to human-readable frequency."""
    if mhz is None:
        return "N/A"
    if mhz >= 1000:
        return f"{mhz / 1000.0:.2f} GHz"
    return f"{mhz:.0f} MHz"


def format_temp(celsius: float) -> str:
    """Format temperature with color hint."""
    if celsius is None:
        return "N/A"
    return f"{celsius:.0f}°C"


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable form."""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_percent(value: float) -> str:
    """Format a percentage value."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def color_for_percent(value: float) -> str:
    """Return a Rich color name based on percentage threshold."""
    if value is None:
        return "white"
    if value < 50:
        return "green"
    elif value < 75:
        return "yellow"
    elif value < 90:
        return "dark_orange"
    else:
        return "red"


def color_for_temp(celsius: float) -> str:
    """Return a Rich color name based on temperature."""
    if celsius is None:
        return "white"
    if celsius < 50:
        return "cyan"
    elif celsius < 70:
        return "green"
    elif celsius < 85:
        return "yellow"
    else:
        return "red"


def bar_graph(value: float, width: int = 20, filled: str = "█", empty: str = "░") -> str:
    """Create a simple text-based bar graph."""
    if value is None:
        value = 0
    value = max(0, min(100, value))
    filled_count = int(value / 100 * width)
    return filled * filled_count + empty * (width - filled_count)
