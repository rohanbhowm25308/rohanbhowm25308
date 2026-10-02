#!/usr/bin/env python3
"""
Animated GitHub profile builder  (Rohan Bhowmik)
=================================================
Generates hero.svg, about-life.svg, stack.svg, id-dashboard.svg, connect.svg and README.md.

  python3 build.py            -> build everything (pulls live GitHub stats if the API is reachable)
  python3 build.py --offline  -> never touch the network

Optional personal art (drop files into ./assets/):
  hello.mp4 (.mov/.webm/.gif)  2-second clip of you waving   -> plays inside the hero
  hero.jpg  (.png)             still photo instead of a video -> hero (if no clip)
  portrait.jpg (.png)          ID-badge photo (falls back to hero.jpg, then a monogram)
  character.png                transparent PNG, pointing pose -> connect banner (falls back to monogram)

Only needs Python 3.8+ and Pillow (pip install pillow). ffmpeg is needed only for a video clip.
"""
import base64, datetime, io, json, math, os, re, shutil, subprocess, sys, tempfile, urllib.request

# ───────────────────────────── YOUR DETAILS (edit these) ─────────────────────────────
CFG = dict(
    user="rohanbhowm25308",
    name="Rohan Bhowmik",
    role="AI / ML Developer",                 # hero alt text
    id_role="AI / ML DEVELOPER",              # ID badge sub-title (CAPS, ~18 chars max)
    roles=["AI / ML Developer", "Generative AI Builder", "AI Agents Explorer", "Data Science & Web Dev"],
    tagline=["Building intelligent applications with Python,", "machine learning, GenAI and AI agents."],
    location="India", degree="B.Tech CSE", building="Orchestrator AI",
    base="India", id_no="RB-25308",
    email="bhowmikrohan83@gmail.com",
    instagram="rohan_._.bhowmik.84",
    linkedin_path="rohan-bhowmik-b014473a1",
    quote=("Driven by curiosity. ", "Building with AI."),
    connect_sub="Open to AI, data & web projects and learning opportunities.",
    # shown if live stats can't be fetched
    fallback_stats=dict(repos=0, stars=0, forks=0, followers=0),
)
# brand ramp (red / black, matching your banner).  The original used cyan / violet / pink.
PALETTE = {"#22d3ee": "#ef4444", "#a78bfa": "#fb7185", "#f472b6": "#f59e0b"}
# ────────────────────────────────────────────────────────────────────────────────────

HERE = os.path.dirname(os.path.abspath(__file__))
OFFLINE = "--offline" in sys.argv
C1, C2, C3 = "#ef4444", "#fb7185", "#f59e0b"
ICONS = json.load(open(os.path.join(HERE, "icons.json")))


def tpl(n): return open(os.path.join(HERE, "templates", n), encoding="utf-8").read()
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def recolor(s):
    for a, b in PALETTE.items(): s = s.replace(a, b).replace(a.upper(), b)
    return s
def b64(data): return base64.b64encode(data).decode()
def lighten(hexc):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if 0.299 * r + 0.587 * g + 0.114 * b < 95:  # too dark for a dark card -> lift it
        r, g, b = (int(c + (255 - c) * .78) for c in (r, g, b))
    return "#%02x%02x%02x" % (r, g, b)
def icon_path(slug): return ICONS["paths"][slug]
def icon_color(slug): return lighten(ICONS["hex"][slug])

# ───────────────────────────── assets / placeholder art ─────────────────────────────
def asset(*names):
    for n in names:
        for ext in ("", ):
            p = os.path.join(HERE, "assets", n)
            if os.path.exists(p): return p
    return None

def find_asset(stem, exts):
    for e in exts:
        p = os.path.join(HERE, "assets", stem + e)
        if os.path.exists(p): return p
    return None

def monogram(w, h, transparent=False):
    """Clean geometric 'R' monogram (PIL only, no fonts needed)."""
    from PIL import Image, ImageDraw, ImageFilter
    S = 3; W, H = w * S, h * S
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0) if transparent else (13, 14, 22, 255))
    if not transparent:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((W * .05, H * .15, W * .95, H * .95), fill=(239, 68, 68, 120))
        base = Image.alpha_composite(base, g.filter(ImageFilter.GaussianBlur(W * .12)))
    m = min(W, H) * (0.70 if transparent else 0.60)
    cx, cy = W / 2, H * 0.52
    Ht, Wd = m, m * .74
    L, T = cx - Wd / 2, cy - Ht / 2
    t = m * .19; bh = Ht * .58
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    d.rounded_rectangle((L, T, L + Wd, T + bh), radius=bh * .46, fill=255)                      # bowl (outer)
    d.rounded_rectangle((L + t, T + t, L + Wd - t, T + bh - t), radius=max(2, bh * .46 - t), fill=0)  # bowl (inner cut)
    d.rounded_rectangle((L, T, L + t, T + Ht), radius=t * .25, fill=255)                         # stem
    leg = [(L + Wd * .30, T + bh - t * .6), (L + Wd * .30 + t * 1.1, T + bh - t * .6), (L + Wd * 1.02, T + Ht), (L + Wd * 1.02 - t * 1.25, T + Ht)]
    d.polygon(leg, fill=255)                                                                     # leg
    # red -> amber vertical gradient fill
    grad = Image.new("RGBA", (W, H)); gp = grad.load()
    for yy in range(H):
        k = min(1, max(0, (yy - T) / Ht)); c = (int(239 + (245 - 239) * k), int(68 + (158 - 68) * k), int(68 + (11 - 68) * k), 255)
        for xx in range(W): gp[xx, yy] = c
    glyph = Image.new("RGBA", (W, H), (0, 0, 0, 0)); glyph.paste(grad, (0, 0), mask)
    glow = Image.new("RGBA", (W, H), (239, 68, 68, 0)); glow.putalpha(mask.filter(ImageFilter.GaussianBlur(S * 10)).point(lambda v: int(v * .7)))
    out = Image.alpha_composite(Image.alpha_composite(base, glow), glyph)
    return out.resize((w, h), Image.LANCZOS)

