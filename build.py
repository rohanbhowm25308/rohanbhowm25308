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


def logo_img(w, h, transparent=False, pad=0.0):
    """Your stylish R logo (assets/logo.png). Black background is removed when transparent=True."""
    from PIL import Image, ImageChops
    p = find_asset("logo", (".png", ".jpg", ".jpeg", ".webp"))
    if not p: return monogram(w, h, transparent)
    im = Image.open(p).convert("RGB")
    im = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)   # smooth upscale
    if transparent:
        a = im.convert("L").point(lambda v: min(255, int(v * 3.2)))  # luminance -> alpha: black vanishes, glow stays
        im = im.convert("RGBA"); im.putalpha(a)
        box = (int(w * (1 - pad)), int(h * (1 - pad)))
        im.thumbnail(box, Image.LANCZOS)
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0)); out.paste(im, ((w - im.width) // 2, (h - im.height) // 2), im)
        return out
    out = Image.new("RGB", (w, h), (8, 4, 6))
    im.thumbnail((int(w * (1 - pad)), int(h * (1 - pad))), Image.LANCZOS)
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out.convert("RGBA")

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
    return to_uri(logo_img(272, 336, pad=0.04), "jpeg")

def character_uri():
    from PIL import Image
    p = find_asset("character", (".png", ".webp"))
    if p:
        im = Image.open(p).convert("RGBA"); im.thumbnail((736, 848)); return to_uri(im, "png")
    return to_uri(logo_img(368, 424, transparent=True, pad=0.0), "png")

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
    # animated placeholder: live vector R logo (floats, sways, shines, orbiting ball)
    ph = f'''<g mask="url(#vmask)"><g mask="url(#vmaskB)">
    <rect x="560" y="0" width="724" height="540" fill="#0a0407"/>
    {connect_logo(922, 262, 2.0, style='solid')}
    <rect x="560" y="0" width="724" height="3" fill="{C1}" fill-opacity=".25"><animate attributeName="y" values="0;540;0" dur="6s" repeatCount="indefinite"/></rect></g></g>'''
    return ph, "HELLO.MP4"


# ───────────────────── animated 3D-style vector "R" logo (hero) ─────────────────────
def vector_logo(cx=922, cy=270, k=2.7):
    """Your stylish R as live vector art: floating, swaying, shine sweep, glow, and a ball that
    really orbits - passing BEHIND the letter on the far side and IN FRONT on the near side."""
    A = ("M52 49H139C153 49 162 63 162 81C162 96 157 104 150 111L183 179H150L100 118L113 104L108 98H125"
         "C133 98 137 92 137 85C137 78 133 72 125 72H74Z")
    B = "M73 80L93 98L77 179H50Z"
    px, py, a, b, ang = 111, 114, 102, 31, -20.6      # orbit centre, radii, tilt
    front = f"M{px + a} {py}A{a} {b} 0 0 1 {px - a} {py}"   # lower (near) half
    back  = f"M{px - a} {py}A{a} {b} 0 0 1 {px + a} {py}"   # upper (far) half
    full  = f"M{px + a} {py}A{a} {b} 0 0 1 {px - a} {py}A{a} {b} 0 0 1 {px + a} {py}Z"
    DUR = 5.5
    def ball(off, r, op):
        m = f'<animateMotion dur="{DUR}s" begin="{off}s" repeatCount="indefinite" path="{full}"/>'
        f_ = f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" values="{op};0" keyTimes="0;0.5" dur="{DUR}s" begin="{off}s" repeatCount="indefinite"/><circle r="{r}" fill="url(#lgBall)">{m}</circle></g>'
        b_ = f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" values="0;{op * .75:.2f}" keyTimes="0;0.5" dur="{DUR}s" begin="{off}s" repeatCount="indefinite"/><circle r="{r * .86:.1f}" fill="url(#lgBall)">{m}</circle></g>'
        return f_, b_
    fronts = backs = ""
    for off, r, op in [(-.50, 2.0, .18), (-.38, 2.6, .30), (-.26, 3.3, .50), (-.14, 4.2, .75), (0, 6.2, 1)]:   # comet tail + head
        fr, bk = ball(off, r, op); fronts += fr; backs += bk
    embers = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#ff8a7a" opacity="0"><animate attributeName="cy" values="{y};{y - 34}" dur="{d}s" begin="{o}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;.9;0" dur="{d}s" begin="{o}s" repeatCount="indefinite"/></circle>'
        for x, y, r, d, o in [(60, 150, 1.2, 4.2, 0), (95, 168, 1.6, 5.0, 1.3), (140, 160, 1.1, 4.6, 2.2), (170, 150, 1.5, 5.4, .7), (45, 120, 1.0, 4.8, 3.1), (125, 170, 1.3, 4.0, 2.8)])
    return f"""<g>
  <defs>
    <linearGradient id="lgFill" x1="0" y1="0" x2=".55" y2="1"><stop offset="0" stop-color="#ff6a55"/><stop offset=".35" stop-color="#ff1b2d"/><stop offset=".75" stop-color="#d1061b"/><stop offset="1" stop-color="#7a0010"/></linearGradient>
    <linearGradient id="lgRing" gradientUnits="userSpaceOnUse" x1="{px - a}" y1="0" x2="{px + a}" y2="0"><stop offset="0" stop-color="#ff3b4a" stop-opacity="0"/><stop offset=".25" stop-color="#ff4d5a"/><stop offset=".8" stop-color="#ffb199"/><stop offset="1" stop-color="#ff4d5a" stop-opacity=".1"/></linearGradient>
    <radialGradient id="lgBall"><stop offset="0" stop-color="#fff7e0"/><stop offset=".35" stop-color="#ffb347"/><stop offset="1" stop-color="#ff3b2f" stop-opacity="0"/></radialGradient>
    <radialGradient id="lgHalo"><stop offset="0" stop-color="#ff1b2d" stop-opacity=".55"/><stop offset="1" stop-color="#ff1b2d" stop-opacity="0"/></radialGradient>
    <linearGradient id="lgShine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <clipPath id="lgClip"><path d="{A}"/><path d="{B}"/></clipPath>
    <filter id="lgBlur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.6"/></filter>
  </defs>
  <g transform="translate({cx} {cy}) scale({k}) translate({-px} {-py})">
    <g><animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" keyTimes="0;.5;1" dur="4.5s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>
     <g transform="translate({px} {py})"><g><animateTransform attributeName="transform" type="scale" values="1 1;.93 1;1 1;1.0 1" keyTimes="0;.5;1;1" dur="7s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1;0 0 1 1"/>
      <g transform="translate({-px} {-py})">
        <ellipse cx="{px}" cy="{py}" rx="92" ry="64" fill="url(#lgHalo)"><animate attributeName="opacity" values=".55;1;.55" dur="3.2s" repeatCount="indefinite"/></ellipse>
        <g transform="rotate({ang} {px} {py})">
          <path d="{back}" fill="none" stroke="#ff4d5a" stroke-opacity=".38" stroke-width="1.5"/>
          {backs}
        </g>
        <g transform="translate(3.2 3.8)" fill="#4a0007"><path d="{A}"/><path d="{B}"/></g>
        <g><path d="{A}" fill="url(#lgFill)"/><path d="{B}" fill="url(#lgFill)"/>
          <g clip-path="url(#lgClip)"><rect x="-70" y="30" width="46" height="170" fill="url(#lgShine)" transform="skewX(-18)"><animate attributeName="x" values="-70;-70;260;260" keyTimes="0;.15;.55;1" dur="5.5s" repeatCount="indefinite"/></rect></g>
          <g fill="none" stroke="#ffd0c8" stroke-opacity=".55" stroke-width=".7" stroke-linejoin="round"><path d="{A}"/><path d="{B}"/></g></g>
        <g transform="rotate({ang} {px} {py})">
          <path d="{front}" fill="none" stroke="url(#lgRing)" stroke-width="5" opacity=".5" filter="url(#lgBlur)"/>
          <path d="{front}" fill="none" stroke="url(#lgRing)" stroke-width="2"/>
          {fronts}
        </g>
        {embers}
      </g></g></g>
    </g>
  </g>
</g>"""

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


# ───────────── ID-badge R: "scanner reveal" hologram (inside the photo frame) ─────────────
def id_logo(x0=144, y0=204, w=136, h=168):
    """R sits dim in the frame, a scan beam sweeps down and lights it up, then a VERIFIED tag pops."""
    import math as m
    A = ("M52 49H139C153 49 162 63 162 81C162 96 157 104 150 111L183 179H150L100 118L113 104L108 98H125"
         "C133 98 137 92 137 85C137 78 133 72 125 72H74Z")
    B = "M73 80L93 98L77 179H50Z"
    cx, cy, k = x0 + w / 2, y0 + 80, 0.74
    px, py = 116, 114
    D = 6
    rays = "".join(
        f'<path d="M{cx} {cy}L{cx + 130 * m.cos(m.radians(a - 4)):.1f} {cy + 130 * m.sin(m.radians(a - 4)):.1f}L{cx + 130 * m.cos(m.radians(a + 4)):.1f} {cy + 130 * m.sin(m.radians(a + 4)):.1f}Z" fill="#ff4d5a" fill-opacity=".10"/>'
        for a in range(0, 360, 36))
    pulses = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="30" fill="none" stroke="#ef4444" stroke-width="1.2" opacity="0"><animate attributeName="r" values="30;96" dur="3s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;.5;0" keyTimes="0;.2;1" dur="3s" begin="{b}s" repeatCount="indefinite"/></circle>' for b in (0, 1.5))
    bits = "".join(
        f'<text class="jb" x="{x}" y="{y0 + h}" font-size="9" fill="#ff6b6b" opacity="0">{ch}<animate attributeName="y" values="{y0 + h};{y0 + 8}" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;.45;0" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></text>'
        for x, ch, d, b in [(x0 + 12, "1", 4.2, 0), (x0 + 30, "0", 5.0, 1.1), (x0 + 52, "1", 4.6, 2.0), (x0 + 96, "0", 5.4, .6), (x0 + 112, "1", 4.4, 1.7), (x0 + 124, "0", 5.1, 2.6)])
    def br(dx, dy, sx, sy):
        px_, py_ = x0 + (8 if dx == 0 else w - 8), y0 + (8 if dy == 0 else h - 8)
        return f'<path d="M{px_} {py_ + 14 * sy}V{py_}H{px_ + 14 * sx}" fill="none" stroke="#ff6b6b" stroke-width="2" stroke-linecap="round"><animate attributeName="stroke-opacity" values=".9;.35;.9" dur="1.8s" repeatCount="indefinite"/></path>'
    brackets = br(0, 0, 1, 1) + br(1, 0, -1, 1) + br(0, 1, 1, -1) + br(1, 1, -1, -1)
    hgt = 150
    return f"""<g>
  <defs>
    <linearGradient id="idlBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b0a10"/><stop offset="1" stop-color="#0b0408"/></linearGradient>
    <linearGradient id="idlFace" x1="0" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="#ff7a66"/><stop offset=".35" stop-color="#ff1f33"/><stop offset="1" stop-color="#9a0b18"/></linearGradient>
    <linearGradient id="idlBeam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9aa2" stop-opacity="0"/><stop offset="1" stop-color="#ffd9d4" stop-opacity=".95"/></linearGradient>
    <radialGradient id="idlHalo"><stop offset="0" stop-color="#ff1b2d" stop-opacity=".6"/><stop offset="1" stop-color="#ff1b2d" stop-opacity="0"/></radialGradient>
    <clipPath id="idlRev"><rect x="{x0}" y="{y0}" width="{w}" height="0"><animate attributeName="height" values="0;0;{hgt};{hgt};{hgt}" keyTimes="0;.08;.58;.9;1" dur="{D}s" repeatCount="indefinite"/></rect></clipPath>
    <filter id="idlGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#idlBg)"/>
  <g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="30s" repeatCount="indefinite"/>{rays}</g>
  {pulses}
  <circle cx="{cx}" cy="{cy}" r="62" fill="url(#idlHalo)"><animate attributeName="opacity" values=".5;.9;.5" dur="2.6s" repeatCount="indefinite"/></circle>
  {bits}
  <g transform="translate({cx} {cy}) scale({k}) translate({-px} {-py})">
    <g fill="#2a0810" fill-opacity=".85" stroke="#ff4d5a" stroke-opacity=".4" stroke-width="1" stroke-linejoin="round"><path d="{A}"/><path d="{B}"/></g></g>
  <g clip-path="url(#idlRev)"><g>
    <animate attributeName="opacity" values="1;1;1;1;0" keyTimes="0;.08;.58;.9;1" dur="{D}s" repeatCount="indefinite"/>
    <g transform="translate({cx} {cy}) scale({k}) translate({-px} {-py})"><g filter="url(#idlGlow)">
      <animate attributeName="opacity" values="1;.88;1;.95;1" dur=".7s" repeatCount="indefinite"/>
      <path d="{A}" fill="url(#idlFace)"/><path d="{B}" fill="url(#idlFace)"/>
      <g fill="none" stroke="#ffe3dc" stroke-opacity=".75" stroke-width="1.1" stroke-linejoin="round"><path d="{A}"/><path d="{B}"/></g></g></g></g></g>
  <g><rect x="{x0}" y="{y0 - 14}" width="{w}" height="14" fill="url(#idlBeam)"><animate attributeName="y" values="{y0 - 14};{y0 - 14};{y0 + hgt - 14};{y0 + hgt - 14}" keyTimes="0;.08;.58;1" dur="{D}s" repeatCount="indefinite"/></rect>
     <rect x="{x0}" y="{y0 - 1.5}" width="{w}" height="2" fill="#fff" fill-opacity=".95"><animate attributeName="y" values="{y0 - 1.5};{y0 - 1.5};{y0 + hgt - 1.5};{y0 + hgt - 1.5}" keyTimes="0;.08;.58;1" dur="{D}s" repeatCount="indefinite"/></rect>
     <animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.08;.1;.56;.58;1" dur="{D}s" repeatCount="indefinite"/></g>
  {brackets}
  <g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.6;.66;.88;.96;1" dur="{D}s" repeatCount="indefinite"/>
    <rect x="{cx - 46}" y="{y0 + h - 34}" width="92" height="20" rx="10" fill="#34d399" fill-opacity=".16" stroke="#34d399" stroke-opacity=".7"/>
    <path d="M{cx - 34} {y0 + h - 24}l4 4 8 -9" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <text class="jbb" x="{cx - 18}" y="{y0 + h - 20}" font-size="10" fill="#34d399" letter-spacing="1.4">VERIFIED</text></g>
</g>"""

def build_id(st):
    c = CFG; s = recolor(tpl("id-dashboard.tpl.svg"))
    if find_asset("portrait", (".jpg", ".jpeg", ".png", ".webp")) or find_asset("hero", (".jpg", ".jpeg", ".png", ".webp")):
        port_uri = portrait_uri()
    else:   # no photo supplied -> animated scanner-reveal R inside the frame
        s = re.sub(r'<g clip-path="url\(#photoClip\)"><image[^>]*href="\{\{PORTRAIT\}\}"[^>]*/></g>',
                   lambda m_: '<g clip-path="url(#photoClip)">' + id_logo() + '</g>', s)
        port_uri = ""
    s = fill(s, PORTRAIT=port_uri, LANYARD=" &#183; ".join([c["name"].split()[0].upper() + ".DEV", "AI/ML"] * 2),
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


# ───────────── animated "signal hub" R logo (connect banner) — different style from the hero ─────────────
def connect_logo(cx=254, cy=250, k=1.7, style="outline"):
    """Neon-outline R that draws itself, then lights up, at the centre of a live network:
    broadcast rings, a spinning radar ring, and three nodes orbiting with live link lines."""
    import math as m
    A = ("M52 49H139C153 49 162 63 162 81C162 96 157 104 150 111L183 179H150L100 118L113 104L108 98H125"
         "C133 98 137 92 137 85C137 78 133 72 125 72H74Z")
    B = "M73 80L93 98L77 179H50Z"
    px, py = 116, 114
    D = 10
    rings = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="70" fill="none" stroke="#ef4444" stroke-width="1.6" opacity="0">'
        f'<animate attributeName="r" values="70;190" dur="4.8s" begin="{b}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".2 .6 .3 1"/>'
        f'<animate attributeName="opacity" values="0;.55;0" keyTimes="0;.15;1" dur="4.8s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for b in (0, 1.6, 3.2))
    ticks = "".join(
        f'<line x1="{cx + 122 * m.cos(m.radians(a)):.1f}" y1="{cy + 122 * m.sin(m.radians(a)):.1f}" x2="{cx + (130 if a % 90 else 136) * m.cos(m.radians(a)):.1f}" y2="{cy + (130 if a % 90 else 136) * m.sin(m.radians(a)):.1f}" stroke="#fb7185" stroke-opacity="{.7 if a % 90 == 0 else .35}" stroke-width="1.4"/>'
        for a in range(0, 360, 15))
    spin = (f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="36s" repeatCount="indefinite"/>{ticks}'
            f'<circle cx="{cx}" cy="{cy}" r="122" fill="none" stroke="#ef4444" stroke-opacity=".35" stroke-dasharray="2 8"/></g>'
            f'<g><animateTransform attributeName="transform" type="rotate" from="360 {cx} {cy}" to="0 {cx} {cy}" dur="52s" repeatCount="indefinite"/>'
            f'<circle cx="{cx}" cy="{cy}" r="158" fill="none" stroke="#f59e0b" stroke-opacity=".28" stroke-width="1.4" stroke-dasharray="26 12 4 12"/></g>')
    nodes = ""; lines = ""
    for rx, ry, tilt, T, ph, col in [(150, 62, -24, 16, 0.0, "#34d399"), (176, 84, 28, 24, 2.1, "#f59e0b"), (136, 50, 70, 12, 4.0, "#fb7185")]:
        N = 48; xs = []; ys = []
        for i in range(N + 1):
            t = ph + 2 * m.pi * i / N
            ex, ey = rx * m.cos(t), ry * m.sin(t)
            c, s_ = m.cos(m.radians(tilt)), m.sin(m.radians(tilt))
            xs.append(cx + ex * c - ey * s_); ys.append(cy + ex * s_ + ey * c)
        fx = ";".join(f"{v:.1f}" for v in xs); fy = ";".join(f"{v:.1f}" for v in ys)
        anim = lambda a, vals: f'<animate attributeName="{a}" values="{vals}" dur="{T}s" repeatCount="indefinite"/>'
        lines += (f'<line x1="{cx}" y1="{cy}" x2="{xs[0]:.1f}" y2="{ys[0]:.1f}" stroke="{col}" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="3 5">{anim("x2", fx)}{anim("y2", fy)}'
                  f'<animate attributeName="stroke-dashoffset" values="0;-16" dur=".9s" repeatCount="indefinite"/></line>')
        nodes += (f'<g><circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="17" fill="{col}" fill-opacity=".16">{anim("cx", fx)}{anim("cy", fy)}</circle>'
                  f'<circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="8.5" fill="#171a2c" stroke="{col}" stroke-width="2">{anim("cx", fx)}{anim("cy", fy)}</circle>'
                  f'<circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="3.2" fill="{col}">{anim("cx", fx)}{anim("cy", fy)}</circle></g>')
    if style == "solid":
        import math as _m
        NF, L, ZD, T3 = 40, 16, 8.0, 8
        frames = [_m.radians(38) * _m.sin(2 * _m.pi * f / NF) for f in range(NF + 1)]
        layers = ""
        for li in range(L + 1):
            z = -ZD + 2 * ZD * li / L
            kcol = li / L
            col = "#%02x%02x%02x" % (int(70 + (150 - 70) * kcol), int(0 + 6 * kcol), int(8 + 10 * kcol))
            tv = []; sv = []
            for th in frames:
                c_, s2 = _m.cos(th), _m.sin(th)
                tv.append(f"{px - c_ * px + z * s2:.3f} {-z * 0.22:.3f}"); sv.append(f"{c_:.4f} 1")
            a_t = f'<animateTransform attributeName="transform" type="translate" values="{";".join(tv)}" dur="{T3}s" repeatCount="indefinite"/>'
            a_s = f'<animateTransform attributeName="transform" type="scale" values="{";".join(sv)}" dur="{T3}s" repeatCount="indefinite"/>'
            if li < L:
                layers += f'<g>{a_t}<g fill="{col}">{a_s}<path d="{A}"/><path d="{B}"/></g></g>'
            else:   # front face: gradient, rim light, travelling shine
                layers += (f'<g>{a_t}<g>{a_s}<path d="{A}" fill="url(#cnFace)"/><path d="{B}" fill="url(#cnFace)"/>'
                           f'<g clip-path="url(#cnClip)"><rect x="-80" y="20" width="34" height="190" fill="url(#cnShine)" transform="skewX(-18)">'
                           f'<animate attributeName="x" values="-80;-80;260;260" keyTimes="0;.2;.6;1" dur="6s" repeatCount="indefinite"/></rect></g>'
                           f'<g fill="none" stroke="#ffe3dc" stroke-opacity=".7" stroke-width=".9" stroke-linejoin="round"><path d="{A}"/><path d="{B}"/></g></g></g>')
        rblock = (f'<ellipse cx="{cx}" cy="{cy + 150}" rx="95" ry="12" fill="#000" opacity=".5"><animate attributeName="rx" values="95;78;95" dur="{T3 / 2}s" repeatCount="indefinite"/></ellipse>'
                  f'<g transform="translate({cx} {cy}) scale({k}) translate({-px} {-py})">{layers}</g>')
    else:
        rblock = f"""  <g transform="translate({cx} {cy}) scale({k}) translate({-px} {-py})">
    <g><animateTransform attributeName="transform" type="scale" values="1;1.035;1" dur="3s" repeatCount="indefinite" additive="replace" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/>
      <g transform="translate({px} {py}) translate({-px} {-py})">
      <g fill="url(#cnFill)"><path d="{A}"/><path d="{B}"/>
        <animate attributeName="fill-opacity" values="0;0;.9;.9;0" keyTimes="0;.2;.34;.9;1" dur="{D}s" repeatCount="indefinite"/></g>
      <g clip-path="url(#cnClip)"><rect x="40" y="40" width="150" height="3" fill="url(#cnScan)"><animate attributeName="y" values="40;40;180;180" keyTimes="0;.34;.62;1" dur="{D}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.34;.36;.6;.62;1" dur="{D}s" repeatCount="indefinite"/></rect></g>
      <g fill="none" stroke="url(#cnStroke)" stroke-width="2.2" stroke-linejoin="round" filter="url(#cnGlow)" stroke-dasharray="1" stroke-dashoffset="1">
        <path d="{A}" pathLength="1"/><path d="{B}" pathLength="1"/>
        <animate attributeName="stroke-dashoffset" values="1;0;0;0;1" keyTimes="0;.22;.5;.9;1" dur="{D}s" repeatCount="indefinite"/></g>
      </g>
    </g>
  </g>
"""
    return f"""<g>
  <defs>
    <linearGradient id="cnFill" x1="0" y1="0" x2=".5" y2="1"><stop offset="0" stop-color="#ff6a55"/><stop offset=".5" stop-color="#ef1b2d"/><stop offset="1" stop-color="#8a0a14"/></linearGradient>
    <linearGradient id="cnStroke" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffd0c8"/><stop offset=".5" stop-color="#ff4d5a"/><stop offset="1" stop-color="#f59e0b"/></linearGradient>
    <linearGradient id="cnFace" x1="0" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="#ff7a66"/><stop offset=".3" stop-color="#ff2236"/><stop offset=".7" stop-color="#d20a1f"/><stop offset="1" stop-color="#8e0a16"/></linearGradient>
    <linearGradient id="cnShine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <radialGradient id="cnHalo"><stop offset="0" stop-color="#ef4444" stop-opacity=".5"/><stop offset="1" stop-color="#ef4444" stop-opacity="0"/></radialGradient>
    <linearGradient id="cnScan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <clipPath id="cnClip"><path d="{A}"/><path d="{B}"/></clipPath>
    <filter id="cnGlow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <circle cx="{cx}" cy="{cy}" r="150" fill="url(#cnHalo)"><animate attributeName="opacity" values=".6;1;.6" dur="3s" repeatCount="indefinite"/></circle>
  {rings}{spin}{lines}
  {rblock}
  {nodes}
</g>"""

def build_connect():
    c = CFG; s = recolor(tpl("connect.tpl.svg"))
    if find_asset("character", (".png", ".webp")):
        char_uri = character_uri()
    else:   # no pointing-character art supplied -> animated signal-hub logo
        s = re.sub(r'<g class="her"><g class="float"><image[^>]*href="\{\{CHARACTER\}\}"[^>]*/></g></g>',
                   lambda m_: '<g class="her">' + vector_logo(254, 252, 1.8) + '</g>', s)
        char_uri = ""
    s = fill(s, CONNECT_SUB=esc(c["connect_sub"]), USER=c["user"], EMAIL=esc(c["email"]), IG="@" + c["instagram"], LI=c["linkedin_path"][:26],
             QUOTE=esc(c["quote"][1]), CHARACTER=char_uri)
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
    import math as m
    rows = [
        ("LANGUAGES", C1, [("Python", "python"), ("C", "c"), ("C++", "cplusplus"), ("JavaScript", "javascript"), ("HTML5", "html5"), ("CSS", "css3")]),
        ("AI / ML & DATA", C2, [("TensorFlow", "tensorflow"), ("Pandas", "pandas"), ("NumPy", "numpy"), ("Scikit-learn", "scikitlearn"), ("Kaggle", "kaggle")]),
        ("GENERATIVE AI & AGENTS", C3, [("Generative AI", "g:spark"), ("LLMs", "g:brain"), ("RAG", "g:rag"), ("AI Agents", "g:bot"), ("Hugging Face", "huggingface")]),
        ("WEB & TOOLS", "#34d399", [("Flask", "flask"), ("Streamlit", "streamlit"), ("Bootstrap", "bootstrap"), ("Git", "git"), ("GitHub", "github"), ("MySQL", "mysql")]),
    ]
    palette = {"g:spark": C3, "g:brain": C2, "g:rag": C1, "g:bot": C3}
    body = ""; delay = .5; gi = 0
    for ri, (title, tint, chips) in enumerate(rows):
        y0 = 120 + ri * 80
        pw = 22 + len(str(len(chips))) * 8
        body += (f'<g class="fu" style="animation-delay:{delay:.2f}s"><rect x="552" y="{y0 + 5}" width="14" height="3" rx="1.5" fill="{tint}"/>'
                 f'<text class="jbb" x="574" y="{y0 + 10}" font-size="12" fill="#8d93ab" letter-spacing="2">{esc(title)}</text>'
                 f'<rect x="{574 + len(title) * 9.4 + 8:.0f}" y="{y0 - 2}" width="{pw}" height="17" rx="8.5" fill="{tint}" fill-opacity=".14" stroke="{tint}" stroke-opacity=".45"/>'
                 f'<text class="jbb" x="{574 + len(title) * 9.4 + 8 + pw / 2:.0f}" y="{y0 + 10}" font-size="10.5" text-anchor="middle" fill="{tint}">{len(chips)}</text></g>')
        x = 552
        for ci, (label, slug) in enumerate(chips):
            col = palette[slug] if slug.startswith("g:") else icon_color(slug)
            w = 40 + len(label) * 8.2 + 12
            ic = generic_icon(slug[2:], col) if slug.startswith("g:") else f'<path fill="{col}" d="{icon_path(slug)}"/>'
            wave = f'begin="{gi * .27:.2f}s"'
            body += (f'<g class="chip" style="animation-delay:{delay + .1 + ci * .07:.2f}s"><rect x="{x}" y="{y0 + 28}" width="{w:.0f}" height="40" rx="12" fill="{col}" fill-opacity=".08" stroke="{col}" stroke-opacity=".38">'
                     f'<animate attributeName="stroke-opacity" values=".38;1;.38;.38" keyTimes="0;.08;.2;1" dur="6.5s" {wave} repeatCount="indefinite"/>'
                     f'<animate attributeName="fill-opacity" values=".08;.24;.08;.08" keyTimes="0;.08;.2;1" dur="6.5s" {wave} repeatCount="indefinite"/></rect>'
                     f'<g transform="translate({x + 13},{y0 + 38}) scale(.83)">{ic}</g><text class="jb" x="{x + 42}" y="{y0 + 53}" font-size="14" fill="#eceef6">{esc(label)}</text></g>')
            x += w + 8; gi += 1
        delay += .25

    # ───── left: AI core with Saturn ring + depth-aware orbiting icons
    cx, cy, a, b, DUR_RING = 262, 274, 158, 90, 9
    full = lambda A_, B_: f"M{cx + A_} {cy}A{A_} {B_} 0 0 1 {cx - A_} {cy}A{A_} {B_} 0 0 1 {cx + A_} {cy}Z"
    half_f = lambda A_, B_: f"M{cx + A_} {cy}A{A_} {B_} 0 0 1 {cx - A_} {cy}"   # near (lower) half
    half_b = lambda A_, B_: f"M{cx - A_} {cy}A{A_} {B_} 0 0 1 {cx + A_} {cy}"   # far (upper) half
    def depth_pair(inner, path, dur, begin, rot=0, scale=(0.78, 1.24)):
        """returns (front_copy, back_copy): same motion, visible only on the near / far half of the orbit"""
        mo = f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" path="{path}"/>'
        sc = (f'<animateTransform attributeName="transform" type="scale" values="1;{scale[1]};1;{scale[0]};1" keyTimes="0;.25;.5;.75;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1;.4 0 .6 1;.4 0 .6 1"/>')
        def mk(vals):
            return (f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" values="{vals}" keyTimes="0;0.5" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
                    f'<g>{mo}<g transform="rotate({-rot})"><g>{sc}{inner}</g></g></g></g>')
        return mk("1;0"), mk("0;1")
    def icon_node(slug, r=19):
        col = icon_color(slug)
        return (f'<circle r="{r}" fill="#171a2c" stroke="{col}" stroke-opacity=".7" stroke-width="1.5"/><circle r="{r + 5}" fill="{col}" fill-opacity=".10"/>'
                f'<g transform="translate(-8,-8) scale(.67)"><path fill="{col}" d="{icon_path(slug)}"/></g>')
    back_layer = ""; front_layer = ""
    orbits = [0, 60, 120]
    for k, rot in enumerate(orbits):
        col = [C1, C2, C3][k]
        back_layer += (f'<g transform="rotate({rot} {cx} {cy})"><path d="{half_b(a, b)}" fill="none" stroke="{col}" stroke-opacity=".20" stroke-width="1.4"/></g>')
        front_layer += (f'<g transform="rotate({rot} {cx} {cy})"><path d="{half_f(a, b)}" fill="none" stroke="{col}" stroke-opacity=".5" stroke-width="1.6"/></g>')
    movers = [("python", 0, 0, 24), ("tensorflow", 0, -12, 24), ("github", 1, -2, 28), ("pandas", 1, -14, 28), ("scikitlearn", 2, -4, 30), ("huggingface", 2, -19, 30), ("numpy", 0, -18, 24), ("streamlit", 1, -9, 28)]
    bl = fl = ""
    for slug, k, begin, dur in movers:
        f_, b_ = depth_pair(icon_node(slug), full(a, b), dur, begin, rot=orbits[k])
        bl += f'<g transform="rotate({orbits[k]} {cx} {cy})">{b_}</g>'; fl += f'<g transform="rotate({orbits[k]} {cx} {cy})">{f_}</g>'
    # Saturn ring around the core
    rr, rb, tilt = 98, 24, -16
    spark_f, spark_b = depth_pair(f'<circle r="4.2" fill="url(#sBall)"/>', full(rr, rb), DUR_RING, 0, rot=tilt, scale=(.8, 1.2))
    ring_back = (f'<g transform="rotate({tilt} {cx} {cy})"><path d="{half_b(rr, rb)}" fill="none" stroke="{C2}" stroke-opacity=".5" stroke-width="2.2"/>{spark_b}</g>')
    ring_front = (f'<g transform="rotate({tilt} {cx} {cy})"><path d="{half_f(rr, rb)}" fill="none" stroke="url(#sRing)" stroke-width="7" opacity=".4" filter="url(#sBlur)"/>'
                  f'<path d="{half_f(rr, rb)}" fill="none" stroke="url(#sRing)" stroke-width="2.6"/>{spark_f}</g>')
    core = (f'<circle cx="{cx}" cy="{cy}" r="108" fill="url(#sHalo)"><animate attributeName="opacity" values=".55;1;.55" dur="3.4s" repeatCount="indefinite"/></circle>'
            + "".join(f'<circle cx="{cx}" cy="{cy}" r="62" fill="none" stroke="{C1}" stroke-width="1.3" opacity="0"><animate attributeName="r" values="62;112" dur="4.5s" begin="{t}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.45;0" keyTimes="0;.15;1" dur="4.5s" begin="{t}s" repeatCount="indefinite"/></circle>' for t in (0, 2.25))
            + f'<circle cx="{cx}" cy="{cy}" r="58" fill="url(#orbG)"/><circle cx="{cx}" cy="{cy}" r="58" fill="url(#sShade)"/>'
            f'<ellipse cx="{cx - 18}" cy="{cy - 26}" rx="24" ry="12" fill="#fff" opacity=".28" transform="rotate(-24 {cx - 18} {cy - 26})" filter="url(#sBlur)"/>'
            f'<text class="sg" x="{cx}" y="{cy + 14}" font-size="40" text-anchor="middle" fill="#fff">AI<animate attributeName="opacity" values="1;.86;1" dur="2.6s" repeatCount="indefinite"/></text>')
    # twinkling stars + a shooting star
    stars = ""
    for i, (sx, sy, sr) in enumerate([(70, 150, 1.4), (120, 128, 1), (205, 120, 1.2), (330, 140, 1.5), (430, 175, 1), (452, 260, 1.3), (85, 340, 1.2), (150, 420, 1), (330, 430, 1.3), (440, 380, 1), (60, 250, 1), (395, 120, 1.1)]):
        stars += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="#fff" opacity=".1"><animate attributeName="opacity" values=".08;.7;.08" dur="{2.6 + (i % 4) * .7:.1f}s" begin="{i * .37:.2f}s" repeatCount="indefinite"/></circle>'
    shoot = (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.1;.13;.25;1" dur="9s" begin="2s" repeatCount="indefinite"/>'
             f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;150 75;150 75" keyTimes="0;.1;.25;1" dur="9s" begin="2s" repeatCount="indefinite"/>'
             f'<line x1="60" y1="170" x2="30" y2="155" stroke="url(#sTail)" stroke-width="2" stroke-linecap="round"/><circle cx="60" cy="170" r="2" fill="#fff"/></g>')
    # typing ticker
    msg = "now exploring: AI agents · RAG · LLM apps"; tw = len(msg) * 7.3
    ticker = (f'<defs><clipPath id="tk"><rect x="40" y="446" width="0" height="22"><animate attributeName="width" values="0;{tw + 24:.0f};{tw + 24:.0f};0" keyTimes="0;.35;.92;1" dur="11s" repeatCount="indefinite"/></rect></clipPath></defs>'
              f'<g class="fu" style="animation-delay:1.4s"><circle cx="46" cy="457" r="3" fill="#34d399"><animate attributeName="opacity" values="1;.25;1" dur="1.2s" repeatCount="indefinite"/></circle>'
              f'<g clip-path="url(#tk)"><text class="jb" x="58" y="461" font-size="12" fill="#8d93ab">{esc(msg)}</text></g>'
              f'<rect x="58" y="450" width="1.6" height="14" fill="{C1}"><animate attributeName="x" values="58;{58 + tw:.0f};{58 + tw:.0f};58" keyTimes="0;.35;.92;1" dur="11s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect></g>')
    defs = (f'<linearGradient id="cardbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#171a2c"/><stop offset="1" stop-color="#0f1120"/></linearGradient>'
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C3}" stop-opacity=".55"/></linearGradient>'
            f'<radialGradient id="orbG" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="{C3}"/><stop offset=".55" stop-color="{C1}"/><stop offset="1" stop-color="#7f1d1d"/></radialGradient>'
            f'<radialGradient id="sShade" cx=".35" cy=".3" r=".95"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#2a0306" stop-opacity=".55"/></radialGradient>'
            f'<radialGradient id="sHalo"><stop offset="0" stop-color="{C1}" stop-opacity=".38"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="sBall"><stop offset="0" stop-color="#fff7e0"/><stop offset=".4" stop-color="#ffb347"/><stop offset="1" stop-color="#ff3b2f" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="sRing" gradientUnits="userSpaceOnUse" x1="{cx - 100}" y1="0" x2="{cx + 100}" y2="0"><stop offset="0" stop-color="{C2}" stop-opacity=".2"/><stop offset=".5" stop-color="#ffd0c8"/><stop offset="1" stop-color="{C3}" stop-opacity=".5"/></linearGradient>'
            f'<linearGradient id="sTail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
            f'<linearGradient id="sBar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            f'<filter id="sBlur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>'
            f'<pattern id="dots3" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r=".8" fill="#fff" fill-opacity=".05"/></pattern>')
    css = ".chip{animation:chipIn .6s cubic-bezier(.2,.8,.2,1) both}@keyframes chipIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}"
    title = (f'<g class="fu" style="animation-delay:.1s"><text class="jbb" x="40" y="54" font-size="12.5" fill="{C1}" letter-spacing="2.2">// TECH STACK</text>'
             f'<rect x="168" y="43" width="7" height="12" fill="{C1}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>'
             f'<text class="sg" x="40" y="94" font-size="29" fill="#eceef6" letter-spacing="-.5">Tools I build with</text>'
             f'<rect x="40" y="106" width="0" height="3" rx="1.5" fill="url(#sBar)"><animate attributeName="width" values="0;96" dur=".9s" begin=".5s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 480" width="1280" height="480" role="img" aria-label="Tech stack"><title>Tech stack</title>'
            f'<defs>{style_block(css)}{defs}</defs>'
            f'<rect width="1280" height="480" rx="24" fill="url(#cardbg)"/><rect width="1280" height="480" rx="24" fill="url(#dots3)"/>'
            f'<rect x=".75" y=".75" width="1278.5" height="478.5" rx="23.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>'
            f'{title}<line x1="520" y1="120" x2="520" y2="440" stroke="#262a42"/>{stars}{shoot}'
            f'{back_layer}{bl}{ring_back}{core}{ring_front}{front_layer}{fl}{ticker}{body}</svg>')

# ───────────────────────────── ABOUT / FOCUS (two cards) ─────────────────────────────
def build_about():
    import math as m, random
    rnd = random.Random(11)
    T = 7.0                      # left pipeline loop (s)
    G = {"in": C3, "orc": C1, "llm": C2, "tools": C3, "mem": C2, "out": "#34d399"}

    # ---------- small helpers ----------
    def hl(windows, peak, total):
        """keyTimes/values for a glow that fades in/out inside each (start,end) window"""
        pts = [(0, 0)]
        for s, e in windows:
            pts += [(s, 0), (s + .25, peak), (e, peak), (e + .25, 0)]
        pts.append((total, 0))
        kt = ";".join(f"{min(1, t / total):.4f}" for t, _ in pts); vv = ";".join(str(v) for _, v in pts)
        return f'values="{vv}" keyTimes="{kt}"'
    def packet(path, a, b, col, rev=False, r=4.6, total=T):
        ka, kb = a / total, b / total
        kp = "1;1;0;0" if rev else "0;0;1;1"
        return (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{ka:.4f};{ka + .004:.4f};{kb - .004:.4f};{kb:.4f};1" dur="{total}s" repeatCount="indefinite"/>'
                f'<circle r="{r * 2.4}" fill="{col}" opacity=".25"><animateMotion dur="{total}s" repeatCount="indefinite" path="{path}" keyPoints="{kp}" keyTimes="0;{ka:.4f};{kb:.4f};1" calcMode="linear"/></circle>'
                f'<circle r="{r}" fill="#fff"><animateMotion dur="{total}s" repeatCount="indefinite" path="{path}" keyPoints="{kp}" keyTimes="0;{ka:.4f};{kb:.4f};1" calcMode="linear"/></circle></g>')
    def window_chrome(x, label, extra=""):
        return (f'<rect x="{x}" y="118" width="564" height="34" fill="#1c2036"/>'
                f'<circle cx="{x + 18}" cy="135" r="5" fill="#ff5f57"/><circle cx="{x + 34}" cy="135" r="5" fill="#febc2e"/><circle cx="{x + 50}" cy="135" r="5" fill="#28c840"/>'
                f'<rect x="{x + 150}" y="126" width="264" height="18" rx="9" fill="#0b0d1b"/><text class="jb" x="{x + 282}" y="139" font-size="11" fill="#8d93ab" text-anchor="middle">{label}</text>'
                f'<rect class="cursor" x="{x + 404}" y="130" width="1.5" height="11" fill="{C1}"/>{extra}')

    # ---------- defs / css ----------
    css = (".slide{animation:slide 12s cubic-bezier(.2,.8,.2,1) infinite both}@keyframes slide{0%{opacity:0;transform:translateX(46px)}5%{opacity:1;transform:translateX(0)}29%{opacity:1;transform:translateX(0)}33.3%{opacity:0;transform:translateX(-46px)}100%{opacity:0;transform:translateX(-46px)}}"
           ".cap{animation:cap 12s ease infinite both}@keyframes cap{0%{opacity:0;transform:translateY(10px)}6%{opacity:1;transform:translateY(0)}29%{opacity:1;transform:translateY(0)}33%{opacity:0;transform:translateY(-8px)}100%{opacity:0}}"
           ".row{animation:rowIn .7s cubic-bezier(.2,.8,.2,1) both}@keyframes rowIn{from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:translateX(0)}}"
           ".cardL{animation:fadeUp .8s cubic-bezier(.2,.8,.2,1) .1s both}.cardR{animation:fadeUp .8s cubic-bezier(.2,.8,.2,1) .3s both}.cursor{animation:pulse 1s steps(1) infinite}")
    def grad(i, c1, c2): return f'<linearGradient id="{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
    defs = (grad("cardbg", "#171a2c", "#0f1120") + grad("edgeL", C1 + "99", "#262a42") + grad("edgeR", C3 + "99", "#262a42")
            + f'<linearGradient id="sweepL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}" stop-opacity="0"/><stop offset=".5" stop-color="#ffb199"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            + f'<linearGradient id="sweepR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C3}" stop-opacity="0"/><stop offset=".5" stop-color="#ffd9a0"/><stop offset="1" stop-color="{C2}"/></linearGradient>'
            + f'<linearGradient id="nodeBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e2238"/><stop offset="1" stop-color="#141729"/></linearGradient>'
            + f'<linearGradient id="bgA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a1018"/><stop offset="1" stop-color="#130a14"/></linearGradient>'
            + f'<linearGradient id="bgB" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b1a10"/><stop offset="1" stop-color="#140d12"/></linearGradient>'
            + f'<linearGradient id="bgC" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a1220"/><stop offset="1" stop-color="#110c16"/></linearGradient>'
            + f'<linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></linearGradient>'
            + f'<linearGradient id="lineG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C3}"/><stop offset="1" stop-color="#fff"/></linearGradient>'
            + f'<radialGradient id="blobL"><stop offset="0" stop-color="{C1}" stop-opacity=".30"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            + f'<radialGradient id="blobR"><stop offset="0" stop-color="{C3}" stop-opacity=".26"/><stop offset="1" stop-color="{C3}" stop-opacity="0"/></radialGradient>'
            + '<clipPath id="winL"><rect x="28" y="118" width="564" height="352" rx="14"/></clipPath><clipPath id="winR"><rect x="688" y="118" width="564" height="352" rx="14"/></clipPath>'
            + '<clipPath id="cardL"><rect x="0" y="0" width="620" height="640" rx="24"/></clipPath><clipPath id="cardR"><rect x="660" y="0" width="620" height="640" rx="24"/></clipPath>'
            + '<pattern id="dots2" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r=".8" fill="#fff" fill-opacity=".05"/></pattern>'
            + '<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>'
            + f'<filter id="gl2" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    # ================= LEFT CARD =================
    N = {"in": (100, 278, 112, 44), "orc": (284, 278, 144, 60), "llm": (494, 204, 116, 44), "tools": (494, 278, 116, 44), "mem": (494, 352, 126, 44), "out": (284, 384, 116, 44)}
    def ctr(k): return N[k][0], N[k][1]
    def edge(a, b):
        (x1, y1, w1, h1), (x2, y2, w2, h2) = N[a], N[b]
        if a == "orc" and b == "out": return f"M{x1} {y1 + h1 // 2}V{y2 - h2 // 2}"
        sx = x1 + w1 // 2; ex = x2 - w2 // 2
        if abs(y1 - y2) < 3: return f"M{sx} {y1}H{ex}"
        mx = (sx + ex) / 2
        return f"M{sx} {y1}C{mx} {y1} {mx} {y2} {ex} {y2}"
    E = {k: edge(*k) for k in [("in", "orc"), ("orc", "llm"), ("orc", "tools"), ("orc", "mem"), ("orc", "out")]}
    diag = '<rect x="28" y="152" width="564" height="318" fill="#0f1224"/><rect x="28" y="152" width="564" height="318" fill="url(#dots2)"/>'
    for (a, b), d in E.items():
        diag += f'<path d="{d}" fill="none" stroke="{G[b]}" stroke-opacity=".28" stroke-width="1.6" stroke-dasharray="4 5"><animate attributeName="stroke-dashoffset" values="0;-18" dur="1.4s" repeatCount="indefinite"/></path>'
    # packets
    diag += packet(E[("in", "orc")], .3, 1.0, G["in"])
    for k, col in (("llm", G["llm"]), ("tools", G["tools"]), ("mem", G["mem"])):
        diag += packet(E[("orc", k)], 1.2, 2.0, col)
        diag += packet(E[("orc", k)], 2.7, 3.4, col, rev=True)
    diag += packet(E[("orc", "out")], 3.9, 4.6, G["out"])
    def node(k, label, sub, windows, big=False):
        x, y, w, h = N[k]; col = G[k]
        return (f'<g><rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" rx="12" fill="{col}" opacity="0" filter="url(#gl)"><animate attributeName="opacity" {hl(windows, .75, T)} dur="{T}s" repeatCount="indefinite"/></rect>'
                f'<rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" rx="12" fill="url(#nodeBg)" stroke="{col}" stroke-opacity=".75" stroke-width="1.6"/>'
                f'<rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" rx="12" fill="{col}" opacity="0"><animate attributeName="opacity" {hl(windows, .18, T)} dur="{T}s" repeatCount="indefinite"/></rect>'
                f'<text class="sg" x="{x}" y="{y + (-2 if sub else 5)}" font-size="{15 if big else 13}" text-anchor="middle" fill="#eceef6">{esc(label)}</text>'
                + (f'<text class="jb" x="{x}" y="{y + 14}" font-size="9.5" text-anchor="middle" fill="#8d93ab">{esc(sub)}</text>' if sub else "") + '</g>')
    diag += (node("in", "Request", "user / data", [(.2, 1.0)]) + node("orc", "Orchestrator", "plans & routes", [(1.0, 1.7), (3.4, 3.95)], True)
             + node("llm", "LLM", "reasoning", [(2.0, 2.7)]) + node("tools", "Tools & APIs", "actions", [(2.0, 2.7)]) + node("mem", "Memory / RAG", "context", [(2.0, 2.7)])
             + node("out", "Answer", "result", [(4.6, 6.4)]))
    ox, oy = ctr("out")
    diag += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{4.7 / T:.4f};{4.85 / T:.4f};{6.3 / T:.4f};{6.6 / T:.4f};1" dur="{T}s" repeatCount="indefinite"/>'
             f'<circle cx="{ox + 70}" cy="{oy}" r="13" fill="#34d399" fill-opacity=".18" stroke="#34d399"/><path d="M{ox + 64} {oy}l4.5 4.5 8 -9" fill="none" stroke="#34d399" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>')
    # status bar
    diag += ('<rect x="28" y="440" width="564" height="30" fill="#0b0d1b"/><line x1="28" y1="440" x2="592" y2="440" stroke="#ffffff" stroke-opacity=".06"/>'
             f'<circle cx="46" cy="455" r="4" fill="#34d399"><animate attributeName="opacity" values="1;.3;1" dur="1.2s" repeatCount="indefinite"/></circle>'
             f'<text class="jb" x="60" y="459" font-size="11.5" fill="#8d93ab" opacity="1"><animate attributeName="opacity" calcMode="discrete" values="1;0;1" keyTimes="0;{4.7 / T:.4f};{6.8 / T:.4f}" dur="{T}s" repeatCount="indefinite"/>agent.run(task)  ·  planning · calling tools…</text>'
             f'<text class="jb" x="60" y="459" font-size="11.5" fill="#34d399" opacity="0"><animate attributeName="opacity" calcMode="discrete" values="0;1;0" keyTimes="0;{4.7 / T:.4f};{6.8 / T:.4f}" dur="{T}s" repeatCount="indefinite"/>done  ·  3 tools  ·  0.9s</text>'
             '<text class="jb" x="576" y="459" font-size="11" fill="#5d6483" text-anchor="end">v2.0 · live</text>')
    left = ('<g class="cardL">'
            '<rect x="0" y="0" width="620" height="640" rx="24" fill="url(#cardbg)"/>'
            f'<g clip-path="url(#cardL)"><circle cx="520" cy="60" r="190" fill="url(#blobL)"><animate attributeName="cx" values="520;430;520" dur="12s" repeatCount="indefinite"/><animate attributeName="cy" values="60;110;60" dur="12s" repeatCount="indefinite"/></circle></g>'
            '<rect x="0" y="0" width="620" height="640" rx="24" fill="url(#dots2)"/>'
            '<rect x=".75" y=".75" width="618.5" height="638.5" rx="23.25" fill="none" stroke="url(#edgeL)" stroke-width="1.5"/>'
            '<rect x="1" y="1" width="618" height="638" rx="23" fill="none" stroke="url(#sweepL)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray=".16 .84"><animate attributeName="stroke-dashoffset" values="1;0" dur="9s" repeatCount="indefinite"/></rect>'
            f'<text class="jbb" x="28" y="46" font-size="12.5" fill="{C1}" letter-spacing="2.2">// WHAT I BUILD</text><text class="sg" x="28" y="86" font-size="29" fill="#eceef6" letter-spacing="-.5">Intelligent apps, end to end</text>'
            f'<g clip-path="url(#winL)"><rect x="28" y="118" width="564" height="352" fill="#0f1224"/>{window_chrome(28, "localhost:8501/orchestrator-ai")}{diag}</g>'
            '<rect x="28.5" y="118.5" width="563" height="351" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity=".10"/>')
    caps = [("brain", C1, "AI / ML & Data Science", "Python, TensorFlow, Pandas, NumPy, scikit-learn"),
            ("spark", C2, "Generative AI & AI Agents", "LLMs, RAG and agentic workflows"),
            ("rag", C3, "Web apps & deployment", "Flask, Streamlit, REST APIs, Render")]
    for i, (g, col, t, sub) in enumerate(caps):
        y = 492 + i * 48
        left += (f'<g class="row" style="animation-delay:{.9 + i * .15:.2f}s"><rect x="28" y="{y}" width="40" height="40" rx="12" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".4">'
                 f'<animate attributeName="stroke-opacity" values=".4;1;.4;.4" keyTimes="0;.1;.25;1" dur="{T}s" begin="{i * 2.2:.1f}s" repeatCount="indefinite"/></rect>'
                 f'<g transform="translate(36,{y + 8})">{generic_icon(g, col)}</g><text class="sg" x="82" y="{y + 17}" font-size="15.5" fill="#eceef6">{esc(t)}</text><text class="jb" x="82" y="{y + 34}" font-size="11.5" fill="#8d93ab">{esc(sub)}</text></g>')
    left += "</g>"

    # ================= RIGHT CARD (carousel) =================
    slides = []
    # --- slide A: neural network with live signals + loss curve
    layers = [(3, 756), (5, 852), (5, 948), (2, 1044)]
    pos = [[(x, 300 + (j - (n - 1) / 2) * 50) for j in range(n)] for n, x in layers]
    na = '<rect x="688" y="118" width="564" height="352" fill="url(#bgA)"/>'
    for li in range(3):
        for (x1, y1) in pos[li]:
            for (x2, y2) in pos[li + 1]:
                na += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C2}" stroke-opacity=".17" stroke-width="1"/>'
    for li in range(3):                       # travelling signals
        for j in range(5):
            a_ = rnd.choice(pos[li]); b_ = rnd.choice(pos[li + 1]); col = [C3, "#fff", C1][j % 3]
            na += (f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.02;.22;.26;1" dur="2.4s" begin="{li * .55 + j * .17:.2f}s" repeatCount="indefinite"/>'
                   f'<circle r="3.4" fill="{col}"><animateMotion dur="2.4s" begin="{li * .55 + j * .17:.2f}s" repeatCount="indefinite" path="M{a_[0]} {a_[1]}L{b_[0]} {b_[1]}" keyPoints="0;1;1" keyTimes="0;.25;1" calcMode="linear"/></circle></g>')
    for li, col in enumerate(pos):
        for j, (x, y) in enumerate(col):
            c = [C3, C1, C2, "#34d399"][li]
            na += (f'<circle cx="{x}" cy="{y}" r="11" fill="#171a2c" stroke="{c}" stroke-width="1.8"><animate attributeName="fill" values="#171a2c;{c};#171a2c;#171a2c" keyTimes="0;.1;.3;1" dur="2.4s" begin="{li * .55 + .5 + j * .05:.2f}s" repeatCount="indefinite"/></circle>')
    for (x, _), lab in zip(layers, ["input", "hidden", "hidden", "output"]):
        na += f'<text class="jb" x="{x}" y="446" font-size="10.5" text-anchor="middle" fill="#8d93ab" letter-spacing="1.4">{lab}</text>'
    lx, ly, lw, lh = 1100, 176, 130, 92
    pts = [(lx + 12 + i * (lw - 24) / 11, ly + lh - 14 - (lh - 34) * (1 - m.exp(-i / 3.2)) * .96) for i in range(12)]
    ld = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    na += (f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="12" fill="#000" fill-opacity=".28" stroke="#fff" stroke-opacity=".08"/>'
           f'<text class="jbb" x="{lx + 12}" y="{ly + 18}" font-size="10" fill="#8d93ab" letter-spacing="1.4">LOSS</text><text class="jbb" x="{lx + lw - 12}" y="{ly + 18}" font-size="10" fill="#34d399" text-anchor="end">↓ 0.18</text>'
           f'<path d="{ld}" fill="none" stroke="url(#lineG)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" values="1;0;0" keyTimes="0;.3;1" dur="12s" repeatCount="indefinite"/></path>')
    slides.append(na)
    # --- slide B: agent loop (plan -> act -> observe)
    cx, cy, R = 970, 300, 92
    angs = [-90, 30, 150]; names = [("Plan", "break it down", C3), ("Act", "call tools", C1), ("Observe", "check result", C2)]
    sb = '<rect x="688" y="118" width="564" height="352" fill="url(#bgB)"/>'
    sb += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#fff" stroke-opacity=".10" stroke-width="1.4" stroke-dasharray="3 6"><animate attributeName="stroke-dashoffset" values="0;-18" dur="2s" repeatCount="indefinite"/></circle>'
    sb += f'<circle cx="{cx}" cy="{cy}" r="38" fill="url(#nodeBg)" stroke="{C1}" stroke-opacity=".7" stroke-width="1.6"/><circle cx="{cx}" cy="{cy}" r="48" fill="none" stroke="{C1}" stroke-opacity=".3"><animate attributeName="r" values="42;62;42" dur="3s" repeatCount="indefinite"/><animate attributeName="stroke-opacity" values=".5;0;.5" dur="3s" repeatCount="indefinite"/></circle>'
    sb += f'<g transform="translate({cx - 12},{cy - 22}) scale(1)">{generic_icon("bot", "#eceef6")}</g><text class="sg" x="{cx}" y="{cy + 18}" font-size="12" text-anchor="middle" fill="#eceef6" letter-spacing="1">AGENT</text>'
    TB = 6.0
    for i, ((nm, sub, col), a) in enumerate(zip(names, angs)):
        px_ = cx + R * m.cos(m.radians(a)); py_ = cy + R * m.sin(m.radians(a))
        sb += (f'<g><rect x="{px_ - 52:.0f}" y="{py_ - 22:.0f}" width="104" height="44" rx="13" fill="{col}" opacity="0" filter="url(#gl)"><animate attributeName="opacity" {hl([(i * 2 - .05 if i else 0, i * 2 + 1.6)], .7, TB)} dur="{TB}s" repeatCount="indefinite"/></rect>'
               f'<rect x="{px_ - 52:.0f}" y="{py_ - 22:.0f}" width="104" height="44" rx="13" fill="url(#nodeBg)" stroke="{col}" stroke-width="1.7"/>'
               f'<text class="sg" x="{px_:.0f}" y="{py_ - 2:.0f}" font-size="14" text-anchor="middle" fill="#eceef6">{nm}</text><text class="jb" x="{px_:.0f}" y="{py_ + 13:.0f}" font-size="9.5" text-anchor="middle" fill="#8d93ab">{sub}</text></g>')
    orbit = f"M{cx} {cy - R}A{R} {R} 0 1 1 {cx} {cy + R}A{R} {R} 0 1 1 {cx} {cy - R}Z"
    sb += (f'<circle r="11" fill="{C3}" opacity=".35" filter="url(#gl2)"><animateMotion dur="{TB}s" repeatCount="indefinite" path="{orbit}"/></circle><circle r="5" fill="#fff"><animateMotion dur="{TB}s" repeatCount="indefinite" path="{orbit}"/></circle>')
    for k, (tx, ty, lab, col) in enumerate([(790, 200, "web search", C3), (1150, 210, "python tool", C1), (1150, 400, "vector DB", C2)]):
        w_ = 26 + len(lab) * 7.2
        sb += (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="{3 + k * .6:.1f}s" repeatCount="indefinite"/>'
               f'<line x1="{tx}" y1="{ty}" x2="{cx}" y2="{cy}" stroke="{col}" stroke-opacity=".18" stroke-dasharray="3 5"/>'
               f'<rect x="{tx - w_ / 2:.0f}" y="{ty - 14}" width="{w_:.0f}" height="28" rx="14" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".55"/><text class="jb" x="{tx}" y="{ty + 4}" font-size="11.5" text-anchor="middle" fill="#eceef6">{lab}</text></g>')
    sb += f'<text class="jb" x="720" y="446" font-size="10.5" fill="#8d93ab" letter-spacing="1.4">reason → act → observe → repeat</text>'
    slides.append(sb)
    # --- slide C: data / accuracy chart
    vals = [52, 58, 56, 66, 71, 69, 80, 85, 89, 94]
    px0, px1, py0, py1 = 740, 1200, 240, 420
    cp = [(px0 + i * (px1 - px0) / 9, py1 - (v - 45) / 55 * (py1 - py0)) for i, v in enumerate(vals)]
    ld2 = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in cp)
    ad2 = ld2 + f" L{px1} {py1} L{px0} {py1} Z"
    sc = '<rect x="688" y="118" width="564" height="352" fill="url(#bgC)"/>'
    for gy, lab in [(py0, "100%"), ((py0 + py1) / 2, "75%"), (py1, "50%")]:
        sc += f'<line x1="{px0 - 6}" y1="{gy}" x2="{px1 + 10}" y2="{gy}" stroke="#fff" stroke-opacity=".09" stroke-dasharray="4 6"/><text class="jb" x="{px0 - 12}" y="{gy + 4}" font-size="10" text-anchor="end" fill="#8d93ab">{lab}</text>'
    for i, (name, val, col) in enumerate([("accuracy", "94.2%", C3), ("f1 score", "0.91", C2), ("loss", "0.18", "#34d399")]):
        bx = 724 + i * 150
        sc += (f'<rect x="{bx}" y="164" width="138" height="42" rx="12" fill="{col}" fill-opacity=".10" stroke="{col}" stroke-opacity=".5"/>'
               f'<text class="jb" x="{bx + 12}" y="181" font-size="9.5" fill="#8d93ab" letter-spacing="1.4">{name.upper()}</text><text class="sg" x="{bx + 12}" y="199" font-size="17" fill="#eceef6">{val}</text>')
    sc += (f'<defs><clipPath id="revC"><rect x="{px0 - 12}" y="{py0 - 20}" width="0" height="{py1 - py0 + 40}"><animate attributeName="width" values="0;0;{px1 - px0 + 40};{px1 - px0 + 40}" keyTimes="0;.667;.88;1" dur="12s" repeatCount="indefinite"/></rect></clipPath></defs>'
           f'<g clip-path="url(#revC)"><path d="{ad2}" fill="url(#areaG)"/><path d="{ld2}" fill="none" stroke="url(#lineG)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#gl2)"/>')
    for (x, y) in cp: sc += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#0f1120" stroke="#fff" stroke-width="1.6"/>'
    sc += '</g>'
    ex, ey = cp[-1]
    sc += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;.88;.9;1" dur="12s" repeatCount="indefinite"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="6" fill="{C3}"><animate attributeName="r" values="6;14;6" dur="1.6s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0;.8" dur="1.6s" repeatCount="indefinite"/></circle>'
           f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5.5" fill="#fff"/></g>')
    for i in range(0, 10, 3): sc += f'<text class="jb" x="{cp[i][0]:.0f}" y="{py1 + 20}" font-size="10" text-anchor="middle" fill="#8d93ab">ep {i + 1}</text>'
    sc += f'<text class="jb" x="{cp[9][0]:.0f}" y="{py1 + 20}" font-size="10" text-anchor="middle" fill="#8d93ab">ep 10</text>'
    slides.append(sc)

    caps_r = [("AI / ML", C1, "Machine learning", "Models, features and experiments with Python."),
              ("GENAI", C3, "Generative AI & agents", "LLM apps that plan, use tools and act."),
              ("DATA", C2, "Data science", "Clean it, explore it, visualise it, explain it.")]
    right = ('<g class="cardR">'
             '<rect x="660" y="0" width="620" height="640" rx="24" fill="url(#cardbg)"/>'
             f'<g clip-path="url(#cardR)"><circle cx="760" cy="580" r="200" fill="url(#blobR)"><animate attributeName="cx" values="760;860;760" dur="13s" repeatCount="indefinite"/><animate attributeName="cy" values="580;520;580" dur="13s" repeatCount="indefinite"/></circle></g>'
             '<rect x="660" y="0" width="620" height="640" rx="24" fill="url(#dots2)"/>'
             '<rect x="660.75" y=".75" width="618.5" height="638.5" rx="23.25" fill="none" stroke="url(#edgeR)" stroke-width="1.5"/>'
             '<rect x="661" y="1" width="618" height="638" rx="23" fill="none" stroke="url(#sweepR)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray=".16 .84"><animate attributeName="stroke-dashoffset" values="1;0" dur="9s" begin="1.5s" repeatCount="indefinite"/></rect>'
             f'<text class="jbb" x="688" y="46" font-size="12.5" fill="{C3}" letter-spacing="2.2">// FOCUS AREAS</text><text class="sg" x="688" y="86" font-size="29" fill="#eceef6" letter-spacing="-.5">Always learning, always building</text>'
             '<g clip-path="url(#winR)">')
    for i, sl in enumerate(slides):
        right += f'<g class="slide" style="animation-delay:{i * 4}s">{sl}</g>'
    right += "</g>"
    for i in range(3):
        x = 708 + i * 178
        right += (f'<rect x="{x}" y="130" width="170" height="3" rx="1.5" fill="#fff" fill-opacity=".18"/><rect x="{x}" y="130" width="0" height="3" rx="1.5" fill="#fff">'
                  f'<animate attributeName="width" values="0;0;170;170" keyTimes="0;{i / 3:.4f};{(i + 1) / 3:.4f};1" dur="12s" repeatCount="indefinite"/></rect>')
    right += '<rect x="688.5" y="118.5" width="563" height="351" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity=".10"/>'
    for i, (pill, col, t, sub) in enumerate(caps_r):
        right += (f'<g class="cap" style="animation-delay:{i * 4}s"><rect x="688" y="494" width="{26 + len(pill) * 9}" height="28" rx="14" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".5"/>'
                  f'<text class="jbb" x="{688 + 13}" y="513" font-size="11.5" fill="{col}" letter-spacing="1.4">{pill}</text><text class="sg" x="{688 + 44 + len(pill) * 9}" y="514" font-size="19" fill="#eceef6">{esc(t)}</text>'
                  f'<text class="sgm" x="688" y="552" font-size="15" fill="#8d93ab">{esc(sub)}</text></g>')
    # "my loop" track
    TL = 8.0; xs = [800, 920, 1040, 1160]; yl = 604
    right += f'<text class="jbb" x="688" y="608" font-size="10.5" fill="#8d93ab" letter-spacing="1.8">MY LOOP</text>'
    right += f'<line x1="{xs[0]}" y1="{yl}" x2="{xs[-1]}" y2="{yl}" stroke="#fff" stroke-opacity=".12" stroke-width="2"/>'
    right += f'<rect x="{xs[0]}" y="{yl - 1}" width="0" height="2" fill="url(#sweepR)"><animate attributeName="width" values="0;{xs[-1] - xs[0]};{xs[-1] - xs[0]};0" keyTimes="0;.75;.97;1" dur="{TL}s" repeatCount="indefinite"/></rect>'
    right += (f'<circle r="8" fill="{C3}" opacity=".4" filter="url(#gl2)"><animateMotion dur="{TL}s" repeatCount="indefinite" path="M{xs[0]} {yl}H{xs[-1]}" keyPoints="0;1;1" keyTimes="0;.75;1" calcMode="linear"/></circle>'
              f'<circle r="3.6" fill="#fff"><animateMotion dur="{TL}s" repeatCount="indefinite" path="M{xs[0]} {yl}H{xs[-1]}" keyPoints="0;1;1" keyTimes="0;.75;1" calcMode="linear"/></circle>')
    for i, (lab, col) in enumerate([("Learn", C1), ("Build", C3), ("Experiment", C2), ("Deploy", "#34d399")]):
        t_ = .75 * i / 3
        right += (f'<circle cx="{xs[i]}" cy="{yl}" r="9" fill="#171a2c" stroke="{col}" stroke-width="2"><animate attributeName="fill" calcMode="discrete" values="#171a2c;{col};#171a2c" keyTimes="0;{t_:.3f};{.97:.3f}" dur="{TL}s" repeatCount="indefinite"/></circle>'
                  f'<text class="jb" x="{xs[i]}" y="{yl + 28}" font-size="11.5" text-anchor="middle" fill="#eceef6">{lab}</text>')
    right += "</g>"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640" role="img" aria-label="What I build and my focus areas"><title>What I build and my focus areas</title>'
            f'<defs>{style_block(css)}{defs}</defs>{left}{right}</svg>')


