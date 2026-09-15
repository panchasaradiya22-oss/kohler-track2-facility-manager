# Commercial Smart Facility & Sustainability Manager — Day 1

Simulated IoT telemetry + rule-based detection for leaks, hygiene thresholds,
and sensor faults across a set of restroom units (Track 2, KOHLER-MITWPU AI
Research Lab Program).

## What's here

| File | Purpose |
|---|---|
| `config.py` | Sensor list, timing, and detection thresholds — tune everything here |
| `simulator.py` | Generates telemetry each tick, with injected leak/dead/spike anomalies |
| `database.py` | SQLite storage for raw telemetry and triggered alerts |
| `detection.py` | The three detection rules (leak, hygiene, sensor fault) |
| `main.py` | Runs the full loop end-to-end and prints alerts live |
| `view_data.py` | Quick CLI check of what's stored in `facility.db` |

## Requirements

Python 3.8+. No external packages needed — everything used (`sqlite3`,
`random`, `datetime`, `time`) is in the standard library.

## How to run (VS Code)

1. Open this folder in VS Code (`File > Open Folder`)
2. Open a terminal (`` Ctrl+` ``)
3. Run:
   ```
   python main.py
   ```
4. Watch alerts print live as anomalies get injected and detected. Leave it
   running for a minute or two — anomalies are randomly injected, so you
   won't see one on every run instantly.
5. Stop anytime with `Ctrl+C`. A `facility.db` file will now exist in the
   folder with everything that happened.
6. To inspect what got stored:
   ```
   python view_data.py
   ```

## Tuning for your demo

If you want anomalies to show up faster for a live demo, raise the
probabilities in `config.py`:
```python
P_START_LEAK = 0.05
P_START_DEAD = 0.03
P_START_SPIKE = 0.08
```

## What's next (Day 2)

- Build the Streamlit dashboard reading from `facility.db`
- Turn each alert into an auto-generated maintenance ticket (LLM call for
  human-readable priority + recommended action)
- Add a prioritized ticket queue view
