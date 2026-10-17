"""Build the source index while preserving the course edition paragraph positions."""
from pathlib import Path
from docx import Document
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'upload' / 'نسخة_التنفيذ_بدون_حواش(1).docx'
doc = Document(SOURCE)
paragraphs = doc.paragraphs
records = []
for n, para in enumerate(paragraphs, 1):
    text = ' '.join(para.text.split()).strip()
    if not text:
        continue
    records.append((n, text, para.style.name))

# Reuse the already published complete text. Fail instead of silently accepting
# a dropped paragraph, truncated upload, or a mismatched paragraph index.
original = []
for n in range(1, 7):
    path = ROOT / f'material-{n:02}.js'
    script = path.read_text(encoding='utf-8')
    original.extend(json.loads(script.split('.concat(', 1)[1].rsplit(');', 1)[0]))
assert len(original) == len(records) == 1920
assert [n for n, _, _ in records] == list(range(1, 1921))
records = [(n, item['text'], style) for item, (n, _, style) in zip(original, records)]

toc_start = next(n for n, text, style in records if text == 'الفهرس' and style == 'Heading 1')
reference_start = next(n for n, text, style in records if text == 'قائمة المراجع')
headings = []
levels = {}
for n, text, style in records:
    if style.startswith('Heading'):
        level = int(style.rsplit(' ', 1)[1])
        levels[str(n)] = level
        if n < toc_start:
            headings.append({'p': n, 'level': level, 'title': text})

# Add a source heading only when its paragraph has no heading style already.
for n, level in [(477, 5), (483, 5), (514, 5), (1290, 3)]:
    if str(n) in levels:
        continue
    levels[str(n)] = level
    headings.append({'p': n, 'level': level, 'title': records[n-1][1]})
headings.sort(key=lambda h: h['p'])
for index, heading in enumerate(headings):
    heading['end'] = next((h['p']-1 for h in headings[index+1:] if h['level'] <= heading['level']), toc_start-1)

digest = hashlib.sha256('\n'.join(t for _, t, _ in records).encode()).hexdigest()
meta = {
    'title': records[0][1], 'author': 'مقرر المادة', 'edition': 'نسخة تعليمية بهوية المقرر مع حفظ مواضع الإحالات',
    'paragraphCount': len(records), 'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'textSha256': digest, 'bodyStart': 8, 'bodyEnd': reference_start-1,
    'referenceStart': reference_start, 'tocStart': toc_start,
    'levels': levels, 'headings': headings,
    'parts': [h for h in headings if h['level'] == 1 and h['title'].startswith('الباب')],
}
(ROOT / 'book-index.js').write_text('window.BOOK_INDEX='+json.dumps(meta, ensure_ascii=False, separators=(',', ':'))+';\n', encoding='utf-8')
print(json.dumps({'paragraphs': len(records), 'parts': len(meta['parts']), 'headings': len(headings), 'textSha256': digest}, ensure_ascii=False))
