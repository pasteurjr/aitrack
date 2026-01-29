import os
from pathlib import Path


def _parse_line(line: str):
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None
    if '=' not in line:
        return None, None
    key, val = line.split('=', 1)
    key = key.strip()
    val = val.strip().strip('"').strip("'")
    return key, val


def load_dotenv(paths=("config/.env", ".env")):
    for p in paths:
        fp = Path(p)
        if not fp.exists():
            continue
        try:
            for raw in fp.read_text(encoding='utf-8').splitlines():
                k, v = _parse_line(raw)
                if not k:
                    continue
                # não sobrescreve se já setado no ambiente
                if k not in os.environ:
                    os.environ[k] = v
        except Exception:
            # falha silenciosa para não quebrar import
            pass

