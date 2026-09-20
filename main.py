"""
Entry point. Runs the simulation loop:
  simulate telemetry -> store it -> run detection rules -> store + print alerts

Run with:  python main.py
Stop with: Ctrl+C
"""

import time

import config
import database
import ticketing
from simulator import TelemetrySimulator
from detection import DetectionEngine

# Alert types that warrant sending someone out. Everything else is logged only.
DISPATCHABLE = {"LEAK", "HYGIENE", "SENSOR_OFFLINE"}


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
                    alert_id = database.insert_alert(alert)
                    print(
                        f"[{alert['timestamp']}] [{alert['severity']}] "
                        f"{alert['alert_type']} @ {alert['location']} "
                        f"({alert['sensor_id']}): {alert['message']}"
                    )

                    # Recovery notices are informational - log them, but don't
                    # dispatch a technician for them.
                    if alert["alert_type"] not in DISPATCHABLE:
                        continue

                    # Auto-dispatch: turn the raw alert into an actionable ticket
                    ticket = ticketing.generate_ticket(alert, alert_id)
                    database.insert_ticket(ticket)
                    print(
                        f"    -> TICKET [{ticket['priority_label']} "
                        f"{ticket['priority_score']}] {ticket['title']}\n"
                        f"       Team: {ticket['assigned_team']} | "
                        f"via {ticket['generated_by']}\n"
                        f"       Action: {ticket['recommended_action']}"
                    )

            tick += 1
            if max_ticks and tick >= max_ticks:
                break

            time.sleep(config.TICK_SECONDS)

    except KeyboardInterrupt:
        print("\nSimulation stopped.")


if __name__ == "__main__":
    run()
