"""Verify the 2026-11-18 docs trimming (81 -> 9 active files).

Mirror of B2B-Knowledge-Base/TEMP_TRIMMING/gt_v2_parts/assemble_verify.py:
print [OK]/[FAIL] per assertion, exit 1 if any fails.
Run: $env:PYTHONIOENCODING='utf-8'; python -X utf8 scripts/verify_docs_trimming.py
"""

import hashlib
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
ARCHIVE = os.path.join(ROOT, "_ARCHIVE")
ACTIVE = {
    "00_DOCS_CONTRACT.md",
    "01_EVIDENCE_DIGEST.md",
    "02_COACHING_EXEMPLARS.md",
    "AUDIT_INTEGRATION_2026-11-13.md",
    "CLI_USAGE.md",
    "COMPACT_JSON_FOR_LLM.md",
    "HALUCINACE_ROOT_CAUSE_ANALYSIS.md",
    "PATTERN_DISCOVERY_METHODOLOGY.md",
    "SESSION_HANDOFF_2026-11-17.md",
}
# Digests and the contract may legitimately cite archived files as historical
# provenance; operational docs may not.
DIGEST_FILES = {
    "01_EVIDENCE_DIGEST.md",
    "02_COACHING_EXEMPLARS.md",
    "00_DOCS_CONTRACT.md",
}

ok = True


def chk(label, cond, detail=""):
    global ok
    print("[%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        ok = False


def tracked():
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return [line for line in out.stdout.splitlines() if line]


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


files = tracked()
docs_files = sorted(f for f in os.listdir(DOCS) if os.path.isfile(os.path.join(DOCS, f)))

# 1. active doc count
chk(
    "active docs count == 9",
    len(docs_files) == 9 and set(docs_files) == ACTIVE,
    "= %d" % len(docs_files),
)

# 2. no duplicate SHA256 among tracked md/json
hashes = {}
for rel in files:
    if not rel.endswith((".md", ".json")):
        continue
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    hashes.setdefault(h, []).append(rel)
dups = [v for v in hashes.values() if len(v) > 1]
chk("no duplicate SHA256 among tracked md/json", not dups, "dups=%s" % dups)

# 3. no dangling path references in active docs
pat = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:docs|data|schemas|scripts|src|tests|config|logs)/"
    r"[A-Za-z0-9._/-]+\.(?:md|json|py|log|ps1|yml|toml|pgn))"
)
dangling = []
for name in ACTIVE:
    p = os.path.join(DOCS, name)
    if not os.path.isfile(p):
        continue
    for m in pat.finditer(read(p)):
        rel = m.group(1).replace("/", os.sep)
        # data/ is gitignored and regenerable; digest files cite historical
        # data paths as provenance, so a missing local file is not drift.
        if name in DIGEST_FILES and m.group(1).startswith("data/"):
            continue
        if not os.path.exists(os.path.join(ROOT, rel)):
            dangling.append("%s -> %s" % (name, m.group(1)))
chk("no dangling path refs in active docs", not dangling, "count=%d" % len(dangling))
for d in dangling[:10]:
    print("     " + d)

# 4. operational docs must not cite archived filenames as active sources
archived_names = set()
for root_dir, _dirs, fnames in os.walk(ARCHIVE):
    archived_names.update(fnames)
leaks = []
for name in ACTIVE - DIGEST_FILES:
    p = os.path.join(DOCS, name)
    if not os.path.isfile(p):
        continue
    txt = read(p)
    for a in archived_names:
        if a in txt:
            leaks.append("%s -> %s" % (name, a))
chk("no archived-filename references in operational docs", not leaks, "count=%d" % len(leaks))
for d in leaks[:10]:
    print("     " + d)

# 5. evidence digest contains the unique facts
digest = read(os.path.join(DOCS, "01_EVIDENCE_DIGEST.md"))
facts = ["388", "60/61", "8 873", "5e41461a", "0,3107", "97,8 %", "227:1"]
missing = [f for f in facts if f not in digest]
chk("EVIDENCE_DIGEST holds unique facts", not missing, "missing=%s" % missing)

# 6. version consistency in active docs
bad_version = []
for name in ACTIVE:
    p = os.path.join(DOCS, name)
    if not os.path.isfile(p):
        continue
    t = read(p)
    for wrong in ["compact JSON 2.1", "Compact JSON 2.3", "JSON 2.4"]:
        if wrong in t:
            bad_version.append("%s: %s" % (name, wrong))
chk("version drift removed", not bad_version, "hits=%s" % bad_version)
compact = read(os.path.join(DOCS, "COMPACT_JSON_FOR_LLM.md"))
chk("COMPACT_JSON title says 2.7", compact.startswith("# Compact JSON 2.7"))

# 7. ASCII filenames (GT-080)
bad_ascii = [f for f in files if not re.fullmatch(r"[A-Za-z0-9._/-]+", f)]
chk("ASCII filenames", not bad_ascii, "bad=%s" % bad_ascii[:5])

# 8. zero-byte tracked files except package markers
zero = []
for rel in files:
    p = os.path.join(ROOT, rel)
    if os.path.isfile(p) and os.path.getsize(p) == 0 and not rel.endswith("__init__.py"):
        zero.append(rel)
chk("no 0B tracked except __init__.py", not zero, "bad=%s" % zero)


# 9. integrity snapshot (count + bytes)
def stat(d):
    n = 0
    b = 0
    for r, _dirs, fs in os.walk(d):
        for f in fs:
            n += 1
            b += os.path.getsize(os.path.join(r, f))
    return n, b


dn, db = stat(DOCS)
an, ab = stat(ARCHIVE)
print("     docs: %d files / %d B | _ARCHIVE: %d files / %d B" % (dn, db, an, ab))
chk("docs byte budget < 250 KB", db < 250_000, "= %d B" % db)

# 10. gates presence (actual gate commands are run separately)
chk(
    "CI still references active scripts",
    all(
        os.path.isfile(os.path.join(ROOT, "scripts", s))
        for s in ["generate_dummy_cache.py", "print_engine_pin.py", "verify_engine_identity.py"]
    ),
)

print("\nRESULT: %s" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
