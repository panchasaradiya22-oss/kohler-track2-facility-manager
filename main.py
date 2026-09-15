"""
Entry point. Runs the simulation loop:
  simulate telemetry -> store it -> run detection rules -> store + print alerts

Run with:  python main.py
Stop with: Ctrl+C
"""

import time

import config
import database
from simulator import TelemetrySimulator
from detection import DetectionEngine


def run(max_ticks=None):
    database.init_db()
    simulator = TelemetrySimulator()
    engine = DetectionEngine()

    tick = 0
    print("Starting facility monitoring simulation. Press Ctrl+C to stop.\n")

    try:
        while True:
            readings = simulator.step()

            for reading in readings:
                database.insert_telemetry(reading)
                alerts = engine.process_reading(reading)

                for alert in alerts:
                    database.insert_alert(alert)
                    print(
                        f"[{alert['timestamp']}] [{alert['severity']}] "
                        f"{alert['alert_type']} @ {alert['location']} "
                        f"({alert['sensor_id']}): {alert['message']}"
                    )

            tick += 1
            if max_ticks and tick >= max_ticks:
                break

            time.sleep(config.TICK_SECONDS)

    except KeyboardInterrupt:
        print("\nSimulation stopped.")


if __name__ == "__main__":
    run()
