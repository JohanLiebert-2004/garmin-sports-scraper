#!/usr/bin/env python3
"""
Sports scraper - runs via GitHub Actions every 3 minutes
Scrapes live scores from multiple sources and writes data/scores.json
"""
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

# ── FOOTBALL + AFL via ESPN ──────────────────────────────────────────────────
def espn_sport(sport_label, url, event_label=""):
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for e in data.get("events", []):
            if len(out) >= 5: break
            comps = e.get("competitions", [])
            if not comps: continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2: continue
            status = e.get("status", {})
            if status.get("type", {}).get("state", "") != "in": continue
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
        print(f"  [{sport_label}] ESPN error: {ex}")
    return out

def football():
    results = []
    for slug, label in [("eng.1","EPL"),("esp.1","La Liga"),("ger.1","Bundesliga"),("ita.1","Serie A"),("fra.1","Ligue 1"),("uefa.champions","UCL")]:
        if len(results) >= 5: break
        results += espn_sport("Football", f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard", label)
    return results[:5]

def afl():
    return espn_sport("AFL", "https://site.api.espn.com/apis/site/v2/sports/australian-football/afl/scoreboard", "AFL")[:5]

# ── TENNIS via Flashscore scrape ─────────────────────────────────────────────
def tennis():
    out = []
    try:
        # Flashscore tennis livescore page
        r = requests.get(
            "https://www.flashscore.com/tennis/",
            headers={**HEADERS, "Referer": "https://www.flashscore.com/"},
            timeout=15
        )
        # Flashscore embeds score data in a custom JS format
        # Look for pattern: ¬~AA÷matchid¬...
        text = r.text
        # Try to find live match data in the page source
        # Flashscore uses a specific delimiter format
        matches_raw = re.findall(r'AA÷([^¬]+)¬AB÷([^¬]+)¬', text)
        print(f"  [Tennis] Flashscore raw matches found: {len(matches_raw)}")

        # Alternative: use their public JSON endpoint
        r2 = requests.get(
            "https://d.flashscore.com/x/feed/f_1_tennis_0_en_1",
            headers={**HEADERS,
                     "X-fsign": "SW9D1eZo",
                     "Referer": "https://www.flashscore.com/"},
            timeout=15
        )
        print(f"  [Tennis] Flashscore feed HTTP {r2.status_code} size={len(r2.content)}")
        if r2.status_code == 200:
            content = r2.text
            # Parse flashscore custom format: fields separated by ¬, records by ~
            blocks = content.split("~")
            for block in blocks[:20]:
                if "¬" in block:
                    fields = dict(re.findall(r'([A-Z]{2})÷([^¬]*)', block))
                    if fields.get("AC") == "1":  # AC=1 means live/in-progress
                        home = trim(fields.get("CG","?"), 14)
                        away = trim(fields.get("CH","?"), 14)
                        sh = fields.get("CF","0")
                        sa = fields.get("CG2","0")
                        phase = trim(fields.get("EV","Live"), 12)
                        if home and away and home != "?":
                            out.append({
                                "sport": "Tennis ATP",
                                "home": home, "away": away,
                                "scoreHome": sh, "scoreAway": sa,
                                "phase": phase,
                                "event": "Roland Garros",
                                "updated": now_utc()
                            })
                        if len(out) >= 5: break
    except Exception as ex:
        print(f"  [Tennis] Error: {ex}")
    return out

# ── CRICKET via Cricbuzz unofficial ─────────────────────────────────────────
def cricket():
    out = []
    try:
        r = requests.get(
            "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
            headers={**HEADERS,
                     "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
                     "x-rapidapi-key": "RAPIDAPI_KEY_HERE"},
            timeout=12
        )
        if r.status_code == 200:
            data = r.json()
            for item in data.get("typeMatches", []):
                for series in item.get("seriesMatches", []):
                    for match in series.get("seriesAdWrapper", {}).get("matches", []):
                        if len(out) >= 5: break
                        mi = match.get("matchInfo", {})
                        ms = match.get("matchScore", {})
                        team1 = trim(mi.get("team1", {}).get("teamSName", "T1"), 14)
                        team2 = trim(mi.get("team2", {}).get("teamSName", "T2"), 14)
                        inn1 = ms.get("team1Score", {}).get("inngs1", {})
                        inn2 = ms.get("team2Score", {}).get("inngs1", {})
                        s1 = f"{inn1.get('runs',0)}/{inn1.get('wickets',0)}"
                        s2 = f"{inn2.get('runs',0)}/{inn2.get('wickets',0)}"
                        out.append({
                            "sport": "Cricket",
                            "home": team1, "away": team2,
                            "scoreHome": s1, "scoreAway": s2,
                            "phase": trim(mi.get("status","Live"), 12),
                            "event": trim(mi.get("seriesName",""), 18),
                            "updated": now_utc()
                        })
    except Exception as ex:
        print(f"  [Cricket] Error: {ex}")
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
        print(f"  [{m['sport']}] {m['home']} {m['scoreHome']}-{m['scoreAway']} {m['away']} ({m['phase']})")

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
