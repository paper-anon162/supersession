#!/usr/bin/env python3
"""Convert article markdown sections to LaTeX (semi-automatic).

Reads supersessionbench_article_draft.md, splits by top-level sections,
and emits one .tex file per section under paper/sections/ or
paper/appendix/. Designed to be a high-recall first pass: most
constructs convert correctly, complex cells / nested formatting are
flagged with % TODO comments for manual cleanup.

Handles:
  - # H1, ## H2, ### H3 → \section / \subsection / \subsubsection
  - **bold** → \textbf{}, *emph* → \emph{}, `code` → \texttt{}
    (system identifiers like `structured_sonnet` get _ escaped)
  - markdown tables → booktabs \toprule / \midrule / \bottomrule
    (column alignment auto-detected from `---:|`, `:---:|`, etc.)
  - > blockquote → \begin{quote}...\end{quote}
  - ```code``` blocks → \begin{verbatim}...\end{verbatim}
  - - bullet lists → \begin{itemize}, 1. numbered → \begin{enumerate}
  - Unicode symbols → LaTeX math macros (× → $\times$, Δ → $\Delta$, etc.)
  - %, &, _, #, $ in text → escaped
  - --- separator → ignored

Usage:
  python scripts/md_to_latex.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "supersessionbench_article_draft.md"
PAPER = REPO / "paper"

# Maps markdown # H1 line content (without leading "# ") to output paths.
# Sections we already wrote by hand are skipped.
SECTION_MAP = {
    "3. SupersessionBench: Dataset Design": "sections/03_dataset.tex",
    "4. Evaluation Protocol": "sections/04_protocol.tex",
    "5. Main Results": "sections/05_results.tex",
    "6. Diagnostic Analysis": "sections/06_diagnostic.tex",
    "7. Related Work": "sections/07_related.tex",
    "8. Discussion": "sections/08_discussion.tex",
    "Appendix A. Dataset Construction and Semantic Spines": "appendix/A_construction.tex",
    "Appendix B. Operational Scoring Rules": "appendix/B_scoring.tex",
    "Appendix C. Prompts": "appendix/C_prompts.tex",
    "Appendix D. Dataset Statistics": "appendix/D_dataset_stats.tex",
    "Appendix E. Active-State Identifiability and Naturalness Annotation": "appendix/E_solvability_naturalness.tex",
    "Appendix F. Judge Validation Annotation": "appendix/F_judge_validation.tex",
    "Appendix G. Baseline and Diagnostic System Details": "appendix/G_systems.tex",
    "Appendix H. Full Results": "appendix/H_full_results.tex",
    "Appendix I. Qualitative Failure Analysis": "appendix/I_qualitative.tex",
    "Appendix J. Leakage, Ambiguity, and Audit Procedures": "appendix/J_leakage.tex",
    "Appendix K. Dataset Release Documentation": "appendix/K_release.tex",
}

# Unicode characters → LaTeX (text-mode safe)
UNICODE_MAP = {
    "→": r"$\to$",
    "×": r"$\times$",
    "Δ": r"$\Delta$",
    "ρ": r"$\rho$",
    "κ": r"$\kappa$",
    "−": r"$-$",
    "≥": r"$\ge$",
    "≤": r"$\le$",
    "±": r"$\pm$",
    "≈": r"$\approx$",
    "≠": r"$\neq$",
    "…": r"\ldots ",
    "—": r"---",
    "–": r"--",
    "≪": r"$\ll$",
    "≫": r"$\gg$",
    "∈": r"$\in$",
    "∉": r"$\notin$",
    "∪": r"$\cup$",
    "∩": r"$\cap$",
    "⊆": r"$\subseteq$",
    "⊂": r"$\subset$",
    "·": r"$\cdot$",
    "¬": r"$\neg$",
    "→": r"$\to$",
    "✓": r"\checkmark{}",
    "✗": r"$\times$",
    "↔": r"$\leftrightarrow$",
    "↑": r"$\uparrow$",
    "↓": r"$\downarrow$",
    "⇒": r"$\Rightarrow$",
    "⇐": r"$\Leftarrow$",
    "⇔": r"$\Leftrightarrow$",
    "∗": r"$*$",
    "⊕": r"$\oplus$",
    "·": r"$\cdot$",
    "⋅": r"$\cdot$",
    "α": r"$\alpha$",
    "β": r"$\beta$",
    "γ": r"$\gamma$",
    "θ": r"$\theta$",
    "λ": r"$\lambda$",
    "μ": r"$\mu$",
    "π": r"$\pi$",
    "σ": r"$\sigma$",
    "φ": r"$\phi$",
    "ω": r"$\omega$",
}


def split_sections(md: str) -> list[tuple[str, str]]:
    """Split markdown by top-level # / Appendix headers. Returns [(title, body)]."""
    out = []
    current_title = None
    current_body: list[str] = []
    for line in md.splitlines(keepends=False):
        # Top-level: starts with single "# " (not "##")
        m = re.match(r"^# (.+)$", line)
        if m:
            if current_title is not None:
                out.append((current_title, "\n".join(current_body)))
            current_title = m.group(1).strip()
            current_body = []
        else:
            if current_title is not None:
                current_body.append(line)
    if current_title is not None:
        out.append((current_title, "\n".join(current_body)))
    return out


