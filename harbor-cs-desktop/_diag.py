from pathlib import Path
import re, subprocess

root = Path(r"D:\1010\harbor-cs-desktop")
for rel in ["renderer/app.js", "main.js", "preload.js", "renderer/index.html"]:
    p = root / rel
    t = p.read_text(encoding="utf-8", errors="replace")
    print("====", rel, "====")
    # find odd quotes / replacement chars
    for i,l in enumerate(t.splitlines(),1):
        if "\ufffd" in l:
            print("UFFD", i, repr(l[:140]))
    r = subprocess.run(["node","--check",str(p)], capture_output=True, text=True) if p.suffix==".js" else None
    if r is not None:
        print("check", r.returncode, (r.stderr or "ok")[:300])

# show log
log = Path(r"C:\Users\Administrator\AppData\Roaming\harbor-cs-desktop\cs-desk.log")
print("==== LOG TAIL ====")
if log.exists():
    print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
else:
    print("no log")
