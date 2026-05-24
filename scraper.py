#!/usr/bin/env python3
import requests, json, re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

def now_utc():
    return datetime.now(timezone.utc).strftime("%H:%M UTC")

def trim(v, n):
    return str(v)[:n] if v else ""

def espn_sport(sport_label, url, event_label=""):
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        events = data.get("events", [])
        print(f"  [{sport_label}] {len(events)} events from ESPN")
        for e in events:
            if len(out) >= 5: break
            comps = e.get("competitions", [])
            if not comps: continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2: continue
            status = e.get("status", {})
            state = status.get("type", {}).get("state", "")
            print(f"    {e.get('name','?')} state={state}")
            if state != "in": continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            def name(c):
                t = c.get("team", {})
                return trim(t.get("shortDisplayName") or t.get("abbreviation") or t.get("displayName","?"), 14)
            out.append({
                "sport": sport_label,
                "home": name(home), "away": name(away),
                "scoreHome": str(home.get("score","0") or "0"),
                "scoreAway": str(away.get("score","0") or "0"),
                "phase": trim(status.get("displayClock") or status.get("type",{}).get("shortDetail","Live"), 12),
                "event": event_label,
                "updated": now_utc()
            })
    except Exception as ex:
        print(f"  [{sport_label}] ERROR: {ex}")
    return out

def football():
    results = []
    for slug, label in [("eng.1","EPL"),("esp.1","La Liga"),("ger.1","Bundesliga"),("ita.1","Serie A"),("fra.1","Ligue 1"),("uefa.champions","UCL")]:
        if len(results) >= 5: break
        results += espn_sport("Football", f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard", label)
    return results[:5]

def afl():
    return espn_sport("AFL", "https://site.api.espn.com/apis/site/v2/sports/australian-football/afl/scoreboard", "AFL")[:5]

def tennis():
    out = []
    try:
        # Use livescore.com unofficial JSON feed
        r = requests.get(
            "https://www.livescore.com/en/tennis/",
            headers={**HEADERS, "Referer": "https://www.livescore.com/"},
            timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")
        # Try to find embedded JSON data
        scripts = soup.find_all("script")
        for s in scripts:
            text = s.string or ""
            if "Roland" in text or "roland" in text or "ATP" in text:
                print(f"  [Tennis] Found ATP script len={len(text)}")
                # Try extract JSON
                m = re.search(r'"events"\s*:\s*(\[.*?\])', text, re.DOTALL)
                if m:
                    print(f"  [Tennis] Found events JSON")
                break

        # Try direct livescore API
        r2 = requests.get(
            "https://prod-cdn-public-api.livescore.com/v1/api/app/date/tennis/20260524/0?MD=1",
            headers={**HEADERS,
                     "origin": "https://www.livescore.com",
                     "referer": "https://www.livescore.com/"},
            timeout=15
        )
        print(f"  [Tennis] livescore.com API HTTP {r2.status_code} size={len(r2.content)}")
        if r2.status_code == 200:
            data = r2.json()
            stages = data.get("Stages", [])
            print(f"  [Tennis] {len(stages)} stages")
            for stage in stages:
                events = stage.get("Events", [])
                for e in events:
                    if len(out) >= 5: break
                    # Eps = status: 1=not started, 2=live, 3=finished
                    if e.get("Eps") != "2": continue
                    home = trim(e.get("T1",[{}])[0].get("Nm","P1").split()[-1], 14)
                    away = trim(e.get("T2",[{}])[0].get("Nm","P2").split()[-1], 14)
                    sh = str(e.get("Tr1","0"))
                    sa = str(e.get("Tr2","0"))
                    phase = trim(e.get("Stg","Live"), 12)
                    comp_name = trim(stage.get("Cnm","Roland Garros"), 18)
                    out.append({
                        "sport": "Tennis ATP",
                        "home": home, "away": away,
                        "scoreHome": sh, "scoreAway": sa,
                        "phase": phase,
                        "event": comp_name,
                        "updated": now_utc()
                    })
    except Exception as ex:
        print(f"  [Tennis] ERROR: {ex}")
    print(f"  [Tennis] {len(out)} live matches found")
    return out

def cricket():
    out = []
    try:
        r = requests.get(
            "https://prod-cdn-public-api.livescore.com/v1/api/app/date/cricket/20260524/0?MD=1",
            headers={**HEADERS,
                     "origin": "https://www.livescore.com",
                     "referer": "https://www.livescore.com/"},
            timeout=15
        )
        print(f"  [Cricket] livescore API HTTP {r.status_code} size={len(r.content)}")
        if r.status_code == 200:
            data = r.json()
            for stage in data.get("Stages", []):
                for e in stage.get("Events", []):
                    if len(out) >= 5: break
                    if e.get("Eps") != "2": continue
                    home = trim(e.get("T1",[{}])[0].get("Nm","T1"), 14)
                    away = trim(e.get("T2",[{}])[0].get("Nm","T2"), 14)
                    sh = str(e.get("Tr1","0"))
                    sa = str(e.get("Tr2","0"))
                    out.append({
                        "sport": "Cricket",
                        "home": home, "away": away,
                        "scoreHome": sh, "scoreAway": sa,
                        "phase": trim(e.get("Stg","Live"), 12),
                        "event": trim(stage.get("Cnm",""), 18),
                        "updated": now_utc()
                    })
    except Exception as ex:
        print(f"  [Cricket] ERROR: {ex}")
    print(f"  [Cricket] {len(out)} live matches found")
    return out

def main():
    print(f"[{now_utc()}] Scraping live scores...")
    matches = []
    matches += football()
    matches += tennis()
    matches += cricket()
    matches += afl()
    print(f"Total live matches: {len(matches)}")
    for m in matches:
        print(f"  [{m['sport']}] {m['home']} {m['scoreHome']}-{m['scoreAway']} {m['away']} | {m['phase']} {m['event']}")
    output = {
        "matches": matches,
        "updated": now_utc(),
        "count": len(matches),
        "source": "live" if matches else "no-live-matches"
    }
    with open("data/scores.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Written to data/scores.json")

if __name__ == "__main__":
    main()
