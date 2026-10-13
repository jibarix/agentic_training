"""Build agentic_guide.tex from the research tables (../research/*.md) and content.py.

Usage (from guide/):  python -I build_guide.py
Then:                 pdflatex -disable-installer -interaction=nonstopmode agentic_guide.tex  (x2)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content as C  # noqa: E402

RESEARCH = os.path.join(HERE, C.RESEARCH)
OUT = os.path.join(HERE, "agentic_guide.tex")

BASES = {
    "UVA": "https://www.cs.virginia.edu/~rmw7my/Courses/AgenticAISpring2026/",
    "MANN": "https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Teaching/Large_Language_Models_and_Agents/",
}
CMU_SLIDES = "https://www.cmu-agents.com/slides/"
CMU_SCHEDULE = "https://www.cmu-agents.com/#/schedule"
STAN26_SITE = "https://themodernsoftware.dev/"
MCP_RE = re.compile(r"\bMCP\b|Model Context|\bA2A\b")
TAG2MOD = {t: t for t in C.TAGS if t != "ORG"}

WARNINGS = []
ERRORS = []

# ---------------------------------------------------------------------------
# Text -> LaTeX
# ---------------------------------------------------------------------------
UNI = {
    "\u2014": "---", "\u2013": "--", "\u2192": r"$\rightarrow$", "\u2190": r"$\leftarrow$",
    "\u2194": r"$\leftrightarrow$", "\u21d2": r"$\Rightarrow$",
    "\u2265": r"$\geq$", "\u2264": r"$\leq$", "\u00d7": r"$\times$", "\u2248": r"$\approx$",
    "\u2260": r"$\neq$", "\u223c": r"$\sim$", "\u2018": "`", "\u2019": "'", "\u201c": "``", "\u201d": "''",
    "\u2026": r"\ldots{}", "\u2022": r"\textbullet{}", "\u00b7": r"\textperiodcentered{}",
    "\u00a0": "~", "\u2011": "-", "\u2010": "-", "\u2212": "--", "\u03c4": r"$\tau$", "\u03b1": r"$\alpha$",
    "\u03b2": r"$\beta$", "\u03bb": r"$\lambda$", "\u03c0": r"$\pi$", "\u2713": r"$\checkmark$",
    "\u2605": r"$\star$", "\u2032": "'", "\u202f": "~", "\u2009": " ", "\u200b": "",
}
LATEX_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                 "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def uni(s):
    out = []
    for ch in s:
        if ch in UNI:
            out.append(UNI[ch])
        elif ord(ch) > 0xFF:
            WARNINGS.append(f"unmapped char U+{ord(ch):04X} {ch!r}")
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def esc(s):
    return uni("".join(LATEX_SPECIAL.get(ch, ch) for ch in s))


def url_esc(u):
    u = u.replace("~", "%7E").replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
    return u


URL_RE = re.compile(r"https?://[^\s<>\"'`|]+")
MDLINK_RE = re.compile(r"\[([^\]]+)\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)")
CODE_RE = re.compile(r"`([^`]+)`")


def clean_url(u):
    u = u.rstrip(".,;:")
    while u.endswith(")") and u.count("(") < u.count(")"):
        u = u[:-1]
    while u.endswith("]"):
        u = u[:-1]
    return u.rstrip(".,;:")


def url_label(u):
    low = u.lower()
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", low)
    if m:
        return "arXiv:" + m.group(1)
    if "github.com" in low:
        return "GitHub"
    if "youtube.com" in low or "youtu.be" in low:
        return "video"
    if "docs.google.com/presentation" in low:
        return "slides"
    path = low.split("?")[0]
    for ext, lab in ((".pdf", "PDF"), (".pptx", "PPTX"), (".ipynb.zip", "notebook zip"), (".zip", "zip"),
                     (".ipynb", "notebook"), (".mp3", "audio"), (".m4a", "audio")):
        if path.endswith(ext):
            return lab
    dom = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
    return dom


def expand_base(s, code):
    if code in BASES:
        s = s.replace(".../", BASES[code])
    return s


def md2tex(s, code=None):
    """Convert one Markdown table cell to LaTeX."""
    s = expand_base(s.strip(), code)
    ph = []

    def keep(tex):
        ph.append(tex)
        return f"@@PH{len(ph) - 1}@@"

    s = MDLINK_RE.sub(lambda m: keep(r"\href{%s}{%s}" % (url_esc(m.group(2)), esc(m.group(1)))), s)
    s = CODE_RE.sub(lambda m: keep(r"\texttt{%s}" % re.sub(r"(/|\.|\\_)", r"\1\\allowbreak{}", esc(m.group(1)))), s)

    def bare(m):
        raw = m.group(0)
        u = clean_url(raw)
        tail = raw[len(u):]
        return keep(r"\href{%s}{[%s]}" % (url_esc(u), esc(url_label(u)))) + tail

    s = URL_RE.sub(bare, s)
    s = esc(s).replace(r"\_", r"\_\allowbreak{}")
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    for i, tex in enumerate(ph):
        s = s.replace(f"@@PH{i}@@", tex)
    return s


def links_only(s, code=None):
    """Only the links of a cell, as compact labelled hrefs."""
    s = expand_base(s or "", code)
    out = []
    for m in MDLINK_RE.finditer(s):
        t = m.group(1)
        out.append(r"\href{%s}{[%s]}" % (url_esc(m.group(2)), esc(t if len(t) < 28 else t[:25] + "...")))
    s2 = MDLINK_RE.sub(" ", s)
    for m in URL_RE.finditer(s2):
        u = clean_url(m.group(0))
        out.append(r"\href{%s}{[%s]}" % (url_esc(u), esc(url_label(u))))
    return " ".join(out)


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------
def read(fn):
    with open(os.path.join(RESEARCH, fn), encoding="utf-8") as f:
        return f.read()


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def fit_row(code, r, n, where):
    """Pad a row to n cells; record an error if it has too many (data would shift or be lost)."""
    if len(r) > n:
        ERRORS.append(f"{code} {where}: row has {len(r)} cells, expected {n}: {' | '.join(r)[:80]}")
    return (r + [""] * n)[:n]


def check_header(code, t, n, where):
    if len(t["header"]) != n:
        ERRORS.append(f"{code} {where}: header has {len(t['header'])} columns, expected {n}: {t['header']}")


def check_tags(code, raw, where):
    bad = [t for t in re.split(r"[,\s]+", raw.upper()) if t and t not in C.TAGS and t != "N/A" and not re.fullmatch(r"[\W_]+", t)]
    if bad:
        ERRORS.append(f"{code} {where}: unknown tag(s) {bad}")


def tables_in(text):
    """Return list of tables (list of row-cell-lists, header removed) in text."""
    tables, cur = [], None
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = split_row(line)
            if cur is None:
                cur = {"header": cells, "rows": []}
            elif all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            else:
                cur["rows"].append(cells)
        else:
            if cur is not None:
                tables.append(cur)
                cur = None
    if cur is not None:
        tables.append(cur)
    return tables


def section(text, heading_re, level=2):
    """Text of the first section whose heading matches heading_re (until next heading of same/higher level)."""
    lines = text.splitlines()
    pat = re.compile(r"^#{%d}\s+%s" % (level, heading_re))
    stop = re.compile(r"^#{1,%d}\s" % level)
    out, on = [], False
    for ln in lines:
        if on and stop.match(ln):
            break
        if pat.match(ln):
            on = True
            continue
        if on:
            out.append(ln)
    return "\n".join(out)


def parse_tags(s):
    return [t for t in re.split(r"[,\s]+", s.upper()) if t in C.TAGS]


def make_lecture(code, num, date, title, topics, readings, materials, tags):
    return dict(code=code, num=num, date=date, title=title, topics=topics, readings=readings,
                materials=materials, tags=tags, anchor=f"lec-{code}-{num}")


def eligible_for_modules(L):
    if re.match(r"\s*guest", L["title"], re.I):
        return False
    return bool(set(L["tags"]) - {"ORG"})


def parse_std_lectures(code, text):
    tabs = tables_in(section(text, r"Lectures"))
    if not tabs:
        ERRORS.append(f"{code}: no lecture table")
        return []
    check_header(code, tabs[0], 7, "lectures")
    lecs, extra = [], 0
    for r in tabs[0]["rows"]:
        num, date, title, topics, readings, materials, tags = fit_row(code, r, 7, "lectures")
        check_tags(code, tags, f"lecture {num}")
        tags = parse_tags(tags)
        if re.search(r"no calendar entry|^\(in-class lab", title):
            continue
        if not re.fullmatch(r"\d+", num):
            if not (set(tags) - {"ORG"}):
                continue
            extra += 1
            num = f"x{extra}"
        lecs.append(make_lecture(code, num, date, title, topics, readings, materials, tags))
    return lecs


def parse_cmu_lectures(text):
    tabs = tables_in(text)
    check_header("CMU", tabs[0], 9, "lectures")
    lecs = []
    for r in tabs[0]["rows"]:
        num, date, title, module, lecturer, readings, slides, rec, tags = fit_row("CMU", r, 9, "lectures")
        check_tags("CMU", tags, f"lecture {num}")
        if not re.fullmatch(r"\d+", num):
            continue
        topics = f"Module: {module}" + (f"; lecturer: {lecturer}" if lecturer else "")
        mats = []
        if slides.endswith(".pdf"):
            mats.append(f"[slides]({CMU_SLIDES}{slides})")
        if rec.strip().upper() == "Y":
            mats.append(f"[video]({CMU_SCHEDULE})")
        lecs.append(make_lecture("CMU", num, date, title, topics, readings, " ".join(mats), parse_tags(tags)))
    return lecs


def parse_stan26_lectures(text):
    tabs = tables_in(text)
    check_header("STAN26", tabs[0], 4, "lectures")
    lecs, theme, wk = [], "", ""
    for i, r in enumerate(tabs[0]["rows"], 1):
        w, date, session, tags = fit_row("STAN26", r, 4, "lectures")
        check_tags("STAN26", tags, f"session {i}")
        m = re.match(r"(\d+)\s*(.*)", w)
        if m:
            wk = m.group(1)
            if m.group(2):
                theme = m.group(2)
        title, readings = session, ""
        mm = re.match(r"(.*?)\s*\(readings?:\s*(.*)\)\s*$", session)
        if mm:
            title, readings = mm.group(1), mm.group(2)
        lecs.append(make_lecture("STAN26", str(i), date, title, f"Week {wk}: {theme}", readings,
                                 f"[course site]({STAN26_SITE})", parse_tags(tags)))
    return lecs


def parse_assignments(code, text, subsection=None):
    sec = section(text, r"Assignments")
    if subsection:
        sec = section(sec, re.escape(subsection), level=3)
    if not sec.strip():
        ERRORS.append(f"{code}: no '## Assignments' section" + (f" / '### {subsection}'" if subsection else ""))
    out = []
    for t in tables_in(sec):
        if not t["header"] or not t["header"][0].lower().startswith("name"):
            continue
        check_header(code, t, 5, "assignments")
        for r in t["rows"]:
            name, build, skills, starter, tags = fit_row(code, r, 5, "assignments")
            check_tags(code, tags, f"assignment {name[:30]}")
            out.append(dict(code=code, name=name, build=build, skills=skills, starter=starter,
                            tags=parse_tags(tags), anchor=f"asg-{code}-{len(out) + 1}"))
    if not out:
        ERRORS.append(f"{code}: no assignment table (first header cell must start with 'Name')")
    return out


def bullets(text):
    items, cur = [], None
    for ln in text.splitlines():
        if re.match(r"^\s*[-*]\s+", ln):
            if cur:
                items.append(cur)
            cur = re.sub(r"^\s*[-*]\s+", "", ln)
        elif ln.strip() and cur is not None:
            cur += " " + ln.strip()
        elif not ln.strip() and cur:
            items.append(cur)
            cur = None
    if cur:
        items.append(cur)
    return items


def load_courses():
    for c in C.COURSES:
        text = read(c["file"])
        if c["kind"] == "cmu":
            c["lectures"] = parse_cmu_lectures(text)
        elif c["kind"] == "stan26":
            c["lectures"] = parse_stan26_lectures(text)
        else:
            c["lectures"] = parse_std_lectures(c["code"], text)
        atext = read(c.get("asg_file", c["file"]))
        c["assignments"] = parse_assignments(c["code"], atext, c.get("asg_section"))
        ctext = atext if c["kind"] in ("cmu", "stan26") else text
        c["codebases"] = bullets(section(ctext, r"Codebases"))
        c["notes"] = bullets(section(text if c["kind"] == "std" else ctext, r"Notes"))
        if c["kind"] == "stan26":  # shares stanford-cs146s.md with STAN25; avoid duplicating its lists
            c["codebases"], c["notes"] = [], []
    return {c["code"]: c for c in C.COURSES}


# ---------------------------------------------------------------------------
# Cross references
# ---------------------------------------------------------------------------
CO = {}
MODS = {m["key"]: m for m in C.MODULES}


def find_lecture(code, num):
    c = CO.get(code)
    if not c:
        return None
    for L in c["lectures"]:
        if L["num"] == num:
            return L
    return None


def find_asg(code, prefix):
    c = CO.get(code)
    if not c:
        return None
    for a in c["assignments"]:
        if a["name"].startswith(prefix):
            return a
    return None


def short_title(t, n=70):
    t = re.sub(r"\s*\(.*?\)\s*$", "", t) if len(t) > n else t
    return t if len(t) <= n else t[: n - 3] + "..."


def asg_label(a):
    name = re.split(r"\s+\(", a["name"])[0]
    return f"{CO[a['code']]['short']}: {name}"


def ref_tex(body):
    parts = body.split("|")
    key, mode = parts[0], (parts[1] if len(parts) > 1 else "")
    bits = key.split(":")
    if bits[0] == "M" and len(bits) == 2:
        m = MODS.get(bits[1])
        if not m:
            ERRORS.append(f"bad module ref {body}")
            return "??"
        return r"\hyperlink{mod-%s}{Module~%d (%s)}" % (m["key"], m["num"], m["title"])
    if bits[0] == "C" and len(bits) == 2:
        c = CO.get(bits[1])
        if not c:
            ERRORS.append(f"bad course ref {body}")
            return "??"
        return r"\hyperlink{course-%s}{%s %s}" % (c["code"], esc(c["short"]), esc(c["title"]))
    if bits[0] == "A" and len(bits) >= 3:
        a = find_asg(bits[1], ":".join(bits[2:]))
        if not a:
            ERRORS.append(f"bad assignment ref {body}")
            return "??"
        return r"\hyperlink{%s}{\textbf{%s}}" % (a["anchor"], esc(asg_label(a)))
    if len(bits) == 2:
        L = find_lecture(bits[0], bits[1])
        if not L:
            ERRORS.append(f"bad lecture ref {body}")
            return "??"
        lab = f"{CO[L['code']]['short']}~{L['num']}"
        lab = esc(lab).replace(r"\textasciitilde{}", "~")
        if mode == "short":
            return r"\hyperlink{%s}{%s}" % (L["anchor"], lab)
        return r"\hyperlink{%s}{%s \emph{%s}}" % (L["anchor"], lab, md2tex(short_title(L["title"])))
    ERRORS.append(f"unparsable ref {body}")
    return "??"


REF_RE = re.compile(r"\[\[([^\]]+)\]\]")


def X(s):
    return REF_RE.sub(lambda m: ref_tex(m.group(1)), s)


def refs_in(s):
    return REF_RE.findall(s)


# ---------------------------------------------------------------------------
# Module membership
# ---------------------------------------------------------------------------
def in_module(L, m):
    if not m["tags"] or not eligible_for_modules(L):
        return False
    tag = m["tags"][0]
    if m["mcp"] is True:
        return is_mcp(L)
    if tag not in L["tags"]:
        return False
    if m["mcp"] is False and is_mcp(L):
        return False
    return True


def is_mcp(L):
    """TOOL lectures about MCP/A2A go to the MCP module instead of the TOOL module."""
    return "TOOL" in L["tags"] and bool(MCP_RE.search(L["title"] + " " + L["topics"]))


def starter_label(a):
    """What the links in an assignment's starter column are: code, a spec only, or other resources."""
    s = a["starter"].strip()
    if re.match(r"(none|n/a)\b", s, re.I):
        return "Spec"
    if re.match(r"project topic", a["name"], re.I):  # Mannheim: benchmarks and data sources, not starter code
        return "Resources"
    return "Starter code"


