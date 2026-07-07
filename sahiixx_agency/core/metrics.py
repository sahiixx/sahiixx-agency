"""Metrics and observability collector for the agency."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import HealthCheck, HealthStatus, MetricPoint


class MetricsCollector:
    """Collect, aggregate, and export agency metrics.

    Metrics are kept in memory with a configurable retention window. The
    collector is intentionally simple (no external TSDB dependency) so it works
    in the solo Docker Compose tier out of the box.
    """

    def __init__(self, retention_hours: int = 24) -> None:
        self.retention_hours = retention_hours
        self._points: deque[MetricPoint] = deque()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._health_checks: dict[str, Callable[[], HealthCheck]] = {}
        self._lock_time = time.monotonic

    def record(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> MetricPoint:
        """Record a metric point."""
        point = MetricPoint(name=name, value=value, labels=labels or {})
        self._points.append(point)
        self._trim()
        return point

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._counter_key(name, labels or {})
        self._counters[key] = self._counters.get(key, 0.0) + value
        self.record(name, self._counters[key], labels)

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        key = self._counter_key(name, labels or {})
        self._gauges[key] = value
        self.record(name, value, labels)

    def timer(self, name: str, labels: dict[str, str] | None = None) -> Timer:
        """Context manager / callable timer helper."""
        return Timer(self, name, labels)

    def observe_latency(self, name: str, seconds: float, labels: dict[str, str] | None = None) -> None:
        """Record latency in seconds (also exported as a histogram bucket)."""
        self.record(name, seconds, labels)

    def register_health_check(self, name: str, check: Callable[[], HealthCheck]) -> None:
        """Register a health check callable."""
        self._health_checks[name] = check

    def health(self) -> list[HealthCheck]:
        """Run all registered health checks."""
        results: list[HealthCheck] = []
        for name, check in self._health_checks.items():
            started = self._lock_time()
            try:
                result = check()
                if result.name != name:
                    result.name = name
            except Exception as exc:  # noqa: BLE001
                result = HealthCheck(name=name, status=HealthStatus.UNHEALTHY, message=str(exc))
            result.latency_ms = round((self._lock_time() - started) * 1000, 2)
            results.append(result)
        return results

    def overall_health(self) -> HealthStatus:
        """Aggregate health status across all checks."""
        statuses = {h.status for h in self.health()}
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses or not statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def query(
        self,
        name: str | None = None,
        since: datetime | None = None,
        limit: int = 10000,
    ) -> list[MetricPoint]:
        """Query stored metric points with optional filtering."""
        since = since or datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        results = [
            p
            for p in self._points
            if (name is None or p.name == name) and p.timestamp >= since
        ]
        return results[-limit:]

    def summary(self) -> dict[str, Any]:
        """Return a JSON-friendly summary of current counters/gauges."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "retention_hours": self.retention_hours,
            "total_points": len(self._points),
        }

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus exposition format."""
        lines: list[str] = []

        # Aggregate counters and gauges into latest value per series.
        series: dict[str, dict[str, float]] = {}
        for point in self._points:
            key = self._series_key(point.name, point.labels)
            series.setdefault(point.name, {})[key] = point.value

        for name, values in series.items():
            sanitized = self._sanitize_name(name)
            lines.append(f"# TYPE {sanitized} gauge")
            for key, value in values.items():
                labels = self._key_labels(key)
                label_str = ",".join(f'{k}="{self._escape(v)}"' for k, v in labels.items())
                if label_str:
                    lines.append(f"{sanitized}{{{label_str}}} {value}")
                else:
                    lines.append(f"{sanitized} {value}")

        # Counters that may not have points yet.
        for key, value in self._counters.items():
            name, labels = self._parse_counter_key(key)
            sanitized = self._sanitize_name(name)
            if not any(s.startswith(f"# TYPE {sanitized} ") for s in lines):
                lines.append(f"# TYPE {sanitized} counter")
            label_str = ",".join(f'{k}="{self._escape(v)}"' for k, v in labels.items())
            if label_str:
                lines.append(f"{sanitized}_total{{{label_str}}} {value}")
            else:
                lines.append(f"{sanitized}_total {value}")

        return "\n".join(lines) + "\n"

    def _trim(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        while self._points and self._points[0].timestamp < cutoff:
            self._points.popleft()

    @staticmethod
    def _counter_key(name: str, labels: dict[str, str]) -> str:
        parts = [name]
        for k in sorted(labels):
            parts.append(f"{k}={labels[k]}")
        return "|".join(parts)

    @staticmethod
    def _parse_counter_key(key: str) -> tuple[str, dict[str, str]]:
        parts = key.split("|")
        name = parts[0]
        labels: dict[str, str] = {}
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                labels[k] = v
        return name, labels

    @staticmethod
    def _series_key(name: str, labels: dict[str, str]) -> str:
        return MetricsCollector._counter_key(name, labels)

    @staticmethod
    def _key_labels(key: str) -> dict[str, str]:
        _, labels = MetricsCollector._parse_counter_key(key)
        return labels

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return "opa_" + "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Timer:
    """Simple timer context manager."""

    def __init__(self, collector: MetricsCollector, name: str, labels: dict[str, str] | None = None) -> None:
        self.collector = collector
        self.name = name
        self.labels = labels or {}
        self.started: float | None = None

    def __enter__(self) -> Timer:
        self.started = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.started is not None:
            elapsed = time.monotonic() - self.started
            self.collector.observe_latency(self.name, elapsed, self.labels)

    async def __aenter__(self) -> Timer:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.__exit__(exc_type, exc, tb)
