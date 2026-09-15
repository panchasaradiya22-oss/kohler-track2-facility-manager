"""
Rule-based detection engine. Keeps a small rolling state per sensor and
evaluates three rules on every new reading:
  1. Leak        - sustained high flow with no flush event
  2. Hygiene      - too little cleaning relative to foot traffic
  3. Sensor fault - heartbeat has gone silent for too long
"""

from datetime import datetime

import config


class SensorDetectionState:
    def __init__(self, sensor_id, location):
        self.sensor_id = sensor_id
        self.location = location

        self.high_flow_streak_minutes = 0
        self.leak_alert_active = False

        self.occupancy_since_clean = 0
        self.flush_since_clean = 0
        self.hygiene_alert_active = False

        self.last_heartbeat_time = None
        self.offline_alert_active = False


class DetectionEngine:
    def __init__(self):
        self.state = {
            s["sensor_id"]: SensorDetectionState(s["sensor_id"], s["location"])
            for s in config.SENSORS
        }

    def process_reading(self, reading):
        """Evaluate all rules for one reading. Returns a list of new alert dicts."""
        st = self.state[reading["sensor_id"]]
        ts = reading["timestamp"]
        alerts = []

        # --- Rule 1: Leak detection ---
        if reading["flow_rate"] > config.LEAK_FLOW_BASELINE and not reading["flush_event"]:
            st.high_flow_streak_minutes += config.MINUTES_PER_TICK
        else:
            st.high_flow_streak_minutes = 0
            st.leak_alert_active = False

        if st.high_flow_streak_minutes >= config.LEAK_DURATION_MINUTES and not st.leak_alert_active:
            st.leak_alert_active = True
            alerts.append(self._make_alert(
                st, ts, "LEAK", "HIGH",
                f"Continuous flow of {reading['flow_rate']} L/min for "
                f"{st.high_flow_streak_minutes} min with no flush event."
            ))

        # --- Rule 2: Hygiene threshold ---
        st.occupancy_since_clean += reading["occupancy_delta"]
        if reading["flush_event"]:
            st.flush_since_clean += 1

        if st.occupancy_since_clean >= config.HYGIENE_OCCUPANCY_LIMIT:
            ratio = (st.flush_since_clean / st.occupancy_since_clean) if st.occupancy_since_clean else 1
            if ratio < config.HYGIENE_FLUSH_RATIO_MIN and not st.hygiene_alert_active:
                st.hygiene_alert_active = True
                alerts.append(self._make_alert(
                    st, ts, "HYGIENE", "MEDIUM",
                    f"{st.occupancy_since_clean} visitors since last clean, "
                    f"flush ratio {ratio:.2f} below threshold. Cleaning recommended."
                ))

        # --- Rule 3: Sensor fault / offline ---
        if reading["heartbeat"]:
            st.last_heartbeat_time = datetime.fromisoformat(ts)
            if st.offline_alert_active:
                st.offline_alert_active = False
                alerts.append(self._make_alert(
                    st, ts, "SENSOR_RECOVERED", "LOW",
                    "Sensor heartbeat resumed; sensor back online."
                ))
        else:
            if st.last_heartbeat_time:
                gap_minutes = (datetime.fromisoformat(ts) - st.last_heartbeat_time).total_seconds() / 60
            else:
                gap_minutes = config.HEARTBEAT_TIMEOUT_MINUTES + 1  # never seen a heartbeat yet

            if gap_minutes >= config.HEARTBEAT_TIMEOUT_MINUTES and not st.offline_alert_active:
                st.offline_alert_active = True
                alerts.append(self._make_alert(
                    st, ts, "SENSOR_OFFLINE", "HIGH",
                    f"No heartbeat received for {gap_minutes:.0f} min."
                ))

        return alerts

    def reset_hygiene(self, sensor_id):
        """Call once a cleaning ticket is marked done, to reset the counters."""
        st = self.state[sensor_id]
        st.occupancy_since_clean = 0
        st.flush_since_clean = 0
        st.hygiene_alert_active = False

    @staticmethod
    def _make_alert(st, ts, alert_type, severity, message):
        return {
            "sensor_id": st.sensor_id,
            "location": st.location,
            "timestamp": ts,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
        }
