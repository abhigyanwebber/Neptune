from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

required = [
    "README.md",
    "REPOSITORY_STATUS.md",
    "00_SOURCE_MATERIALS/SOURCE_MANIFEST.md",
    "00_SOURCE_MATERIALS/00_CANONICAL_BIBLE/Infrastructure_Bible_v0.2.md",
    "01_BIBLE/02_ARCHITECTURE_OVERVIEW.md",
    "03_CONTRACTS/TASK_CONTRACT.md",
    "03_CONTRACTS/AGENT_CONTRACT.md",
    "03_CONTRACTS/RUNTIME_CONTRACT.md",
    "03_CONTRACTS/MODEL_CONTRACT.md",
    "03_CONTRACTS/ROUTER_CONTRACT.md",
    "03_CONTRACTS/EVENT_CONTRACT.md",
    "07_SECURITY/01_THREAT_MODEL.md",
    "12_VALIDATION/01_PHASE_0_CHECKLIST.md",
]

missing=[p for p in required if not (ROOT/p).exists()]
if missing:
    raise SystemExit("Missing required files:\n- " + "\n- ".join(missing))

print("Repository verification: PASS")
print(f"Root: {ROOT}")
print(f"Files: {sum(1 for p in ROOT.rglob('*') if p.is_file())}")
