"""
SysPulse — Theme Configuration
Color scheme inspired by btop with vibrant, modern colors.
"""

# ═══════════════════════════════════════════════
# Color Palette
# ═══════════════════════════════════════════════

# Main accent colors
ACCENT_PRIMARY = "cyan"
ACCENT_SECONDARY = "magenta"
ACCENT_TERTIARY = "blue"

# Status colors
STATUS_GOOD = "green"
STATUS_WARN = "yellow"
STATUS_DANGER = "dark_orange"
STATUS_CRITICAL = "red"

# Section border colors
BORDER_CPU = "cyan"
BORDER_RAM = "green"
BORDER_GPU = "magenta"
BORDER_DISK = "blue"
BORDER_USB = "dark_orange"
BORDER_ENERGY = "yellow"
BORDER_LATENCY = "red"
BORDER_PROCESS = "bright_white"

# Bar graph colors (gradient from good to bad)
BAR_COLORS = ["green", "green", "green", "green", "yellow", "yellow", "dark_orange", "dark_orange", "red", "red"]

# Header style
HEADER_STYLE = "bold bright_white on rgb(30,30,50)"
HEADER_BORDER = "bright_cyan"

# Symbols
SYM_CPU = "🖥️ "
SYM_RAM = "🧠"
SYM_GPU = "🎮"
SYM_DISK = "💾"
SYM_USB = "🔌"
SYM_ENERGY = "⚡"
SYM_LATENCY = "📊"
SYM_PROCESS = "📋"
SYM_TEMP = "🌡️ "
SYM_FAN = "🌀"
SYM_POWER = "🔋"
SYM_SPEED = "🚀"
SYM_WARNING = "⚠️ "
SYM_OK = "✅"
SYM_CRITICAL = "🔴"

# Bar characters
BAR_FILLED = "█"
BAR_HALF = "▓"
BAR_QUARTER = "░"
BAR_EMPTY = "░"
BAR_LEFT = "▐"
BAR_RIGHT = "▌"


def get_bar_color(percent: float) -> str:
    """Get the appropriate color for a percentage bar."""
    if percent is None:
        return "white"
    idx = min(int(percent / 10), 9)
    return BAR_COLORS[idx]


def styled_bar(percent: float, width: int = 20) -> str:
    """Create a colored bar string with Rich markup."""
    if percent is None:
        return "[dim]" + BAR_EMPTY * width + "[/dim]"

    percent = max(0, min(100, percent))
    color = get_bar_color(percent)
    filled = int(percent / 100 * width)
    empty = width - filled

    return f"[{color}]{BAR_FILLED * filled}[/{color}][dim]{BAR_EMPTY * empty}[/dim]"


def styled_temp(celsius: float) -> str:
    """Format temperature with color."""
    if celsius is None:
        return "[dim]N/A[/dim]"
    if celsius < 50:
        return f"[cyan]{celsius:.0f}°C[/cyan]"
    elif celsius < 70:
        return f"[green]{celsius:.0f}°C[/green]"
    elif celsius < 85:
        return f"[yellow]{celsius:.0f}°C[/yellow]"
    else:
        return f"[red]{celsius:.0f}°C[/red]"


def styled_percent(value: float) -> str:
    """Format percentage with color."""
    if value is None:
        return "[dim]N/A[/dim]"
    if value < 50:
        return f"[green]{value:.1f}%[/green]"
    elif value < 75:
        return f"[yellow]{value:.1f}%[/yellow]"
    elif value < 90:
        return f"[dark_orange]{value:.1f}%[/dark_orange]"
    else:
        return f"[red]{value:.1f}%[/red]"


def styled_watts(watts: float) -> str:
    """Format watts with color."""
    if watts is None:
        return "[dim]N/A[/dim]"
    if watts < 15:
        return f"[green]{watts:.1f}W[/green]"
    elif watts < 35:
        return f"[yellow]{watts:.1f}W[/yellow]"
    elif watts < 65:
        return f"[dark_orange]{watts:.1f}W[/dark_orange]"
    else:
        return f"[red]{watts:.1f}W[/red]"
