'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const normalize=text=>text.normalize('NFKC').replace(/[\u064B-\u065F\u0670\u0640]/g,'').replace(/[إآٱ]/g,'أ');
const forbidden=/(?:أحمد|احمد)\s+خليل|ياسين\s+شامي|شامي\s+ياسين|لأستاذنا|للأستاذ الدكتور|عمر\s+بن\s+الخطاب|أبي\s+موسى\s+الأشعري|\b(?:COUCHEZ|LEBEAU|DELEBECQUE|VINCENT|PREVAULT)\b/iu;
const files=fs.readdirSync(root).filter(file=>/\.(?:html|js|md)$/.test(file)).map(file=>path.join(root,file));
function media(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,entry.name);if(entry.isDirectory())media(p);else if(/\.(?:txt|vtt|srt|json)$/.test(entry.name))files.push(p);}}
media(path.join(root,'media'));
for(const file of files)assert.ok(!forbidden.test(normalize(fs.readFileSync(file,'utf8'))),'Personal name found in '+path.relative(root,file));
for(let unit=1;unit<=7;unit++){
 const report=JSON.parse(fs.readFileSync(path.join(root,`media/unit-${String(unit).padStart(2,'0')}/report.json`),'utf8'));
 assert.equal(report.durationSeconds,1200);assert.equal(report.source,'مقرر التنفيذ الجبري');
 assert.equal(report.voice,'ar-SA-HamedNeural');assert.ok(report.speakingPortrait.actualNeuralPortraitSeconds>=20);
}
assert.ok(fs.existsSync(path.join(root,'assets/presenter/portrait.jpg')));
assert.ok(!fs.existsSync(path.join(root,'assets/presenter/yassine-chami.jpg')));
assert.ok(!fs.existsSync(path.join(root,'media/presenter-sample')),'The retired sample must not be published');
assert.ok(!fs.existsSync(path.join(root,'presenter.js')),'The retired player must not be published');
for(const file of ['index.html','lesson.html','material.html','app.js']){
 const text=fs.readFileSync(path.join(root,file),'utf8');
 assert.ok(!/عينة الشرح|عينة تعليمية|media\/presenter-sample|presenter\.js/.test(text),'Retired sample reference in '+file);
}
console.log(JSON.stringify({status:'PASS',identity:'course',textFiles:files.length,measuredLectures:7}));
