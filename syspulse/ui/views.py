"""
SysPulse — Views (Tab Pages)
Separate view generators for each tab of the TUI.
Tab 1: Overview (existing dashboard)
Tab 2: Disk Analyzer (block visualization)
Tab 3: Energy Detail (historical graphs)
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich.console import Group
from rich import box

from ..utils.helpers import format_bytes, format_bytes_speed, format_frequency, format_uptime
from . import theme


# ═══════════════════════════════════════════════
# TAB HEADER (shared across all views)
# ═══════════════════════════════════════════════

def create_tab_header(active_tab: int = 1) -> Panel:
    """Create header with tab navigation indicators."""
    title = Text()
    title.append("  ⚡ SysPulse ", style="bold bright_cyan")
    title.append("v1.1 ", style="dim cyan")
    title.append("│ ", style="dim")

    tabs = [
        ("1", "Visão Geral"),
        ("2", "Analisador de Disco"),
        ("3", "Energia Detalhada"),
    ]

    for key, label in tabs:
        tab_num = int(key)
        if tab_num == active_tab:
            title.append(f" [{key}] {label} ", style="bold bright_white on rgb(40,80,120)")
        else:
            title.append(f" {key}:{label} ", style="dim")
        title.append(" ", style="")

    title.append("│ ", style="dim")
    title.append("q", style="bold yellow")
    title.append(":sair ", style="dim")
    title.append("s", style="bold yellow")
    title.append(":ordenar ", style="dim")

    return Panel(title, style="on rgb(20,20,40)", height=3, border_style="bright_cyan")


# ═══════════════════════════════════════════════
# TAB 2: DISK ANALYZER VIEW
# ═══════════════════════════════════════════════

# Color palette for block visualization
BLOCK_COLORS = [
    "bright_red", "bright_green", "bright_yellow", "bright_blue",
    "bright_magenta", "bright_cyan", "red", "green",
    "yellow", "blue", "magenta", "cyan",
    "dark_orange", "deep_pink4", "dark_sea_green", "steel_blue",
    "medium_purple3", "dark_goldenrod", "indian_red", "dark_cyan",
]


def _make_block_map(items: list, total_used: int, width: int = 60, height: int = 8) -> Text:
    """
    Create a treemap-style block visualization of disk usage.
    Each directory gets colored blocks proportional to its size.
    """
    text = Text()
    total_cells = width * height

    if not items or total_used == 0:
        text.append("░" * width + "\n", style="dim")
        return text

    # Calculate cells per item
    blocks = []
    for i, item in enumerate(items):
        ratio = item["size"] / total_used if total_used > 0 else 0
        cells = max(1, int(ratio * total_cells))
        color = BLOCK_COLORS[i % len(BLOCK_COLORS)]
        blocks.append((item, cells, color))

    # Render blocks row by row
    cell_idx = 0
    current_block = 0
    remaining_in_block = blocks[0][1] if blocks else 0

    for row in range(height):
        for col in range(width):
            if current_block < len(blocks):
                _, _, color = blocks[current_block]
                text.append("█", style=color)
                remaining_in_block -= 1
                if remaining_in_block <= 0:
                    current_block += 1
                    if current_block < len(blocks):
                        remaining_in_block = blocks[current_block][1]
            else:
                text.append("░", style="dim")
            cell_idx += 1
        text.append("\n")

    return text


def _make_legend(items: list, total_used: int) -> Table:
    """Create legend table for the block map."""
    t = Table(box=box.SIMPLE, padding=(0, 1), expand=True, show_header=True)
    t.add_column("Cor", width=3, no_wrap=True)
    t.add_column("Nome", min_width=20, no_wrap=True)
    t.add_column("Tamanho", width=12, justify="right")
    t.add_column("%", width=7, justify="right")
    t.add_column("Tipo", width=8)
    t.add_column("Itens", width=7, justify="right", style="dim")

    for i, item in enumerate(items):
        color = BLOCK_COLORS[i % len(BLOCK_COLORS)]
        pct = (item["size"] / total_used * 100) if total_used > 0 else 0
        type_str = "📁 Dir" if item["is_dir"] else "📄 File"

        pct_color = "green" if pct < 20 else "yellow" if pct < 50 else "red"

        t.add_row(
            f"[{color}]██[/{color}]",
            f"[bold]{item['name']}[/bold]",
            format_bytes(item["size"]),
            f"[{pct_color}]{pct:.1f}%[/{pct_color}]",
            type_str,
            str(item.get("child_count", "")) if item["is_dir"] else "",
        )

    return t


def disk_analyzer_view(analysis: list, selected_disk: int = 0, scroll_offset: int = 0) -> Layout:
    """
    Build the disk analyzer tab view.
    Shows treemap-style blocks for the selected partition and a scrollable legend.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="content", ratio=1),
    )

    layout["header"].update(create_tab_header(active_tab=2))

    if not analysis:
        layout["content"].update(Panel(
            "[dim]Nenhum disco para analisar. Aguarde o scan...[/dim]",
            title="💾 Analisador de Disco",
            border_style="blue",
        ))
        return layout

    # Ensure selected disk is in range
    selected_disk = max(0, min(selected_disk, len(analysis) - 1))
    disk = analysis[selected_disk]

    items = disk["items"]
    used = disk["used"]
    total = disk["total"]
    free = disk["free"]

    # Ensure scroll is in range
    max_scroll = max(0, len(items) - 15)  # 15 items visible at once
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    # Info header
    dev = disk.get("device", "?")
    if dev.startswith("/dev/"):
        dev = dev[5:]
    mount = disk["mountpoint"]

    pct = (used / total * 100) if total > 0 else 0
    info = (
        f"[bold]{dev}[/bold] → [cyan]{mount}[/cyan]  "
        f"[dim]({disk.get('fstype', '?')})[/dim]  "
        f"Usado: {format_bytes(used)} / {format_bytes(total)}  "
        f"Livre: [green]{format_bytes(free)}[/green]  "
        f"{theme.styled_percent(pct)}"
    )
    
    nav_info = f"[dim]←/→ para trocar disco ({selected_disk + 1}/{len(analysis)}) | ↑/↓ para rolar lista[/dim]"

    # Block map (uses top 20 items max)
    block_map = _make_block_map(items[:20], used, width=100, height=6)

    # Legend (scrollable)
    visible_items = items[scroll_offset : scroll_offset + 15]
    legend = _make_legend(visible_items, used)

    # Other space
    if disk["other_size"] > 0:
        other_pct = (disk["other_size"] / used * 100) if used > 0 else 0
        other_info = f"\n[dim]+ Outros/Sistema: {format_bytes(disk['other_size'])} ({other_pct:.1f}%)[/dim]"
    else:
        other_info = ""

    content = Group(
        Text.from_markup(info),
        Text.from_markup(nav_info),
        Text(""),
        block_map,
        Text(""),
        legend,
        Text.from_markup(other_info) if other_info else Text(""),
    )

    panel = Panel(
        content,
        title=f"💾 Analisador: {dev} — {mount}",
        border_style="bright_blue",
        padding=(0, 2),
    )
    
    layout["content"].update(panel)
    return layout