def module_lectures(m):
    return [L for c in C.COURSES for L in c["lectures"] if in_module(L, m)]


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def tag_box(t):
    box = r"\tg{%s}" % t
    if t in TAG2MOD:
        return r"\hyperlink{mod-%s}{%s}" % (TAG2MOD[t], box)
    return box


def tag_boxes(tags):
    return " ".join(tag_box(t) for t in tags) or "--"


def dash(s):
    s = (s or "").strip()
    return "--" if s in ("", "n/a", "N/A", "-", "\u2013", "\u2014", "none") else s


PREAMBLE = r"""\documentclass[10pt,oneside]{report}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[letterpaper,margin=2cm,headheight=14pt]{geometry}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{array,longtable,booktabs,tabularx}
\usepackage{enumitem}
\usepackage{amssymb}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{parskip}
\usepackage{multicol}
\usepackage[most]{tcolorbox}
\usepackage[colorlinks=true,linkcolor=blue!55!black,urlcolor=teal!55!black,
            bookmarksnumbered=false,bookmarksopen=true,bookmarksopenlevel=1,
            pdftitle={Learning to Build Agentic Systems: An instructional compilation guide built from public university courses},
            pdfauthor={J. A. Arroyo}]{hyperref}
\usepackage{bookmark}
\urlstyle{same}
\setcounter{secnumdepth}{-1}
\setcounter{tocdepth}{1}
\setlist{nosep,leftmargin=*}
\emergencystretch=2em
\setlength{\LTpre}{4pt}\setlength{\LTpost}{4pt}
\titleformat{\part}[display]{\centering\Huge\bfseries}{}{0pt}{}
\titleformat{\chapter}[hang]{\LARGE\bfseries\color{blue!40!black}}{}{0pt}{}
\titlespacing*{\chapter}{0pt}{0pt}{10pt}
\titleformat{\section}{\large\bfseries\color{blue!40!black}}{}{0pt}{}
\titlespacing*{\section}{0pt}{10pt}{4pt}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{8pt}{2pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\nouppercase{\leftmark}}
\fancyhead[R]{\small\hyperlink{toc}{Contents} $\cdot$ \hyperlink{navmatrix}{Matrix} $\cdot$ \thepage}
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\renewcommand{\headrulewidth}{0.3pt}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcommand{\tg}[1]{{\setlength{\fboxsep}{1.2pt}\colorbox{tag#1}{\kern1pt\textcolor{white}{\sffamily\bfseries\fontsize{5.5}{6}\selectfont\strut #1}\kern1.5pt}}}
\newtcolorbox{infobox}[1][]{colback=blue!4!white,colframe=blue!40!black,boxrule=0.5pt,arc=1mm,left=4pt,right=4pt,top=3pt,bottom=3pt,fonttitle=\bfseries\small,#1}
"""


