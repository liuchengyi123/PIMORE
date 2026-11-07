from pathlib import Path
p = Path(r"D:\1010\harbor-cs-desktop\renderer\app.js")
t = p.read_text(encoding="utf-8")
# print showApp showLogin boot
for name in ["function showLogin", "function showApp", "async function boot", "getConfig", "loggedIn", "DOMContentLoaded", "startLoops"]:
    i = t.find(name)
    print(name, i)
print("--- full boot/show ---")
# extract from showLogin to startLoops and end of file boot
lines = t.splitlines()
for i,l in enumerate(lines):
    if "function showLogin" in l or "function showApp" in l or "async function" in l and "boot" in l or "getConfig" in l or "DOMContentLoaded" in l or "loggedIn" in l:
        print(i+1, l)
print("==== last 80 lines ====")
print("\n".join(f"{i+1}|{l}" for i,l in enumerate(lines[-80:], start=len(lines)-79)))
print("==== first showLogin block ====")
print("\n".join(f"{i+1}|{l}" for i,l in enumerate(lines[50:100], start=51)))
