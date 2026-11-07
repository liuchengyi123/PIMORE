from pathlib import Path
p = Path(r"D:\1010\harbor-cs-desktop\main.js")
t = p.read_text(encoding="utf-8", errors="replace")
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    if "\ufffd" in l or "客服?" in l or "账?" in l or "失?" in l or "+ '?" in l or '+ "?' in l:
        print(i, repr(l))
# also node --check
import subprocess, sys
r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
print("node --check rc", r.returncode)
print(r.stderr[:500] if r.stderr else "syntax ok")