class Doc:
    def __init__(self):
        self.parts = []

    def __call__(self, *lines):
        self.parts.extend(lines)

    def text(self):
        return "\n".join(self.parts) + "\n"


def stats():
    nl = sum(len(c["lectures"]) for c in C.COURSES)
    na = sum(len(c["assignments"]) for c in C.COURSES)
    return nl, na


# ---------------------------------------------------------------------------
# Part I
# ---------------------------------------------------------------------------
def part_intro(D):
    nl, na = stats()
    D(r"\part{Orientation}", r"\chapter{How to Use This Guide}")
    D(r"""This guide compiles %d public university courses on LLM agents and agentic systems, plus %d supplementary resources, into one curriculum you can navigate. Most come from your \emph{CMU-Agentic} bookmarks folder; the rest were added after a targeted search for courses strong in evaluation, training and security.
Every one of the %d catalogued lectures and %d assignments is classified with one shared set of topic tags, so the same subject can be followed across courses.""" % (len(C.COURSES), len(C.SUPPLEMENTS), nl, na))
    D(r"""\begin{infobox}[title=One set of three documents]
\begin{enumerate}
\item \textbf{Learning to Build Agentic Systems} (this guide): the courses, lectures and assignments behind the practices. \emph{Use it to learn a topic.}
\item \textbf{Agentic System Design Process} (\texttt{design\_process/design\_process.pdf}): nine phases from framing a problem to running it in production, each citing the courses indexed here. \emph{Use it to design a system.}
\item \textbf{Screening Tasks for Agentic Automation} (\texttt{design\_process/task\_screening.pdf}): a one-page worksheet, filled in after Phase~1 of the design process, that feeds Phase~2 and sets up the comparison run in Phase~7. \emph{Use it to decide whether a task is worth it.}
\end{enumerate}
The modules map onto the design phases: \hyperlink{mod-ARCH}{\tg{ARCH}} for Phases 2--3, \hyperlink{mod-EVAL}{\tg{EVAL}} for Phases 4 and 7, \hyperlink{mod-TOOL}{\tg{TOOL}} and \hyperlink{mod-MEM}{\tg{MEM}} for Phase~5, \hyperlink{mod-SAFE}{\tg{SAFE}} for Phase~8 and \hyperlink{mod-DEPLOY}{\tg{DEPLOY}} for Phase~9.
\end{infobox}""")
    D(r"""\begin{infobox}[title=Four ways in]
\begin{itemize}
\item \textbf{Follow a track} (\hyperlink{tracks}{Learning tracks}): a role-based path through the modules, or the \hyperlink{plan16}{16-week self-study plan}.
\item \textbf{Study a topic} (Part~II, \hyperlink{mod-SETUP}{Modules 0--14}): each module gives learning objectives, a short conceptual primer, a \emph{curated} sequence of the best lectures across courses, an automatically generated map of \emph{every} relevant lecture, key readings and hands-on assignments.
\item \textbf{Browse a course} (Part~III, \hyperlink{catalog}{Course catalogue}): each course card is followed by its full lecture table and assignment table with all public links.
\item \textbf{Jump around} with the \hyperlink{navmatrix}{course $\times$ module matrix}. Every coloured tag box, lecture reference and assignment name is a hyperlink, and the page header always links back to Contents and the Matrix.
\end{itemize}
\end{infobox}""")
    D(r"""\section{Conventions}
\begin{itemize}
\item Lecture references look like \textbf{CMU~2} (course code and session number in that course's own schedule) and link to the row in the catalogue, which has dates, topics, readings and materials.
\item Material links are labelled by type: \texttt{[slides]}, \texttt{[video]}, \texttt{[PDF]}, \texttt{[PPTX]}, \texttt{[GitHub]}, \texttt{[arXiv:\ldots]}, \texttt{[notebook zip]}, or the site's domain.
\item In module lecture maps, $\star$ marks the lectures chosen for the curated sequence.
\item Guest talks and purely logistical sessions stay in the catalogue but are left out of the module maps.
\item In hands-on lists, ``Starter code'' means the assignment has a public repository or download, ``Spec'' links to a written specification with no code, and ``Resources'' links to benchmarks or data sources the project builds on.
\end{itemize}
\section{A note on currency}
The material spans Spring 2024 (TinyAgent) to courses still running in October 2026. Two things change fast. (1)~\textbf{MCP:} the 2026-07-28 revision made the protocol stateless (see \hyperref[sup-mcp]{the MCP supplement}), so earlier lectures teach the older handshake. (2)~\textbf{Model names and SDKs:} courses use whatever was current when they ran. Learn the concepts from the lectures and take API details from current documentation.""")


