import {chromium} from '../avatar3d-runtime/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';import {spawn,execFileSync} from 'node:child_process';import {once} from 'node:events';import crypto from 'node:crypto';
const ROOT=process.cwd(),OUT=path.join(ROOT,'avatar3d-output/rendered'),INPUT=path.join(ROOT,'avatar3d-output/runtime');fs.mkdirSync(OUT,{recursive:true});
function status(description,state='pending'){if(!process.env.GITHUB_TOKEN)return Promise.resolve();return fetch(`https://api.github.com/repos/${process.env.GITHUB_REPOSITORY}/statuses/${process.env.GITHUB_SHA}`,{method:'POST',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,'Content-Type':'application/json'},body:JSON.stringify({state,context:'avatar3d/render',description:description.slice(0,140)})}).catch(()=>{});}
const server=spawn('python3',['-m','http.server','8787','--bind','127.0.0.1','--directory',ROOT],{stdio:'ignore'});let browser,encoder;
try{
 for(let i=0;i<50;i++){try{await fetch('http://127.0.0.1:8787/avatar3d-trial-20261026/viewer.html');break;}catch{await new Promise(r=>setTimeout(r,200));}}
 await status('Loading the real rigged 3D professor and animated lesson scenes');
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.stack||e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('http://127.0.0.1:8787/avatar3d-trial-20261026/viewer.html');await page.waitForFunction(()=>window.ready===true,null,{timeout:120000});
 const meta=await page.evaluate(()=>window.avatarMetadata);fs.writeFileSync(path.join(OUT,'avatar-metadata.json'),JSON.stringify(meta,null,2));
 if(meta.bones<20||meta.vertices<1000||meta.morphNames.length<8)throw Error('Character does not provide a complete 3D rig and facial controls');
 if(Object.entries(meta.visemeMapping).some(([code,names])=>code!=='X'&&!names.length))throw Error('Incomplete phonetic mouth-shape mapping');
 const evidence=[];for(const t of [3,18,34,46,64,82]){evidence.push(await page.evaluate(t=>window.setFrame(t),t));await page.screenshot({path:path.join(OUT,`probe-${String(t).padStart(2,'0')}.jpg`),type:'jpeg',quality:90});}
 fs.writeFileSync(path.join(OUT,'student-visible.txt'),await page.locator('body').innerText());
 fs.writeFileSync(path.join(OUT,'probe-report.json'),JSON.stringify({status:'PROBE',true3D:true,metadata:meta,evidence,errors},null,2));
 execFileSync('python3',['avatar3d-trial-20261026/retain.py'],{cwd:ROOT,stdio:'inherit'});
 const config=JSON.parse(fs.readFileSync('avatar3d-trial-20261026/render-config.json','utf8'));
 if(config.mode==='probe'){await status('3D preview frames ready for visual review','success');await browser.close();server.kill();process.exit(0);}
 if(errors.length)throw Error(errors.join('\n'));
 const target=path.join(OUT,'professor-3d-90s.mp4');const err=fs.openSync(path.join(OUT,'encoder.log'),'w');
 encoder=spawn('ffmpeg',['-v','warning','-y','-f','image2pipe','-vcodec','mjpeg','-framerate','25','-i','pipe:0','-i',path.join(INPUT,'narration.wav'),'-i',path.join(INPUT,'captions.srt'),'-map','0:v:0','-map','1:a:0','-map','2:s:0','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000','-c:s','mov_text','-metadata:s:s:0','language=ara','-metadata:s:s:0','title=العربية','-metadata:s:a:0','language=ara','-metadata','copyright=3D model: Copyright (c) 2020 Microsoft; MIT License','-metadata','comment='+fs.readFileSync(path.join(INPUT,'THIRD_PARTY_LICENSE.txt'),'utf8'),'-movflags','+faststart','-t','90','-threads','2',target],{stdio:['pipe','ignore',err]});
 const completion=once(encoder,'exit');const started=Date.now();
 for(let i=0;i<2250;i++){await page.evaluate(t=>window.setFrame(t),i/25);const frame=await page.screenshot({type:'jpeg',quality:93});if(!encoder.stdin.write(frame))await once(encoder.stdin,'drain');if(i%250===0){console.log('FRAME',i,'/2250 elapsed',Math.round((Date.now()-started)/1000));await status(`Rendering the independent 3D lesson: ${i}/2250 frames`);}}
 encoder.stdin.end();const [code]=await completion;fs.closeSync(err);if(code!==0)throw Error('Video encoding failed with exit '+code);
 const info=JSON.parse(execFileSync('ffprobe',['-v','error','-show_format','-show_streams','-of','json',target],{encoding:'utf8'}));const v=info.streams.find(s=>s.codec_type==='video'),a=info.streams.find(s=>s.codec_type==='audio');
 if(Number(info.format.duration)!==90||v.width!==1920||v.height!==1080||Number(v.nb_frames)!==2250||Math.abs(Number(a.duration)-90)>.03)throw Error('Final timing or dimensions failed');
 execFileSync('ffmpeg',['-v','error','-i',target,'-f','null','-'],{stdio:'inherit'});
 for(const name of ['captions.srt','captions.vtt','transcript.txt','THIRD_PARTY_LICENSE.txt'])fs.copyFileSync(path.join(INPUT,name),path.join(OUT,name));
 const bytes=fs.readFileSync(target),parts=[];for(let i=0;i<bytes.length;i+=700000){const name=`movie-part-${String(parts.length).padStart(3,'0')}.bin`,buffer=bytes.subarray(i,i+700000);fs.writeFileSync(path.join(OUT,name),buffer);parts.push({name,bytes:buffer.length,sha256:crypto.createHash('sha256').update(buffer).digest('hex')});}
 const report={status:'PASS',durationSeconds:90,frames:2250,resolution:[1920,1080],voice:'D',voiceId:'ar-KW-FahedNeural',true3D:true,bones:meta.bones,vertices:meta.vertices,morphTargets:meta.morphNames.length,mouthCues:JSON.parse(fs.readFileSync(path.join(INPUT,'mouth.json'),'utf8')).mouthCues.length,animations:meta.animations,frameEvidence:evidence,fileBytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),parts,sourceParagraphs:[37,38,40],decodeCheck:'PASS',livePlatformModified:false,renderSeconds:(Date.now()-started)/1000,sourceCommit:process.env.GITHUB_SHA,humanListeningReview:false};
 fs.writeFileSync(path.join(OUT,'report.json'),JSON.stringify(report,null,2));execFileSync('python3',['avatar3d-trial-20261026/retain.py'],{cwd:ROOT,stdio:'inherit'});await status('90.000-second 3D lesson ready; Arabic captions and full decode passed','success');await browser.close();server.kill();console.log(JSON.stringify(report));
}catch(e){fs.writeFileSync(path.join(OUT,'failure.json'),JSON.stringify({status:'FAIL',error:String(e),stack:e.stack},null,2));await status(String(e),'failure');try{execFileSync('python3',['avatar3d-trial-20261026/retain.py'],{cwd:ROOT,stdio:'inherit'});}catch{}if(encoder)encoder.kill();if(browser)await browser.close();server.kill();throw e;}
