"""Central environment loader.

On WSL, reads secrets from Windows Credential Manager in a single PowerShell
call before falling back to .env for non-secret values. Mirrors the _wcm()
alias in ~/.zshrc so that Python processes without an inherited shell env
still pick up WCM secrets.
"""

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _PROJECT_ROOT / ".env"

_WCM_SECRETS = ("DB_PASSWORD", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")


def _is_wsl() -> bool:
    """Return True when running inside Windows Subsystem for Linux."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _wcm_batch(names: tuple[str, ...]) -> dict[str, str]:
    """Fetch multiple secrets from Windows Credential Manager in a single PowerShell call."""
    targets = ", ".join(f"'{n}'" for n in names)
    ps = (
        f"@({targets}) | ForEach-Object {{"
        f" $c = Get-StoredCredential -Target $_;"
        f" if ($c) {{ $v = $c.GetNetworkCredential().Password;"
        f' if ($v) {{ "$_=$v" }} }} }}'
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
        )
        secrets: dict[str, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                if key and value:
                    secrets[key] = value
        return secrets
    except (OSError, subprocess.TimeoutExpired):
        return {}


def load_env() -> None:
    """Load env vars: WCM secrets first (WSL only), then .env for the rest.

    override=False on load_dotenv ensures WCM values and any already-exported
    shell vars are never overwritten by .env.
    """
    if _is_wsl():
        missing = tuple(n for n in _WCM_SECRETS if n not in os.environ)
        if missing:
            for name, value in _wcm_batch(missing).items():
                os.environ[name] = value

    load_dotenv(_DOTENV_PATH, override=False)
