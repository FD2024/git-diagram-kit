import json, os, random

CONFIG_FILE = "git_diagram_config.json"
OUT_DIR = "out"
W, H = 1200, 760
MARGIN, GAP = 24, 14

def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def rect(x,y,w,h, rx=10, ry=10, stroke="#5B4B8A", fill="#fff", sw=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def text(x,y,s, size=16, weight="normal", color="#111", anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(s)}</text>'

def line(x1,y1,x2,y2, stroke="#111", sw=2, marker=None, dash=None):
    m = f' marker-end="url(#{marker})"' if marker else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y="{y1}" x2="{x2}" y="{y2}" stroke="{stroke}" stroke-width="{sw}"{m}{d}/>'

def rounded_label(x,y,w,h,label,bg="#EEE", fg="#111", bold=False):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6" fill="{bg}" stroke="none"/>' + \
           text(x+w/2, y+h*0.7, label, size=13, weight=("bold" if bold else "normal"), color=fg, anchor="middle")

def stack_icon(x, y, n=3, w=16, h=10, stroke="#111"):
    parts = []
    for i in range(n):
        dx = dy = i*2
        parts.append(f'<rect x="{x+dx}" y="{y+dy}" width="{w}" height="{h}" fill="#fff" stroke="{stroke}" stroke-width="1"/>')
    return "".join(parts)

def draw_working_index_table(x, y, w, h, title, color, rows):
    th = 22
    parts = [rect(x,y,w,h, rx=10, ry=10, stroke=color, fill=("#F8FFFB" if color=="#1B9E77" else "#fff")),
             text(x+10, y+th, title, size=13, weight="bold", color=color)]
    by = y + th + 10
    row_h = 20
    name_w = int(w*0.7)
    for i,(depth,label,versions) in enumerate(rows):
        ry = by + i*row_h
        indent = 14*depth
        parts.append(text(x+12+indent, ry+14, label, size=12, color=color))
        if versions>0:
            parts.append(stack_icon(x+name_w+20, ry+6, n=min(versions,4), stroke=color))
            if versions>4:
                parts.append(text(x+name_w+20+18, ry+14, f"x{versions}", size=11, color=color))
    return "".join(parts), th

def draw_history_panel(x, y, w, h, branches, commits, active_branch, is_local=False):
    th = 22
    stroke = "#1B9E77" if is_local else "#111"
    fill = "#F8FFFB" if is_local else "#fff"
    parts = [rect(x,y,w,h, rx=10, ry=10, stroke=stroke, fill=fill),
             f'<rect x="{x}" y="{y}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.7"/>',
             f'<rect x="{x}" y="{y+th}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.5"/>']
    branch_w = int(w*0.60); refs_w = w - branch_w; hash_w = int(refs_w*0.55)
    parts += [
        text(x+10, y+th-6, "Branch", size=13, weight="bold"),
        text(x+branch_w+10, y+th-6, "Refs", size=13, weight="bold"),
        text(x+branch_w+10, y+2*th-6, "Hash", size=12, weight="bold"),
        text(x+branch_w+10+hash_w+10, y+2*th-6, "Type", size=12, weight="bold")
    ]
    if branches:
        sub_w = int((branch_w-20)/len(branches))
        cur_x = x+10
        for b in branches:
            bg = "#E3F2FD" if b==branches[0] else "#EEE"
            parts.append(rounded_label(cur_x, y+th+4, sub_w-10, th-8, b, bg=bg, fg="#111", bold=(b==active_branch)))
            cur_x += sub_w
    dag_x = x+10; dag_y = y+2*th + 10; dag_w = branch_w-20; dag_h = h - (2*th + 20)
    node_count = max(1, len(commits)); step = dag_h / node_count
    for i,c in enumerate(commits):
        cy = dag_y + dag_h - (i+1)*step + 10
        cx = dag_x + dag_w*0.5
        if i>0:
            prev_cy = dag_y + dag_h - (i)*step + 10
            parts.append(line(cx, prev_cy, cx, cy, stroke=stroke, sw=3))
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="#fff" stroke="{stroke}" stroke-width="3"/>')
        parts.append(text(x+branch_w+10, cy+4, c["id"], size=12, color=stroke))
        parts.append(text(x+branch_w+10+hash_w+10, cy+4, c["type"], size=12, color=stroke))
    return "".join(parts), th*2

def draw_repo_block(x, y, w, h, title, is_local, repo_name, branches, commits, active_branch):
    parts = [rect(x,y,w,h, rx=16, ry=16, stroke="#5B4B8A", fill="#fff"),
             text(x+16, y+28, title, size=16, weight="bold")]
    wt_w = int(w*0.36); idx_w = int(w*0.28); hist_w = w - (wt_w + idx_w + GAP*4)
    panel_h = h - 56; base_y = y + 40
    color = "#1B9E77" if is_local else "#111"
    rows = [
        (0, f"{repo_name}/", 0),
        (1, "src/", 0),
        (2, "main.c", len(commits)),
        (1, "README.md", len(commits)),
    ]
    wt_svg, _ = draw_working_index_table(x+GAP, base_y, wt_w, panel_h, f"{repo_name} Working Tree", color, rows)
    idx_svg, _ = draw_working_index_table(x+GAP+wt_w+GAP, base_y, idx_w, panel_h, ".git (Index & Staging Area)", color, rows)
    hist_svg, _ = draw_history_panel(x+GAP+wt_w+GAP+idx_w+GAP, base_y, hist_w, panel_h, branches, commits, active_branch, is_local=is_local)
    parts += [wt_svg, idx_svg, hist_svg]
    return "".join(parts)

def main():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    random.seed(42)
    commits = [{"id":"".join(random.choice("0123456789abcdef") for _ in range(7)), "type":"commit"} for _ in range(3)]
    branches = [cfg["RemoteDefBranch"]]
    remote_url = f"git@{cfg['RemoteServer']}:{cfg['RemoteUser']}/{cfg['RemoteRepoName']}.git"
    local_repo_dir = os.path.join(cfg["LocalBaseDir"], cfg["LocalRepoName"])

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', """
<defs>
  <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
    <path d="M2,1 L10,6 L2,11 Z" fill="#111"/>
  </marker>
  <style> text{font-family: Inter, Segoe UI, Arial, sans-serif} </style>
</defs>
"""]
    title_y = MARGIN + 8
    svg.append(text(MARGIN, title_y, "git clone <URL> [dir]", size=20, weight="bold"))
    cmdline = rf"{cfg['LocalBaseDir']}>git clone {remote_url}"
    desc = rf"Erstellt lokales Repo unter {local_repo_dir}, richtet origin ein, holt Objekte/Refs, checkt Default-Branch {cfg['RemoteDefBranch']} aus."
    svg.append(text(MARGIN, title_y+28, cmdline, size=14, color="#333"))
    svg.append(text(MARGIN, title_y+28+22, desc, size=14, color="#333"))

    repo_y = 120
    repo_w = int((W - MARGIN*3) / 2)
    repo_h = H - repo_y - MARGIN - 40
    svg.append(draw_repo_block(MARGIN, repo_y, repo_w, repo_h, f"Remote Repository {cfg['RemoteServer']}", False, cfg["RemoteRepoName"], branches, commits, cfg["RemoteDefBranch"]))
    svg.append(draw_repo_block(MARGIN+repo_w+MARGIN, repo_y, repo_w, repo_h, f"Lokal: {local_repo_dir}", True, cfg["RemoteRepoName"], branches, commits, cfg["RemoteDefBranch"]))

    arrow_y = repo_y + 24
    svg.append(line(MARGIN+repo_w, arrow_y, MARGIN+repo_w+MARGIN, arrow_y, marker="arrow"))
    svg.append(text(MARGIN+repo_w+MARGIN/2, arrow_y-6, "clone", size=13, anchor="middle"))

    svg.append("</svg>")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "git_clone_diagram.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
