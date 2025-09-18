# render_clone_svg_pillow.py
# - Text-BBox via Pillow
# - bottom-up sizing, top-down placement
# - Cmd-Panel (unsichtbar) für Arrow+Label
# - optional drittes Repo (0px wenn nicht genutzt)
# - Messung mit rechtem Innenabstand: 'Z'
# - Middle-Ellipsis für sehr lange Pfade
# - schlanker, gebogener Cmd-Pfeil (eigener Marker)

import json, os, random, re
from typing import List, Tuple, Dict
from PIL import ImageFont, Image, ImageDraw

CFG = "git_diagram_config.json"

# ---------- Fonts ----------
FONT_CANDIDATES_BODY = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
FONT_CANDIDATES_MONO = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\CascadiaMono.ttf",
    r"C:\Windows\Fonts\CascadiaMonoPL.ttf",
]

SVG_FONT_FAMILY_BODY = "Segoe UI, Arial, sans-serif"
SVG_FONT_FAMILY_MONO = "Consolas, Cascadia Mono, monospace"

# ---------- Farben/Abstände ----------
SIDE_MARGIN = 24
TOP_MARGIN  = 24
GAP_H       = 14    # horizontal zwischen Panels
GAP_V       = 10    # vertikal zwischen Bereichen
PANEL_PAD   = 10
REPO_CORNER = 16
PANEL_CORNER= 10
STROKE_REPO = "#5B4B8A"
COL_LOCAL   = "#1B9E77"
COL_REMOTE  = "#111"

# ---------- Mess-Infrastruktur ----------
_MEASURE_IMG = Image.new("L", (8,8), 0)
_MEASURE_DRAW = ImageDraw.Draw(_MEASURE_IMG)

def load_font(candidates: List[str], size: int) -> ImageFont.FreeTypeFont:
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def measure_text(text: str, font: ImageFont.FreeTypeFont, pad_right: bool = False) -> Tuple[int,int]:
    """Misst Text mit Pillow. pad_right=True hängt temporär 'Z' an (rechter Innenabstand)."""
    s = (text + "Z") if pad_right else text
    bbox = _MEASURE_DRAW.textbbox((0,0), s, font=font)
    return (bbox[2]-bbox[0], bbox[3]-bbox[1])

def wrap_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
    """Greedy Wrap (mit Messung)."""
    if not text:
        return [""]
    tokens = re.split(r'(\s+|[\\/])', text)
    lines, cur = [], ""
    for tok in tokens:
        if tok == "":
            continue
        cand = tok if not cur else cur + tok
        w,_ = measure_text(cand, font, pad_right=True)
        if w <= max_width:
            cur = cand
        else:
            if cur.strip():
                lines.append(cur.rstrip())
                cur = tok
            else:
                # Token alleine zu breit -> hard-wrap pro Zeichen
                buf = ""
                for ch in tok:
                    cand2 = buf + ch
                    w2,_ = measure_text(cand2, font, pad_right=True)
                    if w2 <= max_width:
                        buf = cand2
                    else:
                        if buf:
                            lines.append(buf)
                        buf = ch
                cur = buf
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]

