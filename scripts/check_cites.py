import re
from pathlib import Path

tex_path = Path("paper/conference_paper.tex")
content = tex_path.read_text(encoding="utf-8")

cites = re.findall(r"\\cite\{([^}]+)\}", content)
all_cited_keys = set()
for c in cites:
    for k in c.split(","):
        all_cited_keys.add(k.strip())

print("=== CITED KEYS IN CONFERENCE_PAPER.TEX ===")
for k in sorted(all_cited_keys):
    print(f"  - {k}")

bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", content))
print("\n=== BIBITEMS IN BIBLIOGRAPHY ===")
for b in sorted(bibitems):
    print(f"  - {b}")

missing = all_cited_keys - bibitems
print(f"\nMissing from bibliography: {missing if missing else 'NONE (All exist!)'}")

unused = bibitems - all_cited_keys
print(f"Unused in text: {unused if unused else 'NONE (All cited!)'}")

ref_verify_path = Path("paper/REFERENCES_TO_VERIFY.md")
unverified_content = ref_verify_path.read_text(encoding="utf-8")

# Extract keys from REFERENCES_TO_VERIFY.md
unverified_keys = set(re.findall(r"`([a-zA-Z0-9_]+)`", unverified_content))
print("\n=== UNVERIFIED KEYS IN REFERENCES_TO_VERIFY.MD ===")
for uk in sorted(unverified_keys):
    if "ref_" in uk or "wesad" in uk.lower() or "troika" in uk.lower() or "cvach" in uk.lower() or "uci" in uk.lower():
        print(f"  - {uk}")

intersect = all_cited_keys.intersection(unverified_keys)
print(f"\nOverlap between cited keys and REFERENCES_TO_VERIFY.md: {intersect if intersect else 'NONE (Zero unverified references cited!)'}")
