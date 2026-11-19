#!/usr/bin/env python3
"""Daily data update for the CBB Blind Resume site.

1. Ratings: downloads Bart Torvik's team table (best effort; if the download fails, last data is kept).
2. Scores: reads ESPN's public scoreboard for every day since the season opened and saves final scores.
Results are written to data/teams.csv, data/games.csv and data/meta.json.
"""
import csv, datetime as dt, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TEAMS_CSV = os.path.join(DATA, "teams.csv")
GAMES_CSV = os.path.join(DATA, "games.csv")
META_JSON = os.path.join(DATA, "meta.json")
UNMATCHED = os.path.join(DATA, "unmatched.txt")

SEASON_YEAR = 2027                 # the 2026-27 season is "2027" on barttorvik.com
SEASON_START = dt.date(2026, 11, 1)   # opening games were played Nov 1 (Rome)
TORVIK_URL = f"https://barttorvik.com/{SEASON_YEAR}_team_results.csv"
ESPN_URL = ("https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/"
            "scoreboard?dates={d}&groups=50&limit=1000")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# ESPN school name (lowercase) -> Torvik name, for schools whose names differ
ALIAS = {
    "lsu new orleans": "New Orleans",
    "american university": "American",
    "grambling": "Grambling St.",
    "kansas city": "UMKC",
    "long island university": "LIU",
    "mcneese": "McNeese St.",
    "nicholls": "Nicholls St.",
    "omaha": "Nebraska Omaha",
    "queens university": "Queens",
    "se louisiana": "Southeastern Louisiana",
    "san josé state": "San Jose St.",
    "south carolina upstate": "USC Upstate",
    "ualbany": "Albany",
    "uconn": "Connecticut", "miami": "Miami FL", "ole miss": "Mississippi", "uic": "Illinois Chicago",
    "pennsylvania": "Penn", "sam houston": "Sam Houston St.", "seattle u": "Seattle",
    "app state": "Appalachian St.", "loyola maryland": "Loyola MD", "umass": "Massachusetts",
    "pitt": "Pittsburgh", "ut martin": "Tennessee Martin", "texas a&m-corpus christi": "Texas A&M Corpus Chris",
    "texas a&m corpus christi": "Texas A&M Corpus Chris", "california baptist": "Cal Baptist",
    "mississippi state": "Mississippi St.", "iu indianapolis": "IU Indy", "iu indy": "IU Indy",
    "southern miss": "Southern Miss", "louisiana": "Louisiana", "ul monroe": "Louisiana Monroe",
    "uc davis": "UC Davis", "st. thomas": "St. Thomas", "saint thomas": "St. Thomas",
    "william & mary": "William & Mary", "fiu": "FIU", "florida international": "FIU",
    "usc": "USC", "ucf": "UCF", "unlv": "UNLV", "uab": "UAB", "vcu": "VCU", "smu": "SMU", "tcu": "TCU",
    "lsu": "LSU", "byu": "BYU", "unc": "North Carolina", "nc state": "N.C. State",
}

def log(*a):
    print(*a, flush=True)

def http_get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def norm(n):
    n = n.lower().replace("&", "and")
    n = re.sub(r"\bstate\b", "st", n)
    n = re.sub(r"\bsaint\b", "st", n)
    return re.sub(r"[^a-z0-9]", "", n)

# ---------------------------------------------------------------- Torvik ratings
def read_teams():
    if not os.path.exists(TEAMS_CSV):
        return []
    with open(TEAMS_CSV, newline="") as f:
        return [r for r in csv.reader(f) if len(r) >= 8]

def fetch_torvik(old_rows):
    """Return rows [name, conf, record, adjoe, adjde, barthag, tempo, wab] or None."""
    try:
        text = http_get(TORVIK_URL)
    except Exception as e:
        log("Torvik download failed:", e)
        return None
    if "<html" in text[:500].lower():
        log("Torvik returned a web page instead of data (likely a bot check). Keeping existing ratings.")
        return None
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return None
    header = [h.strip().lower() for h in rows[0]]
    has_header = not header[0].isdigit()
    if has_header:
        idx = {h: i for i, h in enumerate(header)}
        body = rows[1:]
    else:  # no header row: assume the documented column order
        idx = {"rank": 0, "team": 1, "conf": 2, "record": 3, "adjoe": 4, "adjde": 6, "barthag": 8}
        body = rows
    def col(*names):
        for n in names:
            if n in idx:
                return idx[n]
        return None
    c_team, c_conf, c_rec = col("team"), col("conf"), col("record", "rec")
    c_oe, c_de, c_bar = col("adjoe", "adj oe", "adj_oe"), col("adjde", "adj de", "adj_de"), col("barthag")
    c_wab, c_t = col("wab"), col("adjt", "adj t.", "adj_t", "adj tempo", "adjtempo")
    c_rank = col("rank")
    if None in (c_team, c_conf, c_rec, c_oe, c_de, c_bar):
        log("Torvik file has unexpected columns:", header[:12])
        return None
    old = {r[0]: r for r in old_rows}
    out = []
    for r in body:
        try:
            name = r[c_team].strip().replace(",", "")
            rank = float(r[c_rank]) if c_rank is not None else len(out) + 1
            oe, de, bar = float(r[c_oe]), float(r[c_de]), float(r[c_bar])
            wab = float(r[c_wab]) if c_wab is not None and r[c_wab] != "" else float(old.get(name, [0] * 8)[7] or 0)
            tempo = float(r[c_t]) if c_t is not None and r[c_t] != "" else float(old.get(name, [0, 0, 0, 0, 0, 0, 70.0])[6] or 70.0)
            rec = r[c_rec].strip()
            if not re.fullmatch(r"\d+-\d+", rec):
                continue
            out.append((rank, [name, r[c_conf].strip(), rec, f"{oe:g}", f"{de:g}", f"{bar:.4f}".lstrip("0"), f"{tempo:g}", f"{wab:g}"]))
        except (ValueError, IndexError):
            continue
    if len(out) < 100:
        log("Torvik file had only", len(out), "usable rows. Keeping existing ratings.")
        return None
    out.sort(key=lambda x: x[0])
    return [r for _, r in out]