def shorten_middle(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
    """Mittiges '…' einfügen, sodass der Text in max_width passt."""
    if not text:
        return ""
    w,_ = measure_text(text, font, pad_right=True)
    if w <= max_width:
        return text
    ell = "…"
    ew,_ = measure_text(ell, font, pad_right=True)
    # Start: etwa 60% links / 40% rechts behalten
    left = int(len(text)*0.6)
    right = len(text) - left
    L = text[:left]
    R = text[-right:] if right>0 else ""
    def total_w(L,R):
        lw,_ = measure_text(L, font, pad_right=True)
        rw,_ = measure_text(R, font, pad_right=True)
        return lw + ew + rw
    # Shrink bis passend
    while total_w(L,R) > max_width and (len(L)>1 or len(R)>1):
        if len(L) >= len(R) and len(L)>1:
            L = L[:-1]
        elif len(R)>1:
            R = R[1:]
        else:
            break
    return L + ell + R

# ---------- SVG helpers ----------
def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def svg_text(x,y,s,fs=16,fw="normal",color="#111",anchor="start",font_family=SVG_FONT_FAMILY_BODY):
    ff = font_family.replace('"','&quot;').replace("'", "&apos;")
    return f'<text x="{x}" y="{y}" font-size="{fs}" font-weight="{fw}" fill="{color}" text-anchor="{anchor}" font-family="{ff}">{esc(s)}</text>'

def svg_rect(x,y,w,h,rx=10,ry=10,stroke="#5B4B8A",fill="#fff",sw=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def svg_line(x1,y1,x2,y2,stroke="#111",sw=2,marker=None):
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{m}/>'

def svg_path(d, stroke="#111", sw=2, fill="none", marker_end=None, linecap="round", linejoin="round"):
    m = f' marker-end="url(#{marker_end})"' if marker_end else ""
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{linecap}" stroke-linejoin="{linejoin}"{m}/>'

def svg_circle(cx,cy,r,stroke="#111",fill="#fff",sw=3):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def rounded_label(x,y,w,h,label,bg="#EEE",fg="#111",bold=False):
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6" fill="{bg}"/>',
        svg_text(x+w/2, y+h*0.7, label, fs=13, fw=("bold" if bold else "normal"), color=fg, anchor="middle")
    ])

def stack_icon(x,y,n=3,w=16,h=10,stroke="#111"):
    parts=[]
    for i in range(n):
        dx=dy=i*2
        parts.append(f'<rect x="{x+dx}" y="{y+dy}" width="{w}" height="{h}" fill="#fff" stroke="{stroke}" stroke-width="1"/>')
    return "\n".join(parts)

# ---------- Panels: measure & draw ----------
def measure_table(title:str, rows:List[Tuple[int,str,int]], font_title, font_row, color:str) -> Tuple[int,int,List[str]]:
    title_lines = wrap_text(title, 600, font_title)
    max_line_w = 0
    for line in title_lines:
        w,_ = measure_text(line, font_title, pad_right=True)
        max_line_w = max(max_line_w, w)
    header_h = 18 + (len(title_lines)-1)*16

    indent_px = 14
    name_w = 0
    for depth,label,_vers in rows:
        w,_ = measure_text(label, font_row, pad_right=True)
        name_w = max(name_w, depth*indent_px + w)

    versions_w = 24 + 18
    content_w = PANEL_PAD + name_w + 20 + versions_w + PANEL_PAD
    total_w = max(PANEL_PAD + max_line_w + PANEL_PAD, content_w)
    row_h = 20
    total_h = PANEL_PAD + header_h + 10 + len(rows)*row_h + PANEL_PAD
    return total_w, total_h, title_lines

def draw_table(x,y,w,h,title_lines,rows,color:str, font_title, font_row):
    parts = [svg_rect(x,y,w,h,PANEL_CORNER,PANEL_CORNER,stroke=color,fill=("#F8FFFB" if color==COL_LOCAL else "#fff"))]
    ty = y + PANEL_PAD + 8
    for i,line in enumerate(title_lines):
        parts.append(svg_text(x+PANEL_PAD, ty + i*16, line, fs=13, fw="bold", color=color))
    by = y + PANEL_PAD + 8 +  (18 + (len(title_lines)-1)*16) + 10
    row_h = 20
    indent_px = 14
    for i,(depth,label,versions) in enumerate(rows):
        ry = by + i*row_h
        indent = depth*indent_px
        parts.append(svg_text(x+PANEL_PAD+indent, ry+12, label, fs=12, color=color))
        if versions>0:
            parts.append(stack_icon(x + w - PANEL_PAD - (24+2), ry+4, n=min(versions,4), stroke=color))
            if versions>4:
                parts.append(svg_text(x + w - PANEL_PAD - (24+2) - 22, ry+12, f"x{versions}", fs=11, color=color))
    return "\n".join(parts)