def to_uri(img, fmt):
    buf = io.BytesIO()
    if fmt == "jpeg": img.convert("RGB").save(buf, "JPEG", quality=84, optimize=True)
    else: img.save(buf, "PNG", optimize=True)
    return f"data:image/{fmt};base64," + b64(buf.getvalue())

def fit(img, w, h, anchor_top=False):
    from PIL import Image
    r = max(w / img.width, h / img.height); img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x = (img.width - w) // 2; y = 0 if anchor_top else (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))

def portrait_uri():
    from PIL import Image
    p = find_asset("portrait", (".jpg", ".jpeg", ".png", ".webp")) or find_asset("hero", (".jpg", ".jpeg", ".png", ".webp"))
    if p: return to_uri(fit(Image.open(p).convert("RGB"), 272, 336, True), "jpeg")
    return to_uri(monogram(272, 336), "jpeg")

def character_uri():
    from PIL import Image
    p = find_asset("character", (".png", ".webp"))
    if p:
        im = Image.open(p).convert("RGBA"); im.thumbnail((736, 848)); return to_uri(im, "png")
    return to_uri(monogram(368, 424, transparent=True), "png")

# ───────────────────────────── live GitHub stats ─────────────────────────────
def gh(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-builder", "Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"): req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

def stats():
    fb = CFG["fallback_stats"]; out = dict(repos=fb["repos"], stars=fb["stars"], forks=fb["forks"], followers=fb["followers"], bars=None, live=False)
    if OFFLINE: return out
    try:
        u = gh(f"https://api.github.com/users/{CFG['user']}")
        repos = [r for r in gh(f"https://api.github.com/users/{CFG['user']}/repos?per_page=100&type=owner") if not r["fork"]]
        out.update(repos=u["public_repos"], followers=u["followers"], stars=sum(r["stargazers_count"] for r in repos),
                   forks=sum(r["forks_count"] for r in repos), live=True)
        top = sorted(repos, key=lambda r: -r["stargazers_count"])
        if top and top[0]["stargazers_count"] > 0:
            out["bars"] = ("MOST-STARRED PROJECTS", [(r["name"], r["stargazers_count"]) for r in top[:5]], "stars per repository")
        else:
            from collections import Counter
            c = Counter(r["language"] for r in repos if r["language"]).most_common(5)
            if c: out["bars"] = ("REPOS BY LANGUAGE", c, "primary language of each public repo")
    except Exception as e:
        print("  (live stats unavailable, using fallback):", e)
    return out

# ───────────────────────────── shared svg pieces ─────────────────────────────
def style_block(extra=""):
    hero = tpl("hero.tpl.svg")
    fonts = re.search(r"<style>(@font-face.*?)\ntext\{", hero, re.S).group(1)
    base = ("text{font-family:'JBM',ui-monospace,Menlo,Consolas,monospace}\n"
            ".sg{font-family:'SG','Segoe UI',Helvetica,Arial,sans-serif;font-weight:700}\n"
            ".sgm{font-family:'SGM','Segoe UI',Helvetica,Arial,sans-serif;font-weight:500}\n"
            ".jb{font-family:'JBM',ui-monospace,Menlo,Consolas,monospace}\n"
            ".jbb{font-family:'JBMB',ui-monospace,Menlo,Consolas,monospace;font-weight:700}\n"
            "@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}\n"
            "@keyframes fadeIn{from{opacity:0}to{opacity:1}}\n@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}\n"
            ".fu{animation:fadeUp .7s cubic-bezier(.2,.8,.2,1) both}\n.fi{animation:fadeIn .7s ease both}\n"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important;opacity:1!important;transform:none!important}}\n")
    return "<style>" + fonts + "\n" + base + extra + "</style>"

def fill(s, **kw):
    for k, v in kw.items(): s = s.replace("{{" + k + "}}", str(v))
    return s