# ---------------------------------------------------------------- ESPN scores
class Mapper:
    def __init__(self, names):
        self.by_norm = {norm(n): n for n in names}
        self.unmatched = set()
    def __call__(self, school):
        a = ALIAS.get(school.lower())
        if a and norm(a) in self.by_norm:
            return self.by_norm[norm(a)], True
        k = norm(school)
        if k in self.by_norm:
            return self.by_norm[k], True
        self.unmatched.add(school)
        return school, False

def parse_day(payload, mapper):
    games = []
    for ev in payload.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status = (comp.get("status") or ev.get("status") or {}).get("type", {})
        if not status.get("completed"):
            continue
        cs = comp.get("competitors") or []
        if len(cs) != 2:
            continue
        cs = sorted(cs, key=lambda c: 0 if c.get("homeAway") == "home" else 1)
        try:
            sc = [int(float(c.get("score"))) for c in cs]
        except (TypeError, ValueError):
            continue
        names = []
        for c in cs:
            t = c.get("team", {})
            names.append(mapper(t.get("location") or t.get("displayName") or ""))
        if not any(ok for _, ok in names):
            continue   # neither team is in the ratings list
        games.append([names[0][0], names[1][0], str(sc[0]), str(sc[1]), str(ev.get("id"))])
    return games

def read_games():
    if not os.path.exists(GAMES_CSV):
        return []
    with open(GAMES_CSV, newline="") as f:
        r = list(csv.reader(f))
    return [x for x in r[1:] if len(x) >= 6]

def main():
    os.makedirs(DATA, exist_ok=True)
    meta = json.load(open(META_JSON)) if os.path.exists(META_JSON) else {}
    teams = read_teams()
    fresh = fetch_torvik(teams)
    torvik_ok = fresh is not None
    if fresh:
        teams = fresh
        with open(TEAMS_CSV, "w", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(teams)
        log("Ratings updated:", len(teams), "teams")
    mapper = Mapper([r[0] for r in teams])

    games = {g[5]: g for g in read_games() if g[5]}
    undated = [g for g in read_games() if not g[5]]
    fetched = set(meta.get("fetched", []))
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date()   # US Eastern, close enough
    d, got_any, errors = SEASON_START, False, 0
    while d <= today:
        key = d.strftime("%Y%m%d")
        if key not in fetched or d >= today - dt.timedelta(days=2):
            try:
                day = parse_day(json.loads(http_get(ESPN_URL.format(d=key))), mapper)
                for g in day:
                    games[g[4]] = [d.isoformat()] + g
                got_any = got_any or bool(day)
                if d < today - dt.timedelta(days=2):
                    fetched.add(key)
            except Exception as e:
                errors += 1
                log("ESPN fetch failed for", key, ":", e)
        d += dt.timedelta(days=1)
    # a hand-added game (id starting with "manual") is dropped once ESPN supplies the same matchup
    real = {(g[0], frozenset((g[1], g[2]))) for g in games.values() if not g[5].startswith("manual")}
    games = {k: g for k, g in games.items() if not (g[5].startswith("manual") and (g[0], frozenset((g[1], g[2]))) in real)}
    rows = sorted(games.values(), key=lambda g: (g[0], g[5]))
    if not got_any:
        rows = undated + rows      # keep the starter data until real results arrive
    with open(GAMES_CSV, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "team", "opp", "ts", "os", "id"])
        w.writerows(rows)
    with open(UNMATCHED, "w") as f:
        f.write("\n".join(sorted(mapper.unmatched)) + "\n")
    meta.update({"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                 "torvik_ok": torvik_ok, "games": len(rows), "espn_errors": errors, "fetched": sorted(fetched)})
    json.dump(meta, open(META_JSON, "w"), indent=1)
    log(f"Games saved: {len(rows)} (ESPN errors: {errors}, unmatched school names: {len(mapper.unmatched)})")

if __name__ == "__main__":
    main()
