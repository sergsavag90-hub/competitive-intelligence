from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

registry = CollectorRegistry()

scans_total = Counter("ci_scans_total", "Total scans", ["competitor", "status", "module"], registry=registry)
scan_duration = Histogram(
    "ci_scan_duration_seconds",
    "Scan duration seconds",
    ["competitor", "module"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
    registry=registry,
)
queue_size = Gauge("ci_scan_queue_size", "Current scan queue size", ["queue"], registry=registry)
active_scans = Gauge("ci_active_scans", "Number of active scans", registry=registry)


def record_scan_metrics(competitor: str, module: str, duration: float, success: bool):
    scans_total.labels(competitor=competitor, status="success" if success else "failed", module=module).inc()
    scan_duration.labels(competitor=competitor, module=module).observe(duration)
