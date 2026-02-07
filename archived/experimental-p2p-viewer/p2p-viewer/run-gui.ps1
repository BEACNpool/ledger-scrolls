# Ledger Scrolls P2P GUI (PowerShell)
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$py = "python"
try { & $py --version | Out-Null } catch { $py = "py" }

if (!(Test-Path ".\.venv")) {
  & $py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m gui.app