# --- Inline conversions ----------------------------------------------------

def escape_special_chars(text: str) -> str:
    """Escape LaTeX-special chars in plain prose. Skips inside `code`,
    $math$, and \\command{} regions by tokenising first."""
    # Tokenise: keep `code`, $math$, --- separators verbatim
    tokens = re.split(r"(`[^`]*`|\$[^$]*\$)", text)
    out = []
    for t in tokens:
        if t.startswith("`") and t.endswith("`") and len(t) >= 2:
            out.append(_render_inline_code(t[1:-1]))
        elif t.startswith("$") and t.endswith("$"):
            out.append(t)  # already math
        else:
            out.append(_escape_prose(t))
    return "".join(out)


def _escape_prose(t: str) -> str:
    """Escape LaTeX specials in plain prose (text mode).
    Order matters: backslash first so we don't double-escape."""
    # Unicode replacements first (these introduce $...$, so do before
    # other escaping)
    for u, repl in UNICODE_MAP.items():
        t = t.replace(u, repl)
    # Now escape LaTeX-meta chars in remaining text. Skip $...$ regions
    # we just introduced.
    parts = re.split(r"(\$[^$]*\$)", t)
    escaped = []
    for p in parts:
        if p.startswith("$") and p.endswith("$"):
            escaped.append(p)
            continue
        # Escape order: & % # first (safest), then _ outside math, then ~
        # (don't escape \ since it might already be \cmd from prior pass)
        p = p.replace("&", r"\&")
        p = p.replace("%", r"\%")
        p = p.replace("#", r"\#")
        # Escape isolated `$` (literal dollar) in prose chunks; paired
        # `$math$` chunks have already been split out above.
        p = p.replace("$", r"\$")
        # Don't escape _ in plain prose generally (most _ underscores are
        # in `code` already handled). But system identifiers in non-code
        # spans (e.g. `Across all top-10 domains, structured_sonnet ranks
        # first`) need _ escaped. Heuristic: any _ in word characters
        # outside math gets escaped.
        p = re.sub(r"(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])", r"\_", p)
        escaped.append(p)
    return "".join(escaped)


def _render_inline_code(s: str) -> str:
    """`code` → \\texttt{code} with _ escaped inside."""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("_", r"\_")
    s = s.replace("#", r"\#")
    s = s.replace("%", r"\%")
    s = s.replace("&", r"\&")
    s = s.replace("$", r"\$")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    return r"\texttt{" + s + r"}"


def _bold_emph(t: str) -> str:
    """**bold** and *emph* (after inline-code is already wrapped)."""
    # Bold: **...** (double asterisks). Greedy non-greedy so ** doesn't span paragraphs.
    t = re.sub(r"\*\*([^\*\n]+?)\*\*", r"\\textbf{\1}", t)
    # Emph: *...* (single asterisks). Avoid ** (already done).
    t = re.sub(r"(?<!\*)\*([^\*\n]+?)\*(?!\*)", r"\\emph{\1}", t)
    return t


