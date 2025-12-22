from prometheus_client import Counter, Histogram, Gauge

scans_total = Counter("ci_scans_total", "Total scans", ["competitor", "status"])
scan_duration = Histogram("ci_scan_duration_seconds", "Scan duration seconds")
queue_size = Gauge("ci_scan_queue_size", "Current scan queue size")


def record_scan_metrics(competitor: str, duration: float, success: bool):
    scans_total.labels(competitor=competitor, status="success" if success else "failed").inc()
    scan_duration.observe(duration)
