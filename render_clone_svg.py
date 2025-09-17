# render_clone_svg.py  — saubere SVG-Ausgabe, kurze Zeilen, kein doppeltes Attribut
import json, os, random

CFG = "git_diagram_config.json"
W, H = 1200, 760
M, G  = 24, 14

def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def T(x,y,s,fs=16,fw="normal",color="#111",anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{fs}" font-weight="{fw}" fill="{color}" text-anchor="{anchor}">{esc(s)}</text>'

def R(x,y,w,h,rx=10,ry=10,stroke="#5B4B8A",fill="#fff",sw=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def L(x1,y1,x2,y2,stroke="#111",sw=2,marker=None):  # <- y1/y2 KORREKT
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{m}/>'

def rounded_label(x,y,w,h,label,bg="#EEE",fg="#111",bold=False):
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6" fill="{bg}"/>',
        T(x+w/2, y+h*0.7, label, fs=13, fw=("bold" if bold else "normal"), color=fg, anchor="middle")
    ])

def stack_icon(x,y,n=3,w=16,h=10,stroke="#111"):
    return "\n".join([f'<rect x="{x+i*2}" y="{y+i*2}" width="{w}" height="{h}" fill="#fff" stroke="{stroke}" stroke-width="1"/>' for i in range(n)])

def draw_table(x,y,w,h,title,color,rows):
    parts = [
        R(x,y,w,h,rx=10,ry=10,stroke=color,fill="#F8FFFB" if color=="#1B9E77" else "#fff"),
        T(x+10, y+22, title, fs=13, fw="bold", color=color),
    ]
    by = y + 22 + 10
    row_h = 20
    name_w = int(w*0.7)
    for i,(depth,label,versions) in enumerate(rows):
        ry = by + i*row_h
        indent = 14*depth
        parts.append(T(x+12+indent, ry+14, label, fs=12, color=color))
        if versions>0:
            parts.append(stack_icon(x+name_w+20, ry+6, n=min(versions,4), stroke=color))
            if versions>4:
                parts.append(T(x+name_w+20+18, ry+14, f"x{versions}", fs=11, color=color))
    return "\n".join(parts)

def draw_history(x,y,w,h,branches,commits,active,is_local=False):
    stroke = "#1B9E77" if is_local else "#111"
    fill   = "#F8FFFB" if is_local else "#fff"
    th = 22
    parts = [
        R(x,y,w,h,rx=10,ry=10,stroke=stroke,fill=fill),
        f'<rect x="{x}" y="{y}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.7"/>',
        f'<rect x="{x}" y="{y+th}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.5"/>'
    ]
    branch_w = int(w*0.60)
    refs_w   = w - branch_w
    hash_w   = int(refs_w*0.55)

    parts += [
        T(x+10, y+th-6, "Branch", fs=13, fw="bold"),
        T(x+branch_w+10, y+th-6, "Refs", fs=13, fw="bold"),
        T(x+branch_w+10, y+2*th-6, "Hash", fs=12, fw="bold"),
        T(x+branch_w+10+hash_w+10, y+2*th-6, "Type", fs=12, fw="bold"),
    ]

    if branches:
        sub_w = int((branch_w-20)/len(branches))
        cur_x = x+10
        for b in branches:
            bg = "#E3F2FD" if b == branches[0] else "#EEE"
            parts.append(rounded_label(cur_x, y+th+4, sub_w-10, th-8, b, bg=bg, fg="#111", bold=(b==active)))
            cur_x += sub_w

    # DAG
    dag_x = x+10
    dag_y = y+2*th + 10
    dag_w = branch_w-20
    dag_h = h - (2*th + 20)
    n = max(1, len(commits))
    step = dag_h / n
    sx = dag_x + dag_w*0.5

    for i,c in enumerate(commits):
        cy = dag_y + dag_h - (i+1)*step + 10
        if i>0:
            prev = dag_y + dag_h - (i)*step + 10
            parts.append(L(sx, prev, sx, cy, stroke=stroke, sw=3))
        parts.append(f'<circle cx="{sx}" cy="{cy}" r="8" fill="#fff" stroke="{stroke}" stroke-width="3"/>')
        parts.append(T(x+branch_w+10,           cy+4, c["id"],   fs=12, color=stroke))
        parts.append(T(x+branch_w+10+hash_w+10, cy+4, c["type"], fs=12, color=stroke))
    return "\n".join(parts)

