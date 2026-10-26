import {chromium} from '../../avatar3d-runtime/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';import {spawn,execFileSync} from 'node:child_process';import {once} from 'node:events';
const ROOT=process.cwd(),n=Number(process.env.VIDEO_UNIT),DIR=path.join(ROOT,`rendered-3d/unit-${String(n).padStart(2,'0')}`),WORK=path.join(DIR,'work');
const data=JSON.parse(fs.readFileSync(path.join(ROOT,'avatar3d-output/runtime/performance.json'),'utf8'));
async function status(text,state='pending'){const r=await fetch(`https://api.github.com/repos/${process.env.GITHUB_REPOSITORY}/statuses/${process.env.GITHUB_SHA}`,{method:'POST',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,'Content-Type':'application/json'},body:JSON.stringify({state,context:`course/avatar3d-${n}`,description:text.slice(0,140)})});if(!r.ok)console.log('Status update unavailable',r.status);}
const server=spawn('python3',['-m','http.server','8787','--bind','127.0.0.1','--directory',ROOT],{stdio:'ignore'});let browser,encoder;
try{
 for(let i=0;i<50;i++){try{await fetch('http://127.0.0.1:8787/video-production/avatar3d/actor.html');break;}catch{await new Promise(r=>setTimeout(r,200));}}
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:640,height:884},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:8787/video-production/avatar3d/actor.html');await page.waitForFunction(()=>window.ready===true,null,{timeout:120000});
 const meta=await page.evaluate(()=>window.avatarMetadata);
 if(meta.bones<20||meta.morphTargets<10||Object.entries(meta.visemeMapping).some(([code,names])=>code!=='X'&&!names.length))throw Error('Incomplete 3D professor rig');
 const evidence=[];let frames=0;const total=data.appearances.reduce((v,s)=>v+Math.round(s.seconds*25),0);
 for(const [i,segment] of data.appearances.entries()){
  await status(`Animating the approved 3D professor: appearance ${i+1}/${data.appearances.length}`);
  const destination=path.join(WORK,`actor-${i}.mp4`),err=fs.openSync(path.join(WORK,`encoder-${i}.log`),'w');
  encoder=spawn('ffmpeg',['-v','warning','-y','-f','image2pipe','-vcodec','mjpeg','-framerate','25','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-g','25','-pix_fmt','yuv420p','-threads','2',destination],{stdio:['pipe','ignore',err]});const completion=once(encoder,'exit');
  for(let frame=0;frame<Math.round(segment.seconds*25);frame++){
   const t=segment.offset+frame/25,proof=await page.evaluate(t=>window.setFrame(t),t);
   const jpeg=await page.screenshot({type:'jpeg',quality:93});if(!encoder.stdin.write(jpeg))await once(encoder.stdin,'drain');frames++;
   if(frame===50){fs.writeFileSync(path.join(WORK,`actor-proof-${i}.jpg`),jpeg);evidence.push({...proof,appearance:i,lessonTime:segment.start+frame/25});}
   if(frames%250===0){console.log('FRAME',frames,'/',total);await status(`Rendering 3D appearances: ${frames}/${total} frames`);}
  }
  encoder.stdin.end();const [code]=await completion;fs.closeSync(err);encoder=null;if(code!==0)throw Error(`Appearance ${i} encoding failed`);
 }
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(DIR,'avatar-evidence.json'),JSON.stringify({...meta,appearances:data.appearances,renderedFrames:frames,mouthCues:JSON.parse(fs.readFileSync('avatar3d-output/runtime/mouth.json','utf8')).mouthCues.length,frameEvidence:evidence},null,2));
 await browser.close();server.kill();
}catch(e){if(encoder)encoder.kill();if(browser)await browser.close();server.kill();throw e;}
