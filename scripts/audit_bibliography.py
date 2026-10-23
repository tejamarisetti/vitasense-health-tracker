"""Audit bibliography entries against fetched raw page texts.

Reads the saved page files directly from disk and extracts the raw matched line
for each citation field (author, title, journal, year, volume/article, DOI, URL).
Prints 'NOT FOUND' for any field that cannot be extracted from the raw page text.
Contains no hard-coded status text.
"""

from pathlib import Path
import re

BASE_LOGS = Path(r"C:\Users\Master\.gemini\antigravity-ide\brain\c84ae576-da71-4751-a138-b2e1c847674a\.system_generated\steps")

def find_matched_line(lines, pattern):
    """Find the first line matching pattern, extracting the tag if line is minified HTML."""
    if not pattern:
        return None
    for line in lines:
        m = re.search(pattern, line, re.I)
        if m:
            stripped = line.strip()
            # If the raw line is a minified HTML blob, extract the enclosing tag or local snippet
            if len(stripped) > 250:
                start = stripped.rfind('<', 0, m.start())
                end = stripped.find('>', m.end())
                if start != -1 and end != -1 and (end - start) < 250:
                    return stripped[start:end+1]
                s_start = max(0, m.start() - 30)
                s_end = min(len(stripped), m.end() + 50)
                return f"... {stripped[s_start:s_end].strip()} ..."
            return stripped
    return None

def main():
    refs = [
        {
            "num": 1,
            "id": "ref_reiss_dalia",
            "citation": "A. Reiss, I. Indlekofer, P. Schmidt, and K. Van Laerhoven, 'Deep PPG: Large-scale heart rate estimation with convolutional neural networks,' Sensors, vol. 19, no. 14, p. 3079, 2019.",
            "file": BASE_LOGS / "6310" / "content.md",
            "patterns": {
                "author": r'\[Attila Reiss\]',
                "title": r'Deep PPG: Large-Scale Heart Rate Estimation',
                "journal": r'term="Sensors%20\(Basel\)"\[jour\]',
                "year": r'Collection date 2019',
                "volume/article": r'sensors-19-03079\.pdf',
                "DOI": r'10\.3390/s19143079',
                "URL": r'^Source:\s*https?://',
            }
        },
        {
            "num": 2,
            "id": "ref_elgendi_sqi",
            "citation": "M. Elgendi, 'Optimal signal quality index for photoplethysmogram signals,' Bioengineering, vol. 3, no. 4, p. 21, 2016.",
            "file": BASE_LOGS / "6370" / "content.md",
            "patterns": {
                "author": r'\[Mohamed Elgendi\]',
                "title": r'Optimal Signal Quality Index',
                "journal": r'term="Bioengineering%20\(Basel\)"\[jour\]',
                "year": r'Collection date 2016',
                "volume/article": r'bioengineering-03-00021\.pdf',
                "DOI": r'10\.3390/bioengineering3040021',
                "URL": r'^Source:\s*https?://',
            }
        },
        {
            "num": 3,
            "id": "ref_charlton_roadmap",
            "citation": "P. H. Charlton et al., 'The 2023 wearable photoplethysmography roadmap,' Physiological Measurement, vol. 44, no. 11, p. 111001, 2023, DOI: 10.1088/1361-6579/acead2.",
            "file": BASE_LOGS / "6396" / "content.md",
            "patterns": {
                "author": r'\[Peter H Charlton\]',
                "title": r'The 2023 wearable photoplethysmography roadmap',
                "journal": r'term="Physiol%20Meas"\[jour\]',
                "year": r'Issue date 2023|Collection date 2023',
                "volume/article": r'pmea_44_11_111001\.pdf',
                "DOI": r'10\.1088/1361-6579/acead2',
                "URL": r'^Source:\s*https?://',
            }
        },
        {
            "num": 4,
            "id": "ref_vazquez_conformal",
            "citation": "J. Vazquez and J. C. Facelli, 'Conformal prediction in clinical medical sciences,' Journal of Healthcare Informatics Research, 2022, DOI: 10.1007/s41666-021-00113-8.",
            "file": BASE_LOGS / "6406" / "content.md",
            "patterns": {
                "author": r'\[Janette Vazquez\]',
                "title": r'Conformal Prediction in Clinical Medical Sciences',
                "journal": r'term="J%20Healthc%20Inform%20Res"\[jour\]',
                "year": r'Collection date 2022',
                "volume/article": None,
                "DOI": r'10\.1007/s41666-021-00113-8',
                "URL": r'^Source:\s*https?://',
            }
        },
        {
            "num": 5,
            "id": "ref_uci_dalia",
            "citation": "'PPG-DaLiA,' UCI Machine Learning Repository, DOI: 10.24432/C53890, URL: https://archive.ics.uci.edu/dataset/495/ppg+dalia.",
            "file": BASE_LOGS / "455" / "content.md",
            "patterns": {
                "author": None,
                "title": r'<title>PPG-DaLiA',
                "journal": r'<title>UCI Machine Learning Repository',
                "year": None,
                "volume/article": None,
                "DOI": r'https://doi\.org/10\.24432/C53890',
                "URL": r'^Source:\s*https?://',
            }
        },
        {
            "num": 6,
            "id": "ref_physionet_wearable",
            "citation": "A. Hongn, F. Bosch, L. Prado, and P. Bonomini, 'Wearable Device Dataset from Induced Stress and Structured Exercise Sessions,' PhysioNet, Version 1.0.1, 2025, DOI: 10.13026/he0v-tf17.",
            "file": BASE_LOGS / "449" / "content.md",
            "patterns": {
                "author": r'<meta name="citation_author" content="Hongn, Andrea">',
                "title": r'<meta name="citation_title" content="Wearable Device Dataset',
                "journal": r'<meta name="citation_technical_report_institution" content="PhysioNet">',
                "year": r'<meta name="citation_publication_date" content="2025',
                "volume/article": r'Version: 1\.0\.1|version 1\.0\.1',
                "DOI": r'<meta name="citation_doi" content="10\.13026/he0v-tf17">',
                "URL": r'^Source:\s*https?://',
            }
        },
    ]

    fields = ["author", "title", "journal", "year", "volume/article", "DOI", "URL"]

    for ref in refs:
        print("=" * 80)
        print(f"REFERENCE {ref['num']}: {ref['id']}")
        print(f"File: {ref['file'].name}")
        print(f"Citation: {ref['citation']}")
        print("-" * 80)

        if not ref["file"].exists():
            print(f"FILE NOT FOUND: {ref['file']}")
            continue

        lines = ref["file"].read_text(encoding="utf-8", errors="ignore").splitlines()

        for field in fields:
            pat = ref["patterns"].get(field)
            matched = find_matched_line(lines, pat)
            if matched:
                print(f"{field:<15}: {matched}")
            else:
                print(f"{field:<15}: NOT FOUND")

if __name__ == "__main__":
    main()
