"""SQLite data layer for the Delivery Ops Agent.

The agent never writes SQL. It calls typed tools (see tools.py), and those
tools read from this small seeded database. Keeping the data local makes the
agent reproducible and runnable offline — no Supabase, no network.

Schema:
    clients   — one row per customer deployment (tier, SLA, escalation owner)
    incidents — one row per incident, with severity and status
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("AGENT_DB_PATH") or Path(__file__).with_name("agent_lab.db"))

# name, tier, service, region, deployed_at, uptime_30d, sla_target, owner, email
CLIENTS = [
    ("PNC Bank", "gold", "Payments Portal", "USA", "2025-03-14", 99.97, 99.95,
     "Priya Nair", "priya.nair@example.com"),
    ("Emirates NBD", "gold", "Onboarding KYC", "UAE", "2025-01-08", 99.82, 99.90,
     "Omar Haddad", "omar.haddad@example.com"),
    ("SBI", "gold", "Loan Origination", "India", "2024-11-20", 99.91, 99.90,
     "Arjun Mehta", "arjun.mehta@example.com"),
    ("Maybank", "silver", "Mobile Wallet", "Malaysia", "2026-06-02", 99.61, 99.50,
     "Wei Ling Tan", "weiling.tan@example.com"),
    ("Nordbank", "silver", "Fraud Screening", "Germany", "2026-02-17", 99.34, 99.50,
     "Lena Fischer", "lena.fischer@example.com"),
    ("Axiata", "bronze", "Data Lakehouse", "Malaysia", "2026-08-05", 98.90, 99.00,
     "Ravi Kumar", "ravi.kumar@example.com"),
]

# client, hours_ago_opened, severity, status, summary
INCIDENTS = [
    ("Emirates NBD", 6, "SEV1", "open", "KYC document upload times out for 12% of requests"),
    ("Nordbank", 2, "SEV1", "open", "Fraud scoring p95 latency above 2s"),
    ("Emirates NBD", 30, "SEV2", "open", "OCR queue backlog above alert threshold"),
    ("Nordbank", 52, "SEV2", "open", "Model retraining pipeline stalled since Friday"),
    ("SBI", 18, "SEV2", "open", "Loan export job fails on retry after 3 attempts"),
    ("Axiata", 8, "SEV2", "open", "Partition skew on the ingest pipeline"),
    ("Maybank", 96, "SEV3", "open", "Tamil localisation strings missing in wallet UI"),
    ("PNC Bank", 120, "SEV3", "open", "Help-centre docs link returns 404"),
    ("PNC Bank", 200, "SEV2", "resolved", "CSV export truncated above 50k rows"),
    ("SBI", 400, "SEV1", "resolved", "SSO users could not log in"),
    ("Maybank", 720, "SEV3", "resolved", "Push notifications duplicated"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    name             TEXT PRIMARY KEY,
    tier             TEXT NOT NULL,
    service          TEXT NOT NULL,
    region           TEXT NOT NULL,
    deployed_at      TEXT NOT NULL,
    uptime_30d       REAL NOT NULL,
    sla_target       REAL NOT NULL,
    escalation_owner TEXT NOT NULL,
    escalation_email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client     TEXT NOT NULL REFERENCES clients(name),
    opened_at  TEXT NOT NULL,
    severity   TEXT NOT NULL,
    status     TEXT NOT NULL,
    summary    TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection with dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force: bool = False) -> Path:
    """Create and seed the database if it does not exist yet.

    Args:
        force: Drop existing tables and re-seed. Used by tests.

    Returns:
        The path to the SQLite file.
    """
    if DB_PATH.exists() and not force:
        return DB_PATH

    now = datetime.now(timezone.utc)

    conn = get_connection()
    cur = conn.cursor()
    if force:
        cur.executescript("DROP TABLE IF EXISTS incidents; DROP TABLE IF EXISTS clients;")
    cur.executescript(SCHEMA)

    cur.executemany(
        "INSERT INTO clients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        CLIENTS,
    )
    cur.executemany(
        "INSERT INTO incidents (client, opened_at, severity, status, summary) VALUES (?, ?, ?, ?, ?)",
        [
            (
                client,
                (now - timedelta(hours=hours_ago)).isoformat(timespec="seconds"),
                severity,
                status,
                summary,
            )
            for client, hours_ago, severity, status, summary in INCIDENTS
        ],
    )

    conn.commit()
    cur.close()
    conn.close()
    return DB_PATH


if __name__ == "__main__":
    path = init_db()
    conn = get_connection()
    client_count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    incident_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    open_sev1 = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'open' AND severity = 'SEV1'"
    ).fetchone()[0]
    conn.close()

    print(f"Database: {path}")
    print(f"Clients: {client_count}")
    print(f"Incidents: {incident_count} ({open_sev1} open SEV1)")