def convert_inline(text: str) -> str:
    """Apply inline conversions in correct order."""
    # 1. Quote characters: smart quotes / curly quotes — markdown doesn't
    #    use them, but " → `` and " → ''. Skip; user copy is plain ASCII.
    # 2. Escape, render code, render math (combined).
    text = escape_special_chars(text)
    # 3. Bold/emph (after escapes since *_ doesn't matter in text mode).
    text = _bold_emph(text)
    return text


# --- Table conversion ------------------------------------------------------

_TABLE_COUNTER = [0]


def convert_table(lines: list[str]) -> list[str]:
    """Convert a contiguous markdown table to a LaTeX booktabs table.
    `lines` is the list of pipe-rows including the separator row."""
    # Parse cells per row.
    def parse_row(s: str) -> list[str]:
        s = s.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]

    if len(lines) < 2:
        return ["% TODO malformed table"] + lines

    header = parse_row(lines[0])
    sep = parse_row(lines[1])
    body = [parse_row(l) for l in lines[2:]]

    # Column alignment from separator row
    aligns = []
    for s in sep:
        s = s.strip()
        if s.startswith(":") and s.endswith(":"):
            aligns.append("c")
        elif s.endswith(":"):
            aligns.append("r")
        elif s.startswith(":"):
            aligns.append("l")
        else:
            aligns.append("l")

    _TABLE_COUNTER[0] += 1
    n = _TABLE_COUNTER[0]
    out = []
    out.append(r"\begin{table}[ht]")
    out.append(r"\centering")
    out.append(rf"\caption{{TODO caption {n}.}}")
    out.append(rf"\label{{tab:auto{n}}}")
    out.append(r"\begin{tabular}{" + "".join(aligns) + r"}")
    out.append(r"\toprule")
    out.append(" & ".join(convert_inline(c) for c in header) + r" \\")
    out.append(r"\midrule")
    for row in body:
        # Pad row to header length
        while len(row) < len(header):
            row.append("")
        out.append(" & ".join(convert_inline(c) for c in row[: len(header)]) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")
    return out


# --- Main block-level converter -------------------------------------------

def is_table_row(line: str) -> bool:
    return bool(re.match(r"^\s*\|.+\|\s*$", line))


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|\-]+\|?\s*$", line)) and "-" in line


