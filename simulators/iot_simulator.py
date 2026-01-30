#!/usr/bin/env python3
"""
IoT Telemetry Data Simulator for Fabric Real-Time Intelligence
Generates realistic IoT sensor data and sends it to Azure Event Hub
"""

import json
import time
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, List
import os
import sys

try:
    from azure.eventhub import EventHubProducerClient, EventData
except ImportError:
    print("Please install azure-eventhub: pip install azure-eventhub")
    sys.exit(1)


class IoTDevice:
    """Simulates an IoT device with realistic sensor readings"""

    def __init__(
        self,
        device_id: str,
        device_type: str,
        location: str,
        latitude: float,
        longitude: float,
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.location = location
        self.latitude = latitude
        self.longitude = longitude

        # Base values for realistic drift
        self.base_temperature = random.uniform(20, 25)
        self.base_humidity = random.uniform(40, 60)
        self.base_pressure = random.uniform(1000, 1020)
        self.base_voltage = random.uniform(220, 240)
        self.base_current = random.uniform(5, 15)

        # Status weights
        self.status_weights = {"healthy": 0.95, "warning": 0.04, "error": 0.01}

    def generate_telemetry(self) -> Dict:
        """Generate a single telemetry reading"""
        # Add realistic variations
        temperature = self.base_temperature + random.gauss(0, 2)
        humidity = self.base_humidity + random.gauss(0, 5)
        pressure = self.base_pressure + random.gauss(0, 2)
        voltage = self.base_voltage + random.gauss(0, 5)
        current = self.base_current + random.gauss(0, 1)

        # Calculate power and energy
        power = voltage * current
        energy_consumed = power / 3600  # Wh per second

        # Determine status
        status = random.choices(
            list(self.status_weights.keys()),
            weights=list(self.status_weights.values()),
            k=1,
        )[0]

        # Occasionally introduce anomalies
        if random.random() < 0.02:  # 2% chance
            temperature += random.choice([-20, 20, 40])  # Temperature spike/drop
        if random.random() < 0.01:  # 1% chance
            voltage += random.choice([-50, 50])  # Voltage anomaly

        telemetry = {
            "eventTime": datetime.now(timezone.utc).isoformat(),
            "deviceId": self.device_id,
            "deviceType": self.device_type,
            "location": self.location,
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2),
            "pressure": round(pressure, 2),
            "voltage": round(voltage, 2),
            "current": round(current, 2),
            "power": round(power, 2),
            "energyConsumed": round(energy_consumed, 4),
            "status": status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "metadata": {
                "firmwareVersion": "1.2.3",
                "protocol": "MQTT",
                "dataFormat": "JSON",
            },
        }

        return telemetry