def part_legend(D):
    D(r"\chapter{Tag Legend}", r"""Every lecture and assignment carries one or more tags. Each tag (except \tg{ORG}) corresponds to a module in Part~II. \tg{TOOL} lectures that are mainly about MCP or A2A are collected in their own module.""")
    D(r"\begin{longtable}{l P{4cm} P{7.5cm} r}", r"\toprule Tag & Meaning & Module & Lectures\\ \midrule")
    for t, (name, _) in C.TAGS.items():
        n = sum(1 for c in C.COURSES for L in c["lectures"] if t in L["tags"])
        mod = "--"
        if t in TAG2MOD:
            m = MODS[TAG2MOD[t]]
            mod = r"\hyperlink{mod-%s}{Module %d: %s}" % (m["key"], m["num"], m["title"])
            if t == "TOOL":
                mm = MODS["MCP"]
                mod += r"; \hyperlink{mod-MCP}{Module %d: %s}" % (mm["num"], mm["title"])
        D(r"%s & %s & %s & %d\\" % (tag_box(t), esc(name), mod, n))
    D(r"\bottomrule\end{longtable}")


def part_glance(D):
    D(r"\chapter{The Courses at a Glance}")
    D(r"""The courses fall into a few archetypes, and knowing which kind you are reading tells you how to use it:
\begin{itemize}
\item \textbf{Systems and training} (CMU): the backbone, from harnesses to RL, with the best assignments.
\item \textbf{Builder courses} (Northeastern, UVA, Buffalo, Mannheim): framework-based, hands-on and lab-driven.
\item \textbf{Coding-agent practice} (Stanford CS146S, both years): how practitioners work with and around coding agents.
\item \textbf{Research seminars} (UW--Madison, CU Boulder): curated paper lists, for depth and for the research frontier.
\item \textbf{Program synthesis} (JHU): the PL view of code generation, from classic search to LLM coding agents.
\item \textbf{Applied social science} (UChicago): agents as simulated subjects and research instruments.
\end{itemize}""")
    D(r"{\footnotesize\begin{longtable}{P{2.2cm} P{3.0cm} P{2.9cm} P{1.6cm} P{5.2cm}}",
      r"\toprule Course & Archetype / level & Public materials & Lectures / assignments & Best for\\ \midrule\endhead")
    for c in C.COURSES:
        D(r"\hyperlink{course-%s}{\textbf{%s}}\newline %s & %s\newline\emph{%s} & Slides: %s\newline Video: %s\newline Code: %s & %d / %d & %s\\ \midrule" % (
            c["code"], esc(c["short"]), esc(c["title"]), esc(c["archetype"]), esc(c["level"]),
            esc(c["slides"]), esc(c["video"]), esc(c["codepub"]), len(c["lectures"]), len(c["assignments"]), esc(c["best"])))
    D(r"\end{longtable}}")


