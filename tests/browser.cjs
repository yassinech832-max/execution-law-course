'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const base = process.env.COURSE_TEST_URL || 'http://127.0.0.1:8765/';
const output = process.env.COURSE_TEST_OUTPUT || path.resolve(__dirname, '../test-results');
const url = p => new URL(p, base).href;

(async () => {
  fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext({viewport: {width: 1360, height: 1000}, reducedMotion: 'reduce'});
  const page = await context.newPage();
  const errors = [];
  let stage = 'home desktop';
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);});
  const noOverflow = async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Page overflow: ${page.url()}`);
  try {
    await page.goto(url('index.html'));
    await page.locator('.unit-row').last().waitFor();
    assert.equal(await page.locator('.unit-row').count(), 7);
    assert.equal(await page.locator('#coverage-rows tr').count(), 5);
    await noOverflow();
    await page.screenshot({path: path.join(output, 'home-desktop.png'), fullPage: true});

    const readingLinks = new Set();
    let testedVideos=0;
    for (let unit = 1; unit <= 7; unit++) {
      stage = `unit ${unit} desktop`;
      await page.goto(url(`lesson.html?unit=${unit}`));
      await page.locator('.lesson-intro h1').waitFor();
      assert.equal(await page.locator('.prompt').count(), 3);
      assert.equal(await page.locator('.objectives li').count(), 4);
      assert.equal(await page.locator('[aria-current="page"]').count(), 1);
      assert.equal(new URL(await page.locator('[aria-current="page"]').getAttribute('href'),base).searchParams.get('unit'),String(unit));
      const links = await page.locator('a[href^="material.html?from="]').evaluateAll(nodes => nodes.map(n => n.href));
      links.forEach(link => readingLinks.add(link));
      const hasVideo=await page.evaluate(id=>window.COURSE_VIDEOS?.[id]?.status==='ready',unit);
      if(hasVideo){
        stage=`unit ${unit} video metadata`;
        await page.waitForFunction(()=>document.getElementById('lecture-video').readyState>=1,null,{timeout:30000});
        assert.equal(await page.locator('#lecture-video').evaluate(v=>v.duration),1200);
        assert.equal(await page.locator('#lecture-video').evaluate(v=>v.videoWidth),1920);
        const captions=page.locator('#lecture-video track[kind=captions]');
        assert.equal(await captions.getAttribute('srclang'),'ar');
        await page.waitForFunction(()=>document.querySelector('track[kind=captions]').readyState===2);
        assert.ok(await page.locator('#lecture-video').evaluate(v=>v.textTracks[0].cues.length)>100);
        await page.locator('.video-chapters summary').click();
        await page.locator('.chapter-button').nth(1).click();
        const expected=await page.evaluate(id=>window.COURSE_VIDEOS[id].chapters[1].start,unit);
        await page.waitForFunction(expected=>{const v=document.getElementById('lecture-video');return !v.seeking&&Math.abs(v.currentTime-expected)<.3;},expected,{timeout:20000});
        await page.locator('#lecture-video').evaluate(async v=>{v.muted=true;await v.play();});
        await page.waitForFunction(start=>document.getElementById('lecture-video').currentTime>start+.1,expected);
        await page.locator('#lecture-video').evaluate(v=>v.pause());
        testedVideos++;
      }
      await noOverflow();
      if (unit === 1) {
        await page.locator('#reading-notes').fill('ملاحظة اختبار · موضع المصدر 34');
        await page.reload();
        assert.equal(await page.locator('#reading-notes').inputValue(), 'ملاحظة اختبار · موضع المصدر 34');
        await page.screenshot({path: path.join(output, 'unit-1-desktop.png'), fullPage: true});
      }
    }

    // Exercise every distinct educational source link, including both endpoints.
    for (const href of readingLinks) {
      stage = `source ${new URL(href).search}`;
      const target = new URL(href), from = Number(target.searchParams.get('from')), to = Number(target.searchParams.get('to'));
      await page.goto(href);
      await page.locator(`#p${String(from).padStart(4, '0')}`).waitFor();
      const first = await page.locator('.source-paragraph').first().getAttribute('id');
      assert.equal(first, `p${String(from).padStart(4, '0')}`);
      assert.ok((await page.locator('#reading-range').innerText()).includes(String(to)));
      await page.goto(href.replace(/#.*$/, '') + `#p${String(to).padStart(4, '0')}`);
      await page.locator(`#p${String(to).padStart(4, '0')}`).waitFor();
      assert.equal(await page.locator('.source-paragraph').last().getAttribute('id'), `p${String(to).padStart(4, '0')}`);
    }

    // Traverse all reader pages and compare the rendered text to the complete source.
    stage = 'complete source reader';
    await page.goto(url('material.html'));
    const rendered = [];
    for (;;) {
      const records = await page.locator('.source-paragraph').evaluateAll(nodes => nodes.map(n => ({id: n.id, text: n.lastElementChild.textContent})));
      rendered.push(...records);
      const next = page.locator('#pager-top button').last();
      if (await next.isDisabled()) break;
      const previousFirst = records[0].id;
      await next.click();
      await page.waitForFunction(id => document.querySelector('.source-paragraph').id !== id, previousFirst);
    }
    assert.equal(rendered.length, 1920);
    const original = await page.evaluate(() => window.EXECUTION_MATERIAL.map(p => p.text));
    assert.deepEqual(rendered.map(p => p.text), original);
    assert.equal(rendered[1919].id, 'p1920');

    // Arabic normalization, empty results, range reset, and deep links.
    stage = 'search and deep links';
    await page.goto(url('material.html?from=471&to=539&unit=2#p0520'));
    await page.locator('#p0520').waitFor();
    assert.equal(new URL(await page.locator('#reader-return a').getAttribute('href'),base).searchParams.get('unit'),'2');
    await page.locator('#search').fill('صيغة');
    await page.locator('#search-form button[type=submit]').click();
    assert.ok(await page.locator('.source-paragraph').count() > 0);
    await page.locator('#search').fill('عبارةاختبارلاتوجد1234567');
    await page.locator('#search-form button[type=submit]').click();
    assert.equal(await page.locator('.source-paragraph').count(), 0);
    assert.ok(await page.locator('.empty').isVisible());
    await page.locator('#reset-reader').click();
    assert.equal(await page.locator('.source-paragraph').count(), 45);
    const counts = [];
    for (const word of ['إجراءات', 'اجراءات']) {
      await page.locator('#search').fill(word);
      await page.locator('#search-form button[type=submit]').click();
      counts.push(await page.locator('#search-status').innerText());
    }
    assert.equal(counts[0], counts[1]);
    assert.match(counts[0], /^[1-9]/);
    await page.goto(url('material.html#p1920'));
    await page.locator('#p1920').waitFor();
    await page.goto(url('material.html?from=539&to=520&page=999'));
    assert.equal(await page.locator('.source-paragraph').count(), 20);
    await page.goto(url('lesson.html?unit=999'));
    assert.match(await page.locator('h1').innerText(), /غير موجودة/);

    for (const width of [390, 768]) {
      await page.setViewportSize({width, height: 844});
      for (const [label, route] of [['home', 'index.html'], ['unit-4', 'lesson.html?unit=4'], ['reader', 'material.html?from=1201&to=1227#p1201']]) {
        stage = `${label} width ${width}`;
        await page.goto(url(route));
        await noOverflow();
        await page.screenshot({path: path.join(output, `${label}-${width}.png`), fullPage: true});
      }
    }
    stage = 'runtime errors';
    assert.deepEqual(errors, []);
    const report = {status: 'PASS', units: 7, questions: 21, videoFiles: testedVideos, sourceLinkDestinations: readingLinks.size,
      renderedSourceParagraphs: rendered.length, testedViewportWidths: [1360, 768, 390], consoleErrors: errors.length};
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify({status: 'FAIL', stage, error: error.message, stack: error.stack}, null, 2));
    await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true}).catch(() => {});
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
