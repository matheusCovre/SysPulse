#!/usr/bin/env python3
"""
SysPulse — Terminal System Monitor
A btop-inspired system monitor with CPU, RAM, GPU, Disk, USB,
energy consumption, latency/FPS, and process ranking.

Now with tabbed views:
  Tab 1: Overview (all metrics)
  Tab 2: Disk Analyzer (block visualization of storage usage)
  Tab 3: Energy Detail (sparkline graphs + statistics)

Usage:
    python main.py                   # Normal mode
    sudo python main.py              # With energy readings (RAPL)
    python main.py --interval 2      # Update every 2 seconds

Controls:
    1 / 2 / 3   — Switch tabs
    q / Ctrl+C  — Quit
    s           — Toggle sort (CPU / MEM)
    r           — Force refresh
"""

import sys
import os
import time
import signal
import argparse
import select
import termios
import tty
import threading
from typing import Optional

from rich.console import Console
from rich.live import Live

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from syspulse.collectors.cpu import get_cpu_info
from syspulse.collectors.memory import get_memory_info
from syspulse.collectors.gpu import get_gpu_info, shutdown_nvml
from syspulse.collectors.disk import get_disk_info, get_disk_io
from syspulse.collectors.usb import get_usb_devices
from syspulse.collectors.energy import get_total_power
from syspulse.collectors.latency import get_latency_info, record_loop_time
from syspulse.collectors.processes import get_top_processes, get_process_summary
from syspulse.collectors.disk_analyzer import get_disk_analysis
from syspulse.collectors.energy_detail import energy_history
from syspulse.ui.dashboard import build_dashboard


# ═══════════════════════════════════════════════
# Non-blocking keyboard input
# ═══════════════════════════════════════════════

class KeyboardReader:
    """Non-blocking keyboard reader for terminal."""

    def __init__(self):
        self._old_settings = None
        self._active = False

    def start(self):
        """Set terminal to raw mode for non-blocking key reads."""
        try:
            self._old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            self._active = True
        except Exception:
            self._active = False

    def stop(self):
        """Restore terminal settings."""
        if self._old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass
        self._active = False

    def get_key(self) -> Optional[str]:
        """Get a key press if available (non-blocking). Returns None if no key."""
        if not self._active:
            return None
        try:
            if select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                # Handle escape sequences for arrow keys
                if char == '\x1b':
                    # Read the next two chars if available
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        next1 = sys.stdin.read(1)
                        if next1 == '[':
                            if select.select([sys.stdin], [], [], 0.01)[0]:
                                next2 = sys.stdin.read(1)
                                if next2 == 'A': return 'UP'
                                if next2 == 'B': return 'DOWN'
                                if next2 == 'C': return 'RIGHT'
                                if next2 == 'D': return 'LEFT'
                return char
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════
# Background Disk Scanner
# ═══════════════════════════════════════════════

class DiskScanner:
    """Runs disk analysis in background to avoid blocking the UI."""

    def __init__(self):
        self._result = None
        self._scanning = False
        self._lock = threading.Lock()

    def start_scan(self, partitions: list):
        """Start a background scan of disk partitions."""
        if self._scanning:
            return

        self._scanning = True
        thread = threading.Thread(
            target=self._scan_worker,
            args=(partitions,),
            daemon=True,
        )
        thread.start()

    def _scan_worker(self, partitions: list):
        """Worker thread for disk scanning."""
        try:
            result = get_disk_analysis(partitions, max_items=100) # Increased to allow scrolling
            with self._lock:
                self._result = result
        except Exception:
            pass
        finally:
            self._scanning = False

    def get_result(self) -> Optional[list]:
        """Get the latest scan result (thread-safe)."""
        with self._lock:
            return self._result

    @property
    def is_scanning(self) -> bool:
        return self._scanning


# ═══════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SysPulse — Monitor de Sistema para Terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controles:
  1 / 2 / 3   — Alternar abas (Visão Geral / Discos / Energia)
  q / Ctrl+C  — Sair
  s           — Alternar ordenação (CPU / MEM)
  r           — Forçar atualização

