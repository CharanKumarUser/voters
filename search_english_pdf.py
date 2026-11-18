import pymupdf
import re

doc = pymupdf.open('2026-EROLLGEN-S01-175-SIR-DraftRoll-Revision1-ENG-159-WI (1).pdf')
print(f"Total pages in English PDF: {len(doc)}")

results = []
for p_no in range(len(doc)):
    text = doc[p_no].get_text()
    if 'RENUKAMMA' in text.upper() or 'MANGAMMA' in text.upper() or 'CHALAPATHI' in text.upper():
        for line in text.split('\n'):
            line_u = line.upper()
            if any(k in line_u for k in ['RENUKAMMA', 'MANGAMMA', 'CHALAPATHI']):
                results.append((p_no + 1, line.strip()))

print(f"Found {len(results)} occurrences:")
for r in results:
    print(f"Page {r[0]}: {r[1]}")
