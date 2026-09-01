"""pytest 全局配置：把 backend/ 根目录加入 sys.path，便于 `from config... / from src...` 导入。"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
