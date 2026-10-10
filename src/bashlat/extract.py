"""Pull readable text out of a book file, falling back to OCR when needed.

Handles PDF, DjVu and EPUB, plus the FB2/DOCX/DOC that turn up alongside them.

Two things matter for language detection and both are easy to get wrong:

**Sample the body, not the front.** Copyright pages, УДК/ББК codes and imprint
data are in Russian even in a thoroughly Bashkort book. Reading page 1 and
concluding "Russian" is the single most common failure. Everything here samples
across the interior of the volume.

**Know when the text layer is a lie.** Many scans carry either no text layer or
a garbage one. Below `MIN_USABLE` characters the extractor reports failure so
the caller can decide whether to pay for OCR.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logging.getLogger("pypdf").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

MIN_USABLE = 400
SAMPLE_PAGES = 14
OCR_PAGES = 6
OCR_LANGS = "tat+rus"      # tesseract ships no `bak`; see detect.OCR_SAFE_*

TAGS = re.compile(rb"<[^>]+>")

# Elements whose *contents* must go, not just their tags. FB2 embeds cover art
# as base64 inside <binary>, which survives naive tag-stripping as hundreds of
# thousands of Latin characters and makes a Bashkort novel look like a Latin
# document. EPUB does the same with <style> and <script>.
DROP_ELEMENTS = re.compile(
    rb"<(binary|style|script|svg)\b[^>]*>.*?</\1>", re.S | re.I)


def strip_markup(raw: bytes, limit: Optional[int] = None) -> str:
    """Remove embedded binary payloads, then tags, then decode."""
    raw = DROP_ELEMENTS.sub(b" ", raw)
    text = TAGS.sub(b" ", raw).decode("utf-8", "ignore")
    return text[:limit] if limit else text


@dataclass
class Extraction:
    text: str
    source: str          # text | ocr | none
    pages: Optional[int] = None
    note: str = ""

    def __bool__(self) -> bool:
        return len(self.text.strip()) >= MIN_USABLE


CYR_RANGE = re.compile(r"[Ѐ-ӿ]")
LATIN_ALPHA = re.compile(r"[A-Za-z]")
TURKIC_CHARS = set("әөүңһӘӨҮҢҺ")


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def suspect_text_layer(text: str) -> bool:
    """True when a PDF's text layer is present but its encoding is broken.

    Some scanned-then-OCR'd PDFs carry a ToUnicode CMap that maps the Turkic
    letters to arbitrary Latin glyphs. The result extracts cleanly, looks like
    prose, and is missing precisely the characters that identify the language —
    so a Bashkort book reads as confident Russian.

    The tell is Cyrillic running alongside heavy Latin with *no* ә ө ү ң һ at
    all. Genuine Russian has the same zero Turkic count but does not carry a
    parallel stream of Latin letters.
    """
    cyr = len(CYR_RANGE.findall(text))
    if cyr < 300:
        return False
    if any(c in TURKIC_CHARS for c in text):
        return False                       # Turkic letters survived; layer is fine
    return len(LATIN_ALPHA.findall(text)) > 0.4 * cyr


def _turkic_count(text: str) -> int:
    return sum(1 for c in text if c in TURKIC_CHARS)


def _run(cmd, timeout=180) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", "ignore")
    except Exception:
        return ""


def _body_pages(n: int, want: int) -> List[int]:
    """Page numbers spread across the interior, skipping front and back matter."""
    if n <= 2:
        return list(range(1, n + 1))
    lo = max(1, min(10, n // 10))
    hi = max(lo + 1, n - max(1, n // 20))
    if hi <= lo:
        return [max(1, n // 2)]
    step = (hi - lo) / max(1, want - 1)
    return sorted({int(lo + step * i) for i in range(want)})


# --- PDF -------------------------------------------------------------------

def _pdf_pagecount(path: Path) -> Optional[int]:
    if _have("pdfinfo"):
        out = _run(["pdfinfo", str(path)], timeout=60)
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        if m:
            return int(m.group(1))
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path), strict=False).pages)
    except Exception:
        return None


def _pdf_text(path: Path, pages: Optional[int]) -> str:
    if not pages:
        return ""
    want = _body_pages(pages, SAMPLE_PAGES)
    if _have("pdftotext"):
        out = []
        for p in want:
            out.append(_run(["pdftotext", "-f", str(p), "-l", str(p),
                             "-q", str(path), "-"], timeout=60))
            if sum(len(o) for o in out) > 40000:
                break
        joined = "\n".join(out)
        if len(joined.strip()) >= MIN_USABLE:
            return joined
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path), strict=False)
        out = []
        for p in want:
            if p - 1 < len(r.pages):
                try:
                    out.append(r.pages[p - 1].extract_text() or "")
                except Exception:
                    pass
        return "\n".join(out)
    except Exception:
        return ""


def _pdf_ocr(path: Path, pages: Optional[int]) -> str:
    if not (_have("pdftoppm") and _have("tesseract")) or not pages:
        return ""
    out = []
    with tempfile.TemporaryDirectory() as td:
        for p in _body_pages(pages, OCR_PAGES):
            pre = str(Path(td) / f"p{p}")
            _run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "250",
                  "-gray", "-png", str(path), pre], timeout=180)
            for img in sorted(Path(td).glob(f"p{p}*.png")):
                out.append(_run(["tesseract", str(img), "stdout",
                                 "-l", OCR_LANGS, "--psm", "3"], timeout=180))
                img.unlink(missing_ok=True)
    return "\n".join(out)


# --- DjVu ------------------------------------------------------------------

def _djvu_pagecount(path: Path) -> Optional[int]:
    if _have("djvused"):
        out = _run(["djvused", "-e", "n", str(path)], timeout=60).strip()
        if out.isdigit():
            return int(out)
    return None


def _djvu_text(path: Path) -> str:
    if not _have("djvutxt"):
        return ""
    full = _run(["djvutxt", str(path)], timeout=180)
    if len(full.strip()) < MIN_USABLE:
        return full
    a, b = int(len(full) * 0.10), int(len(full) * 0.85)
    return full[a:b][:60000]


def _djvu_ocr(path: Path, pages: Optional[int]) -> str:
    if not (_have("ddjvu") and _have("tesseract")):
        return ""
    pages = pages or 20
    out = []
    with tempfile.TemporaryDirectory() as td:
        for p in _body_pages(pages, OCR_PAGES):
            img = Path(td) / f"p{p}.tif"
            _run(["ddjvu", "-format=tiff", f"-page={p}", "-quality=85",
                  str(path), str(img)], timeout=180)
            if img.exists():
                out.append(_run(["tesseract", str(img), "stdout",
                                 "-l", OCR_LANGS, "--psm", "3"], timeout=180))
                img.unlink(missing_ok=True)
    return "\n".join(out)


# --- container formats -----------------------------------------------------

def _zip_text(path: Path, pattern: str) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            members = [n for n in z.namelist() if re.search(pattern, n, re.I)]
            if not members:
                return ""
            members.sort()
            body = members[len(members) // 8:] or members   # skip front matter
            raw, total = [], 0
            for m in body:
                chunk = strip_markup(z.read(m)).encode("utf-8")
                raw.append(chunk)
                total += len(chunk)
                if total > 80000:
                    break
            return b" ".join(raw).decode("utf-8", "ignore")
    except Exception:
        return ""


def _fb2_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
        if raw[:2] == b"PK":
            with zipfile.ZipFile(path) as z:
                inner = [n for n in z.namelist() if n.lower().endswith(".fb2")]
                raw = z.read(inner[0]) if inner else b""
        body = raw[len(raw) // 10:][:400000]
        return strip_markup(body)
    except Exception:
        return ""


def _doc_text(path: Path) -> str:
    """Legacy .doc: no parser here, so pick whichever decoding yields most Cyrillic."""
    try:
        raw = path.read_bytes()[:4_000_000]
        best, score = "", 0
        for enc in ("utf-16-le", "cp1251", "utf-8"):
            s = raw.decode(enc, "ignore")
            n = sum(1 for c in s if "Ѐ" <= c <= "ӿ")
            if n > score:
                best, score = s, n
        return best[len(best) // 8:][:80000]
    except Exception:
        return ""


# --- entry point -----------------------------------------------------------

def extract(path, allow_ocr: bool = True) -> Extraction:
    """Extract sampled body text, using OCR only if the text layer is unusable."""
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")

    if ext == "pdf" or path.name.endswith(".crdownload"):
        n = _pdf_pagecount(path)
        t = _pdf_text(path, n)
        if len(t.strip()) >= MIN_USABLE:
            if not suspect_text_layer(t):
                return Extraction(t, "text", n)
            # Layer extracts but its encoding looks broken. Re-read by OCR and
            # keep whichever version actually contains Turkic letters.
            if allow_ocr:
                o = _pdf_ocr(path, n)
                if len(o.strip()) >= MIN_USABLE and _turkic_count(o) > _turkic_count(t):
                    return Extraction(o, "ocr", n, "text layer encoding broken")
            return Extraction(t, "text?", n, "text layer encoding looks broken")
        if allow_ocr:
            o = _pdf_ocr(path, n)
            if len(o.strip()) >= MIN_USABLE:
                return Extraction(o, "ocr", n, "no usable text layer")
        return Extraction(t, "none", n, "no text layer; OCR unavailable or failed")

    if ext == "djvu":
        n = _djvu_pagecount(path)
        t = _djvu_text(path)
        if len(t.strip()) >= MIN_USABLE:
            return Extraction(t, "text", n)
        if allow_ocr:
            o = _djvu_ocr(path, n)
            if len(o.strip()) >= MIN_USABLE:
                return Extraction(o, "ocr", n, "no usable text layer")
        return Extraction(t, "none", n, "no text layer; OCR unavailable or failed")

    if ext == "epub":
        t = _zip_text(path, r"\.x?html?$")
    elif ext == "docx":
        t = _zip_text(path, r"word/document\.xml$")
    elif ext == "fb2":
        t = _fb2_text(path)
    elif ext == "txt":
        t = path.read_text(encoding="utf-8", errors="ignore")
    else:
        t = _doc_text(path)

    return Extraction(t, "text" if len(t.strip()) >= MIN_USABLE else "none")


CHARS_PER_PAGE = 2000    # rough equivalence for formats with no page concept


def extract_full(path, skip_pages: int = 0, skip_end_pages: int = 0) -> Extraction:
    """Extract the whole document rather than a sample.

    `extract` deliberately samples, because language detection only needs a
    representative slice and sampling keeps a 500-page scan cheap. Corpus
    building needs everything, so this takes the slow path.

    `skip_pages` and `skip_end_pages` drop front and back matter — title pages,
    imprint data, tables of contents, colophons, blank leaves. For formats with
    no page structure (DOC, FB2, EPUB) they are approximated as
    `n * CHARS_PER_PAGE` characters from each end, which is coarse but adequate
    for the purpose.
    """
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")

    if ext == "pdf" or path.name.endswith(".crdownload"):
        n = _pdf_pagecount(path)
        if _have("pdftotext"):
            cmd = ["pdftotext", "-q"]
            if skip_pages:
                cmd += ["-f", str(skip_pages + 1)]
            if skip_end_pages and n and n - skip_end_pages > skip_pages:
                cmd += ["-l", str(n - skip_end_pages)]
            t = _run(cmd + [str(path), "-"], timeout=900)
            if len(t.strip()) >= MIN_USABLE and not suspect_text_layer(t):
                return Extraction(t, "text", n)
        try:
            from pypdf import PdfReader
            r = PdfReader(str(path), strict=False)
            out = []
            for pg in r.pages:
                try:
                    out.append(pg.extract_text() or "")
                except Exception:
                    pass
            t = "\n".join(out)
            if len(t.strip()) >= MIN_USABLE:
                src = "text?" if suspect_text_layer(t) else "text"
                return Extraction(t, src, n)
        except Exception:
            pass
        return Extraction("", "none", n, "no usable text layer")

    if ext == "djvu":
        n = _djvu_pagecount(path)
        if not _have("djvutxt"):
            return Extraction("", "none", n, "djvutxt unavailable")
        if (skip_pages or skip_end_pages) and n:
            last = max(skip_pages + 1, n - skip_end_pages)
            parts = [_run(["djvutxt", f"--page={p}", str(path)], timeout=120)
                     for p in range(skip_pages + 1, last + 1)]
            t = "\n".join(parts)
        else:
            t = _run(["djvutxt", str(path)], timeout=900)
        if len(t.strip()) >= MIN_USABLE:
            return Extraction(t, "text", n)
        return Extraction("", "none", n, "no usable text layer")

    off = skip_pages * CHARS_PER_PAGE
    end = skip_end_pages * CHARS_PER_PAGE
    trim = (lambda t: t[off:len(t) - end] if end and len(t) > off + end else t[off:])
    if ext == "epub":
        return Extraction(trim(_zip_all(path, r"\.x?html?$")), "text")
    if ext == "docx":
        return Extraction(trim(_zip_all(path, r"word/document\.xml$")), "text")
    if ext == "fb2":
        try:
            raw = path.read_bytes()
            if raw[:2] == b"PK":
                with zipfile.ZipFile(path) as z:
                    inner = [x for x in z.namelist() if x.lower().endswith(".fb2")]
                    raw = z.read(inner[0]) if inner else b""
            return Extraction(trim(strip_markup(raw)), "text")
        except Exception:
            return Extraction("", "none")
    if ext == "txt":
        return Extraction(trim(path.read_text(encoding="utf-8", errors="ignore")), "text")
    return Extraction(trim(_doc_text(path)), "text")


def _zip_all(path: Path, pattern: str) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            members = sorted(n for n in z.namelist() if re.search(pattern, n, re.I))
            return " ".join(strip_markup(z.read(m)) for m in members)
    except Exception:
        return ""


def capabilities() -> dict:
    """Which external tools are present, for diagnostics."""
    return {
        "pdftotext": _have("pdftotext"), "pdfinfo": _have("pdfinfo"),
        "pdftoppm": _have("pdftoppm"), "djvutxt": _have("djvutxt"),
        "djvused": _have("djvused"), "ddjvu": _have("ddjvu"),
        "tesseract": _have("tesseract"),
    }
