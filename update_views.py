#!/usr/bin/env python3
"""Updates ONLY views.svg (blue theme kept) + views-data.json, and bumps the cache-buster in README.md.
Run:  python3 update_views.py           (live)
      python3 update_views.py --offline (no network; just re-stamps time, for testing)
"""
import datetime, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "rohanbhowm25308"
OFFLINE = "--offline" in sys.argv
SVG, DATA, README = (os.path.join(HERE, f) for f in ("views.svg", "views-data.json", "README.md"))

# blue theme colours (same as your current views.svg)
EDGE, PLATE = "#367BFF", "#030713"
CWID, CHT, STEP, Y0 = 44, 64, 50, 56
W = 460


def komarev_raw():
    """Read the komarev counter once. NOTE: this read itself adds +1 on their side."""
    url = f"https://komarev.com/ghpvc/?username={USER}&label=Views"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    svg = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    for pat in (r'aria-label="[^"]*?:\s*([\d,]+)"', r"<title>[^<]*?:\s*([\d,]+)</title>", r">\s*([\d,]+)\s*</text>"):
        nums = re.findall(pat, svg)
        if nums:
            return int(nums[-1].replace(",", ""))
    return None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def load():
    try:
        return json.load(open(DATA))
    except Exception:
        return {"views": 455}


def refresh_count(d):
    if OFFLINE:
        print("offline: keeping", d["views"]); return d
    raw = komarev_raw()
    if raw is None:
        raise RuntimeError("could not read the komarev counter")
    # first run: measure whether our own read counts as a view
    if d.get("self_inc") is None:
        raw2 = komarev_raw()
        d["self_inc"] = 1 if (raw2 is not None and raw2 - raw >= 1) else 0
        raw = raw2 if raw2 is not None else raw
    inc = d["self_inc"]
    if d.get("last_raw") is None:
        # baseline: never go below what you already show (455)
        d["views"] = max(d.get("views", 0), raw - inc)
    else:
        d["views"] = d["views"] + max(0, raw - d["last_raw"] - inc)
    d["last_raw"] = raw
    d["fetched_at"] = now_utc().isoformat() + "Z"
    print(f"live: raw={raw} own_read_counts={inc} -> views={d['views']}")
    return d


def columns(v):
    digits = str(v); n = len(digits)
    x0 = 118 + (W - 24 - 118 - n * STEP + 6) / 2
    rows = lambda cx: "".join(
        f'<text class="sg" x="{cx + CWID / 2:.1f}" y="{Y0 + 47 + k * CHT}" font-size="42" text-anchor="middle" fill="#fff">{k}</text>' for k in range(10))
    clips, cols = "", ""
    for i, ch in enumerate(digits):
        dg = int(ch); cx = x0 + i * STEP
        clips += f'<clipPath id="dc{i}"><rect x="{cx:.1f}" y="{Y0}" width="{CWID}" height="{CHT}" rx="11"/></clipPath>'
        cols += (f'<rect x="{cx:.1f}" y="{Y0}" width="{CWID}" height="{CHT}" rx="11" fill="{PLATE}" stroke="{EDGE}" stroke-opacity=".45"/>'
                 f'<g clip-path="url(#dc{i})"><g><animateTransform attributeName="transform" type="translate" '
                 f'values="0 0;0 {-dg * CHT};0 {-dg * CHT};0 0" keyTimes="0;.22;.94;1" dur="10s" begin="{.5 + i * .22:.2f}s" '
                 f'repeatCount="indefinite" calcMode="spline" keySplines=".2 .8 .2 1;0 0 1 1;.5 0 .5 1"/>{rows(cx)}</g>'
                 f'<rect x="{cx:.1f}" y="{Y0}" width="{CWID}" height="{CHT / 2}" fill="#fff" fill-opacity=".06"/>'
                 f'<rect x="{cx:.1f}" y="{Y0 + CHT / 2 - .5}" width="{CWID}" height="1" fill="#000" fill-opacity=".55"/></g>')
    return x0, clips, cols


def patch_svg(v, ts_iso):
    s = open(SVG, encoding="utf-8").read()
    x0, clips, cols = columns(v)
    # 1) clip paths for the digits
    s, c1 = re.subn(r'(<clipPath id="dc\d+">.*?</clipPath>)+', lambda m: clips, s, count=1, flags=re.S)
    # 2) the odometer columns
    s, c2 = re.subn(r'(<g class="fu" style="animation-delay:\.4s">).*?(</g>)(?=<text class="jb")',
                    lambda m: m.group(1) + cols + m.group(2), s, count=1, flags=re.S)
    # 3) title / aria-label
    s = re.sub(r'aria-label="Profile views: [\d,]+"', f'aria-label="Profile views: {v}"', s)
    s = re.sub(r"<title>Profile views: [\d,]+</title>", f"<title>Profile views: {v}</title>", s)
    # 4) "last recorded" stamp (IST)
    t = datetime.datetime.fromisoformat(ts_iso.replace("Z", "")) + datetime.timedelta(hours=5, minutes=30)
    stamp = t.strftime("%b %d, %Y · %I:%M %p IST").replace(" 0", " ").replace("· 0", "· ")
    s, c3 = re.subn(r"last recorded: [^<]*", f"last recorded: {stamp}", s)
    # 5) keep the left-aligned labels in line with the odometer
    s = re.sub(r'(<text class="jbb" x=")[\d.]+(" y="34" font-size="11.5")', rf'\g<1>{x0:.1f}\2', s)
    s = re.sub(r'(<text class="jb" x=")[\d.]+(" y="144")', rf'\g<1>{x0:.1f}\2', s)
    s = re.sub(r'(<text class="jb" x=")[\d.]+(" y="160")', rf'\g<1>{x0:.1f}\2', s)
    assert c1 and c2 and c3, f"svg layout changed, patch failed {(c1, c2, c3)}"
    open(SVG, "w", encoding="utf-8").write(s)
    print("views.svg updated:", v, "|", stamp)


def bump_readme():
    """GitHub caches images hard - change ?v= so the new views.svg is actually fetched."""
    if not os.path.exists(README):
        return
    r = open(README, encoding="utf-8").read()
    v = now_utc().strftime("%Y%m%d%H%M")
    r2 = re.sub(r'(\./views\.svg)(\?v=\d+)?', rf'\1?v={v}', r)
    if r2 != r:
        open(README, "w", encoding="utf-8").write(r2); print("README cache-buster ->", v)


def main():
    d = load()
    try:
        d = refresh_count(d)
    except Exception as e:                      # fail LOUDLY so the Actions tab shows a red X and the reason
        print("ERROR: could not read the live counter from komarev.com:", repr(e))
        sys.exit(1)
    if not d.get("fetched_at"):
        d["fetched_at"] = now_utc().isoformat() + "Z"
    json.dump(d, open(DATA, "w"), indent=1)
    patch_svg(d["views"], d["fetched_at"])
    bump_readme()


if __name__ == "__main__":
    main()