class IoTSimulator:
    """Main simulator class that manages multiple devices"""

    def __init__(self, connection_string: str = None, num_devices: int = 10):
        self.connection_string = connection_string
        self.devices: List[IoTDevice] = []
        self.num_devices = num_devices
        self.producer = None

        # Initialize producer if connection string provided
        if connection_string:
            try:
                self.producer = EventHubProducerClient.from_connection_string(
                    connection_string
                )
                print(f"Connected to Event Hub")
            except Exception as e:
                print(f"Failed to connect to Event Hub: {e}")
                print("Continuing in console-only mode")

        self._initialize_devices()

    def _initialize_devices(self):
        """Create simulated IoT devices"""
        locations = [
            {"name": "Seattle", "lat": 47.6062, "lon": -122.3321},
            {"name": "New York", "lat": 40.7128, "lon": -74.0060},
            {"name": "London", "lat": 51.5074, "lon": -0.1278},
            {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
            {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
        ]

        device_types = ["Sensor", "Gateway", "Controller", "Monitor"]

        for i in range(self.num_devices):
            location = random.choice(locations)
            device = IoTDevice(
                device_id=f"device-{i+1:03d}",
                device_type=random.choice(device_types),
                location=location["name"],
                latitude=location["lat"] + random.uniform(-0.1, 0.1),
                longitude=location["lon"] + random.uniform(-0.1, 0.1),
            )
            self.devices.append(device)

        print(f"Initialized {len(self.devices)} virtual IoT devices")

    def send_telemetry_batch(self):
        """Generate and send telemetry from all devices"""
        telemetry_batch = []

        for device in self.devices:
            telemetry = device.generate_telemetry()
            telemetry_batch.append(telemetry)

        if self.producer:
            try:
                # Send to Event Hub
                event_data_batch = self.producer.create_batch()
                for telemetry in telemetry_batch:
                    event_data = EventData(json.dumps(telemetry))
                    event_data_batch.add(event_data)

                self.producer.send_batch(event_data_batch)
                print(
                    f"[{datetime.now().isoformat()}] Sent {len(telemetry_batch)} events to Event Hub"
                )
            except Exception as e:
                print(f"Error sending to Event Hub: {e}")
        else:
            # Console output only
            print(f"\n[{datetime.now().isoformat()}] Generated telemetry:")
            for telemetry in telemetry_batch[:3]:  # Show first 3
                print(f"  {telemetry['deviceId']}: Temp={telemetry['temperature']}°C, "
                      f"Humidity={telemetry['humidity']}%, Status={telemetry['status']}")
            if len(telemetry_batch) > 3:
                print(f"  ... and {len(telemetry_batch) - 3} more devices")

        return telemetry_batch

    def run(self, duration: int = 60, interval: int = 1):
        """
        Run the simulator

        Args:
            duration: How long to run in seconds (0 for infinite)
            interval: Seconds between telemetry batches
        """
        print(f"\nStarting IoT Simulator")
        print(f"Devices: {self.num_devices}")
        print(f"Interval: {interval} second(s)")
        print(f"Duration: {'Infinite' if duration == 0 else f'{duration} seconds'}")
        print("-" * 60)

        start_time = time.time()
        iteration = 0

        try:
            while True:
                self.send_telemetry_batch()
                iteration += 1

                # Check if we should stop
                if duration > 0 and (time.time() - start_time) >= duration:
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nSimulator stopped by user")
        finally:
            elapsed = time.time() - start_time
            print(f"\nSimulation Summary:")
            print(f"  Duration: {elapsed:.2f} seconds")
            print(f"  Iterations: {iteration}")
            print(f"  Total Events: {iteration * self.num_devices}")
            print(f"  Events/sec: {(iteration * self.num_devices) / elapsed:.2f}")

            if self.producer:
                self.producer.close()
                print("  Event Hub connection closed")

    def generate_sample_data(self, count: int = 100) -> List[Dict]:
        """Generate sample data without sending to Event Hub"""
        print(f"Generating {count} sample telemetry records...")
        samples = []

        for _ in range(count):
            device = random.choice(self.devices)
            telemetry = device.generate_telemetry()
            samples.append(telemetry)

        return samples


def main():
    parser = argparse.ArgumentParser(
        description="IoT Telemetry Simulator for Fabric Real-Time Intelligence"
    )
    parser.add_argument(
        "--connection-string",
        type=str,
        default=os.environ.get("EVENTHUB_CONNECTION_STRING"),
        help="Event Hub connection string (or set EVENTHUB_CONNECTION_STRING env var)",
    )
    parser.add_argument(
        "--devices",
        type=int,
        default=10,
        help="Number of devices to simulate (default: 10)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (0 for infinite, default: 60)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Seconds between telemetry batches (default: 1)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Generate N sample records to console only (no Event Hub)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save sample data to JSON file",
    )

    args = parser.parse_args()

    # Create simulator
    simulator = IoTSimulator(
        connection_string=args.connection_string, num_devices=args.devices
    )

    if args.sample > 0:
        # Generate sample data only
        samples = simulator.generate_sample_data(args.sample)
        print(f"\nGenerated {len(samples)} samples")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(samples, f, indent=2)
            print(f"Saved to {args.output}")
        else:
            # Print first few samples
            for i, sample in enumerate(samples[:5]):
                print(f"\nSample {i+1}:")
                print(json.dumps(sample, indent=2))
            if len(samples) > 5:
                print(f"\n... and {len(samples) - 5} more samples")
    else:
        # Run simulator
        simulator.run(duration=args.duration, interval=args.interval)


if __name__ == "__main__":
    main()