def measure_history(branches:List[str], commits, active_branch:str, is_local:bool,
                    font_branch, font_hdr, font_hash):
    th = 22
    pill_w = 0
    for b in (branches or ["main"]):
        w,_ = measure_text(b, font_branch, pad_right=True)
        pill_w = max(pill_w, w+20)
    num = max(1, len(branches) if branches else 1)
    branch_area_w = PANEL_PAD + 10 + num*(pill_w+10) + PANEL_PAD
    branch_area_w = max(branch_area_w, 180)

    hash_header_w,_ = measure_text("Hash", font_hdr, pad_right=True)
    type_header_w,_ = measure_text("Type", font_hdr, pad_right=True)
    hash_col_w = hash_header_w
    type_col_w = type_header_w
    for c in commits:
        hw,_ = measure_text(c.get("id",""), font_hash, pad_right=True)
        tw,_ = measure_text(c.get("type","commit"), font_hdr, pad_right=True)
        hash_col_w = max(hash_col_w, hw)
        type_col_w = max(type_col_w, tw)
    refs_w = PANEL_PAD + 10 + hash_col_w + 10 + type_col_w + PANEL_PAD

    total_w = branch_area_w + refs_w
    hdrH = th*2
    min_step = 48
    dag_h = max(1,len(commits)) * min_step
    total_h = PANEL_PAD + hdrH + 10 + dag_h + PANEL_PAD
    return total_w, total_h, {"pill_w":pill_w, "hdrH":hdrH, "branch_area_w":branch_area_w,
                              "hash_col_w":hash_col_w, "type_col_w":type_col_w}

def draw_history(x,y,w,h,branches,commits,active_branch,is_local, font_branch, font_hdr, font_hash, meta:Dict):
    stroke = COL_LOCAL if is_local else COL_REMOTE
    th = 22
    parts = [svg_rect(x,y,w,h,PANEL_CORNER,PANEL_CORNER,stroke=stroke,fill=("#F8FFFB" if is_local else "#fff"))]
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.7"/>')
    parts.append(f'<rect x="{x}" y="{y+th}" width="{w}" height="{th}" fill="#F0F0FF" opacity="0.5"/>')

    branch_area_w = meta["branch_area_w"]
    refs_x = x + branch_area_w

    parts.append(svg_text(x+10, y+th-6, "Branch", fs=13, fw="bold"))
    parts.append(svg_text(refs_x+10, y+th-6, "Refs", fs=13, fw="bold"))
    parts.append(svg_text(refs_x+10, y+2*th-6, "Hash", fs=12, fw="bold"))
    parts.append(svg_text(refs_x+10+meta["hash_col_w"]+10, y+2*th-6, "Type", fs=12, fw="bold"))

    pill_w = meta["pill_w"]
    bx = x+10; by = y+th+4
    for b in (branches or ["main"]):
        parts.append(rounded_label(bx, by, pill_w, th-8, b, bg=("#E3F2FD" if b==(branches or ["main"])[0] else "#EEE"),
                                   fg="#111", bold=(b==active_branch)))
        bx += pill_w + 10

    hdrH = meta["hdrH"]
    dag_y = y + hdrH + 10
    dag_h = h - (PANEL_PAD + hdrH + 10 + PANEL_PAD)
    min_step = 48
    step = max(min_step, dag_h / max(1,len(commits)))
    sx = x + 10 + (branch_area_w - (PANEL_PAD+10+PANEL_PAD))/2
    hash_x = refs_x + 10
    type_x = hash_x + meta["hash_col_w"] + 10

    for i,c in enumerate(commits):
        cy = dag_y + dag_h - (i+1)*step + 10
        if i>0:
            prev = dag_y + dag_h - (i)*step + 10
            parts.append(svg_line(sx, prev, sx, cy, stroke=stroke, sw=3))
        parts.append(svg_circle(sx, cy, 8, stroke=stroke))
        parts.append(svg_text(hash_x, cy+4, c.get("id",""),   fs=12, color=stroke, font_family=SVG_FONT_FAMILY_MONO))
        parts.append(svg_text(type_x, cy+4, c.get("type","commit"), fs=12, color=stroke))
    return "\n".join(parts)