# ───────────────────────────── HERO ─────────────────────────────
def hero_video():
    """returns (svg-group-markup, label)"""
    clip = find_asset("hello", (".mp4", ".mov", ".webm", ".gif", ".mkv"))
    still = find_asset("hero", (".jpg", ".jpeg", ".png", ".webp"))
    from PIL import Image
    if clip and shutil.which("ffmpeg"):
        tmp = tempfile.mkdtemp()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", "2", "-i", clip, "-vf",
                        "fps=24,scale=362:270:force_original_aspect_ratio=increase,crop=362:270", "-q:v", "9", os.path.join(tmp, "f%03d.jpg")], check=True)
        frames = sorted(f for f in os.listdir(tmp) if f.endswith(".jpg"))
        uris = ["data:image/jpeg;base64," + b64(open(os.path.join(tmp, f), "rb").read()) for f in frames]
        n, dur = len(uris), 4.0; step = 1 / (24 * dur)
        parts = ['<g><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.8875;0.9625;1" dur="4.0s" repeatCount="indefinite"/>']
        for i, u in enumerate(uris):
            a = i * step; b = (i + 1) * step
            img = f'<image x="560" y="0" width="724" height="540" href="{u}" opacity="{1 if i == 0 else 0}" preserveAspectRatio="none">'
            if i == 0: kt, vals = f"0;{b:.4f}", "1;0"
            elif i == n - 1: kt, vals = f"0;{a:.4f}", "0;1"
            else: kt, vals = f"0;{a:.4f};{b:.4f}", "0;1;0"
            parts.append(img + f'<animate attributeName="opacity" calcMode="discrete" values="{vals}" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/></image>')
        parts.append("</g>")
        return '<g mask="url(#vmask)"><g mask="url(#vmaskB)">' + "".join(parts) + "</g></g>", "HELLO.MP4"
    if clip: print("  ! ffmpeg not found - skipping video clip")
    if still:
        im = fit(Image.open(still).convert("RGB"), 724, 540, True)
        uri = to_uri(im, "jpeg")
        return f'<g mask="url(#vmask)"><g mask="url(#vmaskB)"><image x="560" y="0" width="724" height="540" href="{uri}" preserveAspectRatio="none"/></g></g>', "PORTRAIT.JPG"
    # animated placeholder: monogram + orbit + scan line
    ph = f'''<g mask="url(#vmask)"><g mask="url(#vmaskB)">
    <rect x="560" y="0" width="724" height="540" fill="#120a10"/>
    <circle cx="922" cy="270" r="230" fill="{C1}" fill-opacity=".10"/><circle cx="922" cy="270" r="150" fill="{C1}" fill-opacity=".10"/>
    <path id="phOrbit" d="M692 270a230 78 -18 1 0 460 0a230 78 -18 1 0 -460 0" fill="none" stroke="{C1}" stroke-opacity=".35" stroke-width="1.5"/>
    <circle r="6" fill="{C3}"><animateMotion dur="6s" repeatCount="indefinite"><mpath href="#phOrbit"/></animateMotion></circle>
    <g><animateTransform attributeName="transform" type="translate" values="0 0;0 -10;0 0" dur="4s" repeatCount="indefinite"/>
      <text class="sg" x="922" y="368" font-size="270" text-anchor="middle" fill="url(#nameG2)" filter="url(#glow)">R</text></g>
    <rect x="560" y="0" width="724" height="3" fill="{C1}" fill-opacity=".35"><animate attributeName="y" values="0;540;0" dur="5s" repeatCount="indefinite"/></rect></g></g>'''
    return ph, "HELLO.MP4"

def build_hero():
    c = CFG; s = recolor(tpl("hero.tpl.svg")); vid, label = hero_video()
    chips = [c["location"], c["degree"], c["building"]]
    w = lambda t: len(t) * 8.8
    x2 = 88 + w(chips[0]) + 40; x3 = x2 + 16 + w(chips[1]) + 40
    name_size = 76 if len(c["name"]) <= 12 else max(56, int(76 * 12.2 / len(c["name"])))
    s = fill(s, NAME=esc(c["name"]), ROLE=esc(c["role"]), NAME_SIZE=name_size, VIDEO=vid, VIDEO_LABEL=label,
             ROLE1=esc(c["roles"][0]), ROLE2=esc(c["roles"][1]), ROLE3=esc(c["roles"][2]), ROLE4=esc(c["roles"][3]),
             TAG1=esc(c["tagline"][0]), TAG2=esc(c["tagline"][1]), CHIP1=esc(chips[0]), CHIP2=esc(chips[1]), CHIP3=esc(chips[2]),
             X2=round(x2), X2T=round(x2 + 16), X3=round(x3), X3T=round(x3 + 16))
    return s

# ───────────────────────────── ID + DASHBOARD ─────────────────────────────
def counter(final, x, i):
    t0 = 1.0 + .05 * i; stp = .22; vals = sorted({0, round(final * .25), round(final * .5), round(final * .75), final}); dur = t0 + stp * len(vals) + .1
    out = ""
    for k, v in enumerate(vals):
        last = k == len(vals) - 1; a = (t0 + k * stp) / dur; b = (t0 + (k + 1) * stp) / dur
        if last: kt, vv = f"0;{a:.4f}", "0;1"
        else: kt, vv = f"0;{a:.4f};{b:.4f}", "0;1;0"
        out += (f'<text class="sg" x="{x}" y="188" font-size="36" fill="#eceef6" opacity="{1 if last else 0}">{v}'
                f'<animate attributeName="opacity" calcMode="discrete" values="{vv}" keyTimes="{kt}" dur="{dur:.2f}s" begin="0s" fill="freeze"/></text>')
    return out

