#!/usr/bin/env python
"""Wrap the pages in a passphrase gate and write them to docs/ for GitHub Pages.

Why encryption rather than a password prompt: GitHub Pages serves a private
repository's site publicly on the free and Pro plans, and a JavaScript password
check protects nothing -- the data sits in the file and View Source reveals it.
Here the page body is gzipped, encrypted with AES-256-GCM, and only the
ciphertext is committed. The passphrase derives the key in the reader's browser
(PBKDF2-SHA256), so a visitor without it downloads bytes that decode to nothing.

The honest limit: anyone who has the file can try passphrases offline as fast as
their hardware allows. 300k PBKDF2 iterations make each guess cost real time,
but a short or guessable passphrase still falls. Use a long one.

    python scripts/publish_site.py --passphrase 'something long'
"""

import argparse
import base64
import getpass
import gzip
import hashlib
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERATIONS = 300_000
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GATE = """<meta charset="utf-8">
<title>%(title)s</title>
<style>
:root{--bg:#f3f5f7;--fg:#15181d;--dim:#68717e;--card:#fff;--rule:#dde2e8;--accent:#2a78d6;
      --bad:#bd3320}
@media (prefers-color-scheme:dark){:root{--bg:#0f1216;--fg:#e8ebef;--dim:#8d97a4;
      --card:#171b21;--rule:#28303a;--accent:#3987e5;--bad:#e0705c}}
html,body{height:100%%}
body{margin:0;background:var(--bg);color:var(--fg);display:grid;place-items:center;
     font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
form{width:min(380px,88vw);background:var(--card);border:1px solid var(--rule);
     border-radius:12px;padding:26px 24px}
h1{font-family:ui-serif,Georgia,serif;font-size:20px;margin:0 0 4px}
p{color:var(--dim);font-size:13.5px;margin:0 0 18px}
input{width:100%%;font:inherit;padding:10px 12px;border-radius:7px;
      border:1px solid var(--rule);background:var(--bg);color:var(--fg)}
button{width:100%%;margin-top:10px;font:inherit;font-weight:600;padding:10px;
       border-radius:7px;border:0;background:var(--accent);color:#fff;cursor:pointer}
button:disabled{opacity:.6;cursor:default}
.err{color:var(--bad);font-size:13px;margin-top:10px;min-height:1.2em}
iframe{position:fixed;inset:0;width:100%%;height:100%%;border:0;background:var(--bg)}
</style>
<form id="f">
  <h1>%(title)s</h1>
  <p>This page is encrypted. Enter the passphrase your group uses.</p>
  <input id="p" type="password" autocomplete="current-password" autofocus
         placeholder="passphrase">
  <button id="b">Open</button>
  <div class="err" id="e"></div>
</form>
<script>
const PAYLOAD = %(payload)s;
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
document.getElementById("f").onsubmit = async ev => {
  ev.preventDefault();
  const btn = document.getElementById("b"), err = document.getElementById("e");
  btn.disabled = true; err.textContent = ""; btn.textContent = "Decrypting\\u2026";
  try{
    const key = await crypto.subtle.deriveKey(
      {name:"PBKDF2", salt:b64(PAYLOAD.salt), iterations:PAYLOAD.iterations,
       hash:"SHA-256"},
      await crypto.subtle.importKey("raw",
        new TextEncoder().encode(document.getElementById("p").value),
        "PBKDF2", false, ["deriveKey"]),
      {name:"AES-GCM", length:256}, false, ["decrypt"]);
    const plain = await crypto.subtle.decrypt(
      {name:"AES-GCM", iv:b64(PAYLOAD.iv)}, key, b64(PAYLOAD.ct));
    // the payload is gzipped before encryption; a 3.7 MB page ships as ~1 MB
    const html = await new Response(
      new Blob([plain]).stream().pipeThrough(new DecompressionStream("gzip"))
    ).text();
    const frame = document.createElement("iframe");
    frame.srcdoc = html;
    document.body.replaceChildren(frame);
  }catch(e){
    err.textContent = "That passphrase does not open this page.";
    btn.disabled = false; btn.textContent = "Open";
  }
};
</script>
"""


def wrap(html_path, title, passphrase):
    raw = open(html_path, "rb").read()
    blob = gzip.compress(raw, 9)
    salt, iv = os.urandom(16), os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS, 32)
    ct = AESGCM(key).encrypt(iv, blob, None)
    payload = json.dumps({"salt": base64.b64encode(salt).decode(),
                          "iv": base64.b64encode(iv).decode(),
                          "iterations": ITERATIONS,
                          "ct": base64.b64encode(ct).decode()})
    return GATE % {"title": title, "payload": payload}, len(raw), len(ct)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--passphrase", help="prompted for if omitted")
    ap.add_argument("--out", default=os.path.join(REPO, "docs"))
    args = ap.parse_args(argv)

    phrase = args.passphrase or getpass.getpass("passphrase: ")
    if not phrase:
        sys.exit("a passphrase is required")
    if len(phrase) < 12:
        print("warning: %d characters. Anyone holding the file can try "
              "passphrases offline; a longer one is the only thing that makes "
              "that expensive." % len(phrase), file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    pages = [("inspector.html", "Item Inspector", "index.html"),
             ("report.html", "Rating Distributions", "report.html")]
    for src, title, dst in pages:
        path = os.path.join(REPO, "result", src)
        if not os.path.exists(path):
            print("skipped %s (not built yet)" % src)
            continue
        html, n_raw, n_ct = wrap(path, title, phrase)
        with open(os.path.join(args.out, dst), "w", encoding="utf-8") as fh:
            fh.write(html)
        print("%-14s -> docs/%-12s %.1f MB page, %.1f MB encrypted"
              % (src, dst, n_raw / 1048576, n_ct / 1048576))
    open(os.path.join(args.out, ".nojekyll"), "w").close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
