"""Render a StructuredResume into a fixed, ATS-friendly LaTeX template and compile it.

The LLM never writes LaTeX: it only chooses and rewords content, which is escaped
here, so output always compiles and odd characters can't break the document.
Compiler order: system TeX Live (xelatex, then pdflatex) → bundled/installed Tectonic.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import DATA_DIR, PROJECT_ROOT
from app.services.structured_resume import StructuredResume

logger = get_logger(__name__)

COMPILE_TIMEOUT_S = 300  # Tectonic's first run downloads packages (can take minutes)
TECTONIC_ENV = "JOB_SEARCH_TECTONIC"

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(k) for k in _ESCAPES))


def escape(text: str) -> str:
    text = (text or "").replace("\r", "")
    text = _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group(0)], text)
    # Stray icon glyphs from PDF extraction break pdflatex; drop them.
    return text.replace("\ufffd", "").strip()


def _url(link: str) -> str:
    link = link.strip()
    if not re.match(r"^(https?://|mailto:)", link):
        link = "https://" + link
    return (
        link.replace("\\", "/")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("{", "")
        .replace("}", "")
    )


def _display_link(link: str) -> str:
    return escape(re.sub(r"^https?://(www\.)?", "", link.strip()).rstrip("/"))


def _dates(start: str, end: str) -> str:
    start, end = escape(start), escape(end)
    if start and end:
        return f"{start} -- {end}"
    return start or end


def _bullets(items: list[str]) -> list[str]:
    items = [escape(i) for i in items if i and i.strip()]
    if not items:
        return []
    return ["\\begin{itemize}", *[f"  \\item {i}" for i in items], "\\end{itemize}"]


PREAMBLE = r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=0.65in]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\titleformat{\section}{\large\bfseries}{}{0em}{}[\vspace{-4pt}\rule{\linewidth}{0.4pt}]
\titlespacing*{\section}{0pt}{9pt}{4pt}
\setlist[itemize]{leftmargin=1.2em,itemsep=1pt,topsep=2pt,parsep=0pt,partopsep=0pt}
\newcommand{\entry}[4]{\textbf{#1}\hfill #2\\ \textit{#3}\hfill \textit{#4}\par}
"""


def render_tex(resume: StructuredResume) -> str:
    c = resume.contact
    contact_bits = [escape(x) for x in (c.location, c.phone) if x]
    if c.email:
        mail = (
            c.email.strip()
            .removeprefix("mailto:")
            .replace("%", r"\%")
            .replace("#", r"\#")
        )
        contact_bits.append(f"\\href{{mailto:{mail}}}{{{escape(c.email)}}}")
    contact_bits += [
        f"\\href{{{_url(link)}}}{{{_display_link(link)}}}"
        for link in c.links
        if link.strip()
    ]
    out = [
        PREAMBLE,
        "\\begin{document}",
        "\\begin{center}",
        f"{{\\LARGE\\bfseries {escape(c.name) or 'Resume'}}}\\\\[3pt]",
    ]
    if contact_bits:
        out.append(" $\\cdot$ ".join(contact_bits))
    out.append("\\end{center}")

    if resume.summary.strip():
        out += ["\\section*{Summary}", escape(resume.summary)]

    if resume.experience:
        out.append("\\section*{Experience}")
        for x in resume.experience:
            out.append(
                f"\\entry{{{escape(x.title)}}}{{{_dates(x.start, x.end)}}}{{{escape(x.company)}}}{{{escape(x.location)}}}"
            )
            out += _bullets(x.bullets)
            out.append("\\vspace{3pt}")

    if resume.projects:
        out.append("\\section*{Projects}")
        for p in resume.projects:
            name = escape(p.name)
            if p.link.strip():
                name = f"\\href{{{_url(p.link)}}}{{{name}}}"
            tech = f" $|$ \\textit{{{escape(', '.join(p.tech))}}}" if p.tech else ""
            out.append(f"\\textbf{{{name}}}{tech}\\par")
            out += _bullets(p.bullets)
            out.append("\\vspace{3pt}")

    if resume.skills:
        out.append("\\section*{Skills}")
        rows = [
            f"\\textbf{{{escape(s.category)}:}} {escape(', '.join(s.items))}"
            if s.category
            else escape(", ".join(s.items))
            for s in resume.skills
            if s.items
        ]
        out.append(" \\\\\n".join(rows))

    if resume.education:
        out.append("\\section*{Education}")
        for e in resume.education:
            degree = ", ".join(x for x in (escape(e.degree), escape(e.field)) if x)
            grade = f" ({escape(e.grade)})" if e.grade else ""
            out.append(
                f"\\entry{{{escape(e.institution)}}}{{{_dates(e.start, e.end)}}}{{{degree}{grade}}}{{{escape(e.location)}}}"
            )
            out += _bullets(e.highlights)
            out.append("\\vspace{3pt}")

    if resume.certifications:
        out += ["\\section*{Certifications}", *_bullets(resume.certifications)]

    if resume.languages:
        out += [
            "\\section*{Languages}",
            ", ".join(
                f"{escape(lang.name)} ({escape(lang.level)})"
                if lang.level
                else escape(lang.name)
                for lang in resume.languages
            ),
        ]

    out.append("\\end{document}")
    return "\n".join(out) + "\n"