def bars_markup(rows):
    mx = max(v for _, v in rows) or 1; out = ""
    for i, (name, v) in enumerate(rows):
        y = 311 + 34 * i; wd = max(14, 210 * v / mx) if v else 14
        kt = .6 + .016 * i; dur = 2.3 + .12 * i
        lab = esc(name if len(name) <= 18 else name[:17] + "…")
        out += (f'<text class="jb" x="442" y="{y}" font-size="12" fill="#8d93ab">{lab}</text>'
                f'<rect x="592" y="{y - 11}" width="210" height="14" rx="7" fill="#ffffff" fill-opacity=".04"/>'
                f'<rect x="592" y="{y - 11}" width="{wd:.1f}" height="14" rx="7" fill="url(#barG)"><animate attributeName="width" values="0;0;{wd:.1f}" keyTimes="0;{kt:.4f};1" dur="{dur:.2f}s" begin="0s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;.2 .8 .2 1"/></rect>'
                f'<text class="jbb" x="{592 + wd + 10:.0f}" y="{y}" font-size="12" fill="#eceef6" opacity="1">{v}<animate attributeName="opacity" calcMode="discrete" values="0;1" keyTimes="0;{.88 + .003 * i:.4f}" dur="{dur + .2:.2f}s" begin="0s" fill="freeze"/></text>')
    return out

def build_id(st):
    c = CFG; s = recolor(tpl("id-dashboard.tpl.svg"))
    s = fill(s, PORTRAIT=portrait_uri(), LANYARD=" &#183; ".join([c["name"].split()[0].upper() + ".DEV", "AI/ML"] * 2),
             NAME=esc(c["name"]), ID_ROLE=esc(c["id_role"]), BASE=esc(c["base"]), L2="DEGREE", V2=esc(c["degree"]), ID_NO=esc(c["id_no"]),
             L4="FOCUS", V4="AI / ML", USER=c["user"],
             PANEL_TITLE="TOOLKIT", PANEL_A="6", PANEL_A_L="LANGUAGES", PANEL_B="25+", PANEL_B_L=esc("TOOLS & FRAMEWORKS"),
             PANEL_NOTE=esc("Python · TensorFlow · GenAI · Agents"),
             NOW1L="BUILDING", NOW1=esc("Orchestrator AI (flagship)"), NOW2L="EXPLORING", NOW2=esc("Generative AI & AI Agents"),
             NOW3L="MOTTO", NOW3=esc("Learn, build, experiment, deploy"))
    vals = [st["repos"], st["stars"], st["forks"], st["followers"]]
    s = re.sub(r"\{\{COUNTER(\d)@([\d.]+)\}\}", lambda m: counter(vals[int(m.group(1)) - 1], m.group(2), int(m.group(1))), s)
    if st["bars"]: title, rows, note = st["bars"]
    else:
        title, note = "CURRENT FOCUS", "what I'm building & learning right now"
        rows = [("AI / ML", 1), ("Data Science", 1), ("Generative AI", 1), ("AI Agents", 1), ("Web Dev", 1)]
    bars = bars_markup(rows)
    if not st["bars"]: bars = bars.replace(">1<animate", "><animate")  # no fake numbers for the focus list
    s = fill(s, BARS=bars, BAR_TITLE=title, BAR_NOTE=esc(note))
    return s

# ───────────────────────────── CONNECT ─────────────────────────────
def icon_markup(slug, x, y, color=None):
    col = color or icon_color(slug)
    return f'<g transform="translate({x},{y}) scale(1)" style="color:{col}"><path fill="{col}" transform="scale(1)" d="{icon_path(slug)}"/></g>'

def build_connect():
    c = CFG; s = recolor(tpl("connect.tpl.svg"))
    s = fill(s, CONNECT_SUB=esc(c["connect_sub"]), USER=c["user"], EMAIL=esc(c["email"]), IG="@" + c["instagram"], LI=c["linkedin_path"][:26],
             QUOTE=esc(c["quote"][1]), CHARACTER=character_uri())
    s = s.replace("&#8220;<tspan", "&#8220;" + esc(c["quote"][0]) + "<tspan")
    for i, slug in enumerate(["github", "gmail", "instagram", "linkedin"], 1):
        s = re.sub(r"\{\{ICON%d@(\d+),(\d+)\}\}" % i, lambda m: icon_markup(slug, m.group(1), m.group(2)), s)
    return s

# ───────────────────────────── STACK ─────────────────────────────
def generic_icon(kind, color):
    st = f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
    shapes = {
        "spark": f'<path {st} d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z"/>',
        "brain": f'<g {st}><circle cx="7" cy="8" r="2.4"/><circle cx="17" cy="8" r="2.4"/><circle cx="12" cy="16.5" r="2.4"/><path d="M9 9l2 5M15 9l-2 5M9.4 8h5.2"/></g>',
        "rag": f'<g {st}><path d="M5 4h10l4 4v12H5z"/><path d="M15 4v4h4M8 12h8M8 16h5"/></g>',
        "bot": f'<g {st}><rect x="5" y="8" width="14" height="10" rx="3"/><path d="M12 8V4.5M9.5 13h.01M14.5 13h.01M3 12v2M21 12v2"/></g>',
    }
    return shapes[kind]

