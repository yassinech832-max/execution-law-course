'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base='https://yassinech832-max.github.io/execution-law-course/';
const output=path.resolve(__dirname,'../test-results');fs.mkdirSync(output,{recursive:true});
const source=fs.readFileSync(path.resolve(__dirname,'../app.js'),'utf8');
const sha=process.env.GITHUB_SHA;
async function status(state,description){if(!process.env.GITHUB_TOKEN)return;const r=await fetch(`https://api.github.com/repos/${process.env.GITHUB_REPOSITORY}/statuses/${sha}`,{method:'POST',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,'Content-Type':'application/json'},body:JSON.stringify({state,context:'course/public',description:description.slice(0,140)})});if(!r.ok)console.log('Could not update public status',r.status);}
(async()=>{
 let browser;
 try{
  await status('pending','Waiting for the approved 3D course deployment');
  let deployed=false;
  for(let i=0;i<24;i++){
   try{const r=await fetch(base+'app.js?v='+sha,{signal:AbortSignal.timeout(20000)});if(r.ok&&(await r.text())===source){deployed=true;break;}}catch{}
   await new Promise(r=>setTimeout(r,15000));
  }
  assert.ok(deployed,'The published site did not serve the approved release');
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1360,height:1000},reducedMotion:'reduce'});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'index.html?v='+sha);await page.locator('.unit-row').last().waitFor();
  assert.equal(await page.locator('.unit-row').count(),7);
  await page.locator('.university-feature img').evaluate(im=>im.decode());
  const lectures=[];
  for(let n=1;n<=7;n++){
   await page.goto(base+`lesson.html?unit=${n}&v=${sha}`);
   await page.waitForFunction(()=>document.getElementById('lecture-video')?.readyState>=1,null,{timeout:60000});
   const report=await page.evaluate(async n=>{const r=await fetch(`media/unit-${String(n).padStart(2,'0')}/report.json?v=20261027-avatar3d`);if(!r.ok)throw Error('Release report unavailable');return r.json();},n);
   assert.equal(report.true3D,true);assert.equal(report.originalAudioPreserved,true);assert.equal(report.durationSeconds,1200);
   const v=page.locator('#lecture-video');assert.equal(await v.evaluate(v=>v.duration),1200);
   assert.equal(await v.evaluate(v=>v.videoWidth),1920);assert.equal(await v.evaluate(v=>v.videoHeight),1080);
   await v.evaluate(async v=>{v.muted=true;v.currentTime=2;await v.play();});
   await page.waitForFunction(()=>document.getElementById('lecture-video').currentTime>2.2);
   await v.evaluate(v=>v.pause());
   await page.waitForFunction(()=>document.querySelector('track[kind=captions]').readyState===2);
   assert.ok(await v.evaluate(v=>v.textTracks[0].cues.length)>100);
   if(n===1){await v.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'public-lesson-desktop.jpg'),type:'jpeg',quality:87});}
   lectures.push({unit:n,duration:1200,playback:'PASS',true3D:report.true3D,sourceTextPreserved:report.publishedTextPreserved});
  }
  await page.setViewportSize({width:390,height:844});await page.goto(base+'lesson.html?unit=7&v='+sha);
  await page.locator('.video-wide').waitFor();await page.locator('.video-wide').click();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.locator('#lecture-video').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'public-lesson-mobile.jpg'),type:'jpeg',quality:87});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(output,'public-report.json'),JSON.stringify({status:'PASS',sourceCommit:sha,site:base,lectures,desktop:true,mobile:true,consoleErrors:0},null,2));
  await status('success','Published site verified: seven playable 20:00 3D lessons; Arabic captions; mobile and desktop');
 }catch(e){fs.writeFileSync(path.join(output,'public-report.json'),JSON.stringify({status:'FAIL',error:e.message,stack:e.stack}));await status('failure',e.message);throw e;}
 finally{if(browser)await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
