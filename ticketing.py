"""
Turns a raw rule-triggered alert into a structured, actionable maintenance
ticket.

Two paths:
  1. LLM path  - an Anthropic API call produces a human-readable diagnosis
                 (likely cause, recommended action, priority reasoning).
  2. Fallback  - a deterministic rules-based generator used when no API key
                 is set or the API call fails. This guarantees the system
                 keeps dispatching tickets under any condition, which matters
                 for a facility platform that can't just stop working.

Set your key before running if you want the LLM path:
    Windows (PowerShell):  $env:ANTHROPIC_API_KEY="sk-ant-..."
    macOS / Linux:         export ANTHROPIC_API_KEY="sk-ant-..."
"""

import json
import os
import re

import config

# --- Static context the model uses to reason about severity ---
FACILITY_CONTEXT = """
Facility: International airport terminal, high footfall (approx. 40,000 passengers/day).
Restroom units are monitored by KOHLER smart sensors reporting water flow,
flush events, occupancy, and a diagnostic heartbeat.
Maintenance teams available: PLUMBING, HOUSEKEEPING, SENSOR_TECH.
Water conservation and passenger experience are both priorities.
""".strip()

SYSTEM_PROMPT = """You are the dispatch intelligence layer of a commercial smart facility \
management platform. You receive a raw sensor alert and convert it into a structured \
maintenance ticket for a facility operations team.

Reason about: how urgent this genuinely is given footfall and water waste, what the most \
likely physical cause is, and which team should handle it.

Respond with ONLY a valid JSON object, no preamble, no markdown fences, with exactly these keys:
{
  "title": "short ticket title, max 10 words",
  "priority_score": integer 1-100 where 100 is most urgent,
  "priority_label": one of "CRITICAL", "HIGH", "MEDIUM", "LOW",
  "likely_cause": "one or two sentences on the most probable physical cause",
  "recommended_action": "one or two sentences of concrete instruction for the technician",
  "assigned_team": one of "PLUMBING", "HOUSEKEEPING", "SENSOR_TECH",
  "est_water_loss_lpd": estimated litres per day lost if unaddressed, number, 0 if not a leak
}"""


def _estimate_water_loss(alert):
    """Pull the flow rate out of the alert text and extrapolate to litres/day."""
    match = re.search(r"([\d.]+)\s*L/min", alert.get("message", ""))
    if not match:
        return 0.0
    return round(float(match.group(1)) * 60 * 24, 1)


def _fallback_ticket(alert):
    """Deterministic ticket generation - no API needed."""
    atype = alert["alert_type"]

    if atype == "LEAK":
        water = _estimate_water_loss(alert)
        return {
            "title": f"Continuous flow detected at {alert['sensor_id']}",
            "priority_score": 90,
            "priority_label": "CRITICAL",
            "likely_cause": "Probable stuck-open flush valve or failed solenoid seal "
                            "causing uninterrupted water flow with no user activity.",
            "recommended_action": "Isolate the supply line to the affected fixture and "
                                  "inspect the flush valve diaphragm. Replace if worn.",
            "assigned_team": "PLUMBING",
            "est_water_loss_lpd": water,
        }

    if atype == "HYGIENE":
        return {
            "title": f"Cleaning threshold exceeded at {alert['sensor_id']}",
            "priority_score": 55,
            "priority_label": "MEDIUM",
            "likely_cause": "Sustained passenger traffic since the last recorded service "
                            "cycle has pushed this unit past its hygiene threshold.",
            "recommended_action": "Dispatch a housekeeping cycle and reset the service "
                                  "counter on completion.",
            "assigned_team": "HOUSEKEEPING",
            "est_water_loss_lpd": 0,
        }

    if atype == "SENSOR_OFFLINE":
        return {
            "title": f"Sensor {alert['sensor_id']} unresponsive",
            "priority_score": 70,
            "priority_label": "HIGH",
            "likely_cause": "Heartbeat loss suggests a power interruption, battery "
                            "depletion, or network dropout at the sensor node.",
            "recommended_action": "Check sensor power and network connectivity on site. "
                                  "Note this unit is unmonitored until restored.",
            "assigned_team": "SENSOR_TECH",
            "est_water_loss_lpd": 0,
        }

    return {
        "title": f"{atype} at {alert['sensor_id']}",
        "priority_score": 20,
        "priority_label": "LOW",
        "likely_cause": "Informational status change reported by the monitoring system.",
        "recommended_action": "No action required. Logged for audit.",
        "assigned_team": "SENSOR_TECH",
        "est_water_loss_lpd": 0,
    }


def _llm_ticket(alert):
    """Ask Claude to diagnose the alert. Returns None if unavailable."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    user_prompt = f"""{FACILITY_CONTEXT}

INCOMING ALERT
Type: {alert['alert_type']}
Raw severity: {alert['severity']}
Location: {alert['location']}
Sensor ID: {alert['sensor_id']}
Timestamp: {alert['timestamp']}
Detail: {alert['message']}

Generate the maintenance ticket JSON."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        # Validate that the model returned everything we need before trusting it.
        required = {"title", "priority_score", "priority_label", "likely_cause",
                    "recommended_action", "assigned_team", "est_water_loss_lpd"}
        if not required.issubset(data.keys()):
            return None
        data["priority_score"] = int(data["priority_score"])
        data["est_water_loss_lpd"] = float(data["est_water_loss_lpd"])
        return data

    except Exception as exc:
        print(f"  [LLM unavailable, using fallback: {type(exc).__name__}]")
        return None


def generate_ticket(alert, alert_id):
    """Build a complete ticket record from an alert. Never raises."""
    enriched = _llm_ticket(alert) if config.USE_LLM else None
    generated_by = "claude-llm" if enriched else "rules-fallback"

    if enriched is None:
        enriched = _fallback_ticket(alert)

    return {
        "alert_id": alert_id,
        "sensor_id": alert["sensor_id"],
        "location": alert["location"],
        "created_at": alert["timestamp"],
        "alert_type": alert["alert_type"],
        "generated_by": generated_by,
        **enriched,
    }
