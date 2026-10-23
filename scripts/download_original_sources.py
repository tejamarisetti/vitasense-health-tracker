import urllib.request
import json
from pathlib import Path

dest_dir = Path("paper/verified_sources")

original_refs = [
    {
        "id": "ref_reiss_dalia",
        "url": "https://api.crossref.org/works/10.3390/s19143079",
        "type": "crossref"
    },
    {
        "id": "ref_elgendi_sqi",
        "url": "https://api.crossref.org/works/10.3390/bioengineering3040021",
        "type": "crossref"
    },
    {
        "id": "ref_charlton_roadmap",
        "url": "https://api.crossref.org/works/10.1088/1361-6579/acead2",
        "type": "crossref"
    },
    {
        "id": "ref_vazquez_conformal",
        "url": "https://api.crossref.org/works/10.1007/s41666-021-00113-8",
        "type": "crossref"
    },
    {
        "id": "ref_physionet_wearable",
        "url": "https://api.crossref.org/works/10.13026/he0v-tf17",
        "type": "crossref"
    },
    {
        "id": "ref_uci_dalia",
        "url": "https://archive.ics.uci.edu/dataset/495/ppg+dalia",
        "type": "html"
    }
]

for item in original_refs:
    key = item["id"]
    out_file = dest_dir / f"{key}.txt"
    print(f"Fetching {key} from {item['url']}...")
    req = urllib.request.Request(item["url"], headers={'User-Agent': 'mailto:researcher@uni.edu'})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8', errors='replace')
            if item["type"] == "crossref":
                data = json.loads(content)['message']
                authors = ', '.join([f"{a.get('given','')} {a.get('family','')}".strip() for a in data.get('author', [])])
                title = data.get('title', [''])[0] if isinstance(data.get('title'), list) else data.get('title', '')
                container = data.get('container-title', [''])[0] if isinstance(data.get('container-title'), list) else data.get('container-title', '')
                vol = data.get('volume', '')
                issue = data.get('issue', '')
                page = data.get('page', '')
                art = data.get('article-number', '')
                pub = data.get('published-print') or data.get('published-online') or data.get('issued')
                year = pub['date-parts'][0][0] if pub else ''
                doi = data.get('DOI', '')
                
                lines = [
                    f"Source: {item['url']}",
                    f"Title: {title}",
                    f"Authors: {authors}",
                    f"Journal: {container}",
                    f"Volume: {vol}",
                    f"Issue: {issue}",
                    f"Page: {page or art}",
                    f"Year: {year}",
                    f"DOI: {doi}",
                    "",
                    "--- RAW JSON ---",
                    json.dumps(data, indent=2)
                ]
                out_file.write_text('\n'.join(lines), encoding='utf-8')
            else:
                out_file.write_text(f"Source: {item['url']}\n\n" + content, encoding='utf-8')
            print(f"  Saved {out_file} ({out_file.stat().st_size} bytes)")
    except Exception as e:
        print(f"  ERROR for {key}: {e}")
