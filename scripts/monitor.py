import csv, json, os, time
from datetime import date, datetime

# Monitoring (Stage 6): "trigger -> run -> check", applied to my own search.
# Each run appends one row per check to data/monitoring/monitoring_log.csv, so the
# history of what was caught (or not) is kept. Run it at least twice, a few days apart.
#
# What "something's wrong with my search" means for me:
#   1. no_response      -- an application sent more than NO_RESPONSE_DAYS ago, still no answer
#   2. stale_offers     -- the offer list is older than STALE_DAYS (nobody re-fetched)
#   3. sources_down     -- a data source failed on its last recorded run
#   4. unapplied_targets-- good offers (priority >= TARGET_PRIORITY) I haven't applied to yet

NO_RESPONSE_DAYS = 10
STALE_DAYS = 7
TARGET_PRIORITY = 50

TODAY = date.today()
LOG_PATH = "data/monitoring/monitoring_log.csv"

def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def days_since(iso_text):
    return (TODAY - datetime.fromisoformat(iso_text[:10]).date()).days

def check_no_response(apps):
    late = [a for a in apps if a["status"] == "envoyee" and a["date_sent"]
            and not a["response_date"] and days_since(a["date_sent"]) > NO_RESPONSE_DAYS]
    detail = ", ".join(f"{a['company']} ({days_since(a['date_sent'])} j)" for a in late)
    return len(late) == 0, len(late), detail or "aucune candidature en attente depuis plus de 10 jours"

def check_stale_offers():
    with open("data/offers/jobspy_offers.json", encoding="utf-8") as f:
        age = days_since(json.load(f)["fetched_at"])
    return age <= STALE_DAYS, age, f"offres recuperees il y a {age} jour(s)"

def check_sources(log):
    last = {}
    for row in log:  # keep each source's most recent row
        last[row["source"]] = row
    down = [s for s, r in last.items() if r["status"] != "ok"]
    return len(down) == 0, len(down), ("sources en echec : " + ", ".join(down)) if down else "toutes les sources OK"

def check_unapplied(apps):
    with open("data/offers/matches_all_local.json", encoding="utf-8") as f:
        offers = json.load(f)["offers"]
    applied = {a["offer_id"] for a in apps}
    todo = [o for o in offers if o["priority"] >= TARGET_PRIORITY and o["id"] not in applied]
    detail = ", ".join(o["company"] for o in todo)
    return len(todo) == 0, len(todo), (f"bonnes offres sans candidature : {detail}" if todo else "toutes les bonnes offres ont une candidature")

def main():
    apps = read_csv("data/tracker/applications.csv")
    sources = read_csv("data/pipeline/source_log.csv")
    checks = {
        "no_response": check_no_response(apps),
        "stale_offers": check_stale_offers(),
        "sources_down": check_sources(sources),
        "unapplied_targets": check_unapplied(apps),
    }

    run_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    new_file = not os.path.exists(LOG_PATH)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["run_at", "check", "status", "value", "detail"])
        for name, (ok, value, detail) in checks.items():
            w.writerow([run_at, name, "OK" if ok else "ALERT", value, detail])

    print(f"Monitoring run {run_at}")
    for name, (ok, value, detail) in checks.items():
        print(f"  [{'OK   ' if ok else 'ALERT'}] {name}: {detail}")
    print(f"Appended to {LOG_PATH}")

if __name__ == "__main__":
    main()