# ---------- Repo-Block ----------
def measure_repo_block(title:str, repo_name:str, is_local:bool, branches, commits,
                       font_title_repo, font_table_title, font_row, font_branch, font_hdr, font_hash):
    rows = [
        (0, f"{repo_name}/", 0),
        (1, "src/", 0),
        (2, "main.c", len(commits)),
        (1, "README.md", len(commits)),
    ]
    wt_w, wt_h, wt_title_lines   = measure_table(f"{repo_name} Working Tree", rows, font_table_title, font_row, COL_LOCAL if is_local else COL_REMOTE)
    idx_w, idx_h, idx_title_lines= measure_table(".git (Index & Staging Area)", rows, font_table_title, font_row, COL_LOCAL if is_local else COL_REMOTE)
    hist_w, hist_h, hist_meta    = measure_history(branches, commits, (branches or [""])[0] if branches else "", is_local, font_branch, font_hdr, font_hash)

    panel_h = max(wt_h, idx_h, hist_h)
    total_w = PANEL_PAD + wt_w + GAP_H + idx_w + GAP_H + hist_w + PANEL_PAD
    _, t_h = measure_text(title, font_title_repo, pad_right=True)
    t_h = max(t_h, 20)
    repo_w = total_w
    repo_h = PANEL_PAD + t_h + 8 + panel_h + PANEL_PAD
    return {
        "wt": (wt_w, wt_h, wt_title_lines),
        "idx": (idx_w, idx_h, idx_title_lines),
        "hist": (hist_w, hist_h, hist_meta),
        "panel_h": panel_h,
        "repo_w": repo_w,
        "repo_h": repo_h,
        "title_h": t_h
    }

def draw_repo_block(x,y,meas,is_local,title,repo_name,branches,commits,
                    font_table_title, font_row, font_branch, font_hdr, font_hash):
    parts=[]
    repo_w = meas["repo_w"]; repo_h = meas["repo_h"]
    parts.append(svg_rect(x,y,repo_w,repo_h,REPO_CORNER,REPO_CORNER,stroke=STROKE_REPO,fill="#fff"))
    parts.append(svg_text(x+PANEL_PAD, y+PANEL_PAD+16, title, fs=16, fw="bold"))
    base_y = y + PANEL_PAD + meas["title_h"] + 8
    panel_h = meas["panel_h"]

    wt_w, _, wt_title_lines = meas["wt"]
    parts.append( draw_table(x+PANEL_PAD, base_y, wt_w, panel_h,
                             wt_title_lines, [
                                 (0, f"{repo_name}/", 0),
                                 (1, "src/", 0),
                                 (2, "main.c", len(commits)),
                                 (1, "README.md", len(commits)),
                             ],
                             COL_LOCAL if is_local else COL_REMOTE,
                             font_table_title, font_row) )

    idx_w, _, idx_title_lines = meas["idx"]
    idx_x = x + PANEL_PAD + wt_w + GAP_H
    parts.append( draw_table(idx_x, base_y, idx_w, panel_h,
                             idx_title_lines, [
                                 (0, f"{repo_name}/", 0),
                                 (1, "src/", 0),
                                 (2, "main.c", len(commits)),
                                 (1, "README.md", len(commits)),
                             ],
                             COL_LOCAL if is_local else COL_REMOTE,
                             font_table_title, font_row) )

    hist_w, _, hist_meta = meas["hist"]
    hist_x = idx_x + idx_w + GAP_H
    parts.append( draw_history(hist_x, base_y, hist_w, panel_h,
                               branches, commits, (branches or [""])[0] if branches else "",
                               is_local, font_branch, font_hdr, font_hash, hist_meta) )
    return "\n".join(parts)

# ---------- Cmd-Panel (unsichtbar, aber mit Kurve & schlanker Spitze) ----------
def measure_cmd_panel(label:str, font_cmd) -> Dict:
    w_text,_ = measure_text(label, font_cmd, pad_right=True)
    arrow_head = 12
    inner_pad  = 16
    w = max(80, w_text + arrow_head*2 + inner_pad*2)
    _, h_text = measure_text(label, font_cmd, pad_right=True)
    h = max(28, h_text + 14)
    return {"w": w, "h": h}

def draw_cmd_panel(x,y,meas_cmd, label:str, font_cmd):
    parts=[]
    w = meas_cmd["w"]; h = meas_cmd["h"]
    cy = y + h/2
    # Gerade Linie, schlanke Spitze:
    parts.append(svg_line(x, cy, x+w, cy, stroke="#111", sw=2, marker="arrowThinOpen"))
    parts.append(svg_text(x + w/2, cy - 8, label, fs=13, anchor="middle"))
    return "\n".join(parts)

