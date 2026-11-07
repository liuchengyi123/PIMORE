import os


def _windows_proxy(enabled_only):
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled = int(winreg.QueryValueEx(key, "ProxyEnable")[0] or 0)
            server = str(winreg.QueryValueEx(key, "ProxyServer")[0] or "").strip()
    except OSError:
        return ""
    if enabled_only and not enabled:
        return ""
    return _proxy_url(server)


def _proxy_url(server):
    server = str(server or "").strip()
    if not server:
        return ""
    if "=" in server:
        parts = {}
        for item in server.split(";"):
            if "=" in item:
                name, value = item.split("=", 1)
                parts[name.strip().lower()] = value.strip()
        server = parts.get("https") or parts.get("http") or ""
    if not server:
        return ""
    if "://" not in server:
        server = "http://" + server
    return server


def outbound_proxy():
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = _proxy_url(os.environ.get(name, ""))
        if value:
            return value
    return _windows_proxy(enabled_only=True)


def remembered_proxy():
    return _windows_proxy(enabled_only=False)
