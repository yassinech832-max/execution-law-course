'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const context = {window: {}};
vm.createContext(context);
for (const file of ['book-index.js', 'course-data.js', ...Array.from({length: 6}, (_, i) => `material-0${i + 1}.js`)]) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context, {filename: file});
}
const {COURSE_UNITS: units, BOOK_INDEX: book, EXECUTION_MATERIAL: paragraphs} = context.window;
assert.equal(units.length, 7);
assert.equal(units.filter(u => u.format === 'video').length, 5);
assert.equal(units.filter(u => u.format === 'reading' && u.proposed).length, 2);
assert.equal(book.parts.length, 5);
assert.equal(paragraphs.length, book.paragraphCount);
assert.equal(book.paragraphCount, 1920);
assert.equal(crypto.createHash('sha256').update(paragraphs.map(p => p.text).join('\n')).digest('hex'), book.textSha256);
const covered = new Set();
let references = 0;
for (const [index, unit] of units.entries()) {
  assert.equal(unit.id, index + 1);
  assert.equal(unit.objectives.length, 4);
  assert.equal(unit.questions.length, 3);
  assert.equal(unit.topics.length, 3);
  assert.ok(unit.overview && unit.bridge && unit.readings.length >= 3);
  for (const range of [...unit.topics, ...unit.readings, ...unit.supporting, ...unit.extensions, ...unit.questions]) {
    assert.ok(Number.isInteger(range.from) && Number.isInteger(range.to));
    assert.ok(range.from >= book.bodyStart && range.to <= book.bodyEnd && range.from <= range.to,
      `Invalid source reference in unit ${unit.id}: ${range.from}–${range.to}`);
    assert.ok(paragraphs[range.from - 1].text && paragraphs[range.to - 1].text);
    references++;
  }
  for (const range of [...unit.readings, ...unit.supporting, ...unit.extensions]) {
    for (let n = range.from; n <= range.to; n++) covered.add(n);
  }
}
const uncovered = [];
for (let n = book.bodyStart; n <= book.bodyEnd; n++) if (!covered.has(n)) uncovered.push(n);
assert.deepEqual(uncovered, [], 'Every body paragraph must be reachable from a unit reading');
assert.equal(paragraphs[book.referenceStart - 1].text, 'قائمة المراجع');
assert.equal(paragraphs[book.tocStart - 1].text, 'الفهرس');
for (const heading of book.headings) {
  assert.equal(heading.title, paragraphs[heading.p - 1].text);
  assert.ok(heading.end >= heading.p && heading.end < book.tocStart);
}
for (const file of ['index.html', 'lesson.html', 'material.html']) {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  assert.match(html, /lang="ar" dir="rtl"/);
  for (const [, target] of html.matchAll(/(?:src|href)="([^"#?]+)(?:[?#][^"]*)?"/g)) {
    if (!target.includes(':')) assert.ok(fs.existsSync(path.join(root, target)), `${file}: missing ${target}`);
  }
}
console.log(JSON.stringify({units: units.length, paragraphs: paragraphs.length, sourceReferences: references,
  coveredBodyParagraphs: covered.size, sourceTextSha256: book.textSha256, status: 'PASS'}, null, 2));
