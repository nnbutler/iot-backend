"""Unit tests for InfluxDB telemetry metrics (store/get/latest)."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call

from app.services.influxdb_metrics import InfluxDBMetrics, _escape_flux_string, INFLUXDB_BUCKET, INFLUXDB_ORG


# ── _escape_flux_string ───────────────────────────────────────────────────────

class TestEscapeFluxString:
    def test_escapes_double_quote(self):
        assert _escape_flux_string('say "hello"') == 'say \\"hello\\"'

    def test_escapes_backslash(self):
        assert _escape_flux_string("a\\b") == "a\\\\b"

    def test_escapes_newline(self):
        assert _escape_flux_string("line1\nline2") == "line1\\nline2"

    def test_escapes_tab(self):
        assert _escape_flux_string("col\tval") == "col\\tval"

    def test_escapes_carriage_return(self):
        assert _escape_flux_string("a\rb") == "a\\rb"

    def test_no_escape_needed(self):
        assert _escape_flux_string("device-001") == "device-001"

    def test_non_string_coerced(self):
        assert _escape_flux_string(42) == "42"


# ── connect / disconnect ──────────────────────────────────────────────────────

class TestConnect:
    def test_connect_success(self):
        db = InfluxDBMetrics()
        mock_client = Mock()
        mock_client.health.return_value = Mock(status="pass")
        mock_client.write_api.return_value = Mock()
        mock_client.query_api.return_value = Mock()
        mock_client.buckets_api.return_value = Mock(find_buckets=Mock(return_value=Mock(buckets=[])))
        mock_client.organizations_api.return_value = Mock(find_organizations=Mock(return_value=[]))

        with patch("app.services.influxdb_metrics.InfluxDBClient", return_value=mock_client):
            db.connect()

        assert db.client is mock_client
        assert db.write_api is not None
        assert db.query_api is not None

    def test_connect_failure_sets_client_none(self):
        db = InfluxDBMetrics()
        with patch("app.services.influxdb_metrics.InfluxDBClient", side_effect=Exception("refused")):
            db.connect()
        assert db.client is None

    def test_disconnect_closes_client(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.disconnect()
        db.client.close.assert_called_once()

    def test_disconnect_noop_when_not_connected(self):
        db = InfluxDBMetrics()
        db.client = None
        db.disconnect()  # should not raise


# ── store_metrics ─────────────────────────────────────────────────────────────

class TestStoreMetrics:
    def _connected_db(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.write_api = Mock()
        return db

    def test_store_all_three_metrics(self):
        db = self._connected_db()
        db.store_metrics("dev-01", throughput=1500.0, cycle_time=2.1, error_rate=0.02)
        assert db.write_api.write.call_count == 1
        record = db.write_api.write.call_args.kwargs["record"]
        assert "throughput" in record
        assert "cycle_time" in record
        assert "error_rate" in record

    def test_store_single_metric(self):
        db = self._connected_db()
        db.store_metrics("dev-01", throughput=1000.0)
        record = db.write_api.write.call_args.kwargs["record"]
        assert "throughput" in record
        assert "cycle_time" not in record
        assert "error_rate" not in record

    def test_store_no_metrics_skips_write(self):
        db = self._connected_db()
        db.store_metrics("dev-01")
        db.write_api.write.assert_not_called()

    def test_store_not_connected_is_noop(self):
        db = InfluxDBMetrics()
        db.client = None
        db.store_metrics("dev-01", throughput=1.0)  # should not raise

    def test_store_write_error_is_caught(self):
        db = self._connected_db()
        db.write_api.write.side_effect = Exception("timeout")
        db.store_metrics("dev-01", throughput=1.0)  # should not raise

    def test_store_uses_correct_bucket(self):
        db = self._connected_db()
        db.store_metrics("dev-01", throughput=99.0)
        kwargs = db.write_api.write.call_args.kwargs
        assert kwargs["bucket"] == INFLUXDB_BUCKET
        assert kwargs["org"] == INFLUXDB_ORG

    def test_store_line_protocol_format(self):
        db = self._connected_db()
        db.store_metrics("dev-01", error_rate=0.05)
        record = db.write_api.write.call_args.kwargs["record"]
        assert "device_id=dev-01" in record
        assert "metric_type=error_rate" in record
        assert "value=0.05" in record


# ── get_metrics ───────────────────────────────────────────────────────────────

class TestGetMetrics:
    def _connected_db(self, records=None):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        if records is None:
            db.query_api.query.return_value = []
        else:
            table = Mock()
            table.records = records
            db.query_api.query.return_value = [table]
        return db

    def _make_record(self, ts, value):
        r = Mock()
        r.get_time.return_value = ts
        r.get_value.return_value = value
        return r

    def test_returns_empty_when_not_connected(self):
        db = InfluxDBMetrics()
        db.client = None
        assert db.get_metrics("dev-01") == []

    def test_returns_metrics(self):
        ts = datetime(2025, 6, 5, 12, 0, 0, tzinfo=timezone.utc)
        db = self._connected_db([self._make_record(ts, 1500.0)])
        result = db.get_metrics("dev-01", "throughput")
        assert len(result) == 1
        assert result[0]["value"] == 1500.0
        assert result[0]["metric_type"] == "throughput"
        assert "timestamp" in result[0]

    def test_escapes_device_id_in_query(self):
        db = self._connected_db()
        db.get_metrics('dev"evil', "throughput")
        query = db.query_api.query.call_args.kwargs["query"]
        assert 'dev\\"evil' in query

    def test_escapes_metric_type_in_query(self):
        db = self._connected_db()
        db.get_metrics("dev-01", 'bad"type')
        query = db.query_api.query.call_args.kwargs["query"]
        assert 'bad\\"type' in query

    def test_hours_param_in_query(self):
        db = self._connected_db()
        db.get_metrics("dev-01", hours=48)
        query = db.query_api.query.call_args.kwargs["query"]
        assert "-48h" in query

    def test_query_error_returns_empty(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.side_effect = Exception("flux error")
        assert db.get_metrics("dev-01") == []


# ── get_all_metrics ───────────────────────────────────────────────────────────

class TestGetAllMetrics:
    def test_returns_all_three_keys(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.return_value = []
        result = db.get_all_metrics("dev-01")
        assert set(result.keys()) == {"throughput", "cycle_time", "error_rate"}

    def test_calls_get_metrics_for_each_type(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.return_value = []
        db.get_all_metrics("dev-01", hours=6)
        queries = [call.kwargs["query"] for call in db.query_api.query.call_args_list]
        assert any("throughput" in q for q in queries)
        assert any("cycle_time" in q for q in queries)
        assert any("error_rate" in q for q in queries)


# ── get_latest_metric ─────────────────────────────────────────────────────────

class TestGetLatestMetric:
    def test_returns_none_when_not_connected(self):
        db = InfluxDBMetrics()
        db.client = None
        assert db.get_latest_metric("dev-01", "throughput") is None

    def test_returns_value_when_found(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        record = Mock()
        record.get_value.return_value = 1234.5
        table = Mock()
        table.records = [record]
        db.query_api.query.return_value = [table]
        assert db.get_latest_metric("dev-01", "throughput") == 1234.5

    def test_returns_none_when_no_results(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.return_value = []
        assert db.get_latest_metric("dev-01", "throughput") is None

    def test_escapes_inputs_in_query(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.return_value = []
        db.get_latest_metric('dev"x', 'type"y')
        query = db.query_api.query.call_args.kwargs["query"]
        assert 'dev\\"x' in query
        assert 'type\\"y' in query

    def test_query_error_returns_none(self):
        db = InfluxDBMetrics()
        db.client = Mock()
        db.query_api = Mock()
        db.query_api.query.side_effect = Exception("boom")
        assert db.get_latest_metric("dev-01", "throughput") is None
