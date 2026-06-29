"""Verify all Python source files parse without syntax errors."""
import ast
import sys
from pathlib import Path

base = Path(__file__).parent / "packages" / "agent-engine"
files = [
    "app/config.py",
    "app/schemas/alert.py",
    "app/schemas/diagnosis.py",
    "app/models/incident.py",
    "app/models/service_topology.py",
    "app/tools/incident_parser.py",
    "app/tools/topology.py",
    "app/tools/knowledge_base.py",
    "app/graph/workflow.py",
    "app/routers/diagnosis.py",
    "app/lib/mongo.py",
    "app/lib/qdrant.py",
    "app/main.py",
]

passed = 0
failed = []

for rel in files:
    path = base / rel
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        passed += 1
    except SyntaxError as e:
        failed.append(f"{rel}: line {e.lineno} — {e.msg}")

print(f"Python syntax check: {passed}/{len(files)} files OK")
if failed:
    for err in failed:
        print(f"  FAIL: {err}")
    sys.exit(1)
else:
    print("All Python files parse successfully.")