def convert_section(title: str, body: str, is_appendix: bool) -> str:
    """Convert one top-level section's body (markdown) to LaTeX."""
    out = []
    out.append(f"% {title}")

    # Top-level heading: section command. Drop "Appendix X." prefix and
    # leading "N." prefix; both become \section{}.
    sec_title = title
    m = re.match(r"^(?:Appendix [A-Z]\.|[0-9]+\.)\s*(.+)$", title)
    if m:
        sec_title = m.group(1)
    # First-letter capitalize, rest preserve
    out.append(rf"\section{{{convert_inline(sec_title)}}}")
    label = re.sub(r"[^a-z0-9]+", "_",
                    sec_title.lower()).strip("_")[:40]
    out.append(rf"\label{{sec:{label}}}")
    out.append("")

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if not s or s == "---":
            out.append("")
            i += 1
            continue

        # Subsection / subsubsection
        m = re.match(r"^## (.+)$", line)
        if m:
            t = m.group(1).strip()
            # Drop "X.Y " prefix or "X.Y.Z " or "Appendix X.Y "
            t = re.sub(r"^[A-Z]?\.?\d+(?:\.\d+)*\s+", "", t)
            t = re.sub(r"^[A-Z]\.\d+\s+", "", t)
            out.append(rf"\subsection{{{convert_inline(t)}}}")
            i += 1
            continue
        m = re.match(r"^### (.+)$", line)
        if m:
            t = m.group(1).strip()
            # Strip numeric / lettered prefix; LaTeX auto-numbers.
            # Handles "5.3.1 ", "H.6 ", "H.6a ", "H.6.1 ", etc.
            t = re.sub(r"^[A-Z]?\.?\d+(?:\.\d+)+[a-z]?\s+", "", t)
            t = re.sub(r"^[A-Z]\.\d+[a-z]?\s+", "", t)
            out.append(rf"\subsubsection{{{convert_inline(t)}}}")
            i += 1
            continue

        # Code block (triple backtick)
        if s.startswith("```"):
            lang = s[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            out.append(r"\begin{verbatim}")
            out.extend(block)
            out.append(r"\end{verbatim}")
            continue

        # Blockquote (incl. bare `>` for empty quote-paragraph lines)
        if s == ">" or s.startswith("> "):
            block = []
            while i < len(lines):
                ls = lines[i].strip()
                if ls == ">":
                    block.append("")
                    i += 1
                elif ls.startswith("> "):
                    block.append(ls[2:])
                    i += 1
                else:
                    break
            out.append(r"\begin{quote}")
            for bl in block:
                out.append(convert_inline(bl) if bl else "")
            out.append(r"\end{quote}")
            continue

        # Markdown table — header row, then separator, then body rows
        if is_table_row(line) and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            tlines = []
            while i < len(lines) and is_table_row(lines[i]):
                tlines.append(lines[i])
                i += 1
            # First table line was header, second was separator. Skip separator
            # in collected list, since convert_table expects [header, sep, body...]
            out.extend(convert_table(tlines))
            continue

        # Bullet list
        if s.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append(r"\begin{itemize}")
            for it in items:
                out.append(rf"  \item {convert_inline(it)}")
            out.append(r"\end{itemize}")
            continue

        # Numbered list (allow blank lines between items — common markdown style)
        m = re.match(r"^\d+\.\s+(.+)$", s)
        if m:
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                m2 = re.match(r"^\d+\.\s+(.+)$", cur)
                if m2:
                    items.append(m2.group(1))
                    i += 1
                elif cur == "":
                    # Peek across blanks: if next non-empty line is also a
                    # numbered item, treat as one continuous list.
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and re.match(r"^\d+\.\s+", lines[j].strip()):
                        i = j
                    else:
                        break
                else:
                    break
            out.append(r"\begin{enumerate}")
            for it in items:
                out.append(rf"  \item {convert_inline(it)}")
            out.append(r"\end{enumerate}")
            continue

        # Plain paragraph: collect contiguous non-empty lines, join, convert.
        para = []
        while i < len(lines) and lines[i].strip() and not (
            lines[i].strip().startswith(("#", ">", "```", "- ", "|"))
            or re.match(r"^\d+\.\s+", lines[i].strip())
            or lines[i].strip() == "---"
        ):
            para.append(lines[i])
            i += 1
        text = " ".join(p.strip() for p in para)
        # Strip handwritten "**Table N: ...**" / "**Figure N: ...**" headers.
        # The LaTeX \caption{} on the corresponding tabular/figure already
        # provides the title; keeping the bold prefix duplicates it and
        # breaks auto-numbering. If only the header is present, drop the
        # whole paragraph; if there is trailing prose, keep the prose.
        text = re.sub(
            r"^\*\*(?:Table|Figure)\s+\d+[a-z]?\s*:\s*[^*]*\*\*\s*",
            "",
            text,
        ).strip()
        if text:
            out.append(convert_inline(text))
            out.append("")
        else:
            # Defensive: if paragraph collection was a no-op (e.g. unhandled
            # marker line), force-advance to avoid infinite loop.
            i += 1

    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    md = ART.read_text()
    sections = split_sections(md)
    print(f"Found {len(sections)} top-level sections in {ART.name}")

    written = 0
    skipped = 0
    for title, body in sections:
        if title not in SECTION_MAP:
            print(f"  skip (no mapping): {title!r}")
            skipped += 1
            continue
        out_path = PAPER / SECTION_MAP[title]
        is_app = title.startswith("Appendix")
        latex = convert_section(title, body, is_app)
        if args.dry_run:
            print(f"\n--- {out_path} ---\n{latex[:500]}\n...")
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(latex)
            print(f"  wrote {out_path.relative_to(REPO)} "
                  f"({len(latex.splitlines())} lines)")
        written += 1

    print(f"\nWrote {written} files, skipped {skipped} headers (Title / §1 / §2 already done by hand).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
