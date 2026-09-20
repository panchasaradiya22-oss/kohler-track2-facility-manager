# Commercial Smart Facility & Sustainability Manager

Real-time IoT monitoring and AI-dispatched maintenance for high-footfall
commercial restroom facilities.
Track 2 — KOHLER-MITWPU AI Research Lab Program.

## The problem

In a facility handling tens of thousands of visitors a day, a single stuck-open
flush valve can waste thousands of litres before anyone notices, and cleaning
schedules run on fixed timers rather than actual usage. This platform monitors
sensor telemetry continuously, detects three failure classes, and automatically
dispatches a prioritised, human-readable maintenance ticket for each one.

## Architecture

```
  simulator.py          detection.py           ticketing.py
  ────────────          ────────────           ────────────
  synthetic      ──▶    rule engine     ──▶    AI diagnosis      ──▶  SQLite
  telemetry             (leak/hygiene/         (cause, action,         │
  + anomalies            sensor fault)          priority, team)        │
                                                    │                  ▼
                                              fallback generator   dashboard.py
                                              (always available)   (Streamlit)
```

**Detection layer** — deterministic rules, so the system is auditable and
never misses a leak because a model hedged.
**Intelligence layer** — an LLM converts each raw trigger into a diagnosis a
technician can act on without interpretation, and assigns a priority score
weighing footfall, water loss, and monitoring blind spots.
**Resilience** — if the API is unreachable, a deterministic generator takes
over and dispatch continues uninterrupted.

## Files

| File | Purpose |
|---|---|
| `config.py` | Sensors, thresholds, anomaly rates, LLM settings |
| `simulator.py` | Generates telemetry with injected leak/dead/spike anomalies |
| `detection.py` | Leak, hygiene, and sensor-fault rules |
| `ticketing.py` | AI ticket generation + deterministic fallback |
| `database.py` | SQLite storage for telemetry, alerts, tickets |
| `main.py` | Ingest pipeline: simulate → detect → dispatch |
| `dashboard.py` | Streamlit operations dashboard |
| `view_data.py` | CLI inspection of stored data |

## Setup

```bash
pip install -r requirements.txt
```

Optional — enable the AI ticket layer:

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

Without a key the system runs on the deterministic fallback generator, and
every ticket is labelled with which path produced it. To disable the LLM path
entirely, set `USE_LLM = False` in `config.py`.

## Running

Two terminals, both in this folder.

**Terminal 1 — ingest pipeline:**
```bash
python main.py
```

**Terminal 2 — dashboard:**
```bash
streamlit run dashboard.py
```

The dashboard opens at `http://localhost:8501` and refreshes every 5 seconds.

To make anomalies appear faster for a demo, raise these in `config.py`:
```python
P_START_LEAK = 0.05
P_START_DEAD = 0.03
P_START_SPIKE = 0.08
```

## Detection rules

| Rule | Trigger | Dispatched to |
|---|---|---|
| Leak | Flow above 0.5 L/min sustained 5 min with no flush event | PLUMBING |
| Hygiene | 40+ visitors since last clean with flush ratio below 0.5 | HOUSEKEEPING |
| Sensor fault | No heartbeat for 3+ min | SENSOR_TECH |

All thresholds are configurable in `config.py`.

## Sustainability impact

Every leak ticket carries a projected litres-per-day loss figure extrapolated
from the measured flow rate, and the dashboard aggregates total water at risk
across all open tickets — turning detection into a quantified conservation
metric rather than just an alert.