# ---- compiling -------------------------------------------------------------------


def _tectonic_candidates() -> list[Path]:
    candidates = []
    if os.environ.get(TECTONIC_ENV):
        candidates.append(Path(os.environ[TECTONIC_ENV]))
    on_path = shutil.which("tectonic")
    if on_path:
        candidates.append(Path(on_path))
    # Dev checkout (make fetch-tectonic) and a user-installed copy.
    candidates += sorted((PROJECT_ROOT / "binaries").glob("tectonic-*"))
    candidates.append(DATA_DIR / "tools" / "tectonic")
    return candidates


def find_compiler() -> tuple[str, Path] | None:
    """("xelatex"|"pdflatex"|"tectonic", path) — system TeX Live preferred."""
    for name in ("xelatex", "pdflatex"):
        found = shutil.which(name)
        if found:
            return name, Path(found)
    for path in _tectonic_candidates():
        if path.is_file() and os.access(path, os.X_OK):
            return "tectonic", path
    return None


class CompileError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


def compile_pdf(tex: str) -> tuple[bytes, str]:
    """Compile LaTeX to PDF bytes. Returns (pdf, compiler name)."""
    compiler = find_compiler()
    if compiler is None:
        raise CompileError(
            "No LaTeX compiler found. Install TeX Live, or run `make fetch-tectonic`. "
            "You can still download the .tex file."
        )
    name, path = compiler
    with tempfile.TemporaryDirectory(prefix="resume-") as tmp:
        src = Path(tmp) / "resume.tex"
        src.write_text(tex, encoding="utf-8")
        if name == "tectonic":
            cmd = [str(path), "-X", "compile", "--keep-logs", "--outdir", tmp, str(src)]
        else:
            cmd = [
                str(path),
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={tmp}",
                str(src),
            ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=COMPILE_TIMEOUT_S,
                cwd=tmp,
                check=False,  # the exit code is inspected below
            )
        except subprocess.TimeoutExpired as e:
            raise CompileError(
                f"{name} timed out after {COMPILE_TIMEOUT_S}s. The first Tectonic run downloads "
                "packages and needs internet."
            ) from e
        pdf = Path(tmp) / "resume.pdf"
        log = (proc.stdout + "\n" + proc.stderr)[-4000:]
        if proc.returncode != 0 or not pdf.exists():
            offline = (
                "network" in log.lower()
                or "resolve" in log.lower()
                or "download" in log.lower()
            )
            hint = (
                " Tectonic needs internet the first time to fetch TeX packages."
                if name == "tectonic" and offline
                else ""
            )
            raise CompileError(f"{name} could not build the PDF.{hint}", log)
        logger.info("compiled resume with %s", name)
        return pdf.read_bytes(), name
