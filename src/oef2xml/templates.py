"""Question templates loaded from data/templates.json (REQ-ARCH-2, REQ-MAP-Q-TEMPLATE)."""
import json
from pathlib import Path

DATA = Path(__file__).with_name("data")
TEMPLATES = {k: v for k, v in json.loads((DATA / "templates.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
