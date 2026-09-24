"""
SysPulse — UI Widgets
Individual panel generators for each system section.
Uses Rich Panel, Table, and styled text for beautiful terminal output.
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

from ..utils.helpers import format_bytes, format_bytes_speed, format_frequency, format_uptime
from . import theme


# ═══════════════════════════════════════════════
# CPU PANEL
# ═══════════════════════════════════════════════

def _core_label(i, usage, cpu_data):
    """Build a single core label string with temp and freq."""
    core_temps = cpu_data["temperature"].get("cores", [])
    num_logical = len(cpu_data["per_cpu_usage"])
    num_temps = len(core_temps)

    temp_str = ""
    if num_temps > 0:
        t_idx = i if num_temps == num_logical else int(i / max(1, num_logical / num_temps))
        if t_idx < num_temps:
            t_val = core_temps[t_idx]
            t_color = "red" if t_val > 85 else "yellow" if t_val > 70 else "green" if t_val > 50 else "cyan"
            temp_str = f" [{t_color}]{t_val:.0f}°[/{t_color}]"

    freq_per = cpu_data["frequency"].get("per_cpu", [])
    if i < len(freq_per):
        core_freq = format_frequency(freq_per[i].get("current"))
        return f"C{i}{temp_str} [dim]{core_freq}[/dim]"
    return f"C{i}{temp_str}"


def cpu_panel(cpu_data: dict) -> Panel:
    """Generate the CPU monitoring panel with per-core bars."""
    num_cores = len(cpu_data["per_cpu_usage"])
    use_two_cols = num_cores > 8

    # Model and arch
    arch_badge = f"[bold cyan]{cpu_data['arch'].upper()}[/bold cyan]"

    # Temperature
    temp = cpu_data["temperature"]
    temp_val = theme.styled_temp(temp.get("package"))

    # Frequency
    freq = cpu_data["frequency"]
    freq_str = format_frequency(freq.get("current"))

    # Load average
    la = cpu_data["load_avg"]
    load_line = f"[dim]Load Avg: {la['1min']:.2f} {la['5min']:.2f} {la['15min']:.2f}[/dim]"

    if use_two_cols:
        # Two-column layout for many cores (> 8)
        half = (num_cores + 1) // 2

        left_t = Table(show_header=False, box=None, padding=(0, 0), expand=True)
        left_t.add_column("L", width=18, no_wrap=True)
        left_t.add_column("B", min_width=10)
        left_t.add_column("V", width=5, justify="right")

        right_t = Table(show_header=False, box=None, padding=(0, 0), expand=True)
        right_t.add_column("L", width=18, no_wrap=True)
        right_t.add_column("B", min_width=10)
        right_t.add_column("V", width=5, justify="right")

        # Total usage in left column
        total = cpu_data["total_usage"]
        left_t.add_row(
            "[bold]Total[/bold]",
            theme.styled_bar(total, width=12),
            theme.styled_percent(total),
        )
        right_t.add_row("", "", "")

        for i, usage in enumerate(cpu_data["per_cpu_usage"]):
            label = _core_label(i, usage, cpu_data)
            row = (label, theme.styled_bar(usage, width=12), theme.styled_percent(usage))
            if i < half:
                left_t.add_row(*row)
            else:
                right_t.add_row(*row)

        outer = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        outer.add_column("left", ratio=1)
        outer.add_column("right", ratio=1)
        outer.add_row(left_t, right_t)

        return Panel(
            outer,
            title=f"{theme.SYM_CPU} CPU — {cpu_data['model'][:40]}  {theme.SYM_TEMP}{temp_val}  {freq_str}",
            subtitle=load_line,
            border_style=theme.BORDER_CPU,
            padding=(0, 1),
        )
    else:
        # Single column for <= 8 cores
        t = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        t.add_column("Label", style="bold", width=12, no_wrap=True)
        t.add_column("Bar", min_width=22)
        t.add_column("Value", width=8, justify="right")

        total = cpu_data["total_usage"]
        t.add_row(
            "[bold]Total[/bold]",
            theme.styled_bar(total, width=24),
            theme.styled_percent(total),
        )

        for i, usage in enumerate(cpu_data["per_cpu_usage"]):
            label = _core_label(i, usage, cpu_data)
            t.add_row(
                label,
                theme.styled_bar(usage, width=24),
                theme.styled_percent(usage),
            )

        return Panel(
            t,
            title=f"{theme.SYM_CPU} CPU — {cpu_data['model'][:40]}",
            subtitle=load_line,
            border_style=theme.BORDER_CPU,
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════
# MEMORY PANEL
# ═══════════════════════════════════════════════

def memory_panel(mem_data: dict) -> Panel:
    """Generate the RAM and Swap monitoring panel."""
    ram = mem_data["ram"]
    swap = mem_data["swap"]

    t = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    t.add_column("Label", style="bold", width=8, no_wrap=True)
    t.add_column("Bar", min_width=20)
    t.add_column("Usage", width=22, justify="right")

    # RAM bar
    ram_usage_str = f"{format_bytes(ram['used'])} / {format_bytes(ram['total'])}"
    t.add_row(
        "[bold green]RAM[/bold green]",
        theme.styled_bar(ram["percent"], width=22),
        f"{theme.styled_percent(ram['percent'])} [dim]{ram_usage_str}[/dim]",
    )

    # Swap bar
    if swap["total"] > 0:
        swap_usage_str = f"{format_bytes(swap['used'])} / {format_bytes(swap['total'])}"
        t.add_row(
            "[bold yellow]Swap[/bold yellow]",
            theme.styled_bar(swap["percent"], width=22),
            f"{theme.styled_percent(swap['percent'])} [dim]{swap_usage_str}[/dim]",
        )

    # Details
    details = f"[dim]Cached: {format_bytes(ram['cached'])}  Buffers: {format_bytes(ram['buffers'])}  " \
              f"Free: {format_bytes(ram['available'])}[/dim]"

    return Panel(
        t,
        title=f"{theme.SYM_RAM} RAM",
        subtitle=details,
        border_style=theme.BORDER_RAM,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# GPU PANEL
# ═══════════════════════════════════════════════

def gpu_panel(gpu_data: dict) -> Panel:
    """Generate the GPU monitoring panel. Supports multiple GPUs."""
    if not gpu_data["available"] or not gpu_data["gpus"]:
        return Panel(
            "[dim]Nenhuma GPU detectada[/dim]",
            title=f"{theme.SYM_GPU} GPU",
            border_style="dim",
            padding=(0, 1),
        )

    t = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    t.add_column("Metric", width=12, no_wrap=True)
    t.add_column("Bar/Value", min_width=20)
    t.add_column("Detail", width=16, justify="right")

    for i, gpu in enumerate(gpu_data["gpus"]):
        if i > 0:
            t.add_row("", "", "")  # Separator

        # GPU Name header
        driver_str = f"[dim]({gpu['driver']})[/dim]" if gpu.get("driver") else ""
        t.add_row(
            f"[bold magenta]{gpu['type']}[/bold magenta]",
            f"[bold]{gpu['name']}[/bold] {driver_str}",
            "",
        )

        # GPU Utilization
        if gpu["gpu_util"] is not None:
            t.add_row(
                "  GPU Uso",
                theme.styled_bar(gpu["gpu_util"], width=20),
                theme.styled_percent(gpu["gpu_util"]),
            )

        # VRAM
        if gpu["vram_total"] is not None:
            vram_str = f"{format_bytes(gpu['vram_used'])} / {format_bytes(gpu['vram_total'])}"
            t.add_row(
                "  VRAM",
                theme.styled_bar(gpu["vram_percent"], width=20),
                f"{theme.styled_percent(gpu['vram_percent'])}",
            )
            t.add_row("", "", f"[dim]{vram_str}[/dim]")

        # Temperature + Power + Clock
        info_parts = []
        if gpu["temperature"] is not None:
            info_parts.append(f"{theme.SYM_TEMP}{theme.styled_temp(gpu['temperature'])}")
        if gpu["power_draw"] is not None:
            info_parts.append(f"{theme.SYM_ENERGY}{theme.styled_watts(gpu['power_draw'] / 1000)}")
        if gpu["clock_gpu"] is not None:
            info_parts.append(f"[dim]{gpu['clock_gpu']} MHz[/dim]")
        if gpu["fan_speed"] is not None:
            info_parts.append(f"{theme.SYM_FAN} [dim]{gpu['fan_speed']}%[/dim]")

        if info_parts:
            t.add_row("  Info", "  ".join(info_parts), "")

    return Panel(
        t,
        title=f"{theme.SYM_GPU} GPU ({gpu_data['count']} detectada{'s' if gpu_data['count'] > 1 else ''})",
        border_style=theme.BORDER_GPU,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# DISK PANEL
# ═══════════════════════════════════════════════

def disk_panel(disk_data: dict, io_data: dict) -> Panel:
    """Generate the disk usage and I/O panel."""
    t = Table(box=box.SIMPLE_HEAVY, padding=(0, 1), expand=True)
    t.add_column("Device", style="bold", no_wrap=True)
    t.add_column("Mount", no_wrap=True)
    t.add_column("FS", width=6)
    t.add_column("Usage", min_width=18)
    t.add_column("%", width=6, justify="right")
    t.add_column("Used/Total", width=18, justify="right")

    for part in disk_data["partitions"]:
        if part["percent"] is not None:
            usage_bar = theme.styled_bar(part["percent"], width=14)
            pct = theme.styled_percent(part["percent"])
            size_str = f"[dim]{format_bytes(part['used'])} / {format_bytes(part['total'])}[/dim]"
        else:
            usage_bar = "[dim]N/A[/dim]"
            pct = "[dim]N/A[/dim]"
            size_str = "[dim]N/A[/dim]"

        # Shorten device name
        dev = part["device"]
        if dev.startswith("/dev/"):
            dev = dev[5:]

        # Shorten mountpoint
        mount = part["mountpoint"]
        if len(mount) > 20:
            mount = "..." + mount[-17:]

        t.add_row(dev, mount, part["fstype"], usage_bar, pct, size_str)

    # I/O summary
    io_read = format_bytes_speed(io_data.get("total_read_sec", 0))
    io_write = format_bytes_speed(io_data.get("total_write_sec", 0))
    io_summary = f"[dim]I/O: ↑Read {io_read}  ↓Write {io_write}[/dim]"

    return Panel(
        t,
        title=f"{theme.SYM_DISK} Discos",
        subtitle=io_summary,
        border_style=theme.BORDER_DISK,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# USB PANEL
# ═══════════════════════════════════════════════

def usb_panel(usb_devices: list) -> Panel:
    """Generate the USB devices panel."""
    if not usb_devices:
        return Panel(
            "[dim]Nenhum dispositivo USB detectado[/dim]",
            title=f"{theme.SYM_USB} USB",
            border_style="dim",
            padding=(0, 1),
        )

    t = Table(box=box.SIMPLE, padding=(0, 1), expand=True)
    t.add_column("ID", width=10, no_wrap=True)
    t.add_column("Dispositivo", min_width=20)
    t.add_column("Tipo", width=14)
    t.add_column("Speed", width=10, justify="right")
    t.add_column("Power", width=8, justify="right")

    for dev in usb_devices:
        vid_pid = f"{dev['vendor_id']}:{dev['product_id']}"
        name = dev["product"]
        if len(name) > 28:
            name = name[:25] + "..."

        # Color based on USB speed
        speed = dev["speed"]
        if speed in ("5000", "10000", "20000"):
            speed_str = f"[cyan]{dev['speed_label'].split('(')[0].strip()}[/cyan]"
        elif speed == "480":
            speed_str = f"[green]{dev['speed_label'].split('(')[0].strip()}[/green]"
        else:
            speed_str = f"[dim]{dev['speed_label'].split('(')[0].strip()}[/dim]"

        power_str = f"[yellow]{dev['max_power']}[/yellow]" if dev["max_power"] != "N/A" else "[dim]N/A[/dim]"

        t.add_row(
            f"[dim]{vid_pid}[/dim]",
            f"[bold]{name}[/bold]\n[dim]{dev['manufacturer']}[/dim]",
            dev["class_name"],
            speed_str,
            power_str,
        )

    return Panel(
        t,
        title=f"{theme.SYM_USB} USB ({len(usb_devices)} dispositivos)",
        border_style=theme.BORDER_USB,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# ENERGY PANEL
# ═══════════════════════════════════════════════

def energy_panel(energy_data: dict) -> Panel:
    """Generate the power consumption panel."""
    t = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    t.add_column("Component", width=20, no_wrap=True)
    t.add_column("Power", width=12, justify="right")

    total = energy_data.get("total_watts")
    breakdown = energy_data.get("breakdown", {})

    if not breakdown:
        return Panel(
            "[dim]Dados de energia indisponíveis\n"
            "Tente rodar com: sudo syspulse[/dim]",
            title=f"{theme.SYM_ENERGY} Energia",
            border_style="dim",
            padding=(0, 1),
        )

    for component, watts in breakdown.items():
        if component.startswith("  "):
            # Sub-domain
            t.add_row(f"[dim]  └─ {component.strip()}[/dim]", f"[dim]{watts:.1f}W[/dim]")
        else:
            t.add_row(f"[bold]{component}[/bold]", theme.styled_watts(watts))

    # Total line
    if total is not None:
        t.add_row("", "")
        total_color = "green" if total < 30 else "yellow" if total < 60 else "red"
        t.add_row(
            f"[bold {total_color}]TOTAL ESTIMADO[/bold {total_color}]",
            f"[bold {total_color}]{total:.1f}W[/bold {total_color}]",
        )

    return Panel(
        t,
        title=f"{theme.SYM_ENERGY} Energia",
        border_style=theme.BORDER_ENERGY,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# LATENCY PANEL
# ═══════════════════════════════════════════════

def latency_panel(lat_data: dict) -> Panel:
    """Generate the system latency and FPS panel."""
    t = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    t.add_column("Metric", width=18, no_wrap=True)
    t.add_column("Value", width=16, justify="right")

    # System FPS
    fps = lat_data["system_fps"]
    fps_color = "green" if fps > 0.8 else "yellow" if fps > 0.3 else "red"
    t.add_row("[bold]System FPS[/bold]", f"[bold {fps_color}]{fps:.1f} FPS[/bold {fps_color}]")

    # Loop time
    t.add_row("[dim]Loop Time[/dim]", f"[dim]{lat_data['avg_loop_time_ms']:.0f}ms[/dim]")

    # Jitter
    jitter = lat_data["jitter_ms"]
    jitter_color = "green" if jitter < 50 else "yellow" if jitter < 200 else "red"
    t.add_row("Jitter", f"[{jitter_color}]{jitter:.1f}ms[/{jitter_color}]")

    # Load average
    la = lat_data["load_avg"]
    ncpu = lat_data["num_cpus"]
    la_color = "green" if la["1min"] < ncpu else "yellow" if la["1min"] < ncpu * 1.5 else "red"
    t.add_row(
        "Load Avg",
        f"[{la_color}]{la['1min']:.2f}[/{la_color}] [dim]{la['5min']:.2f} {la['15min']:.2f}[/dim]",
    )

    # Context switches
    t.add_row("[dim]Ctx Switches/s[/dim]", f"[dim]{lat_data['ctx_switches_sec']:,}[/dim]")
    t.add_row("[dim]Interrupts/s[/dim]", f"[dim]{lat_data['interrupts_sec']:,}[/dim]")

    # Scheduler latency
    if lat_data["sched_latency_ms"] is not None:
        sl = lat_data["sched_latency_ms"]
        sl_color = "green" if sl < 1 else "yellow" if sl < 5 else "red"
        t.add_row("Sched Latency", f"[{sl_color}]{sl:.3f}ms[/{sl_color}]")

    # Uptime
    t.add_row("[dim]Uptime[/dim]", f"[dim]{format_uptime(lat_data['uptime_sec'])}[/dim]")

    # Bottleneck indicator
    bottleneck = lat_data["bottleneck"]
    bn_color = lat_data["bottleneck_color"]

    return Panel(
        t,
        title=f"{theme.SYM_LATENCY} Latência & Performance",
        subtitle=f"[{bn_color}]{bottleneck}[/{bn_color}]",
        border_style=theme.BORDER_LATENCY,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════
# PROCESS PANEL
# ═══════════════════════════════════════════════

def process_panel(processes: list, summary: dict, sort_by: str = "cpu") -> Panel:
    """Generate the top processes panel with resource consumption ranking."""
    t = Table(box=box.SIMPLE_HEAVY, padding=(0, 0), expand=True)
    t.add_column("PID", width=7, justify="right", style="dim")
    t.add_column("User", width=10, no_wrap=True)
    t.add_column("Nome", min_width=16, no_wrap=True)
    t.add_column("CPU%", width=7, justify="right")
    t.add_column("MEM%", width=7, justify="right")
    t.add_column("RSS", width=9, justify="right")
    t.add_column("Threads", width=7, justify="right", style="dim")
    t.add_column("Status", width=8)

    for i, proc in enumerate(processes):
        # Highlight top consumers
        name_style = ""
        if i == 0 and proc["cpu_percent"] > 10:
            name_style = "bold red"
        elif i < 3 and proc["cpu_percent"] > 5:
            name_style = "bold yellow"
        else:
            name_style = "white"

        # Status color
        status = proc["status"]
        status_map = {
            "running": "[green]running[/green]",
            "sleeping": "[dim]sleep[/dim]",
            "disk-sleep": "[yellow]disk[/yellow]",
            "stopped": "[red]stopped[/red]",
            "zombie": "[red]zombie[/red]",
            "idle": "[dim]idle[/dim]",
        }
        status_str = status_map.get(status, f"[dim]{status}[/dim]")

        name = proc["name"]
        if len(name) > 18:
            name = name[:15] + "..."

        t.add_row(
            str(proc["pid"]),
            proc["user"][:10],
            f"[{name_style}]{name}[/{name_style}]",
            theme.styled_percent(proc["cpu_percent"]),
            theme.styled_percent(proc["mem_percent"]),
            format_bytes(proc["rss"]),
            str(proc["threads"]),
            status_str,
        )

    # Summary subtitle
    sort_indicator = "▼CPU" if sort_by == "cpu" else "▼MEM"
    sub = (
        f"[dim]Total: {summary['total']} | "
        f"Running: {summary['running']} | "
        f"Sleeping: {summary['sleeping']} | "
        f"Zombie: {summary.get('zombie', 0)}[/dim]  "
        f"[bold cyan][{sort_indicator}][/bold cyan] "
        f"[dim]Tecla 's' para alternar ordenação[/dim]"
    )

    return Panel(
        t,
        title=f"{theme.SYM_PROCESS} Top Processos — Quem está consumindo mais?",
        subtitle=sub,
        border_style=theme.BORDER_PROCESS,
        padding=(0, 1),
    )
