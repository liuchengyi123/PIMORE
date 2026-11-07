"""Start the image worker on a rented GPU and check the public address."""

import re
import shlex
from pathlib import Path

import httpx

WORKER = Path(__file__).resolve().parent / "gen_worker.py"
REMOTE_DIR = "/root/harbor-gen"


class LinkError(Exception):
    pass


def parse_ssh(host, port="41125", user="root"):
    text = " ".join(str(host or "").split())
    port = str(port or "41125").strip() or "41125"
    user = str(user or "root").strip() or "root"
    if text.lower().startswith("ssh"):
        found_port = re.search(r"(?:^|\s)-p\s+(\d+)", text)
        found_at = re.search(r"([A-Za-z0-9._-]+)@([A-Za-z0-9._-]+)", text)
        if found_port:
            port = found_port.group(1)
        if found_at:
            return found_at.group(2), port, found_at.group(1)
        return "", port, user
    return text, port, user


def _tail(text, *secrets):
    cleaned = text or ""
    for secret in secrets:
        if secret:
            cleaned = cleaned.replace(secret, "******")
    cleaned = cleaned.strip()
    if not cleaned:
        return ""
    return " " + cleaned[-240:]


def open_gpu(*, host, port, user, password, public_url, token):
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=int(port),
            username=user or "root",
            password=password,
            timeout=20,
            auth_timeout=20,
            banner_timeout=20,
            allow_agent=False,
            look_for_keys=False,
        )
    except paramiko.AuthenticationException as exc:
        raise LinkError("SSH 密码不对。") from exc
    except Exception as exc:
        raise LinkError("连不上这台机器。") from exc
    try:
        sftp = client.open_sftp()
        try:
            sftp.mkdir(REMOTE_DIR)
        except OSError:
            pass
        sftp.put(str(WORKER), REMOTE_DIR + "/gen_worker.py")
        with sftp.file(REMOTE_DIR + "/env.sh", "w") as handle:
            handle.write(
                "GEN_HOST=0.0.0.0\nGEN_PORT=6006\nGEN_TOKEN=%s\n"
                "HF_ENDPOINT=https://hf-mirror.com\n"
                "HF_HOME=/root/autodl-tmp/hf\n" % token
            )
        sftp.close()
        _stdin, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(_START), timeout=180)
        code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", "replace") + stderr.read().decode("utf-8", "replace")
        if code != 0:
            raise LinkError("显卡上的程序没起来。" + _tail(output, token, password))
    finally:
        client.close()
    try:
        response = httpx.get(public_url.rstrip("/") + "/health", timeout=20.0)
    except httpx.HTTPError as exc:
        raise LinkError("程序已经在显卡上跑了，但这个公网地址打不开。") from exc
    if response.status_code != 200 or "ok" not in response.text:
        raise LinkError("程序已经在显卡上跑了，但这个公网地址打不开。")
    return "已连上。这张卡会自动领还没出的图。"


_START = r"""
set -e
mkdir -p /root/harbor-gen /root/autodl-tmp/hf
PY=""
for candidate in /root/miniconda3/bin/python /opt/conda/bin/python /usr/local/bin/python /usr/bin/python3; do
  if [ -x "$candidate" ]; then PY=$candidate; break; fi
done
if [ -z "$PY" ]; then PY=$(command -v python || command -v python3 || true); fi
if [ -z "$PY" ]; then echo "no python"; exit 1; fi
"$PY" -c "import PIL" || "$PY" -m pip install -q pillow
if [ -f /root/harbor-gen/gen.pid ]; then kill "$(cat /root/harbor-gen/gen.pid)" 2>/dev/null || true; fi
fuser -k 6006/tcp >/dev/null 2>&1 || true
sleep 0.4
set -a
. /root/harbor-gen/env.sh
set +a
nohup "$PY" /root/harbor-gen/gen_worker.py > /root/harbor-gen/gen.log 2>&1 &
echo $! > /root/harbor-gen/gen.pid
ok=0
for _try in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if "$PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6006/health', timeout=2).read()"; then
    ok=1
    break
  fi
  sleep 0.5
done
if [ "$ok" != 1 ]; then
  tail -n 40 /root/harbor-gen/gen.log || true
  exit 1
fi
"""
