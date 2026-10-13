#!/usr/bin/env python3
"""Local browser tool for transcribing line images into ground truth.

    python3 tools/prepare_transcription.py     # cut the lines first
    python3 tools/transcribe.py                # then open http://localhost:8765

Each line is shown on its own with the Surya+corrector reading already in the
box, so the work is checking rather than typing. Saving records both what you
kept and whether you changed it, which is how we find out later whether the
pre-fill was helping or quietly steering the answers.

Everything is written straight back to `manifest.json` on each save, so closing
the tab loses nothing. Export tesstrain pairs when you are done:

    python3 tools/transcribe.py --export
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "lines" / "human"
MANIFEST = DATA / "manifest.json"
IMAGES = DATA / "images"
PORT = 8765
REVIEW = {"on": False, "min": 3.0}
# Books to serve first. Underlying indices never move, so a client
# holding a stale index still saves to the right row.
PRIORITY: list = []

PAGE = """<!doctype html><html lang="ba"><head><meta charset="utf-8">
<title>Transcribe — Bashkort ground truth</title><style>
:root{--bg:#12160f;--fg:#e8ece6;--dim:#8b958a;--line:#2b332c;--acc:#d8a047;--ok:#7fb069}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,sans-serif}
header{display:flex;align-items:center;gap:1rem;padding:.7rem 1.2rem;border-bottom:1px solid var(--line)}
h1{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin:0;font-weight:600}
.bar{flex:1;height:5px;background:var(--line);border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--ok);width:0}
.count{font-variant-numeric:tabular-nums;color:var(--dim);font-size:.85rem}
main{max-width:1700px;margin:0 auto;padding:1.5rem 1.2rem 4rem}
.meta{color:var(--dim);font-size:.78rem;margin-bottom:.5rem;font-variant-numeric:tabular-nums}
.qpos{float:right;opacity:.65}
.img{background:#fff;border-radius:4px;padding:10px;overflow-x:auto;position:relative}
.img img{display:block;max-width:100%;height:auto;min-height:44px;cursor:zoom-in}
.img.zoom img{max-width:none;cursor:zoom-out}
.imghint{position:absolute;right:8px;top:4px;font:11px ui-monospace,monospace;
 color:#8b958a;background:rgba(255,255,255,.85);padding:0 .3rem;border-radius:3px}
textarea{width:100%;margin-top:1rem;padding:.8rem;font:19px/1.5 Georgia,serif;
 background:#1a201b;color:var(--fg);border:1px solid var(--line);border-radius:4px;resize:vertical}
textarea:focus{outline:2px solid var(--acc);outline-offset:1px}
.keys{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.6rem}
.keys button{font:17px Georgia,serif;background:#1a201b;color:var(--fg);
 border:1px solid var(--line);border-radius:4px;padding:.25rem .6rem;cursor:pointer}
.keys button:hover{border-color:var(--acc);color:var(--acc)}
.row{display:flex;gap:.6rem;margin-top:1rem;align-items:center}
.btn{font:14px inherit;padding:.5rem 1rem;border-radius:4px;cursor:pointer;border:1px solid var(--line);
 background:#1a201b;color:var(--fg)}
.btn.primary{background:var(--ok);border-color:var(--ok);color:#0d130c;font-weight:600}
.btn.warn{color:var(--acc)}
.hint{color:var(--dim);font-size:.78rem;margin-left:auto}
kbd{background:#1a201b;border:1px solid var(--line);border-radius:3px;padding:0 .3rem;font-size:.85em}
.flags{display:flex;flex-wrap:wrap;gap:.35rem;margin:.1rem 0 .6rem}
.flag{font:12px ui-monospace,monospace;padding:.15rem .5rem;border-radius:3px;
 background:#1a201b;border:1px solid var(--line);color:var(--dim)}
.flag.missed-letter{border-color:var(--acc);color:var(--acc)}
.flag.foreign-char{border-color:#c05c4a;color:#e08b7a}
.done{text-align:center;padding:4rem 1rem;color:var(--dim)}
details{margin-top:1rem;border:1px solid var(--line);border-radius:4px}
summary{padding:.5rem .8rem;cursor:pointer;color:var(--dim);font-size:.82rem;user-select:none}
summary:hover{color:var(--acc)}
.pagetext{padding:.2rem .9rem .9rem;font:15px/1.7 Georgia,serif;color:#c9d2c7;
 white-space:pre-wrap;max-height:19rem;overflow:auto}
</style></head><body>
<header><h1>Bashkort ground truth</h1><div class="bar"><i id="bar"></i></div>
<span class="count" id="count"></span></header>
<main id="app"></main>
<script>
let M=[],ORDER=[],i=0,REVIEW=false;
const LETTERS=["ә","ө","ү","ң","һ","ҙ","ҫ","ҡ","ғ","Ә","Ө","Ү","Ң","Һ","Ҙ","Ҫ","Ҡ","Ғ","—","«","»"];
async function load(){const d=await (await fetch("/api/manifest")).json();
 M=d.rows; REVIEW=d.review; ORDER=d.order||M.map((_,k)=>k);
 i=REVIEW?0:ORDER.findIndex(k=>M[k].text===null); if(i<0)i=ORDER.length; draw();}
function draw(){
 const done=REVIEW?i:ORDER.filter(k=>M[k].text!==null).length;
 bar.style.width=(100*done/ORDER.length)+"%";
 count.textContent=done+" / "+ORDER.length+(REVIEW?" reviewed":"");
 if(i>=ORDER.length){app.innerHTML='<div class="done"><h2>All done.</h2>'+
   '<p>Export with <code>python3 tools/transcribe.py --export</code></p></div>';return;}
 const r=M[ORDER[i]];
 const ln=(r.image.match(/_l(\d+)/)||[,"?"])[1].replace(/^0+(?=\d)/,"");
 app.innerHTML=`<div class="meta">${r.book} · page ${r.page} · line ${ln}
  <span class="qpos">${i+1} of ${ORDER.length} in queue</span></div>
  <div class="img" id="imgbox"><img id="lineimg" src="/img/${encodeURIComponent(r.image)}" alt=""><span class="imghint" id="imghint"></span></div>
  <textarea id="ta" rows="2" spellcheck="false"></textarea>
  <div class="keys">${LETTERS.map(c=>`<button data-c="${c}">${c}</button>`).join("")}</div>
  <div class="row">
   <button class="btn primary" id="save">Save &amp; next</button>
   <button class="btn" id="back">Back</button>
   <button class="btn warn" id="skip">Skip line</button>
   <span class="hint"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> save · <kbd>Esc</kbd> skip</span>
  </div>
  ${r.page_text ? `<details open><summary>Machine reading of this whole page —
   reference only, find your line in it</summary>
   <div class="pagetext">${r.page_text.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}</div>
   </details>` : ""}`;
 const box=document.getElementById("imgbox"), im=document.getElementById("lineimg");
 im.onload=()=>{const scaled=im.naturalWidth>im.clientWidth+1;
   document.getElementById("imghint").textContent=
     scaled?`${im.naturalWidth}px — fitted, click to zoom`:`${im.naturalWidth}px — full size`;};
 im.onclick=()=>{box.classList.toggle("zoom");
   document.getElementById("imghint").textContent=
     box.classList.contains("zoom")?"1:1 — click to fit":`${im.naturalWidth}px — fitted, click to zoom`;};
 const ta=document.getElementById("ta");
 ta.value=(r.text!==null?r.text:(r.suggestion||""));
 ta.focus(); ta.setSelectionRange(ta.value.length,ta.value.length);
 document.querySelectorAll(".keys button").forEach(b=>b.onclick=e=>{
   e.preventDefault();const c=b.dataset.c,s=ta.selectionStart;
   ta.value=ta.value.slice(0,s)+c+ta.value.slice(ta.selectionEnd);
   ta.focus();ta.setSelectionRange(s+c.length,s+c.length);});
 save.onclick=()=>commit(ta.value);
 back.onclick=()=>{if(i>0){i--;draw();}};
 skip.onclick=()=>commit(null,true);
 ta.onkeydown=e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){e.preventDefault();commit(ta.value);}
                  else if(e.key==="Escape"){e.preventDefault();commit(null,true);}};
}
async function commit(text,skip=false){
 const idx=ORDER[i], r=M[idx];
 r.text=skip?"":(text||"").trim();
 r.skipped=skip;
 r.edited=skip?null:(r.text!==(r.suggestion||"").trim());
 r.reviewed=REVIEW?true:r.reviewed;
 await fetch("/api/save",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({index:idx,row:r})});
 // ORDER keeps answered rows so Back still works, so plain i++ walks straight
 // into lines that are already done. Jump to the next one actually awaiting an
 // answer; when there is none left, fall off the end and show the done screen.
 if(REVIEW){i++;}
 else{let n=-1;
      for(let k=i+1;k<ORDER.length;k++){if(M[ORDER[k]].text===null){n=k;break;}}
      i=n<0?ORDER.length:n;}
 draw();
}
load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/manifest":
            rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
            # Retired rows keep their labels in the manifest for reference, but
            # their images have been moved to quarantine — serving them gives a
            # 404 and an empty frame with no way to tell why.
            live = [i for i, r in enumerate(rows) if not r.get("clipped")]
            if REVIEW["on"]:
                order = [i for i in live
                         if (rows[i].get("text") or "").strip()
                         and rows[i].get("review_score", 0) >= REVIEW["min"]
                         and not rows[i].get("reviewed")]
                order.sort(key=lambda i: -rows[i].get("review_score", 0))
            else:
                order = list(live)
                if PRIORITY:
                    def rank(i):
                        book = rows[i].get("book", "")
                        for n, pat in enumerate(PRIORITY):
                            if pat.lower() in book.lower():
                                return n
                        return len(PRIORITY)
                    # answered lines keep their place; unanswered ones sort by book
                    order.sort(key=lambda i: (rows[i].get("text") is not None,
                                              rank(i), i))
            body = json.dumps({"rows": rows, "order": order,
                               "review": REVIEW["on"]}, ensure_ascii=False)
            return self._send(body.encode("utf-8"), "application/json")
        if path.startswith("/img/"):
            from urllib.parse import unquote
            name = unquote(path[5:])
            f = IMAGES / name
            if f.exists() and f.parent == IMAGES:
                return self._send(f.read_bytes(), "image/png")
        self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/save":
            return self._send(b"no", "text/plain", 404)
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n).decode("utf-8"))
        rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows[payload["index"]] = payload["row"]
        MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        self._send(b'{"ok":true}', "application/json")


def export(out: Path) -> int:
    """Write tesstrain-format pairs from the transcribed lines."""
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    # A crop can appear twice if a prepare run re-appended pages already in the
    # manifest. Writing both silently leaves the last one standing and reports a
    # count that does not match the files on disk, so collapse them here and say
    # so. The later row wins: it is the more recent reading.
    seen: dict[str, int] = {}
    for i, r in enumerate(rows):
        seen[r["image"]] = i
    dups = len(rows) - len(seen)
    rows = [rows[i] for i in sorted(seen.values())]

    n = edited = clipped = 0
    for r in rows:
        text = (r.get("text") or "").strip()
        if not text or r.get("skipped"):
            continue
        if r.get("clipped"):
            # The crop these were read from cut the descenders off, so the
            # label asserts a ҙ ҫ ҡ ғ ң the image does not show. Training on
            # that teaches the model to hallucinate the stroke from context.
            clipped += 1
            continue
        text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", text))
        stem = Path(r["image"]).stem
        (out / f"{stem}.png").write_bytes((IMAGES / r["image"]).read_bytes())
        (out / f"{stem}.gt.txt").write_text(text + "\n", encoding="utf-8")
        n += 1
        edited += bool(r.get("edited"))
    print(f"  {n:,} verified pairs -> {out}")
    if clipped:
        print(f"  {clipped:,} excluded — read from crops that clipped the descenders")
    if dups:
        print(f"  {dups:,} duplicate manifest rows collapsed (kept the later reading)")
    if n:
        print(f"  {edited:,} ({100*edited/n:.0f}%) needed correcting — "
              f"the rest matched the machine reading")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--out", default="data/lines/verified")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--review", action="store_true",
                    help="revisit already-transcribed lines, worst first")
    ap.add_argument("--min-score", type=float, default=3.0,
                    help="review lines scoring at least this (default 3)")
    ap.add_argument("--priority", nargs="+", default=[], metavar="BOOK",
                    help="serve unanswered lines from these books first "
                         "(substring match on the filename)")
    args = ap.parse_args()

    if not MANIFEST.exists():
        raise SystemExit("No manifest. Run tools/prepare_transcription.py first.")
    if args.export:
        return export(ROOT / args.out)

    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    REVIEW["on"], REVIEW["min"] = args.review, args.min_score
    PRIORITY[:] = args.priority
    if args.review:
        n = sum(1 for r in rows if (r.get("text") or "").strip()
                and r.get("review_score", 0) >= args.min_score
                and not r.get("reviewed"))
        print(f"  review mode: {n:,} flagged lines, worst first")
    else:
        done = sum(1 for r in rows if r.get("text") is not None)
        print(f"  {len(rows):,} lines, {done:,} already transcribed")
    print(f"  http://localhost:{args.port}   (Ctrl-C to stop; progress is saved as you go)")
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
