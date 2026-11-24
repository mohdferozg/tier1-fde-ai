"""Typed tools the agent is allowed to call.

Two objects live here:

1. `TOOL_DECLARATIONS` — the contract the model sees: name, description, and
   JSON-schema parameters. The description is prompt engineering: it tells the
   model *when* to call the tool, not just what it does.
2. `TOOL_REGISTRY` — the Python functions that actually run.

`execute_tool()` is the only bridge between them. It never raises: a bad tool
name, bad arguments, or an exception inside a tool comes back as
`{"error": ...}` so the model can read the failure and correct itself. That is
the difference between an agent and a stack trace.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from db import get_connection, init_db

MAX_ROWS = 20

# zoneinfo needs the IANA database. On a bare Windows box it is often missing,
# so we fall back to fixed offsets for the regions in our seed data.
FALLBACK_UTC_OFFSETS = {
    "UTC": 0,
    "Asia/Dubai": 4,
    "Asia/Kolkata": 5.5,
    "Asia/Kuala_Lumpur": 8,
    "Europe/Berlin": 1,
    "America/New_York": -5,
}


class ToolError(Exception):
    """A tool-level failure the model is allowed to see and recover from."""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def list_clients() -> list[dict]:
    """Return every client deployment with its tier, service, and region."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT name, tier, service, region FROM clients ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_client_snapshot(client: str) -> dict:
    """Return SLA, uptime, deployment date, and open-incident counts for one client."""
    row = _fetch_client(client)
    conn = get_connection()
    counts = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_total,
            SUM(CASE WHEN status = 'open' AND severity = 'SEV1' THEN 1 ELSE 0 END) AS open_sev1
        FROM incidents
        WHERE client = ?
        """,
        (row["name"],),
    ).fetchone()
    conn.close()

    return {
        "client": row["name"],
        "tier": row["tier"],
        "service": row["service"],
        "region": row["region"],
        "deployed_at": row["deployed_at"],
        "uptime_30d_pct": row["uptime_30d"],
        "sla_target_pct": row["sla_target"],
        "sla_met": row["uptime_30d"] >= row["sla_target"],
        "sla_gap_pct": round(row["uptime_30d"] - row["sla_target"], 3),
        "open_incidents": counts["open_total"] or 0,
        "open_sev1_incidents": counts["open_sev1"] or 0,
    }


def get_open_incidents(client: str = "", severity: str = "") -> dict:
    """List open incidents, optionally filtered by client and/or severity."""
    init_db()
    sql = (
        "SELECT id, client, opened_at, severity, summary "
        "FROM incidents WHERE status = 'open'"
    )
    params: list[str] = []

    if client.strip():
        params.append(_fetch_client(client)["name"])
        sql += " AND client = ?"

    if severity.strip():
        params.append(_normalize_severity(severity))
        sql += " AND severity = ?"

    sql += " ORDER BY opened_at ASC"

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    incidents = []
    for row in rows[:MAX_ROWS]:
        opened = datetime.fromisoformat(row["opened_at"])
        incidents.append({
            "incident_id": row["id"],
            "client": row["client"],
            "severity": row["severity"],
            "summary": row["summary"],
            "opened_at": row["opened_at"],
            "age_hours": round((now - opened).total_seconds() / 3600, 1),
        })

    return {"count": len(incidents), "incidents": incidents}


def get_escalation_contact(client: str) -> dict:
    """Return the named escalation owner for a client."""
    row = _fetch_client(client)
    return {
        "client": row["name"],
        "escalation_owner": row["escalation_owner"],
        "email": row["escalation_email"],
        "tier": row["tier"],
    }


def get_current_time(timezone_name: str = "UTC") -> dict:
    """Return the current time in a named IANA timezone."""
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except (ZoneInfoNotFoundError, ValueError):
        if timezone_name not in FALLBACK_UTC_OFFSETS:
            raise ToolError(
                f"Unknown timezone '{timezone_name}'. "
                f"Supported: {', '.join(sorted(FALLBACK_UTC_OFFSETS))}"
            )
        # Build a real tzinfo from the offset. Adding a timedelta to a UTC
        # datetime moves the clock but keeps the +00:00 label, which would
        # report offset 0 for Dubai — right time, wrong answer.
        offset_tz = timezone(timedelta(hours=FALLBACK_UTC_OFFSETS[timezone_name]))
        now = datetime.now(offset_tz)

    offset = now.utcoffset()
    return {
        "timezone": timezone_name,
        "iso_time": now.isoformat(timespec="seconds"),
        "utc_offset_hours": offset.total_seconds() / 3600 if offset is not None else 0,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_client(client: str) -> sqlite3.Row:
    """Resolve a client name case-insensitively, or raise a recoverable error."""
    init_db()
    name = (client or "").strip()
    if not name:
        raise ToolError("client is required.")

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM clients WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()
    known = [r["name"] for r in conn.execute("SELECT name FROM clients ORDER BY name")]
    conn.close()

    if row is None:
        raise ToolError(f"Unknown client '{client}'. Known clients: {', '.join(known)}")
    return row


def _normalize_severity(severity: str) -> str:
    token = severity.strip().upper().replace(" ", "")
    if token in {"SEV1", "S1", "P1", "CRITICAL"}:
        return "SEV1"
    if token in {"SEV2", "S2", "P2", "HIGH"}:
        return "SEV2"
    if token in {"SEV3", "S3", "P3", "MEDIUM", "LOW"}:
        return "SEV3"
    raise ToolError(f"Unknown severity '{severity}'. Use SEV1, SEV2, or SEV3.")



# ---------------------------------------------------------------------------
# Model-facing contract
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    {
        "name": "list_clients",
        "description": (
            "List every customer deployment with its tier (gold/silver/bronze), service, "
            "and region. Call this first when the question refers to clients, tiers, or "
            "'all customers' and you do not already know the exact names."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_client_snapshot",
        "description": (
            "Get one client's SLA status: 30-day uptime, SLA target, whether the SLA is "
            "met, the gap in percentage points, deployment date, and open incident counts. "
            "Use this for any question about SLA, uptime, health, or 'is client X okay'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "client": {"type": "string", "description": "Exact client name, e.g. 'Emirates NBD'."}
            },
            "required": ["client"],
        },
    },
    {
        "name": "get_open_incidents",
        "description": (
            "List open (unresolved) incidents with severity, summary, and how many hours "
            "each has been open. Omit the filters to get every open incident across all "
            "clients. Use this for questions about incidents, outages, breakages, or what "
            "is currently on fire."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "client": {"type": "string", "description": "Optional exact client name."},
                "severity": {"type": "string", "description": "Optional SEV1, SEV2, or SEV3."},
            },
        },
    },
    {
        "name": "get_escalation_contact",
        "description": (
            "Get the named escalation owner and email for a client. Use this whenever the "
            "user asks who to page, notify, or escalate to."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "client": {"type": "string", "description": "Exact client name."}
            },
            "required": ["client"],
        },
    },
    {
        "name": "get_current_time",
        "description": (
            "Get the current date and time in a named IANA timezone. Call this before "
            "reasoning about 'right now', on-call handover, or how long something has been "
            "open in a specific region. Never guess the current time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone_name": {
                    "type": "string",
                    "description": "IANA timezone, e.g. 'UTC', 'Asia/Dubai', 'Europe/Berlin'.",
                }
            },
        },
    },
]


TOOL_REGISTRY = {
    "list_clients": list_clients,
    "get_client_snapshot": get_client_snapshot,
    "get_open_incidents": get_open_incidents,
    "get_escalation_contact": get_escalation_contact,
    "get_current_time": get_current_time,
}


def execute_tool(name: str, args: dict | None = None) -> dict:
    """Run one tool call and always return a JSON-serializable dict.

    Errors are returned, never raised, so the model can observe and recover.
    """
    func = TOOL_REGISTRY.get(name)
    if func is None:
        return {"error": f"Unknown tool '{name}'. Available tools: {', '.join(TOOL_REGISTRY)}"}

    if args is None:
        args = {}
    if not isinstance(args, dict):
        return {"error": f"Arguments for '{name}' must be an object, got {type(args).__name__}."}

    try:
        return func(**args)
    except ToolError as e:
        return {"error": str(e)}
    except TypeError as e:
        return {"error": f"Invalid arguments for '{name}': {e}"}
    except Exception as e:  # tool failures must not kill the agent loop
        return {"error": f"{type(e).__name__} in '{name}': {e}"}


if __name__ == "__main__":
    print(f"Registered tools: {len(TOOL_REGISTRY)}\n")
    for declaration in TOOL_DECLARATIONS:
        params = ", ".join(declaration["parameters"].get("properties", {})) or "(none)"
        print(f"- {declaration['name']}({params})")

    print("\nSample call — get_open_incidents(severity='SEV1'):")
    print(execute_tool("get_open_incidents", {"severity": "SEV1"}))
