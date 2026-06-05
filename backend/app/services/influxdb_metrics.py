"""InfluxDB service for storing and retrieving device telemetry metrics."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from influxdb_client import InfluxDBClient, Point
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
            self.client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG,
            )
            self.write_api = self.client.write_api()
            self.query_api = self.client.query_api()
            logger.info(f"Connected to InfluxDB at {INFLUXDB_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
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
        """Store device telemetry metrics."""
        if not self.client:
            logger.warning("InfluxDB not connected, cannot store metrics")
            return

        try:
            points = []
            now = datetime.now(timezone.utc)

            if throughput is not None:
                points.append(
                    Point("device_metric")
                    .tag("device_id", device_id)
                    .tag("metric_type", "throughput")
                    .field("value", throughput)
                    .time(now)
                )

            if cycle_time is not None:
                points.append(
                    Point("device_metric")
                    .tag("device_id", device_id)
                    .tag("metric_type", "cycle_time")
                    .field("value", cycle_time)
                    .time(now)
                )

            if error_rate is not None:
                points.append(
                    Point("device_metric")
                    .tag("device_id", device_id)
                    .tag("metric_type", "error_rate")
                    .field("value", error_rate)
                    .time(now)
                )

            if points:
                self.write_api.write(bucket=INFLUXDB_BUCKET, records=points)
                logger.debug(f"Stored {len(points)} metrics for {device_id}")
        except Exception as e:
            logger.error(f"Failed to store metrics for {device_id}: {e}")

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
              |> filter(fn: (r) => r.device_id == "{device_id}")
              |> filter(fn: (r) => r.metric_type == "{metric_type}")
              |> sort(columns: ["_time"])
            '''

            result = self.query_api.query(org=INFLUXDB_ORG, query=query)

            metrics = []
            for table in result:
                for record in table.records:
                    metrics.append({
                        "timestamp": record.get_time().isoformat(),
                        "value": record.get_value(),
                        "metric_type": metric_type,
                    })

            return metrics
        except Exception as e:
            logger.error(f"Failed to retrieve metrics for {device_id}: {e}")
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