def part_matrix(D):
    mods = [m for m in C.MODULES if m["tags"]]
    D(r"\chapter{Course $\times$ Module Navigation Matrix}\hypertarget{navmatrix}{}")
    D(r"""Each cell is the number of lectures from a course in a module. Click a number to open the module, or a course name to open its catalogue entry. Column headers are module numbers:
""" + "; ".join(r"\hyperlink{mod-%s}{%d~%s}" % (m["key"], m["num"], m["title"].split(":")[0].split(",")[0]) for m in mods) + ".")
    cols = "l" + "c" * len(mods) + "r"
    D(r"{\small\setlength{\tabcolsep}{4pt}\begin{longtable}{%s}" % cols)
    D(r"\toprule Course & " + " & ".join(r"\hyperlink{mod-%s}{\textbf{%d}}" % (m["key"], m["num"]) for m in mods) + r" & All\\ \midrule")
    tot = [0] * len(mods)
    for c in C.COURSES:
        row = []
        for i, m in enumerate(mods):
            n = sum(1 for L in c["lectures"] if in_module(L, m))
            tot[i] += n
            row.append(r"\hyperlink{mod-%s}{{\setlength{\fboxsep}{1.5pt}\colorbox{blue!%d}{\makebox[1.1em]{%d}}}}" % (m["key"], min(5 + 7 * n, 45), n) if n else r"\textcolor{black!25}{0}")
        D(r"\hyperlink{course-%s}{%s} & %s & %d\\" % (c["code"], esc(c["short"]), " & ".join(row), len(c["lectures"])))
    D(r"\midrule Total & " + " & ".join(str(t) for t in tot) + r" & \\ \bottomrule\end{longtable}}")
    D(r"A lecture can appear in several modules. Logistics rows and guest talks count toward \emph{All} but not toward any module.")


