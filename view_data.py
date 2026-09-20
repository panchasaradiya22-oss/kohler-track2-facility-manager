"""
Quick way to peek at what's in facility.db without a full dashboard.
Run with: python view_data.py
"""

import database

print("=== Last 10 alerts ===")
for row in database.fetch_recent_alerts(10):
    print(row)

print("\n=== Last 10 telemetry readings ===")
for row in database.fetch_recent_telemetry(10):
    print(row)
