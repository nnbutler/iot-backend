"""InfluxDB service for storing and retrieving device telemetry metrics."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

INFLUXDB_URL = "http://influxdb:8086"
INFLUXDB_ORG = "iot"
INFLUXDB_BUCKET = "device_metrics"
INFLUXDB_TOKEN = "device-manager-token"


class InfluxDBMetrics:
    """Manages device telemetry metrics in InfluxDB."""

    def __init__(self):
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None

    def connect(self):
        """Connect to InfluxDB."""
        try:
            print(f"[InfluxDB] Attempting to connect to {INFLUXDB_URL}", flush=True)
            logger.info(f"Attempting to connect to InfluxDB at {INFLUXDB_URL}")
            self.client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG,
            )
            # Test the connection
            health = self.client.health()
            print(f"[InfluxDB] Health check: {health.status}", flush=True)
            logger.info(f"InfluxDB health check: {health.status}")

            self.write_api = self.client.write_api()
            self.query_api = self.client.query_api()
            print(f"[InfluxDB] ✓ Connected to {INFLUXDB_URL} (org={INFLUXDB_ORG}, bucket={INFLUXDB_BUCKET})", flush=True)
            logger.info(f"✓ Connected to InfluxDB at {INFLUXDB_URL} (org={INFLUXDB_ORG}, bucket={INFLUXDB_BUCKET})")
        except Exception as e:
            print(f"[InfluxDB] ✗ Failed to connect: {e}", flush=True)
            logger.error(f"Failed to connect to InfluxDB: {e}", exc_info=True)
            self.client = None

    def disconnect(self):
        """Disconnect from InfluxDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from InfluxDB")

    def store_metrics(
        self,
        device_id: str,
        throughput: Optional[float] = None,
        cycle_time: Optional[float] = None,
        error_rate: Optional[float] = None,
    ):
        """Store device telemetry metrics using line protocol."""
        if not self.client:
            print(f"[InfluxDB] ✗ Not connected, cannot store metrics for {device_id}", flush=True)
            logger.warning(f"InfluxDB not connected, cannot store metrics for {device_id}")
            return

        try:
            lines = []
            now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

            if throughput is not None:
                lines.append(f'device_metric,device_id={device_id},metric_type=throughput value={float(throughput)} {now_ns}')

            if cycle_time is not None:
                lines.append(f'device_metric,device_id={device_id},metric_type=cycle_time value={float(cycle_time)} {now_ns}')

            if error_rate is not None:
                lines.append(f'device_metric,device_id={device_id},metric_type=error_rate value={float(error_rate)} {now_ns}')

            if lines:
                try:
                    line_protocol = '\n'.join(lines)
                    self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, write_precision=WritePrecision.NS, record=line_protocol)
                    msg = f"[InfluxDB] ✓ Stored {len(lines)} metrics for {device_id}"
                    print(msg, flush=True)
                    logger.info(f"Stored {len(lines)} metrics for {device_id}: throughput={throughput}, cycle_time={cycle_time}, error_rate={error_rate}")
                except Exception as write_err:
                    print(f"[InfluxDB] ✗ Write error for {device_id}: {write_err}", flush=True)
                    raise
        except Exception as e:
            print(f"[InfluxDB] ✗ Failed to store metrics for {device_id}: {e}", flush=True)
            logger.error(f"Failed to store metrics for {device_id}: {e}", exc_info=True)

    def get_metrics(
        self,
        device_id: str,
        metric_type: str = "throughput",
        hours: int = 24,
    ) -> list[dict]:
        """Retrieve historical metrics for a device."""
        if not self.client:
            logger.warning("InfluxDB not connected, cannot retrieve metrics")
            return []

        try:
            time_range = f"-{hours}h"
            query = f'''
            from(bucket:"{INFLUXDB_BUCKET}")
              |> range(start: {time_range})
              |> filter(fn: (r) => r._field == "value" and r.device_id == "{device_id}" and r.metric_type == "{metric_type}")
              |> sort(columns: ["_time"])
            '''

            print(f"[InfluxDB] Querying {device_id}/{metric_type} (last {hours}h)", flush=True)
            result = self.query_api.query(org=INFLUXDB_ORG, query=query)

            metrics = []
            for table in result:
                for record in table.records:
                    metrics.append({
                        "timestamp": record.get_time().isoformat(),
                        "value": record.get_value(),
                        "metric_type": metric_type,
                    })

            print(f"[InfluxDB] Found {len(metrics)} records for {device_id}/{metric_type}", flush=True)
            return metrics
        except Exception as e:
            print(f"[InfluxDB] ✗ Query failed for {device_id}/{metric_type}: {e}", flush=True)
            logger.error(f"Failed to retrieve metrics for {device_id}: {e}", exc_info=True)
            return []

    def get_all_metrics(
        self,
        device_id: str,
        hours: int = 24,
    ) -> dict:
        """Retrieve all metric types for a device."""
        return {
            "throughput": self.get_metrics(device_id, "throughput", hours),
            "cycle_time": self.get_metrics(device_id, "cycle_time", hours),
            "error_rate": self.get_metrics(device_id, "error_rate", hours),
        }

    def get_latest_metric(
        self,
        device_id: str,
        metric_type: str,
    ) -> Optional[float]:
        """Get the latest value for a metric."""
        if not self.client:
            return None

        try:
            query = f'''
            from(bucket:"{INFLUXDB_BUCKET}")
              |> range(start: -1h)
              |> filter(fn: (r) => r.device_id == "{device_id}")
              |> filter(fn: (r) => r.metric_type == "{metric_type}")
              |> last()
            '''

            result = self.query_api.query(org=INFLUXDB_ORG, query=query)

            for table in result:
                for record in table.records:
                    return record.get_value()

            return None
        except Exception as e:
            logger.error(f"Failed to get latest metric for {device_id}: {e}")
            return None


# Global metrics instance
metrics_db = InfluxDBMetrics()