# ───────────────────────────── ACTIVITY & CONTRIBUTION GRAPH ─────────────────────────────
def fetch_contribs():
    """Real contribution calendar: scraped from GitHub's public contributions page (no token needed).
    Falls back to the last good copy in activity-data.json."""
    cache = os.path.join(HERE, "activity-data.json")
    if not OFFLINE:
        try:
            req = urllib.request.Request(f"https://github.com/users/{CFG['user']}/contributions", headers={"User-Agent": "Mozilla/5.0"})
            h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
            cells = {}
            for m in re.finditer(r'<td[^>]*?>', h):
                t = m.group(0)
                if "data-date" in t and "data-level" in t:
                    cid = re.search(r'id="(contribution-day-component-[\d-]+)"', t); d = re.search(r'data-date="([\d-]+)"', t); l = re.search(r'data-level="(\d)"', t)
                    if cid and d and l: cells[cid.group(1)] = (d.group(1), int(l.group(1)))
            tips = {m.group(1): m.group(2) for m in re.finditer(r'<tool-tip[^>]*?for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', h)}
            days = []
            for cid, (d, l) in cells.items():
                mm = re.match(r"(\d+) contribution", tips.get(cid, "")); days.append([d, int(mm.group(1)) if mm else 0, l])
            days.sort()
            if len(days) >= 300:
                json.dump(days, open(cache, "w")); print("  contributions: live,", len(days), "days")
                return days
        except Exception as e:
            print("  (live contributions unavailable):", e)
    if os.path.exists(cache):
        print("  contributions: cached copy"); return json.load(open(cache))
    return None

