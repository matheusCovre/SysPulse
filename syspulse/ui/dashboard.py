"""
SysPulse — Dashboard Layout
Composes all widget panels into a full-screen terminal dashboard.
Supports multiple tabs/views.
"""

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from . import theme
from . import widgets
from .views import create_tab_header, disk_analyzer_view, energy_detail_view


def build_dashboard(
    cpu_data: dict,
    mem_data: dict,
    gpu_data: dict,
    disk_data: dict,
    disk_io: dict,
    usb_devices: list,
    energy_data: dict,
    latency_data: dict,
    processes: list,
    proc_summary: dict,
    sort_by: str = "cpu",
    active_tab: int = 1,
    # Tab 2 data
    disk_analysis: list = None,
    # Tab 3 data
    energy_stats: dict = None,
    total_energy_stats: dict = None,
    energy_sparklines: dict = None,
) -> Layout:
    """
    Build the complete dashboard layout for the active tab.

    Tab 1: Overview (CPU, RAM, GPU, Disks, USB, Energy, Latency, Processes)
    Tab 2: Disk Analyzer (treemap block visualization)
    Tab 3: Energy Detail (sparkline graphs + stats)
    """

    if active_tab == 2:
        return disk_analyzer_view(disk_analysis or [])

    if active_tab == 3:
        from ..collectors.energy_detail import sparkline as spark_func
        return energy_detail_view(
            energy_data=energy_data,
            energy_stats=energy_stats or {},
            total_stats=total_energy_stats or {},
            sparklines=energy_sparklines or {},
            sparkline_func=spark_func,
        )

    # ── Tab 1: Overview ──
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="upper", ratio=3),
        Layout(name="middle", ratio=2),
        Layout(name="lower", ratio=3),
    )

    # Header with tabs
    layout["header"].update(create_tab_header(active_tab=1))

    has_gpu = gpu_data.get("available", False) and gpu_data.get("gpus")

    if has_gpu:
        # Upper section: CPU | GPU | Energy
        layout["upper"].split_row(
            Layout(name="cpu", ratio=3),
            Layout(name="gpu", ratio=3),
            Layout(name="energy", ratio=2),
        )

        # CPU + RAM stacked
        cpu_and_ram = Layout()
        cpu_and_ram.split_column(
            Layout(name="cpu_panel", ratio=3),
            Layout(name="ram_panel", ratio=1),
        )
        cpu_and_ram["cpu_panel"].update(widgets.cpu_panel(cpu_data))
        cpu_and_ram["ram_panel"].update(widgets.memory_panel(mem_data))
        layout["cpu"].update(cpu_and_ram)

        # GPU + Latency stacked
        gpu_and_lat = Layout()
        gpu_and_lat.split_column(
            Layout(name="gpu_panel", ratio=2),
            Layout(name="lat_panel", ratio=1),
        )
        gpu_and_lat["gpu_panel"].update(widgets.gpu_panel(gpu_data))
        gpu_and_lat["lat_panel"].update(widgets.latency_panel(latency_data))
        layout["gpu"].update(gpu_and_lat)

        # Energy panel
        layout["energy"].update(widgets.energy_panel(energy_data))
    else:
        # No GPU: CPU gets more space, latency goes next to energy
        layout["upper"].split_row(
            Layout(name="cpu", ratio=4),
            Layout(name="side", ratio=2),
        )

        # CPU + RAM stacked (CPU panel gets much more room for all cores)
        cpu_and_ram = Layout()
        cpu_and_ram.split_column(
            Layout(name="cpu_panel", ratio=4),
            Layout(name="ram_panel", ratio=1),
        )
        cpu_and_ram["cpu_panel"].update(widgets.cpu_panel(cpu_data))
        cpu_and_ram["ram_panel"].update(widgets.memory_panel(mem_data))
        layout["cpu"].update(cpu_and_ram)

        # Energy + Latency stacked on the side
        side = Layout()
        side.split_column(
            Layout(name="energy_panel", ratio=2),
            Layout(name="lat_panel", ratio=1),
        )
        side["energy_panel"].update(widgets.energy_panel(energy_data))
        side["lat_panel"].update(widgets.latency_panel(latency_data))
        layout["side"].update(side)

    # Middle section: Disks | USB
    layout["middle"].split_row(
        Layout(name="disks", ratio=3),
        Layout(name="usb", ratio=2),
    )
    layout["disks"].update(widgets.disk_panel(disk_data, disk_io))
    layout["usb"].update(widgets.usb_panel(usb_devices))

    # Lower section: Process table
    layout["lower"].update(
        widgets.process_panel(processes, proc_summary, sort_by)
    )

    return layout
