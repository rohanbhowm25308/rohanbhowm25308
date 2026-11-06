#!/usr/bin/env python3
"""Refreshes the two live graphs with your real GitHub data, keeping your blue theme + star background:
    activity.svg  ("Every day I ship, mapped")
    city.svg      ("Every commit builds another tower")
It re-uses the drawing code that is already inside build.py (so the layout is identical), then
recolours red -> blue and re-inserts your star layer.   build.py itself is NOT modified.
Run:  python3 update_graphs.py            (live)
      python3 update_graphs.py --offline  (uses cached data - for testing)
"""
import contextlib, importlib.util, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OFFLINE = "--offline" in sys.argv
sys.argv = ["build.py"] + (["--offline"] if OFFLINE else [])     # build.py reads sys.argv at import time
spec = importlib.util.spec_from_file_location("build", os.path.join(HERE, "build.py"))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

# red (build.py colours) -> blue (your Cobalt Chrome theme)
MAP = {"#171a2c": "#050b20", "#0f1120": "#03091d", "#ef4444": "#367bff", "#262a42": "#102a4c", "#f59e0b": "#1c59ef",
       "#ffb199": "#94c5fc", "#eceef6": "#e8f1ff", "#34d399": "#286bff", "#8d93ab": "#b4d9ff", "#0b0d1b": "#090e14",
       "#5d6483": "#275fea", "#1f1822": "#07112d", "#6b1424": "#142d79", "#c81e2d": "#215ef0", "#ff4d5a": "#367bff",
       "#ffb347": "#a8cfff", "#fb7185": "#659eff", "#ffd166": "#a8cfff", "#150810": "#080d14", "#0a0509": "#030713",
       "#06030a": "#060d16", "#1d0d16": "#0a0f16", "#130812": "#080d14", "#ffd0c8": "#9dcafd", "#fff4e6": "#e8f1ff",
       "#e9b9a5": "#3d94f7", "#d9a994": "#0e74e8", "#0d0509": "#080d14", "#090308": "#070d15", "#2a111c": "#050b20",
       "#460d17": "#0a1a4a", "#310910": "#08133a", "#84131d": "#09358f", "#5c0d14": "#062e63", "#a8323b": "#1a3ca0",
       "#752329": "#163a6a", "#a8762e": "#0e77ee", "#755220": "#1c3e83", "#fff4e0": "#f1f6ff", "#ff5a4a": "#558eff",
       "#0d0a14": "#090d13", "#ffe3dc": "#dbf7fe", "#4b8bbe": "#147df5", "#e34c26": "#367bff", "#a78bfa": "#a8cfff",
       "#f1e05a": "#a8cfff", "#f9a03c": "#659eff"}
# blue colours for the language ring/legend of the city (GitHub's own language colours are not blue)
LANG_BLUES = {"Python": "#1A3CA0", "JavaScript": "#A8CFFF", "Jupyter Notebook": "#1C59EF", "HTML": "#367BFF", "CSS": "#183C98"}
EXTRA_BLUES = ["#5FA7FF", "#2F6FE0", "#94C5FC", "#0E74E8", "#659EFF", "#3D94F7"]


def recolor(svg):
    return re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: MAP.get(m.group(0).lower(), m.group(0)), svg)   # single pass, no chain-replace


def blue_languages(langs):
    out, extra = [], iter(EXTRA_BLUES * 4)
    for name, col, n in langs:
        out.append([name, LANG_BLUES.get(name) or (col if name == "other" else next(extra)), n])
    return out


def starfield(path):
    try:
        m = re.search(r'<g class="background-starfield".*?</g>', open(path, encoding="utf-8").read(), re.S)
        return m.group(0) if m else ""
    except OSError:
        return ""


def finish(svg, stars):
    svg = recolor(svg)
    if stars:   # put the star layer right after the card background, behind everything else
        svg, n = re.subn(r'(<rect width="\d+" height="\d+" rx="24" fill="url\(#\w+\)"\s*/>)', lambda m: m.group(1) + stars, svg, count=1)
        if not n:
            print("  warning: could not place the star layer")
    return svg


def quiet(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn()
    return r, buf.getvalue()


def main():
    ok = True
    # ---- live data -------------------------------------------------------------------------------------
    days, log = quiet(b.fetch_contribs)
    live_days = "live" in log
    print("contributions:", "LIVE" if live_days else "NOT live (cached)", "-", len(days or []), "days")
    cd, log2 = quiet(b.fetch_city_data)
    live_city = "live from GitHub" in log2
    cd["languages"] = blue_languages(cd["languages"])
    json.dump(cd, open(os.path.join(HERE, "city-data.json"), "w"), indent=1)
    print("city data:", "LIVE" if live_city else "NOT live (cached)", cd["totals"])
    if not OFFLINE and not (live_days and live_city):
        print("ERROR: could not get live data - graphs left unchanged. Log:", log.strip(), log2.strip())
        sys.exit(1)
    b.fetch_contribs = lambda: days            # build_* will use exactly the data fetched above
    b.fetch_city_data = lambda: cd
    # ---- rebuild ---------------------------------------------------------------------------------------
    for name, fn in (("activity.svg", b.build_activity), ("city.svg", b.build_city)):
        path = os.path.join(HERE, name)
        svg = fn()
        if not svg:
            print("ERROR:", name, "produced nothing"); ok = False; continue
        svg = finish(svg, starfield(path))
        open(path, "w", encoding="utf-8").write(svg)
        print("updated", name, f"{len(svg) / 1024:.0f} KB")
    # ---- cache-buster so GitHub shows the new picture ---------------------------------------------------
    rp = os.path.join(HERE, "README.md")
    if os.path.exists(rp):
        import datetime
        v = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
        r = open(rp, encoding="utf-8").read()
        r2 = re.sub(r"(\./(?:activity|city)\.svg)(\?v=\d+)?", rf"\1?v={v}", r)
        if r2 != r:
            open(rp, "w", encoding="utf-8").write(r2)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
