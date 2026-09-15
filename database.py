"""
SQLite storage layer. Two tables:
  - telemetry: every raw sensor reading
  - alerts: every rule-triggered event (leak, hygiene, sensor fault)
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "facility.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                location TEXT,
                timestamp TEXT,
                flow_rate REAL,
                flush_event INTEGER,
                occupancy_delta INTEGER,
                heartbeat INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                location TEXT,
                timestamp TEXT,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                resolved INTEGER DEFAULT 0
            )
        """)


def insert_telemetry(reading):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO telemetry
                (sensor_id, location, timestamp, flow_rate, flush_event, occupancy_delta, heartbeat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            reading["sensor_id"], reading["location"], reading["timestamp"],
            reading["flow_rate"], int(reading["flush_event"]),
            reading["occupancy_delta"], int(reading["heartbeat"]),
        ))


def insert_alert(alert):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO alerts (sensor_id, location, timestamp, alert_type, severity, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert["sensor_id"], alert["location"], alert["timestamp"],
            alert["alert_type"], alert["severity"], alert["message"],
        ))


def fetch_recent_alerts(limit=20):
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT timestamp, severity, alert_type, location, sensor_id, message
            FROM alerts ORDER BY id DESC LIMIT ?
        """, (limit,))
        return cur.fetchall()


def fetch_recent_telemetry(limit=20):
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT timestamp, sensor_id, location, flow_rate, flush_event, occupancy_delta, heartbeat
            FROM telemetry ORDER BY id DESC LIMIT ?
        """, (limit,))
        return cur.fetchall()
