"""Reproducible API demonstration using actual persisted results."""
import argparse
from datetime import datetime, timezone
import json
import time
import urllib.error
import urllib.request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--mode", choices=["simulation", "nasa"], default="simulation")
    p.add_argument("--keep-running", action="store_true")
    args = p.parse_args()

    def call(path, body=None, method="GET"):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(args.url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    call("/api/replay/stop", method="POST")
    started_at = datetime.now(timezone.utc)
    try:
        if args.mode == "simulation":
            call("/api/simulation/start", {"seed": 42, "machine_count": 20}, "POST")
            machine = "sim-01"
            print("Simulation SYNTHETIQUE : 20 machines, 3 cycles nominaux", flush=True)
            time.sleep(6)
            call(f"/api/simulation/{machine}/scenario", {"scenario": "degradation"}, "POST")
        else:
            ds = call("/api/datasets")
            trial = next(t for t in ds["nasa_ims"]["trials"] if t["trial"] == "2nd_test")
            nasa_start = max(0, trial["files"] - 30)
            call("/api/replay/start", {"trial": "2nd_test", "channel": 1, "speed": 60,
                 "start_index": nasa_start}, "POST")
            machine = "nasa-2nd_test-ch1"
            print("NASA : derniers fichiers REELS de l'essai 2 ; temps historique accelere x60", flush=True)
        deadline = time.monotonic() + 100
        alert = None
        while time.monotonic() < deadline:
            status_filter = "&status=open" if args.mode == "simulation" else ""
            result = call(f"/api/alerts?mode={args.mode}&machine_id={machine}{status_filter}")
            fresh = [a for a in result["items"] if not a["resolved_at"] and datetime.fromisoformat(a["created_at"]) >= started_at]
            if args.mode == "nasa" and call("/api/engine").get("cursor", 0) >= nasa_start + 3:
                fresh = [a for a in result["items"] if not a["resolved_at"]]
            if fresh:
                alert = fresh[0]
                break
            time.sleep(1)
        if alert is None:
            raise RuntimeError("Aucune alerte dans le delai. Examiner les seuils et journaux, sans inventer de resultat.")
        call(f"/api/alerts/{alert['id']}/acknowledge", method="POST")
        event = call("/api/maintenance", {"machine_id": machine, "reason": "Inspection de demonstration",
                     "priority": "high", "comments": "Creee automatiquement par scripts.demo"}, "POST")
        print(json.dumps({"alert_id": alert["id"], "reused_existing_alert": datetime.fromisoformat(alert["created_at"]) < started_at, "triggered_values": alert["triggered_values"],
                          "maintenance_id": event["id"]}, indent=2), flush=True)
        if args.mode == "simulation":
            call(f"/api/simulation/{machine}/scenario", {"scenario": "maintenance"}, "POST")
            time.sleep(6)
            call(f"/api/maintenance/{event['id']}", {"status": "completed", "comments": "Maintenance fictive terminee"}, "PATCH")
            call(f"/api/simulation/{machine}/scenario", {"scenario": "recovery"}, "POST")
        print("Historique et intervention conserves dans SQLite.", flush=True)
    finally:
        if not args.keep_running:
            call("/api/replay/stop", method="POST")


if __name__ == "__main__":
    main()