def part_tracks(D):
    D(r"\chapter{Learning Tracks}\hypertarget{tracks}{}")
    D(r"""Choose a track by goal. All tracks assume Python fluency. Track~C also assumes basic deep learning (PyTorch, transformers). Each module's curated sequence is the default path; the lecture map lists alternatives.""")
    for t in C.TRACKS:
        path = r" $\rightarrow$ ".join(r"\hyperlink{mod-%s}{M%d}" % (k, MODS[k]["num"]) for k in t["path"])
        D(r"\section{%s}" % t["name"],
          r"\textbf{For:} %s\par" % t["who"],
          r"\textbf{Path:} %s\par" % path,
          r"\textbf{Spine courses:} %s\par" % X(t["spine"]),
          r"\textbf{Capstone:} %s\par" % X(t["capstone"]))
    D(r"\section{A 16-Week Self-Study Plan}\hypertarget{plan16}{}")
    D(r"""Roughly 8--10 hours a week: watch or read the listed sessions (slides first, then papers), then build. The plan follows Track~A but includes the core of B and C. Adjust it freely.""")
    D(r"{\footnotesize\begin{longtable}{c P{2.4cm} P{6.4cm} P{6.4cm}}",
      r"\toprule Wk & Module & Watch / read & Build\\ \midrule\endhead")
    for wk, mods, watch, build in C.PLAN:
        mlinks = ", ".join(
            (r"\hyperlink{mod-%s}{%s}" % (k.split()[0], k) if k.split()[0] in MODS else k) for k in [x.strip() for x in mods.split(",")])
        D(r"%s & %s & %s & %s\\ \midrule" % (wk, mlinks, X(watch), X(build)))
    D(r"\end{longtable}}")


# ---------------------------------------------------------------------------
# Part II: modules
# ---------------------------------------------------------------------------
def part_modules(D):
    D(r"\part{Topic Modules}")
    for m in C.MODULES:
        D(r"\chapter{Module %d: %s}\hypertarget{mod-%s}{}" % (m["num"], m["title"], m["key"]))
        if m["tags"]:
            extra = ""
            if m["key"] == "MCP":
                extra = r" (lectures tagged \tg{TOOL} whose title or topics mention MCP or A2A)"
            elif m["key"] == "TOOL":
                extra = r" (MCP-focused lectures are in \hyperlink{mod-MCP}{Module 4})"
            D(r"{\small Tag: %s%s}" % (r"\tg{%s}" % m["tags"][0], extra))
        D(r"\section{Learning objectives}", r"\begin{itemize}")
        for o in m["objectives"]:
            D(r"\item " + X(o))
        D(r"\end{itemize}")
        D(r"\section{Core concepts}", X(m["concepts"]))
        D(r"\section{Curated learning sequence}", r"\begin{enumerate}")
        for ref, note in m["sequence"]:
            D(r"\item %s --- %s" % (X(ref), X(note)))
        D(r"\end{enumerate}")
        curated = set()
        for ref, _ in m["sequence"]:
            for r in refs_in(ref):
                k = r.split("|")[0]
                if k.count(":") == 1 and not k.startswith(("M:", "C:")):
                    curated.add(k)
            # ranges like [[NEU:7]]--[[NEU:9|short]]
            rr = re.findall(r"\[\[(\w+):(\d+)(?:\|short)?\]\]--\[\[\1:(\d+)(?:\|short)?\]\]", ref)
            for code, a, b in rr:
                for n in range(int(a), int(b) + 1):
                    curated.add(f"{code}:{n}")
        lecs = module_lectures(m)
        if lecs:
            D(r"\section{Lecture map (%d lectures)}" % len(lecs))
            D(r"{\footnotesize\begin{longtable}{P{1.75cm} P{0.4cm} P{5.75cm} P{4.2cm} P{2.65cm}}",
              r"\toprule Course & \# & Title (links to catalogue row) & Materials & Tags\\ \midrule\endhead")
            for L in lecs:
                star = r"$\star$\," if f"{L['code']}:{L['num']}" in curated else ""
                D(r"\hyperlink{course-%s}{%s} & %s & %s\hyperlink{%s}{%s} & %s & %s\\" % (
                    L["code"], esc(CO[L["code"]]["short"]), esc(L["num"]), star, L["anchor"], md2tex(L["title"]),
                    links_only(L["materials"], L["code"]) or "--", tag_boxes(L["tags"])))
            D(r"\bottomrule\end{longtable}}")
        if m["readings"]:
            D(r"\section{Key readings}", r"\begin{itemize}")
            for r in m["readings"]:
                D(r"\item " + X(r))
            D(r"\end{itemize}")
        if m["handson"]:
            D(r"\section{Hands-on}", r"\begin{itemize}")
            for h in m["handson"]:
                body = REF_RE.fullmatch(h.strip())
                a = None
                if body and body.group(1).startswith("A:"):
                    bits = body.group(1).split(":")
                    a = find_asg(bits[1], ":".join(bits[2:]))
                if a:
                    st = links_only(a["starter"], a["code"])
                    st = (r" \textit{%s:} %s" % (starter_label(a), st)) if st else r" \textit{(spec only)}"
                    D(r"\item %s --- %s.%s" % (X(h), md2tex(a["build"]).rstrip("."), st))
                else:
                    D(r"\item " + X(h))
            D(r"\end{itemize}")
        sups = [s for s in C.SUPPLEMENTS if m["tags"] and m["tags"][0] in s["tags"] and
                (m["key"] != "TOOL" or s["key"] != "sup-mcp")]
        if sups:
            D(r"\textbf{Related supplements:} " + ", ".join(r"\hyperref[%s]{%s}" % (s["key"], esc(s["name"])) for s in sups) + ".")


