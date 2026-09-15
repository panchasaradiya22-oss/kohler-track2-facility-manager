"""
Generates synthetic sensor telemetry each tick, including occasional
injected anomalies (a stuck leak, a dead sensor, a traffic spike) so the
detection engine has something real to catch.
"""

import random
from datetime import datetime, timedelta

import config


class SensorState:
    """Tracks which simulated 'mode' a sensor is currently in."""

    def __init__(self, sensor_id, location):
        self.sensor_id = sensor_id
        self.location = location
        self.mode = "normal"          # normal | leak | dead | spike
        self.mode_ticks_left = 0

    def maybe_start_anomaly(self):
        if self.mode != "normal":
            return
        r = random.random()
        if r < config.P_START_LEAK:
            self.mode = "leak"
            self.mode_ticks_left = config.LEAK_DURATION_TICKS
        elif r < config.P_START_LEAK + config.P_START_DEAD:
            self.mode = "dead"
            self.mode_ticks_left = config.DEAD_DURATION_TICKS
        elif r < config.P_START_LEAK + config.P_START_DEAD + config.P_START_SPIKE:
            self.mode = "spike"
            self.mode_ticks_left = config.SPIKE_DURATION_TICKS

    def tick_mode(self):
        if self.mode != "normal":
            self.mode_ticks_left -= 1
            if self.mode_ticks_left <= 0:
                self.mode = "normal"


class TelemetrySimulator:
    def __init__(self, sim_start_time=None):
        self.sensors = [SensorState(s["sensor_id"], s["location"]) for s in config.SENSORS]
        self.sim_time = sim_start_time or datetime.now()

    def step(self):
        """Advance simulated time by one tick, return one reading per sensor."""
        self.sim_time += timedelta(minutes=config.MINUTES_PER_TICK)
        readings = []

        for sensor in self.sensors:
            sensor.maybe_start_anomaly()
            ts = self.sim_time.isoformat(timespec="seconds")

            if sensor.mode == "dead":
                reading = {
                    "sensor_id": sensor.sensor_id, "location": sensor.location, "timestamp": ts,
                    "flow_rate": 0.0, "flush_event": False,
                    "occupancy_delta": 0, "heartbeat": False,
                }
            elif sensor.mode == "leak":
                reading = {
                    "sensor_id": sensor.sensor_id, "location": sensor.location, "timestamp": ts,
                    "flow_rate": round(random.uniform(1.5, 3.0), 2),
                    "flush_event": False,
                    "occupancy_delta": random.choice([0, 0, 1]),
                    "heartbeat": True,
                }
            elif sensor.mode == "spike":
                reading = {
                    "sensor_id": sensor.sensor_id, "location": sensor.location, "timestamp": ts,
                    "flow_rate": round(random.uniform(0.1, 0.6), 2),
                    "flush_event": random.random() < 0.6,
                    "occupancy_delta": random.randint(5, 9),
                    "heartbeat": True,
                }
            else:  # normal
                reading = {
                    "sensor_id": sensor.sensor_id, "location": sensor.location, "timestamp": ts,
                    "flow_rate": round(random.uniform(0.0, 0.4), 2),
                    "flush_event": random.random() < 0.25,
                    "occupancy_delta": random.randint(0, 2),
                    "heartbeat": True,
                }

            sensor.tick_mode()
            readings.append(reading)

        return readings
