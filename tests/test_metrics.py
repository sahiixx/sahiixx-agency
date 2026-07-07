"""Tests for the metrics collector."""

from __future__ import annotations

import pytest

from sahiixx_agency.core.metrics import MetricsCollector
from sahiixx_agency.core.models import HealthCheck, HealthStatus


@pytest.fixture
def collector():
    return MetricsCollector(retention_hours=1)


def test_record_and_query(collector):
    collector.record("tasks_total", 1.0, {"status": "completed"})
    points = collector.query(name="tasks_total")
    assert len(points) == 1
    assert points[0].value == 1.0


def test_increment(collector):
    collector.increment("counter", labels={"a": "b"})
    collector.increment("counter", labels={"a": "b"})
    summary = collector.summary()
    assert summary["counters"]["counter|a=b"] == 2.0


def test_gauge(collector):
    collector.gauge("registry_modules", 42.0)
    assert collector.summary()["gauges"]["registry_modules"] == 42.0


def test_timer_context(collector):
    with collector.timer("latency"):
        pass
    points = collector.query(name="latency")
    assert len(points) == 1
    assert points[0].value >= 0.0


def test_health_checks(collector):
    def check():
        return HealthCheck(name="test", status=HealthStatus.HEALTHY, message="ok")

    collector.register_health_check("test", check)
    results = collector.health()
    assert len(results) == 1
    assert results[0].status == HealthStatus.HEALTHY


def test_overall_health(collector):
    collector.register_health_check("good", lambda: HealthCheck(name="good", status=HealthStatus.HEALTHY))
    assert collector.overall_health() == HealthStatus.HEALTHY
    collector.register_health_check("bad", lambda: HealthCheck(name="bad", status=HealthStatus.UNHEALTHY))
    assert collector.overall_health() == HealthStatus.UNHEALTHY


def test_prometheus_export(collector):
    collector.increment("tasks_total", labels={"status": "completed"})
    output = collector.to_prometheus()
    assert "opa_tasks_total" in output
    assert 'status="completed"' in output


def test_health_check_exception_handled(collector):
    collector.register_health_check("boom", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    results = collector.health()
    assert results[0].status == HealthStatus.UNHEALTHY
    assert "fail" in results[0].message