# ═══════════════════════════════════════════════
# TAB 3: ENERGY DETAIL VIEW
# ═══════════════════════════════════════════════

def energy_detail_view(
    energy_data: dict,
    energy_stats: dict,
    total_stats: dict,
    sparklines: dict,
    sparkline_func,
) -> Layout:
    """
    Build the detailed energy monitoring tab view.
    Shows sparkline graphs, stats, and cost estimation.
    """
    from ..collectors.energy_detail import sparkline as make_sparkline

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
    )

    layout["header"].update(create_tab_header(active_tab=3))

    # Body split: left (graphs) | right (stats)
    body = Layout()
    body.split_row(
        Layout(name="graphs", ratio=3),
        Layout(name="stats", ratio=2),
    )

    # ── Left: Sparkline graphs per component ──
    graph_table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1), expand=True)
    graph_table.add_column("Componente", width=22, no_wrap=True)
    graph_table.add_column("Agora", width=8, justify="right")
    graph_table.add_column("Histórico (últimos 2 min)", min_width=42)
    graph_table.add_column("Pico", width=8, justify="right")

    for component, values in sparklines.items():
        if not values:
            continue

        current = values[-1] if values else 0
        peak = max(values) if values else 0

        # Color the sparkline based on power level
        spark_str = make_sparkline(values, width=40)
        if current > 50:
            spark_colored = f"[red]{spark_str}[/red]"
        elif current > 25:
            spark_colored = f"[yellow]{spark_str}[/yellow]"
        else:
            spark_colored = f"[green]{spark_str}[/green]"

        graph_table.add_row(
            f"[bold]{component}[/bold]",
            theme.styled_watts(current),
            spark_colored,
            f"[dim]{peak:.1f}W[/dim]",
        )

    # Total sparkline
    all_values = sparklines.values()
    if all_values:
        total_values = []
        max_len = max(len(v) for v in all_values) if all_values else 0
        for i in range(max_len):
            total = sum(v[i] if i < len(v) else 0 for v in all_values)
            total_values.append(total)

        if total_values:
            total_spark = make_sparkline(total_values, width=40)
            total_current = total_values[-1] if total_values else 0
            total_peak = max(total_values) if total_values else 0
            t_color = "red" if total_current > 80 else "yellow" if total_current > 40 else "green"
            graph_table.add_row("", "", "", "")
            graph_table.add_row(
                f"[bold {t_color}]⚡ TOTAL[/bold {t_color}]",
                f"[bold {t_color}]{total_current:.1f}W[/bold {t_color}]",
                f"[{t_color}]{total_spark}[/{t_color}]",
                f"[bold]{total_peak:.1f}W[/bold]",
            )

    graphs_panel = Panel(
        graph_table,
        title="📈 Consumo em Tempo Real",
        border_style="yellow",
        padding=(0, 1),
    )

    # ── Right: Statistics ──
    stats_table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    stats_table.add_column("Label", width=16, no_wrap=True)
    stats_table.add_column("Value", width=14, justify="right")

    # Total stats
    stats_table.add_row(
        "[bold yellow]⚡ Resumo Geral[/bold yellow]", ""
    )
    stats_table.add_row("", "")
    stats_table.add_row(
        "Consumo Atual",
        theme.styled_watts(total_stats.get("current", 0)),
    )
    stats_table.add_row(
        "Pico Máximo",
        f"[red]{total_stats.get('peak', 0):.1f}W[/red]",
    )
    stats_table.add_row(
        "Média",
        f"[cyan]{total_stats.get('avg', 0):.1f}W[/cyan]",
    )

    # Energy consumed
    wh = total_stats.get("total_wh", 0)
    stats_table.add_row("", "")
    stats_table.add_row(
        "[bold]Energia Gasta[/bold]", ""
    )
    stats_table.add_row(
        "Watt-hora",
        f"[bold green]{wh:.3f} Wh[/bold green]",
    )
    if wh > 0:
        # Estimate cost (Brazilian electricity ~R$0.75/kWh average)
        kwh = wh / 1000
        cost_brl = kwh * 0.75
        stats_table.add_row(
            "Custo Est.",
            f"[bold yellow]R$ {cost_brl:.4f}[/bold yellow]",
        )

    # Per-component breakdown
    stats_table.add_row("", "")
    stats_table.add_row("[bold]Por Componente[/bold]", "")

    for comp, s in energy_stats.items():
        stats_table.add_row("", "")
        stats_table.add_row(
            f"[cyan]{comp}[/cyan]", ""
        )
        stats_table.add_row(
            "  Atual / Pico",
            f"{s['current']:.1f} / {s['peak']:.1f}W",
        )
        stats_table.add_row(
            "  Média",
            f"{s['avg']:.1f}W",
        )
        stats_table.add_row(
            "  Energia",
            f"{s['total_wh']:.3f} Wh",
        )

    # Tips section
    stats_table.add_row("", "")
    stats_table.add_row("[bold green]💡 Dicas[/bold green]", "")
    current_total = total_stats.get("current", 0)
    if current_total > 80:
        stats_table.add_row(
            "", "[red]Sistema consumindo\nmuita energia![/red]"
        )
    elif current_total > 40:
        stats_table.add_row(
            "", "[yellow]Consumo moderado.\nVerifique processos.[/yellow]"
        )
    else:
        stats_table.add_row(
            "", "[green]Consumo normal.\nSistema eficiente.[/green]"
        )

    stats_panel = Panel(
        stats_table,
        title="📊 Estatísticas",
        border_style="magenta",
        padding=(0, 1),
    )

    body["graphs"].update(graphs_panel)
    body["stats"].update(stats_panel)
    layout["body"].update(body)

    return layout
