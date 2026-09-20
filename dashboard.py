"""
Live operations dashboard for the smart facility monitoring platform.

Run the ingest pipeline in one terminal:   python main.py
Then run this in a second terminal:        streamlit run dashboard.py

The dashboard reads from facility.db, so it reflects whatever the pipeline
has processed so far and refreshes automatically.
"""

import time

import pandas as pd
import streamlit as st

import database

st.set_page_config(
    page_title="Smart Facility Manager",
    page_icon="💧",
    layout="wide",
)

REFRESH_SECONDS = 5

PRIORITY_COLORS = {
    "CRITICAL": "#d13438",
    "HIGH": "#e8890c",
    "MEDIUM": "#c9a227",
    "LOW": "#4a7c59",
}


def severity_badge(label):
    color = PRIORITY_COLORS.get(label, "#666")
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:10px;font-size:0.75rem;font-weight:600;'>{label}</span>"
    )


# ------------------------------------------------------------------ header
st.title("💧 Commercial Smart Facility & Sustainability Manager")
st.caption("Real-time IoT monitoring, leak detection, and AI-dispatched maintenance")

database.init_db()

with st.sidebar:
    st.header("Controls")
    auto_refresh = st.toggle("Auto-refresh", value=True)
    st.caption(f"Refreshes every {REFRESH_SECONDS}s while the pipeline runs.")
    if st.button("Refresh now"):
        st.rerun()
    st.divider()
    st.caption(
        "Start the ingest pipeline in a separate terminal:\n\n"
        "`python main.py`"
    )

# ------------------------------------------------------------------ KPI row
stats = database.fetch_summary_stats()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Readings ingested", f"{stats['readings']:,}")
k2.metric("Open tickets", stats["open_tickets"])
k3.metric("Leaks detected", stats["leaks_detected"])
k4.metric("Water at risk", f"{stats['water_at_risk_lpd']:,.0f} L/day")

if stats["readings"] == 0:
    st.info(
        "No telemetry yet. Open a second terminal in this folder and run "
        "`python main.py` to start the sensor pipeline, then come back here."
    )
    st.stop()

st.divider()

# ------------------------------------------------------- live sensor status
st.subheader("Live sensor status")

latest = database.fetch_latest_per_sensor()
open_tickets = database.fetch_open_tickets()
sensors_with_issues = {t["sensor_id"]: t for t in open_tickets}

cols = st.columns(max(len(latest), 1))
for col, reading in zip(cols, latest):
    sid = reading["sensor_id"]
    issue = sensors_with_issues.get(sid)

    if not reading["heartbeat"]:
        status, color = "OFFLINE", "#d13438"
    elif issue:
        status, color = "ATTENTION", "#e8890c"
    else:
        status, color = "NORMAL", "#4a7c59"

    with col:
        st.markdown(
            f"""
            <div style='border:1px solid #444;border-left:5px solid {color};
                        border-radius:6px;padding:12px;'>
              <div style='font-weight:700;font-size:1.05rem;'>{sid}</div>
              <div style='font-size:0.8rem;opacity:0.75;'>{reading['location']}</div>
              <div style='margin-top:8px;color:{color};font-weight:700;'>{status}</div>
              <div style='margin-top:6px;font-size:0.8rem;'>
                Flow: {reading['flow_rate']} L/min<br>
                Last seen: {reading['timestamp'][11:]}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# --------------------------------------------------------------- telemetry
st.subheader("Telemetry trends")

rows = database.fetch_telemetry_df_rows(limit=400)
df = pd.DataFrame(rows)
df["timestamp"] = pd.to_datetime(df["timestamp"])

c1, c2 = st.columns(2)

with c1:
    st.caption("Water flow rate by sensor (L/min)")
    flow = df.pivot_table(
        index="timestamp", columns="sensor_id", values="flow_rate", aggfunc="last"
    )
    st.line_chart(flow, height=260)

with c2:
    st.caption("Occupancy by sensor (visitors per interval)")
    occ = df.pivot_table(
        index="timestamp", columns="sensor_id", values="occupancy_delta", aggfunc="last"
    )
    st.line_chart(occ, height=260)

st.divider()

# ----------------------------------------------------------- ticket queue
left, right = st.columns([3, 2])

with left:
    st.subheader("AI-dispatched maintenance queue")
    st.caption("Auto-generated from detected alerts, ranked by urgency.")

    if not open_tickets:
        st.success("No open tickets. All monitored units nominal.")
    else:
        for t in open_tickets:
            with st.container(border=True):
                head_l, head_r = st.columns([4, 1])
                with head_l:
                    st.markdown(
                        f"{severity_badge(t['priority_label'])} "
                        f"&nbsp;**{t['title']}**",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"#{t['id']} · {t['location']} ({t['sensor_id']}) · "
                        f"{t['created_at'][11:]} · score {t['priority_score']} · "
                        f"team {t['assigned_team']} · via {t['generated_by']}"
                    )
                with head_r:
                    if st.button("Resolve", key=f"res_{t['id']}"):
                        database.close_ticket(t["id"])
                        st.rerun()

                st.markdown(f"**Likely cause:** {t['likely_cause']}")
                st.markdown(f"**Recommended action:** {t['recommended_action']}")
                if t["est_water_loss_lpd"]:
                    st.markdown(
                        f"**Projected loss if unaddressed:** "
                        f"{t['est_water_loss_lpd']:,.0f} L/day"
                    )

with right:
    st.subheader("Alert feed")
    alerts = database.fetch_alert_rows(limit=25)
    if not alerts:
        st.caption("No alerts recorded yet.")
    else:
        for a in alerts:
            st.markdown(
                f"`{a['timestamp'][11:]}` **{a['alert_type']}** — "
                f"{a['sensor_id']}  \n"
                f"<span style='font-size:0.8rem;opacity:0.8;'>{a['message']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown("<hr style='margin:6px 0;opacity:0.2;'>", unsafe_allow_html=True)

# --------------------------------------------------------------- refresh
if auto_refresh:
    time.sleep(REFRESH_SECONDS)
    st.rerun()