def build_stack():
    rows = [
        ("LANGUAGES", C1, [("Python", "python"), ("C", "c"), ("C++", "cplusplus"), ("JavaScript", "javascript"), ("HTML5", "html5"), ("CSS", "css3")]),
        ("AI / ML & DATA", C2, [("TensorFlow", "tensorflow"), ("Pandas", "pandas"), ("NumPy", "numpy"), ("Scikit-learn", "scikitlearn"), ("Kaggle", "kaggle")]),
        ("GENERATIVE AI & AGENTS", C3, [("Generative AI", "g:spark"), ("LLMs", "g:brain"), ("RAG", "g:rag"), ("AI Agents", "g:bot"), ("Hugging Face", "huggingface")]),
        ("WEB & TOOLS", "#34d399", [("Flask", "flask"), ("Streamlit", "streamlit"), ("Bootstrap", "bootstrap"), ("Git", "git"), ("GitHub", "github"), ("MySQL", "mysql")]),
    ]
    palette = {"g:spark": C3, "g:brain": C2, "g:rag": C1, "g:bot": C3}
    body = ""; delay = .5
    for ri, (title, tint, chips) in enumerate(rows):
        y0 = 120 + ri * 80
        body += f'<g class="fu" style="animation-delay:{delay:.2f}s"><rect x="552" y="{y0 + 5}" width="14" height="3" rx="1.5" fill="{tint}"/><text class="jbb" x="574" y="{y0 + 10}" font-size="12" fill="#8d93ab" letter-spacing="2">{esc(title)}</text></g>'
        x = 552
        for ci, (label, slug) in enumerate(chips):
            col = palette[slug] if slug.startswith("g:") else icon_color(slug)
            w = 40 + len(label) * 8.2 + 12
            ic = generic_icon(slug[2:], col) if slug.startswith("g:") else f'<path fill="{col}" d="{icon_path(slug)}"/>'
            body += (f'<g class="chip" style="animation-delay:{delay + .1 + ci * .07:.2f}s"><rect x="{x}" y="{y0 + 28}" width="{w:.0f}" height="40" rx="12" fill="{col}" fill-opacity=".08" stroke="{col}" stroke-opacity=".38"/>'
                     f'<g transform="translate({x + 13},{y0 + 38}) scale(.83)">{ic}</g><text class="jb" x="{x + 42}" y="{y0 + 53}" font-size="14" fill="#eceef6">{esc(label)}</text></g>')
            x += w + 8
        delay += .25
    # orbit system
    cx, cy = 262, 290
    orb = ""
    for k, rot in enumerate((0, 60, 120)):
        orb += f'<ellipse cx="{cx}" cy="{cy}" rx="172" ry="105" transform="rotate({rot} {cx} {cy})" fill="none" stroke="{[C1, C2, C3][k]}" stroke-opacity=".22" stroke-width="1.6"/>'
        a = math.radians(rot)
        # path for motion: sample the ellipse as a polygon-ish path using 4 arcs
        pts = []
        for t in range(0, 360, 10):
            tt = math.radians(t); x = 172 * math.cos(tt); yv = 105 * math.sin(tt)
            pts.append((cx + x * math.cos(a) - yv * math.sin(a), cy + x * math.sin(a) + yv * math.cos(a)))
        d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + " Z"
        orb += f'<path id="orb{k}" d="{d}" fill="none"/>'
    movers = [("python", 0, 0, 24), ("tensorflow", 0, -12, 24), ("github", 1, -2, 28), ("pandas", 1, -14, 26), ("scikitlearn", 2, -4, 30), ("huggingface", 2, -17, 30), ("numpy", 0, -18, 24), ("streamlit", 1, -9, 28)]
    for slug, k, begin, dur in movers:
        col = icon_color(slug)
        orb += (f'<g><animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite"><mpath href="#orb{k}"/></animateMotion>'
                f'<circle r="19" fill="#171a2c" stroke="{col}" stroke-opacity=".6" stroke-width="1.4"/><g transform="translate(-8,-8) scale(.67)"><path fill="{col}" d="{icon_path(slug)}"/></g></g>')
    core = (f'<circle cx="{cx}" cy="{cy}" r="62" fill="url(#orbG)"/><circle cx="{cx}" cy="{cy}" r="60" fill="none" stroke="{C2}" stroke-opacity=".5" stroke-width="1.4"><animate attributeName="r" values="60;70;60" dur="4s" repeatCount="indefinite"/></circle>'
            f'<text class="sg" x="{cx}" y="{cy + 14}" font-size="40" text-anchor="middle" fill="#fff">AI</text>')
    defs = (f'<linearGradient id="cardbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#171a2c"/><stop offset="1" stop-color="#0f1120"/></linearGradient>'
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C3}" stop-opacity=".55"/></linearGradient>'
            f'<radialGradient id="orbG" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="{C3}"/><stop offset=".55" stop-color="{C1}"/><stop offset="1" stop-color="#7f1d1d"/></radialGradient>'
            f'<pattern id="dots3" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r=".8" fill="#fff" fill-opacity=".05"/></pattern>')
    css = ".chip{animation:chipIn .6s cubic-bezier(.2,.8,.2,1) both}@keyframes chipIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 480" width="1280" height="480" role="img" aria-label="Tech stack"><title>Tech stack</title>'
            f'<defs>{style_block(css)}{defs}</defs>'
            f'<rect width="1280" height="480" rx="24" fill="url(#cardbg)"/><rect width="1280" height="480" rx="24" fill="url(#dots3)"/>'
            f'<rect x=".75" y=".75" width="1278.5" height="478.5" rx="23.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>'
            f'<g class="fu" style="animation-delay:.1s"><text class="jbb" x="40" y="54" font-size="12.5" fill="{C1}" letter-spacing="2.2">// TECH STACK</text><text class="sg" x="40" y="94" font-size="29" fill="#eceef6" letter-spacing="-.5">Tools I build with</text></g>'
            f'<line x1="520" y1="120" x2="520" y2="440" stroke="#262a42"/>{orb}{core}{body}</svg>')