# ---------------------------------------------------------------------------
# Part III: catalogue
# ---------------------------------------------------------------------------
def part_catalog(D):
    D(r"\part{Course Catalogue}\hypertarget{catalog}{}")
    for c in C.COURSES:
        D(r"\chapter{%s: %s}\hypertarget{course-%s}{}" % (esc(c["short"]), esc(c["title"]), c["code"]))
        D(r"{\small\begin{tabularx}{\linewidth}{@{}>{\bfseries}l X@{}}\toprule")
        for k, v in (("Institution", esc(c["inst"]) if "\\" not in c["inst"] else c["inst"]), ("Term", esc(c["term"])),
                     ("Instructors", esc(c["people"])), ("Website", r"\href{%s}{%s}" % (url_esc(c["url"]), esc(c["url"]))),
                     ("Level", esc(c["level"])), ("Archetype", esc(c["archetype"])),
                     ("Public materials", "Slides: %s; video: %s; code: %s" % (esc(c["slides"]), esc(c["video"]), esc(c["codepub"]))),
                     ("Best for", esc(c["best"]))):
            D(r"%s & %s\\" % (k, v))
        D(r"\bottomrule\end{tabularx}}", "", X(c["overview"]))
        D(r"\section{Lectures}")
        D(r"{\scriptsize\setlength{\tabcolsep}{2.5pt}\begin{longtable}{P{0.45cm} P{1.2cm} P{2.5cm} P{3.6cm} P{3.6cm} P{3.3cm} P{1.5cm}}",
          r"\toprule \# & Date & Title & Key topics & Readings & Materials & Tags\\ \midrule\endhead")
        for L in c["lectures"]:
            D(r"\hypertarget{%s}{}%s & %s & \textbf{%s} & %s & %s & %s & %s\\ \midrule" % (
                L["anchor"], esc(L["num"]), md2tex(L["date"]), md2tex(L["title"]), md2tex(dash(L["topics"]), c["code"]),
                md2tex(dash(L["readings"]), c["code"]), md2tex(dash(L["materials"]), c["code"]), tag_boxes(L["tags"])))
        D(r"\end{longtable}}")
        if c["assignments"]:
            D(r"\section{Assignments and projects}")
            D(r"{\scriptsize\setlength{\tabcolsep}{2.5pt}\begin{longtable}{P{2.8cm} P{5.4cm} P{3.0cm} P{3.5cm} P{1.5cm}}",
              r"\toprule Name & What you build & Skills & Starter code / resources & Tags\\ \midrule\endhead")
            for a in c["assignments"]:
                D(r"\hypertarget{%s}{}\textbf{%s} & %s & %s & %s & %s\\ \midrule" % (
                    a["anchor"], md2tex(a["name"]), md2tex(dash(a["build"]), c["code"]), md2tex(dash(a["skills"]), c["code"]),
                    md2tex(dash(a["starter"]), c["code"]), tag_boxes(a["tags"])))
            D(r"\end{longtable}}")
    D(r"\chapter{Supplementary Resources}\hypertarget{supplements}{}")
    D(r"These non-course resources (from the bookmarks folder, plus later additions) are referenced throughout the modules.")
    for s in C.SUPPLEMENTS:
        D(r"\section{%s}\label{%s}" % (esc(s["name"]), s["key"]),
          r"{\small \href{%s}{%s} \quad %s}\par" % (url_esc(s["url"]), esc(s["url"]), tag_boxes(s["tags"])),
          X(s["body"]))


# ---------------------------------------------------------------------------
# Part IV: appendices
# ---------------------------------------------------------------------------
PROVENANCE = r"""\begin{itemize}
\item \textbf{Method.} The 20 links in the Chrome bookmarks folder \emph{CMU-Agentic} were each visited. Static pages were fetched directly. The JavaScript-rendered sites (CMU, Stanford) were read in a live browser. Course repositories were read through GitHub. Four more courses (Stanford CS329A, Berkeley Agentic AI Fall 2025, Berkeley Advanced LLM Agents Spring 2025, Stanford CS329T) and the MIT agent-security lecture were added on the same date from a targeted search for open 2025--2026 courses, with candidates found by a Codex consultant and each one then read directly. Each course was summarised into a Markdown table in \texttt{research/}, and this PDF is generated from those tables by \texttt{guide/build\_guide.py}.
\item \textbf{Classification.} Tags were assigned from session titles, listed topics and readings. They are a navigation aid, not ground truth, and some sessions could reasonably be tagged differently.
\item \textbf{CMU.} The lecture table comes from the rendered schedule (October 9, 2026). The milestone dates on that page (A1 Sep~14, A2 Oct~1, A3 Oct~29) take precedence over the due dates in the assignment table, which come from the handouts. Recordings are linked from the schedule page because individual video URLs could not be extracted, and the YouTube playlist ID was not verified.
\item \textbf{Stanford.} Fall 2026 is current: only weeks 1--3 have slides and assignments so far, and most Thursday sessions from week 3 on are guest talks. Fall 2025 dates come from a translated copy of the syllabus and may be off by a day.
\item \textbf{In-progress courses} (CMU, Stanford '26, Northeastern, JHU, Buffalo) will publish more material after this snapshot. Re-run the research step to refresh.
\item \textbf{Unread items.} Some large slide decks could not be text-extracted (several Mannheim PDFs, a few UVA PPTX files), so their topics are inferred from titles. The UChicago week 6 and 8 notebooks were too large to inspect.
\item \textbf{Licences.} Only some repositories state a licence (UW CS 839: MIT; TinyAgent: MIT; OpenClaw: MIT). Before redistributing course material in your own repository, check each licence. Linking is always safe.
\end{itemize}"""


