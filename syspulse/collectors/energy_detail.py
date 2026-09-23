"""
SysPulse — Detailed Energy Collector
Extended energy monitoring with historical tracking for the energy detail view.
"""

import time
from typing import Dict, Any, List, Optional
from collections import deque


class EnergyHistory:
    """Tracks energy readings over time for sparkline/graph display."""

    def __init__(self, max_samples: int = 120):
        """
        Args:
            max_samples: Maximum number of historical samples to keep (at 1s interval = 2 min)
        """
        self.max_samples = max_samples
        self._history = {}  # component_name -> deque of (timestamp, watts)
        self._peak = {}     # component_name -> peak watts
        self._total_energy = {}  # component_name -> total watt-hours consumed

    def record(self, breakdown: Dict[str, float], timestamp: float = None):
        """Record a set of power readings."""
        if timestamp is None:
            timestamp = time.time()

        for component, watts in breakdown.items():
            if component.startswith("  "):
                continue  # Skip sub-domains

            if component not in self._history:
                self._history[component] = deque(maxlen=self.max_samples)
                self._peak[component] = 0.0
                self._total_energy[component] = 0.0

            self._history[component].append((timestamp, watts))

            # Update peak
            if watts > self._peak[component]:
                self._peak[component] = watts

            # Accumulate energy (watt-seconds -> watt-hours)
            if len(self._history[component]) >= 2:
                prev_ts, prev_w = self._history[component][-2]
                dt = timestamp - prev_ts
                avg_watts = (watts + prev_w) / 2
                watt_hours = (avg_watts * dt) / 3600
                self._total_energy[component] += watt_hours

    def get_sparkline_data(self, component: str, num_points: int = 60) -> List[float]:
        """Get recent watts readings for sparkline display."""
        if component not in self._history:
            return []
        readings = list(self._history[component])
        # Take last N points
        recent = readings[-num_points:]
        return [w for _, w in recent]

    def get_all_sparklines(self, num_points: int = 60) -> Dict[str, List[float]]:
        """Get sparkline data for all components."""
        return {
            comp: self.get_sparkline_data(comp, num_points)
            for comp in self._history
        }

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tracked components."""
        stats = {}
        for component in self._history:
            readings = [w for _, w in self._history[component]]
            if readings:
                stats[component] = {
                    "current": readings[-1],
                    "peak": self._peak[component],
                    "avg": sum(readings) / len(readings),
                    "min": min(readings),
                    "max": max(readings),
                    "total_wh": self._total_energy.get(component, 0.0),
                    "samples": len(readings),
                }
        return stats

    def get_total_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = self.get_stats()
        if not stats:
            return {
                "current": 0, "peak": 0, "avg": 0,
                "total_wh": 0, "components": 0,
            }

        return {
            "current": sum(s["current"] for s in stats.values()),
            "peak": sum(s["peak"] for s in stats.values()),
            "avg": sum(s["avg"] for s in stats.values()),
            "total_wh": sum(s["total_wh"] for s in stats.values()),
            "components": len(stats),
        }


# Global history instance
energy_history = EnergyHistory()


def sparkline(values: List[float], width: int = 40) -> str:
    """
    Generate a Unicode sparkline string from a list of values.
    Uses block characters: ▁▂▃▄▅▆▇█
    """
    if not values:
        return "░" * width

    blocks = " ▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val

    if val_range == 0:
        # All values are the same
        return blocks[4] * min(len(values), width)

    # Resample to fit width if needed
    if len(values) > width:
        step = len(values) / width
        resampled = []
        for i in range(width):
            idx = int(i * step)
            resampled.append(values[min(idx, len(values) - 1)])
        values = resampled
    elif len(values) < width:
        # Pad left with empty
        values = [min_val] * (width - len(values)) + values

    result = ""
    for v in values:
        normalized = (v - min_val) / val_range
        idx = int(normalized * (len(blocks) - 1))
        result += blocks[idx]

    return result