# ───────────────────────────── ABOUT / FOCUS (two cards) ─────────────────────────────
def build_about():
    css = (".slide{animation:slide 12s cubic-bezier(.2,.8,.2,1) infinite both}@keyframes slide{0%{opacity:0;transform:translateX(46px)}5%{opacity:1;transform:translateX(0)}29%{opacity:1;transform:translateX(0)}33.3%{opacity:0;transform:translateX(-46px)}100%{opacity:0;transform:translateX(-46px)}}"
           ".cap{animation:cap 12s ease infinite both}@keyframes cap{0%{opacity:0;transform:translateY(10px)}6%{opacity:1;transform:translateY(0)}29%{opacity:1;transform:translateY(0)}33%{opacity:0;transform:translateY(-8px)}100%{opacity:0}}"
           ".row{animation:rowIn .7s cubic-bezier(.2,.8,.2,1) both}@keyframes rowIn{from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:translateX(0)}}"
           ".cardL{animation:fadeUp .8s cubic-bezier(.2,.8,.2,1) .1s both}.cardR{animation:fadeUp .8s cubic-bezier(.2,.8,.2,1) .3s both}.cursor{animation:pulse 1s steps(1) infinite}")
    defs = (f'<linearGradient id="cardbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#171a2c"/><stop offset="1" stop-color="#0f1120"/></linearGradient>'
            f'<linearGradient id="edgeL" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".6"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C2}" stop-opacity=".35"/></linearGradient>'
            f'<linearGradient id="edgeR" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C3}" stop-opacity=".55"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C2}" stop-opacity=".45"/></linearGradient>'
            f'<linearGradient id="bgA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a1018"/><stop offset="1" stop-color="#130a14"/></linearGradient>'
            f'<linearGradient id="bgB" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b1a10"/><stop offset="1" stop-color="#140d12"/></linearGradient>'
            f'<linearGradient id="bgC" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a1220"/><stop offset="1" stop-color="#110c16"/></linearGradient>'
            f'<linearGradient id="barW" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            '<clipPath id="winL"><rect x="28" y="118" width="564" height="352" rx="14"/></clipPath><clipPath id="winR"><rect x="688" y="118" width="564" height="352" rx="14"/></clipPath>'
            '<pattern id="dots2" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r=".8" fill="#fff" fill-opacity=".05"/></pattern>')
    # ---- left card: orchestration diagram inside a browser window
    ox, oy = 28, 152  # content origin (below chrome)
    nodes = {"in": (100, 290), "orc": (290, 290), "llm": (490, 205), "tools": (490, 290), "mem": (490, 375), "out": (290, 408)}
    def P(k): return nodes[k]
    edges = [("in", "orc"), ("orc", "llm"), ("orc", "tools"), ("orc", "mem"), ("orc", "out")]
    diag = '<rect x="28" y="152" width="564" height="318" fill="#0f1224"/><rect x="28" y="152" width="564" height="318" fill="url(#dots2)"/>'
    for i, (a, b) in enumerate(edges):
        (x1, y1), (x2, y2) = P(a), P(b)
        diag += f'<path id="e{i}" d="M{x1} {y1} L{x2} {y2}" stroke="{C2}" stroke-opacity=".35" stroke-width="1.6" fill="none" stroke-dasharray="4 5"/>'
        diag += f'<circle r="4.5" fill="{C3}"><animateMotion dur="{2.4 + i * .5}s" begin="{i * .4}s" repeatCount="indefinite"><mpath href="#e{i}"/></animateMotion></circle>'
    def node(k, label, sub, col, w=118, big=False):
        label, sub = esc(label), esc(sub)
        x, y = P(k); h = 46 if not big else 58
        pulse = f'<animate attributeName="stroke-opacity" values=".9;.35;.9" dur="2.6s" repeatCount="indefinite"/>' if big else ""
        return (f'<g><rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" rx="12" fill="#171a2c" stroke="{col}" stroke-opacity=".7" stroke-width="1.6">{pulse}</rect>'
                f'<text class="sg" x="{x}" y="{y + (-2 if sub else 5)}" font-size="{15 if big else 13}" text-anchor="middle" fill="#eceef6">{label}</text>'
                + (f'<text class="jb" x="{x}" y="{y + 14}" font-size="9.5" text-anchor="middle" fill="#8d93ab">{sub}</text>' if sub else "") + "</g>")
    diag += (node("in", "Request", "user / data", C3) + node("orc", "Orchestrator", "plans & routes", C1, 140, True) + node("llm", "LLM", "reasoning", C2, 104)
             + node("tools", "Tools & APIs", "actions", C3, 118) + node("mem", "Memory / RAG", "context", C2, 126) + node("out", "Answer", "result", C1, 118))
    left = (f'<g class="cardL"><rect x="0" y="0" width="620" height="640" rx="24" fill="url(#cardbg)"/><rect x="0" y="0" width="620" height="640" rx="24" fill="url(#dots2)"/>'
            f'<rect x=".75" y=".75" width="618.5" height="638.5" rx="23.25" fill="none" stroke="url(#edgeL)" stroke-width="1.5"/>'
            f'<text class="jbb" x="28" y="46" font-size="12.5" fill="{C1}" letter-spacing="2.2">// WHAT I BUILD</text><text class="sg" x="28" y="86" font-size="29" fill="#eceef6" letter-spacing="-.5">Intelligent apps, end to end</text>'
            f'<g clip-path="url(#winL)"><rect x="28" y="118" width="564" height="352" fill="#0f1224"/><rect x="28" y="118" width="564" height="34" fill="#1c2036"/>'
            '<circle cx="46" cy="135" r="5" fill="#ff5f57"/><circle cx="62" cy="135" r="5" fill="#febc2e"/><circle cx="78" cy="135" r="5" fill="#28c840"/>'
            '<rect x="178" y="126" width="264" height="18" rx="9" fill="#0b0d1b"/><text class="jb" x="310" y="139" font-size="11" fill="#8d93ab" text-anchor="middle">localhost:8501/orchestrator-ai</text>'
            f'<rect class="cursor" x="420" y="130" width="1.5" height="11" fill="{C1}"/>{diag}</g>'
            '<rect x="28.5" y="118.5" width="563" height="351" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity=".08"/>')
    caps = [("brain", C1, "AI / ML & Data Science", "Python, TensorFlow, Pandas, NumPy, scikit-learn"),
            ("spark", C2, "Generative AI & AI Agents", "LLMs, RAG and agentic workflows"),
            ("rag", C3, "Web apps & deployment", "Flask, Streamlit, REST APIs, Render")]
    for i, (g, col, t, sub) in enumerate(caps):
        y = 492 + i * 48
        left += (f'<g class="row" style="animation-delay:{.9 + i * .15:.2f}s"><rect x="28" y="{y}" width="40" height="40" rx="12" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".4"/>'
                 f'<g transform="translate(36,{y + 8})">{generic_icon(g, col)}</g><text class="sg" x="82" y="{y + 17}" font-size="15.5" fill="#eceef6">{esc(t)}</text><text class="jb" x="82" y="{y + 34}" font-size="11.5" fill="#8d93ab">{esc(sub)}</text></g>')
    left += "</g>"
    # ---- right card: carousel of focus areas
    rx0 = 660
    slides = []
    # slide A: neural net
    layers = [(3, 760), (4, 870), (4, 980), (2, 1090)]
    na = ""
    pos = []
    for li, (n, x) in enumerate(layers):
        col = []
        for j in range(n):
            y = 300 + (j - (n - 1) / 2) * 52; col.append((x, y))
        pos.append(col)
    for li in range(len(pos) - 1):
        for (x1, y1) in pos[li]:
            for (x2, y2) in pos[li + 1]:
                na += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C2}" stroke-opacity=".25" stroke-width="1"/>'
    for li, col in enumerate(pos):
        for j, (x, y) in enumerate(col):
            na += f'<circle cx="{x}" cy="{y}" r="11" fill="#171a2c" stroke="{[C3, C1, C2, C3][li]}" stroke-width="1.8"><animate attributeName="fill" values="#171a2c;{C1};#171a2c" dur="3s" begin="{li * .5 + j * .15:.2f}s" repeatCount="indefinite"/></circle>'
    slides.append(f'<rect x="688" y="118" width="564" height="352" fill="url(#bgA)"/>{na}')
    # slide B: agent loop
    sb = ""
    steps = [("Plan", 740), ("Search", 880), ("Reason", 1020)]
    for i, (t, x) in enumerate(steps):
        sb += (f'<rect x="{x}" y="270" width="110" height="52" rx="14" fill="#171a2c" stroke="{[C3, C1, C2][i]}" stroke-width="1.8"/><text class="sg" x="{x + 55}" y="302" font-size="15" text-anchor="middle" fill="#eceef6">{t}</text>')
        if i < 2: sb += f'<path d="M{x + 114} 296h22M{x + 130} 290l6 6-6 6" fill="none" stroke="{C3}" stroke-width="2" stroke-linecap="round"/>'
    sb += (f'<circle r="6" fill="{C3}"><animateMotion dur="3.4s" repeatCount="indefinite" path="M795 270 L795 240 L1075 240 L1075 270"/></circle>'
           f'<path d="M795 270 L795 240 L1075 240 L1075 270" fill="none" stroke="{C3}" stroke-opacity=".3" stroke-dasharray="4 5"/>'
           f'<text class="jb" x="935" y="226" font-size="11" text-anchor="middle" fill="#8d93ab">agent loop</text>'
           f'<rect x="740" y="350" width="390" height="30" rx="15" fill="#ffffff" fill-opacity=".05"/><text class="jb" x="760" y="370" font-size="12" fill="#eceef6">task → tools → answer</text>'
           f'<rect x="{760 + 150}" y="360" width="8" height="2" fill="{C1}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>')
    slides.append(f'<rect x="688" y="118" width="564" height="352" fill="url(#bgB)"/>{sb}')
    # slide C: data chart
    sc = ""
    vals = [40, 66, 52, 98, 80, 128, 112, 150]
    for i, v in enumerate(vals):
        x = 730 + i * 58
        sc += f'<rect x="{x}" y="{430 - v * 1.6:.0f}" width="34" height="{v * 1.6:.0f}" rx="6" fill="url(#barW)" fill-opacity=".85"><animate attributeName="height" values="0;{v * 1.6:.0f}" dur="1.4s" begin="{i * .08:.2f}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/><animate attributeName="y" values="430;{430 - v * 1.6:.0f}" dur="1.4s" begin="{i * .08:.2f}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>'
    sc += f'<polyline points="{" ".join(f"{747 + i * 58},{420 - v * 1.6 - 12:.0f}" for i, v in enumerate(vals))}" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="2.2" stroke-linejoin="round" stroke-dasharray="700"><animate attributeName="stroke-dashoffset" values="700;0" dur="2.4s" repeatCount="indefinite"/></polyline>'
    slides.append(f'<rect x="688" y="118" width="564" height="352" fill="url(#bgC)"/>{sc}')
    caps_r = [("AI / ML", C1, "Machine learning", "Models, features and experiments with Python."),
              ("GENAI", C3, "Generative AI & agents", "LLM apps that plan, use tools and act."),
              ("DATA", C2, "Data science", "Clean it, explore it, visualise it, explain it.")]
    right = (f'<g class="cardR"><rect x="660" y="0" width="620" height="640" rx="24" fill="url(#cardbg)"/><rect x="660" y="0" width="620" height="640" rx="24" fill="url(#dots2)"/>'
             f'<rect x="660.75" y=".75" width="618.5" height="638.5" rx="23.25" fill="none" stroke="url(#edgeR)" stroke-width="1.5"/>'
             f'<text class="jbb" x="688" y="46" font-size="12.5" fill="{C3}" letter-spacing="2.2">// FOCUS AREAS</text><text class="sg" x="688" y="86" font-size="29" fill="#eceef6" letter-spacing="-.5">Always learning, always building</text>'
             '<g clip-path="url(#winR)">')
    for i, sl in enumerate(slides):
        right += f'<g class="slide" style="animation-delay:{i * 4}s">{sl}</g>'
    right += "</g>"
    for i in range(3):  # story progress bars
        x = 708 + i * 178
        right += (f'<rect x="{x}" y="130" width="170" height="3" rx="1.5" fill="#fff" fill-opacity=".18"/><rect x="{x}" y="130" width="0" height="3" rx="1.5" fill="#fff">'
                  f'<animate attributeName="width" values="0;0;170;170" keyTimes="0;{i / 3:.4f};{(i + 1) / 3:.4f};1" dur="12s" repeatCount="indefinite"/></rect>')
    for i, (pill, col, t, sub) in enumerate(caps_r):
        right += (f'<g class="cap" style="animation-delay:{i * 4}s"><rect x="688" y="494" width="{26 + len(pill) * 9}" height="28" rx="14" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".5"/>'
                  f'<text class="jbb" x="{688 + 13}" y="513" font-size="11.5" fill="{col}" letter-spacing="1.4">{pill}</text><text class="sg" x="{688 + 44 + len(pill) * 9}" y="514" font-size="19" fill="#eceef6">{esc(t)}</text>'
                  f'<text class="sgm" x="688" y="552" font-size="15" fill="#8d93ab">{esc(sub)}</text></g>')
    # rings (philosophy: learn / build / experiment / deploy)
    right += f'<text class="jbb" x="688" y="596" font-size="10.5" fill="#8d93ab" letter-spacing="1.8">MY LOOP</text>'
    for i, (lab, col) in enumerate([("Learn", C1), ("Build", C3), ("Experiment", C2), ("Deploy", "#34d399")]):
        cx = 780 + i * 112; cy = 604; r = 11; circ = 2 * math.pi * r
        right += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="3.5"/>'
                  f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" transform="rotate(-90 {cx} {cy})">'
                  f'<animate attributeName="stroke-dashoffset" values="{circ:.1f};{circ * .1:.1f};{circ * .1:.1f};{circ:.1f}" keyTimes="0;.3;.85;1" dur="6s" begin="{i * .35:.2f}s" repeatCount="indefinite"/></circle>'
                  f'<text class="jb" x="{cx + 18}" y="{cy + 4}" font-size="11.5" fill="#eceef6">{lab}</text>')
    right += "</g>"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640" role="img" aria-label="What I build and my focus areas"><title>What I build and my focus areas</title>'
            f'<defs>{style_block(css)}{defs}</defs>{left}{right}</svg>')

