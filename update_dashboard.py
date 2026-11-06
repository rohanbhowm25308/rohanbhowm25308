#!/usr/bin/env python3
"""Updates the "Profile at a glance" dashboard (id-dashboard-fixed.svg) from live GitHub data:
public repos, total stars, forks, followers and the "most-starred projects" bars.
Only those numbers change - your blue design is untouched.
Run:  python3 update_dashboard.py
"""
import json, os, re, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "rohanbhowm25308"
SVG = os.path.join(HERE, "id-dashboard-fixed.svg")
DATA = os.path.join(HERE, "dashboard-data.json")
README = os.path.join(HERE, "README.md")
# projects shown in the "MOST-STARRED PROJECTS" panel (edit names any time; max 5 fit)
DASHBOARD_REPOS = ["FraudX", "BeyondTrip-AI", "TalentMind-AI", "VeriScope-AI", "Econexa-AI"]

NUM_FILL, LABEL_FILL = "#E8F1FF", "#B4D9FF"   # blue-theme text colours used in your svg


def gh(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"User-Agent": "profile-updater", "Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def fetch():
    u = gh(f"/users/{USER}")
    repos, page = [], 1
    while True:                                           # all pages, in case you have >100 repos
        chunk = gh(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    by = {r["name"].lower(): r["stargazers_count"] for r in own}
    rows = sorted([(n, by.get(n.lower(), 0)) for n in DASHBOARD_REPOS], key=lambda x: -x[1])
    return dict(repos=u["public_repos"], stars=sum(r["stargazers_count"] for r in own),
                forks=sum(r["forks_count"] for r in own), followers=u["followers"], bars=[list(r) for r in rows])


def counter(final, x):
    """Same count-up animation as your original tile numbers."""
    vals = sorted({0, round(final * .25), round(final * .5), round(final * .75), final})
    t0, stp = 1.0, .22
    dur = t0 + stp * len(vals) + .1
    out = ""
    for k, v in enumerate(vals):
        last = k == len(vals) - 1
        a = (t0 + k * stp) / dur; b = (t0 + (k + 1) * stp) / dur
        kt, vv = (f"0;{a:.4f}", "0;1") if last else (f"0;{a:.4f};{b:.4f}", "0;1;0")
        out += (f'<text class="sg" x="{x}" y="188" font-size="36" fill="{NUM_FILL}" opacity="{1 if last else 0}">{v}'
                f'<animate attributeName="opacity" calcMode="discrete" values="{vv}" keyTimes="{kt}" dur="{dur:.2f}s" begin="0s" fill="freeze" /></text>')
    return out


def bars(rows):
    mx = max(v for _, v in rows) or 1
    out = ""
    for i, (name, v) in enumerate(rows):
        y = 311 + 34 * i
        wd = max(14, 210 * v / mx) if v else 14
        kt = .6 + .016 * i; dur = 2.3 + .12 * i
        lab = (name if len(name) <= 18 else name[:17] + "…").replace("&", "&amp;")
        out += (f'<text class="jb" x="442" y="{y}" font-size="12" fill="{LABEL_FILL}">{lab}</text>'
                f'<rect x="592" y="{y - 11}" width="210" height="14" rx="7" fill="#ffffff" fill-opacity=".04" />'
                f'<rect x="592" y="{y - 11}" width="{wd:.1f}" height="14" rx="7" fill="url(#barG)"><animate attributeName="width" values="0;0;{wd:.1f}" keyTimes="0;{kt:.4f};1" dur="{dur:.2f}s" begin="0s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .8 .2 1" /></rect>'
                f'<text class="jbb" x="{592 + wd + 10:.0f}" y="{y}" font-size="12" fill="{NUM_FILL}" opacity="1">{v}<animate attributeName="opacity" calcMode="discrete" values="0;1" keyTimes="0;{.88 + .003 * i:.4f}" dur="{dur + .2:.2f}s" begin="0s" fill="freeze" /></text>')
    return out


def patch(d):
    s = open(SVG, encoding="utf-8").read()
    # 1) the four big numbers
    for label, key in (("PUBLIC REPOS", "repos"), ("TOTAL STARS", "stars"), ("FORKS", "forks"), ("FOLLOWERS", "followers")):
        pat = re.compile(r'((?:<text class="sg" x="[\d.]+" y="188" font-size="36"[^>]*>\d+<animate[^>]*/></text>)+)(<text class="jb"[^>]*>' + label + '</text>)')
        m = pat.search(s)
        assert m, f"tile '{label}' not found - svg layout changed"
        x = re.search(r'x="([\d.]+)"', m.group(1)).group(1)
        s = s[:m.start()] + counter(d[key], x) + m.group(2) + s[m.end():]
    # 2) the most-starred bars
    pat = re.compile(r'<text class="jb" x="442" y="311".*?(?=\s*<text class="jb" x="442" y="494")', re.S)
    assert pat.search(s), "bars block not found - svg layout changed"
    s = pat.sub(lambda m: bars([tuple(r) for r in d["bars"]]), s, count=1)
    open(SVG, "w", encoding="utf-8").write(s)


def bump_readme():
    if not os.path.exists(README):
        return
    r = open(README, encoding="utf-8").read()
    v = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
    r2 = re.sub(r'(\./id-dashboard-fixed\.svg)(\?v=\d+)?', rf'\1?v={v}', r)
    if r2 != r:
        open(README, "w", encoding="utf-8").write(r2)


def main():
    try:
        d = fetch()
    except Exception as e:                                # fail loudly -> red X in the Actions tab
        print("ERROR: could not read live GitHub data:", repr(e))
        sys.exit(1)
    print("live:", {k: d[k] for k in ("repos", "stars", "forks", "followers")}, d["bars"])
    old = json.load(open(DATA)) if os.path.exists(DATA) else {}
    json.dump(d, open(DATA, "w"), indent=1)
    if old == d and "--force" not in sys.argv:
        print("no change in numbers - svg left as is"); return
    patch(d); bump_readme()
    print("id-dashboard-fixed.svg updated")


if __name__ == "__main__":
    main()