def part_appendix(D):
    D(r"\part{Appendices}")
    D(r"\chapter{Codebase and Tool Index}")
    D(r"Repositories, frameworks, benchmarks and tools referenced by each course (as recorded during research).")
    for c in C.COURSES:
        if not c["codebases"]:
            continue
        D(r"\section{%s}" % esc(c["short"]), r"{\small\begin{itemize}")
        for b in c["codebases"]:
            D(r"\item " + md2tex(b, c["code"]))
        D(r"\end{itemize}}")
    D(r"\section{Supplements}", r"{\small\begin{itemize}")
    for s in C.SUPPLEMENTS:
        D(r"\item \hyperref[%s]{%s}: \href{%s}{%s}" % (s["key"], esc(s["name"]), url_esc(s["url"]), esc(s["url"])))
    D(r"\item TinyAgent code: \href{https://github.com/SqueezeAILab/TinyAgent}{github.com/SqueezeAILab/TinyAgent}")
    D(r"\end{itemize}}")

    D(r"\chapter{Canonical Reading Checklist}")
    D(r"The key readings from every module in one checklist. Lecture-level readings are in the catalogue tables.")
    D(r"\begin{multicols}{2}\small")
    for m in C.MODULES:
        if not m["readings"]:
            continue
        D(r"\par\medskip\noindent\textbf{\hyperlink{mod-%s}{M%d %s}}\par" % (m["key"], m["num"], m["title"]),
          r"\begin{itemize}[label=$\square$]")
        for r in m["readings"]:
            D(r"\item " + X(r))
        D(r"\end{itemize}")
    D(r"\end{multicols}")

    D(r"\chapter{Tag Matrix}")
    D(r"Raw tag counts per course (a lecture can carry several tags), including logistics (\tg{ORG}).")
    tags = list(C.TAGS)
    D(r"{\small\setlength{\tabcolsep}{3.5pt}\begin{longtable}{l" + "c" * len(tags) + "}")
    D(r"\toprule Course & " + " & ".join(tag_box(t) for t in tags) + r"\\ \midrule")
    for c in C.COURSES:
        cells = []
        for t in tags:
            n = sum(1 for L in c["lectures"] if t in L["tags"])
            cells.append(str(n) if n else r"\textcolor{black!25}{0}")
        D(r"\hyperlink{course-%s}{%s} & %s\\" % (c["code"], esc(c["short"]), " & ".join(cells)))
    D(r"\bottomrule\end{longtable}}")

    D(r"\chapter{Provenance and Caveats}", PROVENANCE)
    D(r"\section{Per-course research notes}", r"These are the notes recorded while each course was being researched.")
    for c in C.COURSES:
        if c["notes"]:
            D(r"\subsection{%s}" % esc(c["short"]), r"{\small\begin{itemize}")
            for n in c["notes"]:
                D(r"\item " + md2tex(n, c["code"]))
            D(r"\end{itemize}}")


def main():
    global CO
    CO = load_courses()
    D = Doc()
    D(PREAMBLE)
    for t, (_, col) in C.TAGS.items():
        D(r"\definecolor{tag%s}{HTML}{%s}" % (t, col))
    D(r"\begin{document}")
    D(r"""\begin{titlepage}\centering
\vspace*{3cm}{\Huge\bfseries Learning to Build Agentic Systems\par}\vspace{0.6cm}
{\Large An instructional compilation guide built from public university courses\par}\vspace{0.8cm}
{\large J. A. Arroyo\par}\vspace{0.8cm}
{\large %d courses $\cdot$ %d lectures $\cdot$ %d assignments $\cdot$ 15 modules $\cdot$ 3 learning tracks\par}\vspace{1.5cm}
\begin{minipage}{0.8\linewidth}\centering\small
CMU 11-768 $\cdot$ Stanford CS146S (2025, 2026) $\cdot$ Northeastern Agentic AI $\cdot$ Harvard CS 2680 $\cdot$ Buffalo CSE 410/510 $\cdot$ UVA CS 6501 $\cdot$ UW--Madison CS 839 $\cdot$ JHU Machine Programming $\cdot$ CU Boulder CSCI 7000 $\cdot$ Mannheim IE 685/686 $\cdot$ UChicago AI Agents for Social Science\\[4pt]
plus MCP, Anthropic Engineering, OpenClaw, Berkeley TinyAgent and Colab
\end{minipage}\vfill
{\small Snapshot compiled October 9, 2026 and updated October 11 and 12, 2026, from the \emph{CMU-Agentic} bookmarks folder plus a targeted course search.\\ All materials belong to their respective authors. This guide only links to them.\\[6pt]
\emph{Use of AI tools.} I am the sole author. Claude (Anthropic, through Claude Code) searched for the courses, read their public pages and drafted the summaries and structure under my direction. The descriptions are summaries, each linked to its source; titles are the sources' own. I am responsible for the content.\par}
\end{titlepage}""" % ((len(C.COURSES),) + stats()))
    D(r"\hypertarget{toc}{}\tableofcontents")
    part_intro(D)
    part_legend(D)
    part_glance(D)
    part_matrix(D)
    part_tracks(D)
    part_modules(D)
    part_catalog(D)
    part_appendix(D)
    D(r"\end{document}")
    tex = D.text()
    for w in sorted(set(WARNINGS)):
        print("WARN:", w)
    if ERRORS:
        for e in ERRORS:
            print("ERROR:", e)
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(tex)
    for c in C.COURSES:
        print(f"{c['code']:7s} lectures={len(c['lectures']):3d} assignments={len(c['assignments']):3d} "
              f"codebases={len(c['codebases'])} notes={len(c['notes'])}")
    for m in C.MODULES:
        print(f"M{m['num']:<2d} {m['key']:7s} {len(module_lectures(m))} lectures")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