def build_activity():
    import math as m
    days = fetch_contribs()
    if not days: print("  ! no contribution data - activity.svg skipped"); return None
    pad = (datetime.date.fromisoformat(days[0][0]).weekday() + 1) % 7      # Sunday-first rows
    grid = [None] * pad + days
    weeks = (len(grid) + 6) // 7
    grid += [None] * (weeks * 7 - len(grid))
    total = sum(d[1] for d in days); active = sum(1 for d in days if d[1] > 0)
    best = max(days, key=lambda d: d[1])
    cur = 0
    for i, d in enumerate(reversed(days)):
        if d[1] > 0: cur += 1
        elif i == 0: continue
        else: break
    lg = run = 0
    for d in days: run = run + 1 if d[1] > 0 else 0; lg = max(lg, run)
    from collections import Counter
    mo = Counter()
    for d in days: mo[d[0][:7]] += d[1]
    bm = mo.most_common(1)[0]; bm_name = datetime.date.fromisoformat(bm[0] + "-01").strftime("%b %Y").upper()
    wk = [sum(c[1] for c in grid[w * 7:(w + 1) * 7] if c) for w in range(weeks)]
    last, prev = sum(wk[-13:]), sum(wk[-26:-13])
    trend = "RISING" if last > prev * 1.05 else ("COOLING" if last < prev * .8 else "STEADY")
    recent = sum(d[1] for d in days[-14:]); status = "ACTIVE" if recent else "RESTING"
    bdate = datetime.date.fromisoformat(best[0]).strftime("%b %d, %Y").replace(" 0", " ")
    first = datetime.date.fromisoformat(days[0][0]).strftime("%b %Y"); lastd = datetime.date.fromisoformat(days[-1][0]).strftime("%b %Y")

    LV = ["#1f1822", "#6b1424", "#c81e2d", "#ff4d5a", "#ffb347"]
    X0, PITCH, CELL, HY0 = 112, 20, 16, 264
    xc = lambda i: X0 + i * PITCH + CELL / 2
    CHT, CHB = 156, 228
    mx = max(wk) or 1
    pts = [(xc(i), CHB - (m.sqrt(v / mx)) * (CHB - CHT)) for i, v in enumerate(wk)]
    def smooth(p):
        d = f"M{p[0][0]:.1f} {p[0][1]:.1f}"
        for i in range(len(p) - 1):
            p0 = p[i - 1] if i else p[i]; p1 = p[i]; p2 = p[i + 1]; p3 = p[i + 2] if i + 2 < len(p) else p[i + 1]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6); c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        return d
    line = smooth(pts); area = line + f"L{pts[-1][0]:.1f} {CHB}L{pts[0][0]:.1f} {CHB}Z"
    ORB, T0 = 11.0, 3.0
    css = (".c{animation:pop .5s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:center}@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}"
           ".tile{animation:fadeUp .7s cubic-bezier(.2,.8,.2,1) both}")
    defs = (f'<linearGradient id="cardbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#171a2c"/><stop offset="1" stop-color="#0f1120"/></linearGradient>'
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C3}" stop-opacity=".55"/></linearGradient>'
            f'<linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".5"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="lineG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}"/><stop offset=".6" stop-color="{C3}"/><stop offset="1" stop-color="#fff"/></linearGradient>'
            f'<linearGradient id="beamG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C3}" stop-opacity=".0"/><stop offset=".25" stop-color="{C1}" stop-opacity=".30"/><stop offset="1" stop-color="{C1}" stop-opacity=".06"/></linearGradient>'
            f'<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}" stop-opacity="0"/><stop offset=".5" stop-color="#ffb199"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            f'<radialGradient id="orbG"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="{C3}"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="blob"><stop offset="0" stop-color="{C1}" stop-opacity=".26"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            '<pattern id="dots4" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r=".8" fill="#fff" fill-opacity=".05"/></pattern>'
            '<clipPath id="card"><rect width="1280" height="612" rx="24"/></clipPath>'
            f'<clipPath id="revT"><rect x="{X0 - 10}" y="130" width="0" height="120"><animate attributeName="width" values="0;{PITCH * weeks + 30}" dur="2.4s" begin=".6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></rect></clipPath>'
            f'<filter id="gl" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    # header
    def pill(x, w, label, val, col):
        return (f'<g class="fu" style="animation-delay:.3s"><rect x="{x}" y="50" width="{w}" height="30" rx="15" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".55"/>'
                f'<text class="jb" x="{x + 14}" y="69" font-size="10.5" fill="#8d93ab" letter-spacing="1.4">{label}</text><text class="jbb" x="{x + 14 + len(label) * 7.6 + 8:.0f}" y="69" font-size="11" fill="{col}" letter-spacing="1">{val}</text></g>')
    pills = ""; px_ = 1248
    for label, val, col in reversed([("STATUS", status, "#34d399"), ("TREND", ("↑ " if trend == "RISING" else "") + trend, C3), ("PEAK MONTH", bm_name, C1)]):
        w = 14 + len(label) * 7.6 + 8 + len(val) * 8 + 16; px_ -= w; pills = pill(round(px_), round(w), label, val, col) + pills; px_ -= 10
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 612" width="1280" height="612" role="img" aria-label="Activity and contribution graph"><title>Activity and contribution graph</title>'
           f'<defs>{style_block(css)}{defs}</defs>'
           f'<rect width="1280" height="612" rx="24" fill="url(#cardbg)"/><g clip-path="url(#card)"><circle cx="1090" cy="60" r="260" fill="url(#blob)"><animate attributeName="cx" values="1090;960;1090" dur="14s" repeatCount="indefinite"/></circle></g>'
           f'<rect width="1280" height="612" rx="24" fill="url(#dots4)"/><rect x=".75" y=".75" width="1278.5" height="610.5" rx="23.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>'
           f'<rect x="1" y="1" width="1278" height="610" rx="23" fill="none" stroke="url(#sweep)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray=".1 .9"><animate attributeName="stroke-dashoffset" values="1;0" dur="12s" repeatCount="indefinite"/></rect>'
           f'<g class="fu" style="animation-delay:.1s"><text class="jbb" x="40" y="54" font-size="12.5" fill="{C1}" letter-spacing="2.2">// ACTIVITY &amp; CONTRIBUTION GRAPH</text><text class="sg" x="40" y="92" font-size="29" fill="#eceef6" letter-spacing="-.5">Every day I ship, mapped</text></g>{pills}'
           f'<rect x="32" y="118" width="1216" height="332" rx="18" fill="#0b0d1b" fill-opacity=".72" stroke="#fff" stroke-opacity=".07"/>'
           f'<text class="jbb" x="56" y="150" font-size="10.5" fill="#8d93ab" letter-spacing="2">WEEKLY OUTPUT</text><text class="jb" x="56" y="168" font-size="10" fill="#5d6483">{first} → {lastd}</text>'
           f'<circle cx="1224" cy="146" r="4" fill="#34d399"><animate attributeName="opacity" values="1;.3;1" dur="1.4s" repeatCount="indefinite"/></circle><text class="jbb" x="1214" y="150" font-size="10.5" text-anchor="end" fill="#34d399" letter-spacing="1.6">LIVE</text>')
    for gy in (CHT, (CHT + CHB) / 2, CHB):
        out += f'<line x1="{X0 - 6}" y1="{gy:.0f}" x2="{X0 + PITCH * weeks}" y2="{gy:.0f}" stroke="#fff" stroke-opacity=".06" stroke-dasharray="3 6"/>'
    out += (f'<g clip-path="url(#revT)"><path d="{area}" fill="url(#areaG)"/><path d="{line}" fill="none" stroke="url(#lineG)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" filter="url(#gl)"/></g>')
    # month + day labels
    prev_m = -1; labels = []
    for w in range(weeks):
        first_cell = next((c for c in grid[w * 7:(w + 1) * 7] if c), None)
        if not first_cell: continue
        mm = int(first_cell[0][5:7])
        if mm != prev_m and w < weeks - 2: labels.append((w, mm))
        prev_m = mm
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3: labels.pop(0)      # drop a cramped partial first month
    for w, mm in labels:
        out += f'<text class="jb" x="{X0 + w * PITCH}" y="{HY0 - 8}" font-size="10" fill="#8d93ab">{datetime.date(2000, mm, 1).strftime("%b")}</text>'
    for r, nm in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out += f'<text class="jb" x="{X0 - 12}" y="{HY0 + r * PITCH + 12}" font-size="10" text-anchor="end" fill="#8d93ab">{nm}</text>'
    # heatmap cells
    cells = ""; glow = ""; act = []
    for k, c in enumerate(grid):
        if not c: continue
        w, r = divmod(k, 7); x = X0 + w * PITCH; y = HY0 + r * PITCH
        cells += f'<rect class="c" style="animation-delay:{.5 + w * .03 + r * .012:.2f}s" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="4" fill="{LV[c[2]]}"{"" if c[2] else " stroke=\"#fff\" stroke-opacity=\".05\""}/>'
        if c[1] > 0:
            f_ = w / max(1, weeks - 1)
            pts_k = [(0, 0), (max(0, f_ - .012), 0), (f_, .7), (min(1, f_ + .05), 0), (1, 0)]
            kt = ";".join(f"{t:.4f}" for t, _ in pts_k); vals = ";".join(str(v) for _, v in pts_k)
            glow += (f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="4" fill="#fff" opacity="0"><animate attributeName="opacity" values="{vals}" keyTimes="{kt}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/></rect>')
    out += f'<g>{cells}</g><g>{glow}</g>'
    # peak + today rings
    bi = days.index(next(d for d in days if d[0] == best[0])) + pad; bw, br = divmod(bi, 7)
    out += (f'<g><rect x="{X0 + bw * PITCH - 3}" y="{HY0 + br * PITCH - 3}" width="{CELL + 6}" height="{CELL + 6}" rx="7" fill="none" stroke="{C3}" stroke-width="1.8"><animate attributeName="stroke-opacity" values="1;.2;1" dur="1.8s" repeatCount="indefinite"/></rect></g>')
    ti = len(days) - 1 + pad; tw, tr = divmod(ti, 7)
    out += f'<rect x="{X0 + tw * PITCH - 2}" y="{HY0 + tr * PITCH - 2}" width="{CELL + 4}" height="{CELL + 4}" rx="6" fill="none" stroke="#fff" stroke-width="1.4" stroke-dasharray="3 3"><animate attributeName="stroke-opacity" values=".9;.2;.9" dur="1.2s" repeatCount="indefinite"/></rect>'
    # orb + beam (synced through per-week keyframes)
    xs = ";".join(f"{p[0]:.1f}" for p in pts); ys = ";".join(f"{p[1]:.1f}" for p in pts)
    bx = ";".join(f"{p[0] - 10:.1f}" for p in pts)
    out += (f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".4s" begin="{T0}s" fill="freeze"/>'
            f'<rect x="{pts[0][0] - 10:.1f}" y="{CHT - 6}" width="20" height="{HY0 + 7 * PITCH - CHT + 4}" rx="10" fill="url(#beamG)"><animate attributeName="x" values="{bx}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/></rect>'
            f'<line x1="{pts[0][0]:.1f}" y1="{pts[0][1]:.1f}" x2="{pts[0][0]:.1f}" y2="{HY0 + 7 * PITCH}" stroke="{C3}" stroke-opacity=".5" stroke-dasharray="2 4"><animate attributeName="x1" values="{xs}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/><animate attributeName="x2" values="{xs}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/><animate attributeName="y1" values="{ys}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/></line>')
    for k, (r_, op) in enumerate([(16, .22), (11, .4), (7, .6)]):
        out += f'<circle r="{r_}" cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" fill="url(#orbG)" opacity="{op}"><animate attributeName="cx" values="{xs}" dur="{ORB}s" begin="{T0 + k * .08:.2f}s" repeatCount="indefinite"/><animate attributeName="cy" values="{ys}" dur="{ORB}s" begin="{T0 + k * .08:.2f}s" repeatCount="indefinite"/></circle>'
    out += f'<circle r="4.4" cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" fill="#fff"><animate attributeName="cx" values="{xs}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/><animate attributeName="cy" values="{ys}" dur="{ORB}s" begin="{T0}s" repeatCount="indefinite"/></circle></g>'
    # legend
    lx = X0 + PITCH * weeks - 5 * 19 - 70
    out += f'<text class="jb" x="{lx}" y="{HY0 + 7 * PITCH + 22}" font-size="10" fill="#8d93ab" text-anchor="end">Less</text>'
    for i, c in enumerate(LV): out += f'<rect x="{lx + 8 + i * 19}" y="{HY0 + 7 * PITCH + 12}" width="14" height="14" rx="4" fill="{c}"/>'
    out += f'<text class="jb" x="{lx + 8 + 5 * 19 + 4}" y="{HY0 + 7 * PITCH + 22}" font-size="10" fill="#8d93ab">More</text>'
    out += f'<text class="jb" x="{X0}" y="{HY0 + 7 * PITCH + 22}" font-size="10.5" fill="#5d6483">{total} contributions in the last year · pulse follows the weekly trend</text>'
    # stat tiles
    def counter(final, x, y, size, d0):
        vals = sorted({0, round(final * .3), round(final * .6), round(final * .85), final}); step = .2; dur = d0 + step * len(vals) + .2; o = ""
        for k, v in enumerate(vals):
            last = k == len(vals) - 1; a = (d0 + k * step) / dur; b = (d0 + (k + 1) * step) / dur
            kt, vv = (f"0;{a:.4f}", "0;1") if last else (f"0;{a:.4f};{b:.4f}", "0;1;0")
            o += f'<text class="sg" x="{x}" y="{y}" font-size="{size}" fill="#eceef6" opacity="{1 if last else 0}">{v}<animate attributeName="opacity" calcMode="discrete" values="{vv}" keyTimes="{kt}" dur="{dur:.2f}s" begin="0s" fill="freeze"/></text>'
        return o
    icons = {"bars": "M5 20V10M12 20V4M19 20V14", "cal": "M4 7h16v13H4zM4 11h16M8 4v4M16 4v4", "flame": "M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z",
             "trophy": "M8 4h8v5a4 4 0 0 1-8 0zM8 6H5v1a3 3 0 0 0 3 3M16 6h3v1a3 3 0 0 1-3 3M12 13v4M9 20h6", "star": "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"}
    tiles = [("TOTAL", total, "contributions · last year", C1, "bars"), ("ACTIVE DAYS", active, f"of {len(days)} days", C2, "cal"),
             ("CURRENT STREAK", cur, "days in a row", C3, "flame"), ("LONGEST STREAK", lg, "days in a row", "#34d399", "trophy"), ("BEST DAY", best[1], bdate, "#ffd166", "star")]
    for i, (lab, val, sub, col, ic) in enumerate(tiles):
        x = 32 + i * 246; y = 468
        out += (f'<g class="tile" style="animation-delay:{.9 + i * .12:.2f}s"><rect x="{x}" y="{y}" width="232" height="112" rx="16" fill="{col}" fill-opacity=".07" stroke="{col}" stroke-opacity=".4"/>'
                f'<rect x="{x + 20}" y="{y + 18}" width="26" height="3" rx="1.5" fill="{col}"/><text class="jbb" x="{x + 20}" y="{y + 42}" font-size="10.5" fill="#8d93ab" letter-spacing="1.8">{lab}</text>'
                f'<g transform="translate({x + 232 - 46},{y + 16}) scale(1.05)" fill="none" stroke="{col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="{icons[ic]}"/></g>'
                f'{counter(val, x + 20, y + 84, 38, 1.0 + i * .12)}<text class="jb" x="{x + 20}" y="{y + 102}" font-size="11" fill="#8d93ab">{esc(sub)}</text></g>')
    return out + "</svg>"

# ───────────────────────────── ANIMATED CONTRIBUTION CITY ─────────────────────────────
def fetch_city_data():
    """Radar totals + language donut + stars/forks. Live from GitHub GraphQL when a token exists (the daily workflow has one);
    otherwise the last good copy in city-data.json."""
    cache = os.path.join(HERE, "city-data.json")
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and not OFFLINE:
        try:
            q = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions}"
                 "commitContributionsByRepository(maxRepositories:100){repository{primaryLanguage{name color}}contributions{totalCount}}"
                 "totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions totalRepositoryContributions}"
                 "repositories(first:100,ownerAffiliations:OWNER){nodes{forkCount stargazerCount}}}}")
            req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q, "variables": {"login": CFG["user"]}}).encode(),
                                         headers={"Authorization": "bearer " + tok, "Content-Type": "application/json", "User-Agent": "profile-builder"})
            u = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]; cc = u["contributionsCollection"]
            langs = {}
            for r in cc["commitContributionsByRepository"]:
                pl = r["repository"]["primaryLanguage"]
                if not pl: continue
                e = langs.setdefault(pl["name"], [pl["name"], pl["color"] or "#444444", 0]); e[2] += r["contributions"]["totalCount"]
            data = {"seed": False, "totals": {"commit": cc["totalCommitContributions"], "issue": cc["totalIssueContributions"], "pr": cc["totalPullRequestContributions"],
                    "review": cc["totalPullRequestReviewContributions"], "repo": cc["totalRepositoryContributions"], "total": cc["contributionCalendar"]["totalContributions"],
                    "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]), "forks": sum(n["forkCount"] for n in u["repositories"]["nodes"])},
                    "languages": sorted(langs.values(), key=lambda e: -e[2])}
            json.dump(data, open(cache, "w"), indent=1); print("  city data: live from GitHub"); return data
        except Exception as e:
            print("  (city data: live fetch failed)", e)
    print("  city data: cached copy"); return json.load(open(cache))

def build_city():
    import math as m, random
    rnd = random.Random(5)
    days = fetch_contribs()
    if not days: print("  ! no contribution data - city.svg skipped"); return None
    cd = fetch_city_data(); tt = cd["totals"]
    langs = [list(l) for l in cd["languages"][:5]]
    rest = tt["commit"] - sum(l[2] for l in langs)
    if rest > 0: langs.append(["other", "#444444", rest])
    ltot = sum(l[2] for l in langs) or 1
    W, H = 1280, 860
    ox, oy, CW, CH = 150, 250, 16, 8
    pad = (datetime.date.fromisoformat(days[0][0]).weekday() + 1) % 7
    grid = [None] * pad + days; weeks = (len(grid) + 6) // 7; grid += [None] * (weeks * 7 - len(grid))
    P = lambda u, v: (ox + (u - v) * CW, oy + (u + v) * CH)
    LV = ["#1b1218", "#6b1424", "#c81e2d", "#ff4d5a", "#ffb347"]
    def shade(hx, f):
        h = hx.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return "#%02x%02x%02x" % (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))
    pk = lambda pts: " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    best = max(days, key=lambda d: d[1])

    css = (".t{animation:fadeIn .6s ease both}.tw{animation:rise .9s cubic-bezier(.2,.9,.25,1.15) both;transform-box:view-box}@keyframes rise{from{transform:scaleY(0);opacity:0}to{transform:scaleY(1);opacity:1}}"
           ".lg{animation:fadeUp .6s cubic-bezier(.2,.8,.2,1) both}")
    defs = ('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#150810"/><stop offset=".6" stop-color="#0a0509"/><stop offset="1" stop-color="#06030a"/></linearGradient>'
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset=".5" stop-color="#262a42"/><stop offset="1" stop-color="{C3}" stop-opacity=".55"/></linearGradient>'
            f'<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}" stop-opacity="0"/><stop offset=".5" stop-color="#ffb199"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            '<linearGradient id="slabT" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1d0d16"/><stop offset="1" stop-color="#130812"/></linearGradient>'
            '<linearGradient id="bandG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#ffd0c8" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="beamV" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{C3}" stop-opacity=".7"/><stop offset="1" stop-color="{C3}" stop-opacity="0"/></linearGradient>'
            f'<radialGradient id="haze" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{C1}" stop-opacity=".30"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="moon" cx=".38" cy=".36" r=".7"><stop offset="0" stop-color="#fff4e6"/><stop offset="1" stop-color="#e9b9a5"/></radialGradient>'
            '<radialGradient id="sweepW" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(0 0) scale(130)"><stop offset="0" stop-color="#ff4d5a" stop-opacity=".0"/><stop offset="1" stop-color="#ff4d5a" stop-opacity=".45"/></radialGradient>'
            f'<linearGradient id="radF" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}" stop-opacity=".55"/><stop offset="1" stop-color="{C3}" stop-opacity=".35"/></linearGradient>'
            f'<clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath>'
            f'<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            '<filter id="gl3" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="5"/></filter>')
    o = []
    o.append(f'<rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>')
    o.append(f'<g clip-path="url(#card)"><ellipse cx="640" cy="560" rx="560" ry="260" fill="url(#haze)"><animate attributeName="opacity" values=".6;1;.6" dur="7s" repeatCount="indefinite"/></ellipse></g>')
    # sky: stars, moon, shooting star
    for i in range(46):
        sx, sy = rnd.randint(30, W - 30), rnd.randint(30, 560); r = rnd.choice([.8, 1, 1.2, 1.5])
        o.append(f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="#fff" opacity=".1"><animate attributeName="opacity" values=".08;.75;.08" dur="{rnd.uniform(2.4, 5.5):.1f}s" begin="{rnd.uniform(0, 4):.1f}s" repeatCount="indefinite"/></circle>')
    o.append('<g><circle cx="610" cy="96" r="42" fill="#ffb199" opacity=".16" filter="url(#gl3)"><animate attributeName="opacity" values=".12;.25;.12" dur="6s" repeatCount="indefinite"/></circle><circle cx="610" cy="96" r="22" fill="url(#moon)"/><circle cx="602" cy="90" r="4" fill="#d9a994" opacity=".55"/><circle cx="618" cy="104" r="5.5" fill="#d9a994" opacity=".45"/><circle cx="616" cy="86" r="2.6" fill="#d9a994" opacity=".5"/></g>')
    o.append('<g opacity="0"><animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.1;.14;.3;1" dur="10s" begin="3s" repeatCount="indefinite"/><animateTransform attributeName="transform" type="translate" values="0 0;0 0;-260 130;-260 130" keyTimes="0;.1;.3;1" dur="10s" begin="3s" repeatCount="indefinite"/>'
             '<line x1="820" y1="120" x2="856" y2="138" stroke="url(#sweep)" stroke-width="2" stroke-linecap="round"/><circle cx="820" cy="120" r="2.2" fill="#fff"/></g>')
    # slab with roads
    u0, u1, v0, v1 = -1, weeks, -1.7, 7.7
    A_, B_, C_, D_ = P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1); TH = 12
    o.append(f'<polygon points="{pk([D_, C_, (C_[0], C_[1] + TH), (D_[0], D_[1] + TH)])}" fill="#0d0509"/><polygon points="{pk([C_, B_, (B_[0], B_[1] + TH), (C_[0], C_[1] + TH)])}" fill="#090308"/>')
    o.append(f'<polygon points="{pk([A_, B_, C_, D_])}" fill="url(#slabT)" stroke="{C1}" stroke-opacity=".35"/>')
    for va, vb in ((-1.45, -.85), (6.85, 7.45)):
        o.append(f'<polygon points="{pk([P(u0 + .15, va), P(u1 - .15, va), P(u1 - .15, vb), P(u0 + .15, vb)])}" fill="#0a0509"/>')
        vm = (va + vb) / 2
        o.append(f'<line x1="{P(u0 + .3, vm)[0]:.1f}" y1="{P(u0 + .3, vm)[1]:.1f}" x2="{P(u1 - .3, vm)[0]:.1f}" y2="{P(u1 - .3, vm)[1]:.1f}" stroke="#ffb347" stroke-opacity=".35" stroke-dasharray="6 8"/>')
    # ground tiles
    tiles = []
    for k, c in enumerate(grid):
        if not c: continue
        w, r = divmod(k, 7); x, y = P(w, r)
        tiles.append(f'<polygon class="t" style="animation-delay:{w * .018:.2f}s" points="{pk([(x, y - CH), (x + CW, y), (x, y + CH), (x - CW, y)])}" fill="#2a111c" stroke="#0a0509" stroke-width=".7"/>')
    o.append("".join(tiles))
    # towers
    towers = []
    for k, c in enumerate(grid):
        if not c or c[1] <= 0: continue
        w, r = divmod(k, 7); x, y = P(w, r); n = c[1]
        h = 4 + (n ** .65) * 6.5; ck, hk = CW * .8, CH * .8; col = LV[max(1, c[2])]
        top = [(x, y - hk - h), (x + ck, y - h), (x, y + hk - h), (x - ck, y - h)]
        lf = [(x - ck, y - h), (x, y + hk - h), (x, y + hk), (x - ck, y)]
        rt = [(x + ck, y - h), (x, y + hk - h), (x, y + hk), (x + ck, y)]
        g = (f'<g class="tw" style="transform-origin:{x:.1f}px {y + hk:.1f}px;animation-delay:{.7 + w * .028 + rnd.uniform(0, .25):.2f}s">'
             f'<polygon points="{pk(lf)}" fill="{shade(col, .66)}"/><polygon points="{pk(rt)}" fill="{shade(col, .46)}"/><polygon points="{pk(top)}" fill="{col}"/>')
        if h >= 22:   # lit windows
            for face, ang, ex, ey in (("L", 26.565, x - ck, y - h), ("R", -26.565, x, y + hk - h)):
                ws = ""
                for cc_ in (.2, .58):
                    yy = 5
                    while yy + 4 < h - 3:
                        if rnd.random() < .7:
                            op = rnd.choice([.9, .9, .5]); d_ = rnd.uniform(2.5, 8)
                            ws += (f'<rect x="{ck * cc_:.1f}" y="{yy}" width="3.4" height="4" fill="#ffd166" opacity="{op}"><animate attributeName="opacity" values="{op};{rnd.choice([.1, .25])};{op}" dur="{d_:.1f}s" begin="{rnd.uniform(0, 6):.1f}s" repeatCount="indefinite"/></rect>')
                        yy += 8
                g += f'<g transform="translate({ex:.1f},{ey:.1f}) skewY({ang})">{ws}</g>'
        f_ = (w + 1) / (weeks + 1)
        kt = [0, max(0, f_ - .02), f_, min(1, f_ + .06), 1]
        g += (f'<g opacity="0" fill="#fff"><animate attributeName="opacity" values="0;0;.55;0;0" keyTimes="{";".join(f"{t:.4f}" for t in kt)}" dur="9s" begin="3.6s" repeatCount="indefinite"/>'
              f'<polygon points="{pk(lf)}"/><polygon points="{pk(rt)}"/><polygon points="{pk(top)}"/></g></g>')
        towers.append((w + r, g, (x, y, h, n, c[0])))
    towers.sort(key=lambda t: t[0])
    o.append("".join(t[1] for t in towers))
    # moving wave band (ground)
    band = [P(-1, -.5), P(0.6, -.5), P(0.6, 6.5), P(-1, 6.5)]
    o.append(f'<polygon points="{pk(band)}" fill="url(#bandG)"><animateTransform attributeName="transform" type="translate" values="0 0;{(weeks + 1) * CW} {(weeks + 1) * CH}" dur="9s" begin="3.6s" repeatCount="indefinite"/></polygon>')
    # cars
    for lane, v, rev in ((0, -1.15, False), (1, 7.15, True)):
        a, b = P(u0 + .5, v), P(u1 - .5, v); path = f"M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"
        kp = "1;0" if rev else "0;1"
        for j in range(6):
            dur = rnd.uniform(7, 13); bg = -rnd.uniform(0, 12); col = "#fff4e0" if (j + lane) % 2 == 0 else "#ff5a4a"
            mo = f'<animateMotion dur="{dur:.1f}s" begin="{bg:.1f}s" repeatCount="indefinite" path="{path}" keyPoints="{kp}" keyTimes="0;1" calcMode="linear"/>'
            o.append(f'<g><circle r="5" fill="{col}" opacity=".28">{mo}</circle><circle r="1.9" fill="{col}">{mo}</circle></g>')
    # peak callout
    pk_ = next(t for t in towers if t[2][4] == best[0])[2]; bx, by, bh, bn, bd = pk_
    tx, ty = bx, by - bh - hk if False else by - bh - 4
    lab = f"PEAK · {bn} · " + datetime.date.fromisoformat(bd).strftime("%b %d").replace(" 0", " ")
    pw = len(lab) * 7.4 + 24
    o.append(f'<g class="lg" style="animation-delay:2.4s"><rect x="{bx - 6:.1f}" y="{ty - 96:.1f}" width="12" height="92" fill="url(#beamV)" opacity=".8"><animate attributeName="opacity" values=".35;.9;.35" dur="2.4s" repeatCount="indefinite"/></rect>'
             f'<circle cx="{bx:.1f}" cy="{ty:.1f}" r="3.4" fill="#fff"><animate attributeName="r" values="3;4.6;3" dur="1.4s" repeatCount="indefinite"/></circle>'
             f'<circle cx="{bx:.1f}" cy="{ty:.1f}" r="9" fill="none" stroke="{C3}"><animate attributeName="r" values="4;16;4" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0;.9" dur="2s" repeatCount="indefinite"/></circle>'
             f'<rect x="{bx - pw - 14:.1f}" y="{ty - 128:.1f}" width="{pw:.0f}" height="26" rx="13" fill="#0d0a14" stroke="{C3}" stroke-opacity=".7"/><text class="jbb" x="{bx - pw - 14 + pw / 2:.1f}" y="{ty - 111:.1f}" font-size="11" text-anchor="middle" fill="{C3}" letter-spacing="1">{lab}</text>'
             f'<path d="M{bx - 14:.1f} {ty - 102:.1f}L{bx - 2:.1f} {ty - 8:.1f}" stroke="{C3}" stroke-opacity=".6" stroke-dasharray="2 3"/></g>')
    # header
    o.append(f'<g class="fu" style="animation-delay:.1s"><text class="jbb" x="40" y="54" font-size="12.5" fill="{C1}" letter-spacing="2.2">// CONTRIBUTION CITY</text><text class="sg" x="40" y="92" font-size="29" fill="#eceef6" letter-spacing="-.5">Every commit builds another tower</text></g>'
             f'<text class="jb" x="1240" y="54" font-size="12" fill="#8d93ab" text-anchor="end">{days[0][0]} / {days[-1][0]}</text>'
             f'<g class="fu" style="animation-delay:.3s"><circle cx="1240" cy="82" r="4" fill="#34d399"><animate attributeName="opacity" values="1;.3;1" dur="1.4s" repeatCount="indefinite"/></circle><text class="jbb" x="1228" y="86" font-size="10.5" text-anchor="end" fill="#34d399" letter-spacing="1.6">REBUILT DAILY</text></g>')
    # radar
    cx, cy, R = 985, 318, 122
    names = ["Commit", "Issue", "PullReq", "Review", "Repo"]; vals = [tt["commit"], tt["issue"], tt["pr"], tt["review"], tt["repo"]]
    lvl = lambda v: .8 if v < 1 else min(m.log10(v), 5) + 1
    pt = lambda lv, k: (R * lv / 5 * m.sin(k / 5 * 2 * m.pi), -R * lv / 5 * m.cos(k / 5 * 2 * m.pi))
    rad = f'<g transform="translate({cx} {cy})"><text class="jbb" x="0" y="{-R - 40}" font-size="10.5" text-anchor="middle" fill="{C3}" letter-spacing="2">// ACTIVITY RADAR</text>'
    for L in range(1, 6): rad += f'<polygon points="{pk([pt(L, k) for k in range(5)])}" fill="{"#ffffff" if L == 5 else "none"}" fill-opacity=".03" stroke="#fff" stroke-opacity=".22" stroke-dasharray="3 4"/>'
    for k in range(5): rad += f'<line x1="0" y1="0" x2="{pt(5, k)[0]:.1f}" y2="{pt(5, k)[1]:.1f}" stroke="#fff" stroke-opacity=".14" stroke-dasharray="3 4"/>'
    for L, lb in enumerate(["1", "10", "100", "1K", "10K"], 1): rad += f'<text class="jb" x="5" y="{-R * L / 5 + 3:.1f}" font-size="8.5" fill="#8d93ab">{lb}</text>'
    for k, nm in enumerate(names):
        lx, ly = pt(5.85, k); anch = "middle" if abs(lx) < 8 else ("start" if lx > 0 else "end")
        rad += f'<text class="sg" x="{lx:.1f}" y="{ly + 4:.1f}" font-size="13.5" text-anchor="{anch}" fill="#ffe3dc">{nm}</text>'
    poly = [pt(lvl(v), k) for k, v in enumerate(vals)]
    rad += (f'<defs><clipPath id="rclip"><polygon points="{pk([pt(5, k) for k in range(5)])}"/></clipPath></defs>'
            f'<g clip-path="url(#rclip)"><g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="7s" repeatCount="indefinite"/>'
            f'<path d="M0 0L0 {-R}A{R} {R} 0 0 0 {-R * m.sin(m.radians(55)):.1f} {-R * m.cos(m.radians(55)):.1f}Z" fill="url(#sweepW)"/><line x1="0" y1="0" x2="0" y2="{-R}" stroke="{C3}" stroke-width="1.6" stroke-opacity=".9"/></g></g>'
            f'<g><animateTransform attributeName="transform" type="scale" values="0;1.04;1" keyTimes="0;.7;1" dur="1.4s" begin=".9s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1;.3 0 .4 1"/>'
            f'<polygon points="{pk(poly)}" fill="url(#radF)" stroke="{C3}" stroke-width="2.4" stroke-linejoin="round" filter="url(#gl)"><animate attributeName="fill-opacity" values=".85;1;.85" dur="3s" repeatCount="indefinite"/></polygon>')
    for (px_, py_) in poly: rad += f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="3.6" fill="#fff"><animate attributeName="r" values="3;5;3" dur="2s" repeatCount="indefinite"/></circle>'
    rad += "</g></g>"
    o.append(rad)
    # donut
    pcx, pcy, rm, sw = 150, 696, 67, 34; circ = 2 * m.pi * rm
    o.append(f'<text class="jbb" x="40" y="{pcy - 108}" font-size="10.5" fill="{C3}" letter-spacing="2">// LANGUAGES · BY COMMITS</text>')
    acc = 0
    for i, (nm, col, v) in enumerate(langs):
        seg = circ * v / ltot; gap = min(2.2, seg * .4)
        o.append(f'<circle cx="{pcx}" cy="{pcy}" r="{rm}" fill="none" stroke="{col}" stroke-width="{sw}" transform="rotate(-90 {pcx} {pcy})" stroke-dasharray="0 {circ:.2f}" stroke-dashoffset="{-acc:.2f}">'
                 f'<animate attributeName="stroke-dasharray" values="0 {circ:.2f};{seg - gap:.2f} {circ - seg + gap:.2f}" dur=".8s" begin="{1.0 + i * .25:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></circle>')
        acc += seg
    o.append(f'<circle cx="{pcx}" cy="{pcy}" r="{rm + sw / 2 + 4}" fill="none" stroke="#fff" stroke-opacity=".1" stroke-dasharray="2 6"><animateTransform attributeName="transform" type="rotate" from="0 {pcx} {pcy}" to="360 {pcx} {pcy}" dur="40s" repeatCount="indefinite"/></circle>')
    def counter(final, x, y, size, fill, d0, anchor="start"):
        vs = sorted({0, round(final * .3), round(final * .6), round(final * .85), final}); st = .18; dur = d0 + st * len(vs) + .2; s_ = ""
        for k, v in enumerate(vs):
            last = k == len(vs) - 1; a = (d0 + k * st) / dur; b = (d0 + (k + 1) * st) / dur
            kt, vv = (f"0;{a:.4f}", "0;1") if last else (f"0;{a:.4f};{b:.4f}", "0;1;0")
            s_ += f'<text class="sg" x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" opacity="{1 if last else 0}">{v}<animate attributeName="opacity" calcMode="discrete" values="{vv}" keyTimes="{kt}" dur="{dur:.2f}s" begin="0s" fill="freeze"/></text>'
        return s_
    o.append(counter(tt["commit"], pcx, pcy + 6, 25, "#fff", 1.2, "middle") + f'<text class="jb" x="{pcx}" y="{pcy + 24}" font-size="10" text-anchor="middle" fill="#8d93ab" letter-spacing="1.5">COMMITS</text>')
    for i, (nm, col, v) in enumerate(langs):
        y = pcy - 56 + i * 27
        o.append(f'<g class="lg" style="animation-delay:{1.2 + i * .15:.2f}s"><rect x="268" y="{y - 12}" width="14" height="14" rx="4" fill="{col}"/><text class="sg" x="292" y="{y}" font-size="14.5" fill="#eceef6">{esc(nm)}</text>'
                 f'<text class="jb" x="470" y="{y}" font-size="12" text-anchor="end" fill="#8d93ab">{v / ltot * 100:.0f}%</text></g>')
    # footer
    fy = 836; tot = tt["total"]
    o.append(counter(tot, 470, fy, 36, C3, 1.4, "end") + f'<text class="sgm" x="482" y="{fy - 2}" font-size="18" fill="#eceef6">contributions</text>')
    star = "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"; fork = "M6 7.2v1.3a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V7.2M12 11.5v5.3"
    o.append(f'<g class="lg" style="animation-delay:1.6s"><g transform="translate(700,{fy - 30}) scale(1.35)" fill="none" stroke="#ffe3dc" stroke-width="1.7" stroke-linejoin="round"><path d="{star}"/></g>{counter(tt["stars"], 742, fy, 30, "#fff", 1.6)}'
             f'<g transform="translate(830,{fy - 30}) scale(1.35)" fill="none" stroke="#ffe3dc" stroke-width="1.7" stroke-linecap="round"><circle cx="6" cy="5" r="2.2"/><circle cx="18" cy="5" r="2.2"/><circle cx="12" cy="19" r="2.2"/><path d="{fork}"/></g>{counter(tt["forks"], 872, fy, 30, "#fff", 1.7)}</g>')
    body = "".join(o)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution city"><title>Contribution city</title>'
            f'<defs>{style_block(css)}{defs}</defs>{body}'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="23.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="23" fill="none" stroke="url(#sweep)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray=".1 .9"><animate attributeName="stroke-dashoffset" values="1;0" dur="12s" repeatCount="indefinite"/></rect></svg>')

# ───────────────────────────── README ─────────────────────────────
def build_readme():
    t = open(os.path.join(HERE, "README.tpl.md"), encoding="utf-8").read()
    v = datetime.date.today().strftime("%Y%m%d")
    return t.replace("{{V}}", v).replace("{{USER}}", CFG["user"]).replace("{{NAME}}", CFG["name"]).replace("{{ROLE}}", CFG["role"]) \
            .replace("{{EMAIL}}", CFG["email"]).replace("{{IG}}", CFG["instagram"]).replace("{{LI}}", CFG["linkedin_path"])

def main():
    print("Building profile for", CFG["user"], "(offline)" if OFFLINE else "")
    st = stats(); print("  stats:", {k: st[k] for k in ("repos", "stars", "forks", "followers", "live")})
    out = {"hero.svg": build_hero(), "id-dashboard.svg": build_id(st), "connect.svg": build_connect(), "stack.svg": build_stack(), "about-life.svg": build_about(), "activity.svg": build_activity(), "city.svg": build_city()}
    for n, s in out.items():
        if s is None: continue
        left = re.findall(r"\{\{[^}]+\}\}", s)
        assert not left, (n, left[:3])
        open(os.path.join(HERE, n), "w", encoding="utf-8").write(s); print(f"  wrote {n:18s} {len(s) / 1024:7.0f} KB")
    if os.path.exists(os.path.join(HERE, "README.tpl.md")):
        open(os.path.join(HERE, "README.md"), "w", encoding="utf-8").write(build_readme()); print("  wrote README.md")

if __name__ == "__main__":
    main()
