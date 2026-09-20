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
        c.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER,
                sensor_id TEXT,
                location TEXT,
                created_at TEXT,
                alert_type TEXT,
                priority_score INTEGER,
                priority_label TEXT,
                title TEXT,
                likely_cause TEXT,
                recommended_action TEXT,
                assigned_team TEXT,
                est_water_loss_lpd REAL,
                generated_by TEXT,
                status TEXT DEFAULT 'OPEN'
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
    """Insert an alert and return its new row id (used to link a ticket to it)."""
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO alerts (sensor_id, location, timestamp, alert_type, severity, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert["sensor_id"], alert["location"], alert["timestamp"],
            alert["alert_type"], alert["severity"], alert["message"],
        ))
        return cur.lastrowid


def insert_ticket(ticket):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO tickets (
                alert_id, sensor_id, location, created_at, alert_type,
                priority_score, priority_label, title, likely_cause,
                recommended_action, assigned_team, est_water_loss_lpd, generated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket["alert_id"], ticket["sensor_id"], ticket["location"],
            ticket["created_at"], ticket["alert_type"], ticket["priority_score"],
            ticket["priority_label"], ticket["title"], ticket["likely_cause"],
            ticket["recommended_action"], ticket["assigned_team"],
            ticket["est_water_loss_lpd"], ticket["generated_by"],
        ))
        return cur.lastrowid


def fetch_open_tickets():
    """Open tickets, highest priority first."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT * FROM tickets WHERE status = 'OPEN'
            ORDER BY priority_score DESC, id DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def fetch_all_tickets():
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM tickets ORDER BY id DESC")
        return [dict(r) for r in cur.fetchall()]


def close_ticket(ticket_id):
    with get_conn() as conn:
        conn.execute("UPDATE tickets SET status = 'RESOLVED' WHERE id = ?", (ticket_id,))


def fetch_telemetry_df_rows(limit=500):
    """Recent telemetry as dicts, oldest-first, for charting."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT * FROM (
                SELECT * FROM telemetry ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def fetch_latest_per_sensor():
    """Most recent reading for each sensor, for the live status grid."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT t.* FROM telemetry t
            INNER JOIN (
                SELECT sensor_id, MAX(id) AS max_id FROM telemetry GROUP BY sensor_id
            ) m ON t.id = m.max_id
            ORDER BY t.sensor_id
        """)
        return [dict(r) for r in cur.fetchall()]


def fetch_alert_rows(limit=50):
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def fetch_summary_stats():
    """Headline numbers for the dashboard KPI row."""
    with get_conn() as conn:
        c = conn.cursor()
        readings = c.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
        open_tickets = c.execute("SELECT COUNT(*) FROM tickets WHERE status='OPEN'").fetchone()[0]
        leaks = c.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='LEAK'").fetchone()[0]
        water = c.execute(
            "SELECT COALESCE(SUM(est_water_loss_lpd), 0) FROM tickets WHERE alert_type='LEAK'"
        ).fetchone()[0]
        return {
            "readings": readings,
            "open_tickets": open_tickets,
            "leaks_detected": leaks,
            "water_at_risk_lpd": round(water, 1),
        }


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
