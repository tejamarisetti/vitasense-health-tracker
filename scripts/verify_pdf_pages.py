import pymupdf
import os

pdf_path = os.path.join(os.path.dirname(__file__), '..', 'paper', 'conference_paper.pdf')
doc = pymupdf.open(pdf_path)
print('=== PDF SUMMARY ===')
print(f'Total pages: {len(doc)}')

# 1. Render pages to 150 dpi PNG
out_dir = os.path.join(os.path.dirname(__file__), '..', 'paper', 'paper_pages_png')
os.makedirs(out_dir, exist_ok=True)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    img_path = os.path.join(out_dir, f'page_{i+1}.png')
    pix.save(img_path)
    print(f'Saved {img_path} ({pix.width}x{pix.height})')

# 2. Check text blocks for overlaps and margin violations
# US Letter: width=612, height=792.
# Margin bounds for IEEEtran: left >= 36 pt, right <= 576 pt, top >= 36 pt, bottom <= 756 pt
LEFT_MARGIN = 36.0
RIGHT_MARGIN = 576.0
TOP_MARGIN = 36.0
BOTTOM_MARGIN = 756.0

total_overlaps = 0
out_of_margin_count = 0

for i, page in enumerate(doc):
    print(f'\n--- Checking Page {i+1} ---')
    blocks = page.get_text('blocks')
    # Filter text blocks (block type == 0) with non-whitespace text
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    
    # Check margins
    for idx, b in enumerate(text_blocks):
        x0, y0, x1, y1 = b[:4]
        text_snippet = b[4].replace('\n', ' ')[:40]
        if x0 < LEFT_MARGIN - 2:
            print(f'  [Out of margin - Left] Block {idx} ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}): {text_snippet}')
            out_of_margin_count += 1
        if x1 > RIGHT_MARGIN + 2:
            print(f'  [Out of margin - Right] Block {idx} ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}): {text_snippet}')
            out_of_margin_count += 1
        if y0 < TOP_MARGIN - 2:
            print(f'  [Out of margin - Top] Block {idx} ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}): {text_snippet}')
            out_of_margin_count += 1
        if y1 > BOTTOM_MARGIN + 2:
            print(f'  [Out of margin - Bottom] Block {idx} ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}): {text_snippet}')
            out_of_margin_count += 1
            
    # Check pairwise overlaps between text blocks on the same page
    page_overlaps = 0
    for j in range(len(text_blocks)):
        for k in range(j + 1, len(text_blocks)):
            b1 = text_blocks[j]
            b2 = text_blocks[k]
            # Compute intersection rect
            ix0 = max(b1[0], b2[0])
            iy0 = max(b1[1], b2[1])
            ix1 = min(b1[2], b2[2])
            iy1 = min(b1[3], b2[3])
            
            # Substantial intersection (> 1pt in both dims)
            if ix1 > ix0 + 1.0 and iy1 > iy0 + 1.0:
                t1 = b1[4].replace('\n', ' ')[:40].encode('ascii', errors='replace').decode('ascii')
                t2 = b2[4].replace('\n', ' ')[:40].encode('ascii', errors='replace').decode('ascii')
                print(f'  [OVERLAP] Block {j} & Block {k}: intersection ({ix0:.1f}, {iy0:.1f}, {ix1:.1f}, {iy1:.1f})')
                print(f'    Block {j}: "{t1}"')
                print(f'    Block {k}: "{t2}"')
                page_overlaps += 1
                total_overlaps += 1
    if page_overlaps == 0:
        print(f'  Page {i+1}: 0 text block overlaps.')

print(f'\n=== FINAL REPORT ===')
print(f'Total Overlaps: {total_overlaps}')
print(f'Out of margin blocks: {out_of_margin_count}')