# ───────────────────────────── README ─────────────────────────────
def build_readme():
    t = open(os.path.join(HERE, "README.tpl.md"), encoding="utf-8").read()
    v = datetime.date.today().strftime("%Y%m%d")
    return t.replace("{{V}}", v).replace("{{USER}}", CFG["user"]).replace("{{NAME}}", CFG["name"]).replace("{{ROLE}}", CFG["role"]) \
            .replace("{{EMAIL}}", CFG["email"]).replace("{{IG}}", CFG["instagram"]).replace("{{LI}}", CFG["linkedin_path"])

def main():
    print("Building profile for", CFG["user"], "(offline)" if OFFLINE else "")
    st = stats(); print("  stats:", {k: st[k] for k in ("repos", "stars", "forks", "followers", "live")})
    out = {"hero.svg": build_hero(), "id-dashboard.svg": build_id(st), "connect.svg": build_connect(), "stack.svg": build_stack(), "about-life.svg": build_about()}
    for n, s in out.items():
        left = re.findall(r"\{\{[^}]+\}\}", s)
        assert not left, (n, left[:3])
        open(os.path.join(HERE, n), "w", encoding="utf-8").write(s); print(f"  wrote {n:18s} {len(s) / 1024:7.0f} KB")
    if os.path.exists(os.path.join(HERE, "README.tpl.md")):
        open(os.path.join(HERE, "README.md"), "w", encoding="utf-8").write(build_readme()); print("  wrote README.md")

if __name__ == "__main__":
    main()
