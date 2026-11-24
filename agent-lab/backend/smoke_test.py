"""Offline checks for the agent's data layer and tools. No Gemini key needed.

Run this before spending tokens: if it fails, the agent is broken before the
model ever sees the question.
"""
import sys

from db import DB_PATH, get_connection, init_db
from tools import TOOL_DECLARATIONS, TOOL_REGISTRY, execute_tool

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label} {detail}".rstrip())
        failures.append(label)


def main() -> int:
    print("Initializing a fresh database...")
    init_db(force=True)

    conn = get_connection()
    client_count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    incident_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    conn.close()

    check("db file created", DB_PATH.exists(), str(DB_PATH))
    check("6 clients seeded", client_count == 6, f"got {client_count}")
    check("11 incidents seeded", incident_count == 11, f"got {incident_count}")

    # Contract integrity: every declaration has an implementation, and vice versa.
    declared = {d["name"] for d in TOOL_DECLARATIONS}
    implemented = set(TOOL_REGISTRY)
    check("declarations match registry", declared == implemented, f"{declared ^ implemented}")

    clients = execute_tool("list_clients", {})
    check("list_clients returns 6", len(clients) == 6, f"got {len(clients)}")
    check("list_clients includes Emirates NBD",
          any(c["name"] == "Emirates NBD" for c in clients))

    snapshot = execute_tool("get_client_snapshot", {"client": "Emirates NBD"})
    check("ENBD snapshot reports SLA breach", snapshot.get("sla_met") is False, str(snapshot))
    check("ENBD snapshot counts 1 open SEV1", snapshot.get("open_sev1_incidents") == 1,
          str(snapshot.get("open_sev1_incidents")))

    case_insensitive = execute_tool("get_client_snapshot", {"client": "emirates nbd"})
    check("client lookup is case-insensitive",
          case_insensitive.get("client") == "Emirates NBD", str(case_insensitive))

    sev1 = execute_tool("get_open_incidents", {"severity": "SEV1"})
    check("2 open SEV1 incidents", sev1.get("count") == 2, str(sev1.get("count")))
    check("SEV1 incidents carry age_hours",
          all("age_hours" in i for i in sev1.get("incidents", [])))

    nordbank = execute_tool("get_open_incidents", {"client": "Nordbank"})
    check("Nordbank has 2 open incidents", nordbank.get("count") == 2, str(nordbank.get("count")))

    resolved_excluded = execute_tool("get_open_incidents", {"client": "SBI"})
    check("resolved incidents are excluded", resolved_excluded.get("count") == 1,
          str(resolved_excluded.get("count")))

    contact = execute_tool("get_escalation_contact", {"client": "SBI"})
    check("SBI escalation owner is Arjun Mehta",
          contact.get("escalation_owner") == "Arjun Mehta", str(contact))

    dubai = execute_tool("get_current_time", {"timezone_name": "Asia/Dubai"})
    check("Dubai timezone offset is +4", dubai.get("utc_offset_hours") == 4, str(dubai))

    # Failure modes must come back as data, not exceptions.
    unknown_client = execute_tool("get_client_snapshot", {"client": "HSBC"})
    check("unknown client returns an error the model can read",
          "error" in unknown_client and "Known clients" in unknown_client["error"],
          str(unknown_client))

    bad_severity = execute_tool("get_open_incidents", {"severity": "SEV9"})
    check("bad severity returns an error", "error" in bad_severity, str(bad_severity))

    unknown_tool = execute_tool("drop_tables", {})
    check("unknown tool is rejected", "error" in unknown_tool, str(unknown_tool))

    missing_arg = execute_tool("get_escalation_contact", {})
    check("missing argument is caught, not raised", "error" in missing_arg, str(missing_arg))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1

    print("All checks passed. Tools are healthy — safe to spend tokens on the agent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
