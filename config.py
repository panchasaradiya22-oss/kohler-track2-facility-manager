"""
Central configuration for the facility monitoring simulation.
Tune these numbers to change how sensitive the detection rules are,
or to add/remove simulated restroom locations.
"""

# --- Sensor / location setup ---
# Each entry represents one restroom unit reporting flow, flush,
# occupancy, and heartbeat telemetry.
SENSORS = [
    {"sensor_id": "R101", "location": "Terminal A - Restroom 1"},
    {"sensor_id": "R102", "location": "Terminal A - Restroom 2"},
    {"sensor_id": "R201", "location": "Terminal B - Restroom 1"},
    {"sensor_id": "R202", "location": "Terminal B - Restroom 2"},
]

# --- Simulation timing ---
TICK_SECONDS = 1          # real seconds between ticks (compressed for demo purposes)
MINUTES_PER_TICK = 1      # each tick represents this many simulated minutes

# --- Detection thresholds ---
LEAK_FLOW_BASELINE = 0.5       # L/min - flow above this with no flush is suspicious
LEAK_DURATION_MINUTES = 5      # sustained high flow for this long -> leak alert

HYGIENE_OCCUPANCY_LIMIT = 40     # cumulative occupancy since last clean before we check
HYGIENE_FLUSH_RATIO_MIN = 0.5    # flush_count / occupancy below this -> under-cleaned

HEARTBEAT_TIMEOUT_MINUTES = 3    # no heartbeat for this long -> sensor considered offline

# --- Anomaly injection probabilities (checked per tick, per sensor, while "normal") ---
P_START_LEAK = 0.01
P_START_DEAD = 0.005
P_START_SPIKE = 0.02

LEAK_DURATION_TICKS = 8

DEAD_DURATION_TICKS = 6
SPIKE_DURATION_TICKS = 5

# --- AI ticket generation ---
# Set USE_LLM = False to run purely on the deterministic fallback generator
# (useful for offline demos or if you don't have an API key handy).
USE_LLM = True
LLM_MODEL = "claude-sonnet-4-6"