def draw_repo(x,y,w,h,title,is_local,repo_name,branches,commits,active):
    parts = [
        R(x,y,w,h,rx=16,ry=16,stroke="#5B4B8A",fill="#fff"),
        T(x+16, y+28, title, fs=16, fw="bold"),
    ]
    wt_w = int(w*0.36); idx_w = int(w*0.28); hist_w = w - (wt_w + idx_w + G*4)
    panel_h = h - 56
    base_y = y + 40
    color = "#1B9E77" if is_local else "#111"
    rows = [
        (0, f"{repo_name}/", 0),
        (1, "src/", 0),
        (2, "main.c", len(commits)),
        (1, "README.md", len(commits)),
    ]
    parts.append( draw_table(x+G,                   base_y, wt_w,  panel_h, f"{repo_name} Working Tree",        color, rows) )
    parts.append( draw_table(x+G+wt_w+G,            base_y, idx_w,  panel_h, ".git (Index & Staging Area)",     color, rows) )
    parts.append( draw_history(x+G+wt_w+G+idx_w+G,  base_y, hist_w, panel_h, branches, commits, active, is_local=is_local) )
    return "\n".join(parts)

def render():
    with open(CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    random.seed(42)
    commits = [{"id":"".join(random.choice("0123456789abcdef") for _ in range(7)), "type":"commit"} for _ in range(3)]
    branches = [cfg["RemoteDefBranch"]]
    remote_url = f"git@{cfg['RemoteServer']}:{cfg['RemoteUser']}/{cfg['RemoteRepoName']}.git"
    local_repo = os.path.join(cfg["LocalBaseDir"], cfg["LocalRepoName"])

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    parts.append('<defs>')
    parts.append('  <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">')
    parts.append('    <path d="M2,1 L10,6 L2,11 Z" fill="#111"/>')  # <- korrekt geschlossen
    parts.append('  </marker>')
    parts.append('  <style> text{font-family: Segoe UI, Arial, sans-serif} </style>')
    parts.append('</defs>')

    # Header
    title_y = M + 8
    parts.append(T(M, title_y, "git clone <URL> [dir]", fs=20, fw="bold"))
    parts.append(T(M, title_y+28, rf"{cfg['LocalBaseDir']}>git clone {remote_url}", fs=14, color="#333"))
    parts.append(T(M, title_y+50, rf"Erstellt lokales Repo unter {local_repo}, richtet origin ein, holt Objekte/Refs, checkt Default-Branch {cfg['RemoteDefBranch']} aus.", fs=14, color="#333"))

    # Repos
    repo_y = 120
    repo_w = int((W - M*3) / 2)
    repo_h = H - repo_y - M - 40
    parts.append( draw_repo(M,                 repo_y, repo_w, repo_h, f"Remote Repository {cfg['RemoteServer']}", False, cfg["RemoteRepoName"], branches, commits, cfg["RemoteDefBranch"]) )
    parts.append( draw_repo(M+repo_w+M,        repo_y, repo_w, repo_h, f"Lokal: {local_repo}",                   True,  cfg["RemoteRepoName"], branches, commits, cfg["RemoteDefBranch"]) )

    # Operation arrow
    arrow_y = repo_y + 24
    parts.append( L(M+repo_w, arrow_y, M+repo_w+M, arrow_y, marker="arrow") )
    parts.append( T(M+repo_w+M/2, arrow_y-6, "clone", fs=13, anchor="middle") )

    parts.append("</svg>")

    os.makedirs("out", exist_ok=True)
    with open(os.path.join("out", "git_clone_diagram.svg"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))  # jede SVG-Komponente in eigener Zeile

if __name__ == "__main__":
    render()
