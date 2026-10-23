import urllib.request
import json
from pathlib import Path

dest_dir = Path("paper/verified_sources")
dest_dir.mkdir(parents=True, exist_ok=True)

refs_to_save = [
    {
        "id": "ref_zhang_troika",
        "url": "https://api.crossref.org/works/10.1109/TBME.2014.2359372",
        "type": "crossref"
    },
    {
        "id": "ref_salehizadeh_spectral",
        "url": "https://api.crossref.org/works/10.3390/s16010010",
        "type": "crossref"
    },
    {
        "id": "ref_karlen_sqi",
        "url": "https://api.crossref.org/works/10.1088/0967-3334/33/10/1617",
        "type": "crossref"
    },
    {
        "id": "ref_orphanidou_sqi",
        "url": "https://api.crossref.org/works/10.1109/JBHI.2014.2338351",
        "type": "crossref"
    },
    {
        "id": "ref_selvaraj_motion",
        "url": "https://api.crossref.org/works/10.1109/IEMBS.2011.6091232",
        "type": "crossref"
    },
    {
        "id": "ref_li_clifford_fusion",
        "url": "https://api.crossref.org/works/10.1016/j.jelectrocard.2012.07.015",
        "type": "crossref"
    },
    {
        "id": "ref_drew_alarm_fatigue",
        "url": "https://api.crossref.org/works/10.1371/journal.pone.0110274",
        "type": "crossref"
    },
    {
        "id": "ref_cvach_alarm_fatigue",
        "url": "https://api.crossref.org/works/10.2345/0899-8205-46.4.268",
        "type": "crossref"
    },
    {
        "id": "ref_clifford_challenge",
        "url": "https://api.crossref.org/works/10.1088/0967-3334/37/8/e5",
        "type": "crossref"
    },
    {
        "id": "ref_shafer_conformal",
        "url": "https://www.jmlr.org/papers/v9/shafer08a.html",
        "type": "html"
    },
    {
        "id": "ref_angelopoulos_conformal",
        "url": "https://api.crossref.org/works/10.1561/2200000101",
        "type": "crossref"
    },
    {
        "id": "ref_bent_sources",
        "url": "https://api.crossref.org/works/10.1038/s41746-020-0226-6",
        "type": "crossref"
    },
    {
        "id": "ref_perez_apple_heart",
        "url": "https://api.crossref.org/works/10.1056/NEJMoa1901183",
        "type": "crossref"
    },
    {
        "id": "ref_allen_ppg",
        "url": "https://api.crossref.org/works/10.1088/0967-3334/28/3/R01",
        "type": "crossref"
    }
]

for item in refs_to_save:
    key = item["id"]
    out_file = dest_dir / f"{key}.txt"
    print(f"Fetching {key} from {item['url']}...")
    req = urllib.request.Request(item["url"], headers={'User-Agent': 'mailto:researcher@uni.edu'})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8', errors='replace')
            if item["type"] == "crossref":
                data = json.loads(content)['message']
                # Format into readable line-by-line key-value pairs for easy audit line-matching
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
