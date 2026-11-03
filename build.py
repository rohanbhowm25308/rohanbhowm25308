                     f'<rect x="{sx}" y="{sy + 12}" width="40" height="4" rx="2" fill="{[C1, C3][i]}"><animate attributeName="width" values="30;100;30" dur="{5 + i}s" begin="{ph}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/></rect>'
                     f'<circle cx="{sx + 40}" cy="{sy + 14}" r="6" fill="#fff"><animate attributeName="cx" values="{sx + 30};{sx + 100};{sx + 30}" dur="{5 + i}s" begin="{ph}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/></circle>')
        # map panel
        mx, my, mw, mh = wx + 20, wy + 96, 318, 242
        o.append(panel(mx, my, mw, mh, "ROUTE · 4 TRAVEL MODES"))
        A_, B_ = (mx + 34, my + 128), (mx + mw - 34, my + 84)
        modes = [("Flight", C2, (mx + mw / 2, my + 28), 3.0), ("Train", C3, (mx + mw / 2, my + 100), 4.2), ("Car", C1, (mx + mw / 2, my + 140), 5.4), ("Bus", "#286BFF", (mx + mw / 2, my + 172), 6.6)]
        for nm, col, ctl, dur in modes:
            d = f"M{A_[0]} {A_[1]}Q{ctl[0]:.1f} {ctl[1]:.1f} {B_[0]} {B_[1]}"
            o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-opacity=".45" stroke-width="1.8" stroke-dasharray="{"2 5" if nm == "Flight" else "5 4"}"><animate attributeName="stroke-dashoffset" values="0;-18" dur="1.4s" repeatCount="indefinite"/></path>'
                     f'<circle r="9" fill="{col}" opacity=".3"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{d}"/></circle><circle r="4" fill="#fff"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{d}"/></circle>')
            px_ = .25 * A_[0] + .5 * ctl[0] + .25 * B_[0]; py_ = .25 * A_[1] + .5 * ctl[1] + .25 * B_[1]
            o.append(f'<text class="jbb" x="{px_:.0f}" y="{py_ - 6 if nm in ("Flight", "Train") else py_ + 14:.0f}" font-size="9" text-anchor="middle" fill="{col}">{nm}</text>')
        for (px_, py_), cn in ((A_, "DELHI"), (B_, "JAIPUR")):
            o.append(f'<circle cx="{px_}" cy="{py_}" r="8" fill="none" stroke="#fff" stroke-opacity=".6"><animate attributeName="r" values="6;16" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0" dur="2s" repeatCount="indefinite"/></circle><circle cx="{px_}" cy="{py_}" r="6" fill="#fff"/>'
                     f'<text class="jbb" x="{px_}" y="{py_ + 24}" font-size="9" text-anchor="middle" fill="#E8F1FF" letter-spacing="1">{cn}</text>')
        scores = [("Train", 88, C3), ("Car", 79, C1), ("Bus", 71, "#286BFF"), ("Flight", 66, C2)]
        for i, (nm, sc, col) in enumerate(scores):
            yy = my + 192 + i * 12 - 4
            o.append(f'<text class="jb" x="{mx + 18}" y="{yy + 7}" font-size="9.5" fill="#9CC9FC">{nm}</text><rect x="{mx + 66}" y="{yy + 1}" width="178" height="7" rx="3.5" fill="#fff" fill-opacity=".08"/>'
                     f'<rect x="{mx + 66}" y="{yy + 1}" width="0" height="7" rx="3.5" fill="{col}"><animate attributeName="width" values="0;{178 * sc / 100:.0f}" dur="1s" begin="{1.4 + i * .2:.1f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></rect>'
                     f'<text class="jbb" x="{mx + 254}" y="{yy + 8}" font-size="9.5" fill="{col}">{sc}</text>')
        o.append(f'<g class="fu" style="animation-delay:2.4s"><rect x="{mx + 278}" y="{my + 190}" width="30" height="13" rx="6.5" fill="{C3}" fill-opacity=".2" stroke="{C3}"/><text class="jbb" x="{mx + 293}" y="{my + 200}" font-size="7.5" text-anchor="middle" fill="{C3}">BEST</text></g>')
        # score panel
        sx0, sw_ = wx + 358, 302
        o.append(panel(sx0, wy + 96, sw_, 242, "BEYONDTRIP SCORE"))
        gcx, gcy, gr = sx0 + 62, wy + 96 + 128, 42; gc = 2 * m.pi * gr; seg = gc * .87
        o.append(f'<circle cx="{gcx}" cy="{gcy}" r="{gr}" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="10"/>'
                 f'<circle cx="{gcx}" cy="{gcy}" r="{gr}" fill="none" stroke="{C3}" stroke-width="16" opacity=".25" filter="url(#gl3)" transform="rotate(-90 {gcx} {gcy})" stroke-dasharray="0 {gc:.1f}"><animate attributeName="stroke-dasharray" values="0 {gc:.1f};{seg:.1f} {gc - seg:.1f}" dur="1.4s" begin="1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></circle>'
                 f'<circle cx="{gcx}" cy="{gcy}" r="{gr}" fill="none" stroke="url(#sw)" stroke-width="10" stroke-linecap="round" transform="rotate(-90 {gcx} {gcy})" stroke-dasharray="0 {gc:.1f}"><animate attributeName="stroke-dasharray" values="0 {gc:.1f};{seg:.1f} {gc - seg:.1f}" dur="1.4s" begin="1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></circle>'
                 f'{counter(87, gcx, gcy + 8, 26, "#fff", 1.1, anchor="middle")}<text class="jb" x="{gcx}" y="{gcy + 24}" font-size="9" text-anchor="middle" fill="#B4D9FF">/ 100</text>'
                 f'<text class="jb" x="{gcx}" y="{gcy + 70}" font-size="9" text-anchor="middle" fill="#B4D9FF">explainable score</text>')
        facts = [("Budget fit", 92, C3), ("Time", 85, C1), ("Group fit", 88, C2), ("Comfort", 80, "#286BFF"), ("Experience", 90, C3), ("Hidden gems", 84, C2)]
        for i, (nm, v, col) in enumerate(facts):
            yy = wy + 96 + 42 + i * 30
            o.append(f'<text class="jb" x="{sx0 + 130}" y="{yy}" font-size="9.5" fill="#9CC9FC">{nm}</text><text class="jbb" x="{sx0 + sw_ - 18}" y="{yy}" font-size="9.5" text-anchor="end" fill="{col}">{v}</text>'
                     f'<rect x="{sx0 + 130}" y="{yy + 6}" width="154" height="5" rx="2.5" fill="#fff" fill-opacity=".08"/><rect x="{sx0 + 130}" y="{yy + 6}" width="0" height="5" rx="2.5" fill="{col}"><animate attributeName="width" values="0;{154 * v / 100:.0f}" dur=".9s" begin="{1.3 + i * .15:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></rect>')
        # true cost + AI chat
        by = wy + 350
        o.append(f'<text class="jbb" x="{wx + 22}" y="{by + 12}" font-size="9.5" fill="#B4D9FF" letter-spacing="1.6">TRUE TRIP COST · ₹30,000 · everything, not just the ticket</text>')
        costs = [("Transport", 22, C1), ("Stay", 24, C2), ("Food", 16, C3), ("Local", 8, "#286BFF"), ("Activities", 12, "#A8CFFF"), ("Shopping", 10, "#9DCAFD"), ("Buffer", 8, "#54A1F8")]
        bx0, bw = wx + 22, 636
        o.append(f'<defs><clipPath id="cb"><rect x="{bx0}" y="{by + 20}" width="{bw}" height="22" rx="11"/></clipPath></defs><g clip-path="url(#cb)"><rect x="{bx0}" y="{by + 20}" width="{bw}" height="22" fill="#fff" fill-opacity=".06"/>')
        acc = 0
        for i, (nm, pct, col) in enumerate(costs):
            w_ = bw * pct / 100
            o.append(f'<rect x="{bx0 + acc:.1f}" y="{by + 20}" width="0" height="22" fill="{col}"><animate attributeName="width" values="0;{w_ - 2:.1f}" dur=".8s" begin="{1.4 + i * .15:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></rect>'
                     f'<text class="jbb" x="{bx0 + acc + w_ / 2:.1f}" y="{by + 35}" font-size="8.5" text-anchor="middle" fill="#0A1017" opacity="0">{nm}<animate attributeName="opacity" values="0;1" dur=".3s" begin="{2.4 + i * .15:.2f}s" fill="freeze"/></text>')
            acc += w_
        o.append('</g>')
        o.append(f'<g class="fu" style="animation-delay:1s"><rect x="{wx + 20}" y="{by + 52}" width="640" height="42" rx="14" fill="{C1}" fill-opacity=".08" stroke="{C1}" stroke-opacity=".45"/>'
                 f'<rect x="{wx + 32}" y="{by + 60}" width="26" height="26" rx="9" fill="{C1}" fill-opacity=".18"/><g transform="translate({wx + 35},{by + 63}) scale(.83)">{generic_icon("spark", "#9DCBFE")}</g>'
                 f'<text class="jbb" x="{wx + 70}" y="{by + 70}" font-size="9" fill="{C3}" letter-spacing="1.6">AI</text>'
                 f'{typed(wx + 94, by + 82 - 12, "Why train? Best balance of budget, comfort and time for your whole group.", 2, 560, size=12, cid="tpb")}</g>')
        o.append(win_close())

    {"nexora": mock_nexora, "growth": mock_growth, "trip": mock_trip}[P["mock"]]()
    # ---------- pipeline ----------
    T = 6.0; nodes = [(lbl, c) for lbl, c in zip(P["flow"], [C3, C2, C1, "#286BFF", C3])]
    py = 581; xs = [140 + i * 250 for i in range(5)]
    def hl(wins, peak):
        pts = [(0, 0)]
        for s_, e_ in wins: pts += [(s_, 0), (s_ + .25, peak), (e_, peak), (e_ + .25, 0)]
        pts.append((T, 0)); return f'values="{";".join(str(v) for _, v in pts)}" keyTimes="{";".join(f"{min(1, t / T):.4f}" for t, _ in pts)}"'
    o.append(f'<g class="fu" style="animation-delay:1.2s"><rect x="40" y="524" width="1200" height="96" rx="20" fill="#000" fill-opacity=".22" stroke="#fff" stroke-opacity=".07"/>'
             f'<text class="jbb" x="62" y="548" font-size="10" fill="#B4D9FF" letter-spacing="2">HOW IT WORKS</text>')
    for i in range(4):
        a, b = xs[i] + 78, xs[i + 1] - 78; col = nodes[i + 1][1]; t0 = .3 + i * 1.3
        o.append(f'<path d="M{a} {py}H{b}" stroke="{col}" stroke-opacity=".35" stroke-width="1.8" stroke-dasharray="4 5" fill="none"><animate attributeName="stroke-dashoffset" values="0;-18" dur="1.3s" repeatCount="indefinite"/></path>'
                 f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{t0 / T:.4f};{(t0 + .01) / T:.4f};{(t0 + 1) / T:.4f};{(t0 + 1.02) / T:.4f};1" dur="{T}s" repeatCount="indefinite"/>'
                 f'<circle r="9" fill="{col}" opacity=".3"><animateMotion dur="{T}s" repeatCount="indefinite" path="M{a} {py}H{b}" keyPoints="0;0;1;1" keyTimes="0;{t0 / T:.4f};{(t0 + 1) / T:.4f};1" calcMode="linear"/></circle>'
                 f'<circle r="3.6" fill="#fff"><animateMotion dur="{T}s" repeatCount="indefinite" path="M{a} {py}H{b}" keyPoints="0;0;1;1" keyTimes="0;{t0 / T:.4f};{(t0 + 1) / T:.4f};1" calcMode="linear"/></circle></g>')
    for i, (lbl, col) in enumerate(nodes):
        t0 = .3 + (i - 1) * 1.3 + 1.0 if i else 0
        o.append(f'<g><rect x="{xs[i] - 78}" y="{py - 21}" width="156" height="42" rx="21" fill="{col}" opacity="0" filter="url(#gl3)"><animate attributeName="opacity" {hl([(max(0, t0), max(0, t0) + .7)], .6)} dur="{T}s" repeatCount="indefinite"/></rect>'
                 f'<rect x="{xs[i] - 78}" y="{py - 21}" width="156" height="42" rx="21" fill="#09192D" stroke="{col}" stroke-width="1.6"/>'
                 f'<circle cx="{xs[i] - 56}" cy="{py}" r="9" fill="{col}" fill-opacity=".2" stroke="{col}"/><text class="jbb" x="{xs[i] - 56}" y="{py + 4}" font-size="10.5" text-anchor="middle" fill="{col}">{i + 1}</text>'
                 f'<text class="sg" x="{xs[i] - 38}" y="{py + 5}" font-size="14" fill="#E8F1FF">{esc(lbl)}</text></g>')
    o.append('</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Featured project: {esc(P["name"])}"><title>Featured project: {esc(P["name"])}</title>'
            f'<defs>{style_block(css)}{defs}</defs>{"".join(o)}'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="23.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="23" fill="none" stroke="url(#sw)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray=".1 .9"><animate attributeName="stroke-dashoffset" values="1;0" dur="12s" repeatCount="indefinite"/></rect></svg>')


# ───────────────────────────── README ─────────────────────────────
def projects_md(v):
    parts = []
    for i, p in enumerate(CFG["projects"]):
        parts.append(f'<a href="{p["repo"]}"><img src="./project-{i + 1}.svg?v={v}" alt="Featured project: {p["name"]}" width="100%"/></a>\n\n'
                     f'<a href="{p["demo"]}">🚀 <b>Live demo</b></a> &nbsp;·&nbsp; <a href="{p["repo"]}">💻 <b>Source code</b></a>\n\n<br/>\n')
    return "\n".join(parts)

def build_readme():
    t = _emb("README.tpl.md")
    v = datetime.date.today().strftime("%Y%m%d")
    return t.replace("{{V}}", v).replace("{{USER}}", CFG["user"]).replace("{{NAME}}", CFG["name"]).replace("{{ROLE}}", CFG["role"]) \
            .replace("{{EMAIL}}", CFG["email"]).replace("{{IG}}", CFG["instagram"]).replace("{{LI}}", CFG["linkedin_path"])\
            .replace("{{PROJECTS}}", projects_md(v))

def main():
    print("Building profile for", CFG["user"], "(offline)" if OFFLINE else "", "[live-only: README and design files are NOT touched]" if LIVE else "")
    if LIVE:
        # Live refresh updates only the views card and its JSON cache.
        # This avoids unrelated GitHub API requests and keeps the design intact.
        out = {"views.svg": build_views()}
    else:
        st = stats(); print("  stats:", {k: st[k] for k in ("repos", "stars", "forks", "followers", "live")})
        out = {"hero.svg": build_hero(), "id-dashboard.svg": build_id(st), "connect.svg": build_connect(), "stack.svg": build_stack(), "about-life.svg": build_about(),
               "activity.svg": build_activity(), "city.svg": build_city(), "footer.svg": build_footer(), "views.svg": build_views()}
        out.update({f"project-{i + 1}.svg": build_project(i) for i in range(len(CFG["projects"]))})
        out.update(build_buttons())
    for n, s in out.items():
        if s is None: continue
        left = re.findall(r"\{\{[^}]+\}\}", s)
        assert not left, (n, left[:3])
        open(os.path.join(HERE, n), "w", encoding="utf-8").write(s); print(f"  wrote {n:18s} {len(s) / 1024:7.0f} KB")
    if not LIVE:
        open(os.path.join(HERE, "README.md"), "w", encoding="utf-8").write(build_readme()); print("  wrote README.md")

if __name__ == "__main__":
    main()