# ---------- Diagram ----------
def render():
    with open(CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    third = cfg.get("ThirdRepo")  # optionales drittes Repo

    # Fonts
    font_repo_title = load_font(FONT_CANDIDATES_BODY, 16)
    font_table_title= load_font(FONT_CANDIDATES_BODY, 13)
    font_row        = load_font(FONT_CANDIDATES_BODY, 12)
    font_branch     = load_font(FONT_CANDIDATES_BODY, 13)
    font_hdr        = load_font(FONT_CANDIDATES_BODY, 12)
    font_hash       = load_font(FONT_CANDIDATES_MONO, 12)
    font_cmd        = load_font(FONT_CANDIDATES_MONO, 14)
    font_desc       = load_font(FONT_CANDIDATES_BODY, 14)
    font_syntax     = load_font(FONT_CANDIDATES_BODY, 20)

    # Beispiel-Daten
    random.seed(42)
    commits = [{"id":"".join(random.choice("0123456789abcdef") for _ in range(7)), "type":"commit"} for _ in range(3)]
    branches = [cfg.get("RemoteDefBranch","main")]
    third_commits = [{"id":"".join(random.choice("0123456789abcdef") for _ in range(7)), "type":"commit"} for _ in range(third.get("commits",2))] if third else []

    remote_url = f"git@{cfg['RemoteServer']}:{cfg['RemoteUser']}/{cfg['RemoteRepoName']}.git"
    local_repo = os.path.join(cfg["LocalBaseDir"], cfg["LocalRepoName"])

    # Header-Texte
    syntax = "git clone <URL> [dir]"
    cmd    = rf"{cfg['LocalBaseDir']}>git clone {remote_url}"
    desc   = rf"Erstellt lokales Repo unter {local_repo}, richtet origin ein, holt Objekte/Refs, checkt Default-Branch {cfg['RemoteDefBranch']} aus."

    # --- Repos messen ---
    remote_meas = measure_repo_block(
        title=f"Remote Repository {cfg['RemoteServer']}",
        repo_name=cfg["RemoteRepoName"], is_local=False,
        branches=branches, commits=commits,
        font_title_repo=font_repo_title, font_table_title=font_table_title, font_row=font_row,
        font_branch=font_branch, font_hdr=font_hdr, font_hash=font_hash
    )
    local_meas = measure_repo_block(
        title=f"Lokal: {local_repo}",
        repo_name=cfg["RemoteRepoName"], is_local=True,
        branches=branches, commits=commits,
        font_title_repo=font_repo_title, font_table_title=font_table_title, font_row=font_row,
        font_branch=font_branch, font_hdr=font_hdr, font_hash=font_hash
    )
    if third:
        third_meas = measure_repo_block(
            title=third.get("title","Repo3"),
            repo_name=third.get("repo_name", cfg["RemoteRepoName"]),
            is_local=False,
            branches=third.get("branches", branches),
            commits=third_commits,
            font_title_repo=font_repo_title, font_table_title=font_table_title, font_row=font_row,
            font_branch=font_branch, font_hdr=font_hdr, font_hash=font_hash
        )
    else:
        third_meas = {"repo_w":0, "repo_h":0, "panel_h":0, "title_h":0,
                      "wt":(0,0,[]), "idx":(0,0,[]), "hist":(0,0,{"branch_area_w":0,"hash_col_w":0,"type_col_w":0,"hdrH":0})}

    # --- Cmd-Panel messen ---
    cmd_meas = measure_cmd_panel("clone", font_cmd)

    # Breite
    total_width = SIDE_MARGIN + remote_meas["repo_w"] + GAP_H + cmd_meas["w"] + GAP_H + local_meas["repo_w"]
    if third_meas["repo_w"] > 0:
        total_width += GAP_H + third_meas["repo_w"]
    total_width += SIDE_MARGIN

    # Headerhöhen (jetzt: CMD einzeilig mit Middle-Ellipsis, desc wrap)
    header_max_w = int(total_width - 2*SIDE_MARGIN)
    short_cmd = shorten_middle(cmd, header_max_w, font_cmd)
    _, syntax_h = measure_text(syntax, font_syntax, pad_right=True); syntax_h += 8
    ch = measure_text(short_cmd, font_cmd, pad_right=True)[1]
    cmd_h = ch
    desc_lines = wrap_text(desc, header_max_w, font_desc)
    desc_h = sum(measure_text(line, font_desc, pad_right=True)[1] for line in desc_lines) + (len(desc_lines)-1)*4
    header_h = syntax_h + 4 + cmd_h + 4 + desc_h + 10

    # Gesamthöhe
    repos_h = max(remote_meas["repo_h"], local_meas["repo_h"], third_meas["repo_h"])
    total_height = TOP_MARGIN + header_h + GAP_V + repos_h + TOP_MARGIN

    # --- Zeichnen ---
    parts=[]
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_width)}" height="{int(total_height)}" viewBox="0 0 {int(total_width)} {int(total_height)}">')
    parts.append('<defs>')
    # schlankere Pfeilspitze
    parts.append('  <marker id="arrowThinOpen" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="10" refX="12" refY="5" orient="auto">')
    parts.append('    <path d="M1,1 L11,5 L1,9" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append('  </marker>')
    parts.append(f'  <style> .body{{font-family:{SVG_FONT_FAMILY_BODY}}} .mono{{font-family:{SVG_FONT_FAMILY_MONO}}} </style>')
    parts.append('</defs>')

    # Header
    y = TOP_MARGIN + 8
    parts.append(svg_text(SIDE_MARGIN, y, syntax, fs=20, fw="bold"))
    y += measure_text(syntax, font_syntax, pad_right=True)[1] + 4
    parts.append(svg_text(SIDE_MARGIN, y, short_cmd, fs=14, color="#333", font_family=SVG_FONT_FAMILY_MONO))
    y += measure_text(short_cmd, font_cmd, pad_right=True)[1] + 4
    for line in desc_lines:
        parts.append(svg_text(SIDE_MARGIN, y, line, fs=14, color="#333"))
        y += measure_text(line, font_desc, pad_right=True)[1] + 4

    # Repos & Cmd-Panel
    repos_y = y + GAP_V
    x = SIDE_MARGIN

    # Remote
    # (Titel ggf. per Middle-Ellipsis kürzen, damit er sicher in die Box passt)
    remote_title = shorten_middle(f"Remote Repository {cfg['RemoteServer']}", remote_meas["repo_w"] - 2*PANEL_PAD, font_repo_title)
    parts.append( draw_repo_block(x, repos_y, remote_meas, False,
                                  remote_title, cfg["RemoteRepoName"],
                                  branches, commits,
                                  font_table_title, font_row, font_branch, font_hdr, font_hash) )
    x += remote_meas["repo_w"] + GAP_H

    # Cmd-Panel
    parts.append( draw_cmd_panel(x, repos_y + PANEL_PAD + 16, cmd_meas, "clone", font_cmd) )
    x += cmd_meas["w"] + GAP_H

    # Local (Titel per Middle-Ellipsis)
    local_title_full = f"Lokal: {local_repo}"
    local_title = shorten_middle(local_title_full, local_meas["repo_w"] - 2*PANEL_PAD, font_repo_title)
    parts.append( draw_repo_block(x, repos_y, local_meas, True,
                                  local_title, cfg["RemoteRepoName"],
                                  branches, commits,
                                  font_table_title, font_row, font_branch, font_hdr, font_hash) )
    x += local_meas["repo_w"]

    # Optional drittes Repo
    if third_meas["repo_w"] > 0:
        x += GAP_H
        third_title_full = third.get("title","Repo3")
        third_title = shorten_middle(third_title_full, third_meas["repo_w"] - 2*PANEL_PAD, font_repo_title)
        parts.append( draw_repo_block(x, repos_y, third_meas, False,
                                      third_title, third.get("repo_name", cfg["RemoteRepoName"]),
                                      third.get("branches", branches), third_commits,
                                      font_table_title, font_row, font_branch, font_hdr, font_hash) )

    parts.append('</svg>')

    os.makedirs("out", exist_ok=True)
    out = os.path.join("out", "git_clone_diagram.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"Wrote {out}  ({int(total_width)}x{int(total_height)} px)")

if __name__ == "__main__":
    render()
