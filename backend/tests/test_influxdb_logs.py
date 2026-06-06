"""Unit tests for InfluxDB log storage service."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone

from app.services.influxdb_metrics import InfluxDBMetrics, _escape_tag


class TestEscapeTag:
    """Test tag escaping for line protocol safety."""

    def test_escape_comma(self):
        assert _escape_tag("my,device") == "my\\,device"

    def test_escape_space(self):
        assert _escape_tag("my device") == "my\\ device"

    def test_escape_equals(self):
        assert _escape_tag("device=1") == "device\\=1"

    def test_escape_multiple(self):
        assert _escape_tag("my, device=1") == "my\\,\\ device\\=1"

    def test_no_escape_needed(self):
        assert _escape_tag("mydevice123") == "mydevice123"


class TestGetLogs:
    """Test retrieving logs from InfluxDB."""

    def test_get_logs_connected(self):
        """Test retrieving logs when InfluxDB is connected."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()

        # Mock Flux query result
        mock_table = Mock()
        mock_record1 = Mock()
        mock_record1.get_time.return_value = datetime(2025, 6, 5, 14, 30, 0, tzinfo=timezone.utc)
        mock_record1.get_value.return_value = "Sensor error"
        mock_record1.values = {"level": "ERROR"}

        mock_record2 = Mock()
        mock_record2.get_time.return_value = datetime(2025, 6, 5, 14, 25, 0, tzinfo=timezone.utc)
        mock_record2.get_value.return_value = "Temperature warning"
        mock_record2.values = {"level": "WARNING"}

        mock_table.records = [mock_record1, mock_record2]
        metrics_db.query_api.query.return_value = [mock_table]

        result = metrics_db.get_logs("device-001", levels=["ERROR"], limit=50)

        assert len(result["logs"]) == 2
        assert result["logs"][0]["level"] == "ERROR"
        assert result["logs"][0]["message"] == "Sensor error"
        assert result["has_more"] is False
        assert result["next_before_timestamp"] is None

    def test_get_logs_with_level_filter(self):
        """Test that level filter is passed to Flux query."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()
        metrics_db.query_api.query.return_value = [[]]

        metrics_db.get_logs("device-001", levels=["ERROR"], limit=50)

        query = metrics_db.query_api.query.call_args.kwargs["query"]
        assert '"ERROR"' in query
        assert 'contains' in query

    def test_get_logs_without_level_filter(self):
        """Test query when no level filter is specified."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()
        metrics_db.query_api.query.return_value = [[]]

        metrics_db.get_logs("device-001", levels=None, limit=50)

        query = metrics_db.query_api.query.call_args.kwargs["query"]
        assert 'contains' not in query

    def test_get_logs_with_timestamp_cursor(self):
        """Test pagination with before_timestamp cursor."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()
        metrics_db.query_api.query.return_value = [[]]

        before_ts = "2025-06-05T14:30:00Z"
        metrics_db.get_logs("device-001", before_timestamp=before_ts, limit=50)

        query = metrics_db.query_api.query.call_args.kwargs["query"]
        assert f'time(v: "{before_ts}")' in query

    def test_get_logs_pagination_has_more(self):
        """Test has_more flag when more logs exist."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()

        # Return limit + 1 records to indicate more exist
        mock_records = []
        for i in range(51):
            mock_record = Mock()
            mock_record.get_time.return_value = datetime(2025, 6, 5, 14, 0, i, tzinfo=timezone.utc)
            mock_record.get_value.return_value = f"Log {i}"
            mock_record.values = {"level": "INFO"}
            mock_records.append(mock_record)

        mock_table = Mock()
        mock_table.records = mock_records
        metrics_db.query_api.query.return_value = [mock_table]

        result = metrics_db.get_logs("device-001", limit=50)

        assert len(result["logs"]) == 50
        assert result["has_more"] is True
        assert result["next_before_timestamp"] is not None

    def test_get_logs_pagination_next_cursor(self):
        """Test that next cursor is the last log's timestamp."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()

        # Return 2 records (limit=1 + 1 for detection)
        mock_record1 = Mock()
        mock_record1.get_time.return_value = datetime(2025, 6, 5, 14, 30, 0, tzinfo=timezone.utc)
        mock_record1.get_value.return_value = "Log 1"
        mock_record1.values = {"level": "INFO"}

        mock_record2 = Mock()
        mock_record2.get_time.return_value = datetime(2025, 6, 5, 14, 25, 0, tzinfo=timezone.utc)
        mock_record2.get_value.return_value = "Log 2"
        mock_record2.values = {"level": "INFO"}

        mock_table = Mock()
        mock_table.records = [mock_record1, mock_record2]
        metrics_db.query_api.query.return_value = [mock_table]

        result = metrics_db.get_logs("device-001", limit=1)

        assert len(result["logs"]) == 1
        assert result["has_more"] is True
        assert result["next_before_timestamp"] == "2025-06-05T14:30:00+00:00"

    def test_get_logs_disconnected(self):
        """Test retrieving logs when InfluxDB is not connected."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = None

        result = metrics_db.get_logs("device-001")

        assert result["logs"] == []
        assert result["has_more"] is False
        assert result["next_before_timestamp"] is None

    def test_get_logs_query_error(self):
        """Test error handling during query."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()
        metrics_db.query_api.query.side_effect = Exception("Query failed")

        result = metrics_db.get_logs("device-001")

        assert result["logs"] == []
        assert result["has_more"] is False
        assert result["next_before_timestamp"] is None

    def test_get_logs_escapes_device_id(self):
        """Test that device_id is escaped in Flux query."""
        metrics_db = InfluxDBMetrics()
        metrics_db.client = Mock()
        metrics_db.query_api = Mock()
        metrics_db.query_api.query.return_value = [[]]

        metrics_db.get_logs('device"123', levels=None, limit=50)

        query = metrics_db.query_api.query.call_args.kwargs["query"]
        assert 'device\\"123' in query
