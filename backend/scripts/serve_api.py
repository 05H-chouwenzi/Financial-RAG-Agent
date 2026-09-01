"""启动 API 服务

用法:
    python scripts/serve_api.py                 # http://127.0.0.1:8000
    python scripts/serve_api.py --port 9000 --reload
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="启动 Financial-RAG-Agent API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    args = p.parse_args()

    import uvicorn

    uvicorn.run("api.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
