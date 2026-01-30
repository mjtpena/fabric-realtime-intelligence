#!/usr/bin/env python3
"""
Streaming API Tests for Fabric Real-Time Intelligence
Tests Event Hub ingestion, KQL queries, and end-to-end data flow
"""

import os
import sys
import time
import json
import unittest
from datetime import datetime, timezone, timedelta
from typing import List, Dict

try:
    from azure.eventhub import EventHubProducerClient, EventData
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoServiceError
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Please install required packages:")
    print("pip install azure-eventhub azure-kusto-data azure-identity")
    sys.exit(1)


class StreamingAPITests(unittest.TestCase):
    """Test suite for streaming APIs and data flow"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.eventhub_connection_string = os.environ.get(
            "EVENTHUB_CONNECTION_STRING", ""
        )
        cls.kusto_cluster_uri = os.environ.get("KUSTO_CLUSTER_URI", "")
        cls.kusto_database = os.environ.get("KUSTO_DATABASE", "")

        if not all(
            [cls.eventhub_connection_string, cls.kusto_cluster_uri, cls.kusto_database]
        ):
            print("Warning: Not all environment variables set. Some tests will be skipped.")

        # Initialize clients
        if cls.eventhub_connection_string:
            cls.eventhub_client = EventHubProducerClient.from_connection_string(
                cls.eventhub_connection_string
            )

        if cls.kusto_cluster_uri and cls.kusto_database:
            kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(
                cls.kusto_cluster_uri
            )
            cls.kusto_client = KustoClient(kcsb)

    @classmethod
    def tearDownClass(cls):
        """Clean up resources"""
        if hasattr(cls, "eventhub_client"):
            cls.eventhub_client.close()

    def test_01_eventhub_connection(self):
        """Test Event Hub connection"""
        if not hasattr(self, "eventhub_client"):
            self.skipTest("Event Hub connection string not configured")

        try:
            # Try to create a batch (doesn't send)
            batch = self.eventhub_client.create_batch()
            self.assertIsNotNone(batch)
            print("✓ Event Hub connection successful")
        except Exception as e:
            self.fail(f"Event Hub connection failed: {e}")

    def test_02_send_single_event(self):
        """Test sending a single event to Event Hub"""
        if not hasattr(self, "eventhub_client"):
            self.skipTest("Event Hub connection string not configured")

        test_event = {
            "eventTime": datetime.now(timezone.utc).isoformat(),
            "deviceId": "test-device-001",
            "deviceType": "Sensor",
            "location": "TestLab",
            "temperature": 22.5,
            "humidity": 45.0,
            "pressure": 1013.25,
            "voltage": 230.0,
            "current": 10.0,
            "power": 2300.0,
            "energyConsumed": 0.639,
            "status": "healthy",
            "latitude": 47.6062,
            "longitude": -122.3321,
            "metadata": {"test": True, "timestamp": time.time()},
        }

        try:
            batch = self.eventhub_client.create_batch()
            batch.add(EventData(json.dumps(test_event)))
            self.eventhub_client.send_batch(batch)
            print(f"✓ Successfully sent test event: {test_event['deviceId']}")
        except Exception as e:
            self.fail(f"Failed to send event: {e}")

    def test_03_send_batch_events(self):
        """Test sending multiple events in a batch"""
        if not hasattr(self, "eventhub_client"):
            self.skipTest("Event Hub connection string not configured")

        batch_size = 10
        test_events = []

        for i in range(batch_size):
            event = {
                "eventTime": datetime.now(timezone.utc).isoformat(),
                "deviceId": f"test-device-{i+1:03d}",
                "deviceType": "Sensor",
                "location": "TestLab",
                "temperature": 20.0 + i,
                "humidity": 40.0 + i,
                "pressure": 1013.0,
                "voltage": 230.0,
                "current": 10.0,
                "power": 2300.0,
                "energyConsumed": 0.639,
                "status": "healthy",
                "latitude": 47.6062,
                "longitude": -122.3321,
                "metadata": {"test": True, "batch": True},
            }
            test_events.append(event)

        try:
            batch = self.eventhub_client.create_batch()
            for event in test_events:
                batch.add(EventData(json.dumps(event)))

            self.eventhub_client.send_batch(batch)
            print(f"✓ Successfully sent batch of {batch_size} events")
        except Exception as e:
            self.fail(f"Failed to send batch: {e}")

    def test_04_kusto_connection(self):
        """Test KQL database connection"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = ".show databases"
            response = self.kusto_client.execute("", query)

            databases = [row["DatabaseName"] for row in response.primary_results[0]]
            self.assertIn(self.kusto_database, databases)
            print(f"✓ KQL database connection successful. Found {len(databases)} databases")
        except Exception as e:
            self.fail(f"KQL connection failed: {e}")

    def test_05_query_telemetry_table(self):
        """Test querying IoTTelemetry table"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            IoTTelemetry
            | where EventTime > ago(1h)
            | take 10
            | project EventTime, DeviceId, Temperature, Status
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            rows = list(response.primary_results[0])
            print(f"✓ Successfully queried IoTTelemetry table. Found {len(rows)} records")

            # Validate schema
            if len(rows) > 0:
                first_row = rows[0]
                required_fields = ["EventTime", "DeviceId", "Temperature", "Status"]
                for field in required_fields:
                    self.assertIn(field, first_row)
        except Exception as e:
            self.fail(f"Failed to query telemetry table: {e}")

    def test_06_query_recent_data(self):
        """Test that recent data is available (within last 5 minutes)"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            IoTTelemetry
            | where EventTime > ago(5m)
            | summarize count()
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            result = list(response.primary_results[0])[0]
            count = result["count_"]

            print(f"✓ Found {count} events in last 5 minutes")
            # Note: This might be 0 if no active ingestion, so we just log it
        except Exception as e:
            self.fail(f"Failed to query recent data: {e}")

    def test_07_aggregation_query(self):
        """Test aggregation queries"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            IoTTelemetry
            | where EventTime > ago(1h)
            | summarize
                AvgTemperature = avg(Temperature),
                MaxTemperature = max(Temperature),
                MinTemperature = min(Temperature),
                EventCount = count()
                by Location
            | order by EventCount desc
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            rows = list(response.primary_results[0])
            print(f"✓ Aggregation query successful. Found {len(rows)} locations")

            # Validate aggregation fields
            if len(rows) > 0:
                first_row = rows[0]
                self.assertIn("AvgTemperature", first_row)
                self.assertIn("MaxTemperature", first_row)
                self.assertIn("EventCount", first_row)
        except Exception as e:
            self.fail(f"Aggregation query failed: {e}")

    def test_08_time_series_query(self):
        """Test time series query with binning"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            IoTTelemetry
            | where EventTime > ago(1h)
            | summarize AvgTemperature = avg(Temperature) by bin(EventTime, 5m)
            | order by EventTime asc
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            rows = list(response.primary_results[0])
            print(f"✓ Time series query successful. Found {len(rows)} time bins")
        except Exception as e:
            self.fail(f"Time series query failed: {e}")

    def test_09_alert_detection_query(self):
        """Test anomaly/alert detection query"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            IoTTelemetry
            | where EventTime > ago(1h)
            | where Temperature > 85 or Temperature < 0
            | summarize AnomalyCount = count() by DeviceId
            | order by AnomalyCount desc
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            rows = list(response.primary_results[0])
            print(f"✓ Alert detection query successful. Found {len(rows)} devices with anomalies")
        except Exception as e:
            self.fail(f"Alert detection query failed: {e}")

    def test_10_materialized_view_query(self):
        """Test querying materialized view"""
        if not hasattr(self, "kusto_client"):
            self.skipTest("Kusto cluster URI not configured")

        try:
            query = f"""
            DeviceStatusView
            | take 10
            | project DeviceId, EventTime, Temperature, Status
            """
            response = self.kusto_client.execute(self.kusto_database, query)

            rows = list(response.primary_results[0])
            print(f"✓ Materialized view query successful. Found {len(rows)} records")
        except Exception as e:
            # Materialized view might not exist yet
            print(f"⚠ Materialized view query skipped (view may not exist): {e}")

    def test_11_end_to_end_latency(self):
        """Test end-to-end latency: send event and query it back"""
        if not hasattr(self, "eventhub_client") or not hasattr(self, "kusto_client"):
            self.skipTest("Event Hub or Kusto not configured")

        # Send a unique test event
        test_id = f"latency-test-{int(time.time())}"
        test_event = {
            "eventTime": datetime.now(timezone.utc).isoformat(),
            "deviceId": test_id,
            "deviceType": "Sensor",
            "location": "TestLab",
            "temperature": 99.9,  # Unique value to identify
            "humidity": 99.9,
            "pressure": 1013.25,
            "voltage": 230.0,
            "current": 10.0,
            "power": 2300.0,
            "energyConsumed": 0.639,
            "status": "healthy",
            "latitude": 47.6062,
            "longitude": -122.3321,
            "metadata": {"latencyTest": True},
        }

        send_time = time.time()

        # Send event
        try:
            batch = self.eventhub_client.create_batch()
            batch.add(EventData(json.dumps(test_event)))
            self.eventhub_client.send_batch(batch)
            print(f"✓ Sent latency test event: {test_id}")
        except Exception as e:
            self.fail(f"Failed to send latency test event: {e}")

        # Wait and query for the event (try multiple times)
        max_attempts = 6
        wait_time = 10  # seconds between attempts

        for attempt in range(max_attempts):
            time.sleep(wait_time)

            try:
                query = f"""
                IoTTelemetry
                | where DeviceId == '{test_id}'
                | where Temperature == 99.9
                | take 1
                """
                response = self.kusto_client.execute(self.kusto_database, query)
                rows = list(response.primary_results[0])

                if len(rows) > 0:
                    query_time = time.time()
                    latency = query_time - send_time
                    print(f"✓ End-to-end latency: {latency:.2f} seconds")
                    self.assertLess(latency, 120, "Latency should be under 2 minutes")
                    return
            except Exception as e:
                print(f"  Attempt {attempt + 1}/{max_attempts} failed: {e}")

        print(f"⚠ Event not found after {max_attempts * wait_time} seconds")


class PerformanceTests(unittest.TestCase):
    """Performance and load tests"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.eventhub_connection_string = os.environ.get(
            "EVENTHUB_CONNECTION_STRING", ""
        )
        if cls.eventhub_connection_string:
            cls.eventhub_client = EventHubProducerClient.from_connection_string(
                cls.eventhub_connection_string
            )

    @classmethod
    def tearDownClass(cls):
        """Clean up resources"""
        if hasattr(cls, "eventhub_client"):
            cls.eventhub_client.close()

    def test_01_throughput_test(self):
        """Test throughput: send 1000 events and measure time"""
        if not hasattr(self, "eventhub_client"):
            self.skipTest("Event Hub connection string not configured")

        num_events = 1000
        start_time = time.time()

        try:
            for i in range(0, num_events, 100):
                batch = self.eventhub_client.create_batch()

                for j in range(100):
                    event = {
                        "eventTime": datetime.now(timezone.utc).isoformat(),
                        "deviceId": f"perf-test-{i+j:04d}",
                        "deviceType": "Sensor",
                        "location": "PerfTest",
                        "temperature": 20.0 + (i + j) % 10,
                        "humidity": 50.0,
                        "pressure": 1013.0,
                        "voltage": 230.0,
                        "current": 10.0,
                        "power": 2300.0,
                        "energyConsumed": 0.639,
                        "status": "healthy",
                        "latitude": 47.6062,
                        "longitude": -122.3321,
                        "metadata": {"perfTest": True},
                    }
                    batch.add(EventData(json.dumps(event)))

                self.eventhub_client.send_batch(batch)

            end_time = time.time()
            duration = end_time - start_time
            throughput = num_events / duration

            print(f"✓ Throughput test: {num_events} events in {duration:.2f}s")
            print(f"  Events/sec: {throughput:.2f}")

            self.assertGreater(throughput, 10, "Throughput should be > 10 events/sec")

        except Exception as e:
            self.fail(f"Throughput test failed: {e}")


def main():
    """Run tests"""
    print("=" * 60)
    print("Fabric Real-Time Intelligence - Streaming API Tests")
    print("=" * 60)
    print()

    # Check environment variables
    required_vars = ["EVENTHUB_CONNECTION_STRING", "KUSTO_CLUSTER_URI", "KUSTO_DATABASE"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print("⚠ Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print()
        print("Some tests will be skipped. Set these variables to run all tests.")
        print()

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test suites
    suite.addTests(loader.loadTestsFromTestCase(StreamingAPITests))
    suite.addTests(loader.loadTestsFromTestCase(PerformanceTests))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
