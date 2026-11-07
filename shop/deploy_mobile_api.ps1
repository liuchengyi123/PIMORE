# Deploy Harbor mobile JSON API (mobile_api.py) to the live shop host.
# Requires: OpenSSH scp, and env HARBOR_SSH like: root@YOUR_IP
# Optional: HARBOR_REMOTE_DIR (default /opt/harbor/shop)
#
# Example:
#   $env:HARBOR_SSH = "root@1.2.3.4"
#   powershell -File D:\1010\shop\deploy_mobile_api.ps1

$ErrorActionPreference = "Stop"
$hostSpec = $env:HARBOR_SSH
if (-not $hostSpec) { throw "Set HARBOR_SSH first, e.g. root@your.vps.ip" }
$remoteDir = if ($env:HARBOR_REMOTE_DIR) { $env:HARBOR_REMOTE_DIR } else { "/opt/harbor/shop" }
$local = Join-Path $PSScriptRoot "mobile_api.py"
if (-not (Test-Path $local)) { throw "missing $local" }
Write-Host "Uploading $local -> ${hostSpec}:$remoteDir/mobile_api.py"
scp $local "${hostSpec}:$remoteDir/mobile_api.py"
Write-Host "Restart the shop process on the VPS (systemd/supervisor) so /api/auth/social and /api/home go live."
