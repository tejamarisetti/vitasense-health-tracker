import sys
sys.stdout.reconfigure(encoding='utf-8')
import pypdf

reader = pypdf.PdfReader('paper/conference_paper.pdf')
print(f"Total pages: {len(reader.pages)}")
for i, page in enumerate(reader.pages):
    txt = page.extract_text()
    first_line = txt.splitlines()[0] if txt.splitlines() else ""
    last_line = txt.splitlines()[-1] if txt.splitlines() else ""
    print(f"Page {i+1}: Length {len(txt)} chars | First: {first_line[:60]} | Last: {last_line[:60]}")
