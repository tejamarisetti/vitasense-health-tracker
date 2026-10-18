import re

def check_file(path, label):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    print(f"=== {label} .zip or download links ===")
    for m in re.finditer(r'href=["\']([^"\']*(?:download|\.zip|\.tar|\.gz)[^"\']*)["\']', text):
        print(m.group(1))

check_file(r'C:\Users\Master\.gemini\antigravity-ide\brain\c84ae576-da71-4751-a138-b2e1c847674a\.system_generated\steps\449\content.md', 'PhysioNet')
check_file(r'C:\Users\Master\.gemini\antigravity-ide\brain\c84ae576-da71-4751-a138-b2e1c847674a\.system_generated\steps\455\content.md', 'PPG-DaLiA')