Exemplo:
  python main.py --interval 1.5 --sort mem
  sudo python main.py  # Para dados de energia (RAPL)
        """,
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=1.0,
        help="Intervalo de atualização em segundos (padrão: 1.0)",
    )
    parser.add_argument(
        "--sort", "-s",
        choices=["cpu", "mem"],
        default="cpu",
        help="Ordenar processos por (padrão: cpu)",
    )
    parser.add_argument(
        "--processes", "-n",
        type=int,
        default=15,
        help="Número de processos a exibir (padrão: 15)",
    )
    return parser.parse_args()


def collect_tab1_data(sort_by: str, num_processes: int) -> dict:
    """Collect data for Tab 1 (Overview)."""
    return {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "gpu": get_gpu_info(),
        "disk": get_disk_info(),
        "disk_io": get_disk_io(),
        "usb": get_usb_devices(),
        "energy": get_total_power(),
        "latency": get_latency_info(),
        "processes": get_top_processes(n=num_processes, sort_by=sort_by),
        "proc_summary": get_process_summary(),
    }


def collect_tab3_data() -> dict:
    """Collect data for Tab 3 (Energy Detail)."""
    energy = get_total_power()

    # Record in history
    if energy.get("breakdown"):
        energy_history.record(energy["breakdown"])

    return {
        "energy": energy,
        "energy_stats": energy_history.get_stats(),
        "total_energy_stats": energy_history.get_total_stats(),
        "energy_sparklines": energy_history.get_all_sparklines(num_points=60),
    }


def main():
    """Main application entry point."""
    args = parse_args()
    console = Console()
    keyboard = KeyboardReader()
    disk_scanner = DiskScanner()

    sort_by = args.sort
    active_tab = 1
    running = True
    disk_scan_done = False
    
    # State for Tab 2
    disk_selected_idx = 0
    disk_scroll_offset = 0

    # Signal handler for clean exit
    def signal_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initial CPU reading to prime psutil (first call always returns 0)
    import psutil
    psutil.cpu_percent(percpu=True)
    time.sleep(0.1)

    # Prime energy readings
    get_total_power()
    time.sleep(0.1)

    console.clear()
    keyboard.start()

    try:
        with Live(
            console=console,
            refresh_per_second=2,
            screen=True,
            transient=True,
        ) as live:
            while running:
                loop_start = time.time()

                # ── Collect data based on active tab ──
                if active_tab == 1:
                    data = collect_tab1_data(sort_by, args.processes)

                    # Also record energy history even on tab 1
                    if data["energy"].get("breakdown"):
                        energy_history.record(data["energy"]["breakdown"])

                    dashboard = build_dashboard(
                        cpu_data=data["cpu"],
                        mem_data=data["memory"],
                        gpu_data=data["gpu"],
                        disk_data=data["disk"],
                        disk_io=data["disk_io"],
                        usb_devices=data["usb"],
                        energy_data=data["energy"],
                        latency_data=data["latency"],
                        processes=data["processes"],
                        proc_summary=data["proc_summary"],
                        sort_by=sort_by,
                        active_tab=1,
                    )

                elif active_tab == 2:
                    # Trigger disk scan if not done
                    if not disk_scan_done and not disk_scanner.is_scanning:
                        disk_data = get_disk_info()
                        disk_scanner.start_scan(disk_data["partitions"])

                    analysis = disk_scanner.get_result()
                    if analysis is not None:
                        disk_scan_done = True
                        disk_selected_idx = max(0, min(disk_selected_idx, len(analysis) - 1))

                    from syspulse.ui.views import disk_analyzer_view
                    dashboard = disk_analyzer_view(
                        analysis or [],
                        selected_disk=disk_selected_idx,
                        scroll_offset=disk_scroll_offset
                    )

                elif active_tab == 3:
                    tab3_data = collect_tab3_data()

                    dashboard = build_dashboard(
                        cpu_data={}, mem_data={}, gpu_data={},
                        disk_data={}, disk_io={}, usb_devices=[],
                        energy_data=tab3_data["energy"],
                        latency_data={},
                        processes=[], proc_summary={},
                        active_tab=3,
                        energy_stats=tab3_data["energy_stats"],
                        total_energy_stats=tab3_data["total_energy_stats"],
                        energy_sparklines=tab3_data["energy_sparklines"],
                    )

                live.update(dashboard)

                # Record loop time for FPS calculation
                loop_duration = time.time() - loop_start
                record_loop_time(loop_duration)

                # Wait for interval, checking for key presses
                wait_until = time.time() + args.interval
                while time.time() < wait_until and running:
                    key = keyboard.get_key()
                    if key:
                        if key == "q":
                            running = False
                            break
                        elif key == "1":
                            active_tab = 1
                            break
                        elif key == "2":
                            active_tab = 2
                            break
                        elif key == "3":
                            active_tab = 3
                            break
                        elif key == "s":
                            sort_by = "mem" if sort_by == "cpu" else "cpu"
                            break
                        elif key == "r":
                            if active_tab == 2:
                                disk_scan_done = False  # Force rescan
                                disk_scroll_offset = 0
                            break
                        # Handle arrows for tab 2
                        elif active_tab == 2:
                            if key in ("UP", "w", "W"):
                                disk_scroll_offset = max(0, disk_scroll_offset - 1)
                                break
                            elif key in ("DOWN", "s", "S"):
                                disk_scroll_offset += 1
                                break
                            elif key in ("LEFT", "a", "A"):
                                disk_selected_idx = max(0, disk_selected_idx - 1)
                                disk_scroll_offset = 0
                                break
                            elif key in ("RIGHT", "d", "D"):
                                disk_selected_idx += 1
                                disk_scroll_offset = 0
                                break
                                
                    time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"\n[red]Erro: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        keyboard.stop()
        shutdown_nvml()
        console.clear()
        console.print("[bold cyan]SysPulse[/bold cyan] encerrado. Até mais! 👋")


if __name__ == "__main__":
    main()
