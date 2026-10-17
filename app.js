'use strict';
(() => {
  const units = window.COURSE_UNITS;
  const book = window.BOOK_INDEX;
  const videos = window.COURSE_VIDEOS || {};
  const mediaURL=(path,file)=>path+'/'+file+'?v=20261017-final';
  const unitURL = id => `lesson.html?unit=${id}&v=20261017-final`;
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => {const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
  const link = (label, href, cls='') => {const a=el('a',cls,label);a.href=href;return a;};
  const sourceURL = (from,to,unit) => `material.html?from=${from}&to=${to}${unit?'&unit='+unit:''}#p${String(from).padStart(4,'0')}`;
  const locationLabel = (a,b) => `مواضع المصدر ${a} إلى ${b}`;
  if (!Array.isArray(units)||!book) {const node=$('lesson-content')||$('unit-list');if(node)node.append(el('p','error','تعذر تحميل بيانات الوحدات. أعد تحميل الصفحة.'));return;}
  if(document.body.dataset.page==='home'){
    $('paragraph-count').textContent=book.paragraphCount;
    units.forEach(u=>{
      const row=el('article','unit-row');
      if(videos[u.id]?.status==='ready'){
        const cover=link('',unitURL(u.id),'unit-cover');cover.setAttribute('aria-label','شاهد '+u.title);
        const poster=el('img');poster.src=mediaURL(videos[u.id].path,'poster.jpg');poster.alt='مشهد من شرح '+u.title;poster.width=1920;poster.height=1080;poster.loading='lazy';
        const play=el('span','cover-play','▶');play.setAttribute('aria-hidden','true');const duration=el('span','cover-time','20:00');duration.dir='ltr';cover.append(poster,play,duration);row.append(cover);
      }
      row.append(el('span','unit-number',String(u.id).padStart(2,'0')));
      const body=el('div');body.append(el('h3','',u.title),el('p','',u.subtitle));
      const meta=el('div','unit-meta');meta.append(el('span','tag',videos[u.id]?.status==='ready'?'فيديو 20:00 متاح':u.format==='video'?'قراءات الفيديو متاحة':'وحدة قرائية مقترحة'));
      meta.append(el('span','tag warm',`${u.readings.length} مقاطع أساسية`));body.append(meta);row.append(body,link('افتح الوحدة',unitURL(u.id),'button'));$('unit-list').append(row);
    });
    const ready=Object.values(videos).filter(v=>v.status==='ready').length;
    if($('media-status'))$('media-status').textContent=ready===units.length?'الفيديوهات السبعة متاحة للمشاهدة والتنزيل، بمدة 20:00 دقيقة لكل ملف، مع ترجمة عربية ونص مكتوب وفصول زمنية. أسئلة التحليل والقراءات متاحة للتدريب الذاتي.':ready?`${ready} من الفيديوهات متاح للمشاهدة والتنزيل. القراءات وأسئلة التحليل متاحة لجميع الوحدات.`:'القراءات وأسئلة التحليل متاحة الآن، ويجري إعداد الفيديوهات كملفات مستقلة.';
    const mappings=[[1,2,3],[4,5,6],[7],[7],[7]];
    book.parts.forEach((part,i)=>{const row=el('tr');row.append(el('th','',part.title));row.firstChild.scope='row';const cell=el('td');mappings[i].forEach(n=>cell.append(link('الوحدة '+n,unitURL(n))));row.append(cell);const src=el('td');src.append(link('اقرأ الباب',sourceURL(part.p,part.end)));row.append(src);$('coverage-rows').append(row);});
    return;
  }
  const requested=new URLSearchParams(location.search).get('unit');
  const id=requested===null?1:Number(requested);
  const u=units.find(x=>x.id===id);
  if(!u){$('lesson-content').append(el('h1','','الوحدة غير موجودة'),link('العودة إلى المسار','index.html#units','button'));return;}
  document.title=u.title+' | التنفيذ الجبري';$('crumb').textContent=u.title;
  units.forEach(item=>{const a=link(`${item.id}. ${item.title}`,unitURL(item.id),item.id===id?'active':'');if(item.id===id)a.setAttribute('aria-current','page');$('lesson-navigation').append(a);});
  const root=$('lesson-content');
  const intro=el('header','lesson-intro');intro.append(el('span','tag',`الوحدة ${id} · ${u.supplementary?'محاضرة مكملة':'محاضرة أساسية'}`),el('h1','',u.title),el('p','lead',u.overview));root.append(intro);
  const contents=el('nav','lesson-contents');contents.setAttribute('aria-label','محتويات الوحدة');
  for(const [target,title,number] of [['lecture','شاهد الشرح','01'],['readings','اقرأ المادة','02'],['questions','حلّل وأجب','03'],['notes','دوّن ملاحظاتك','04']]){
    if(target==='lecture'&&videos[id]?.status!=='ready')continue;
    const a=link('',`#${target}`);const n=el('span','',number);n.setAttribute('aria-hidden','true');a.append(n,document.createTextNode(title));contents.append(a);
  }
  root.append(contents);
  const lecture=videos[id];
  if(lecture?.status==='ready'){
    const sec=el('section','lecture-player');sec.id='lecture';sec.setAttribute('aria-label','فيديو الوحدة');
    const heading=el('div','video-heading');heading.append(el('h2','','شاهد شرح الوحدة'),el('span','tag warm','20:00 دقيقة · 1080p'));sec.append(heading);
    const video=el('video');video.id='lecture-video';video.controls=true;video.preload='metadata';video.playsInline=true;video.poster=mediaURL(lecture.path,'poster.jpg');video.setAttribute('aria-label','شرح '+u.title);
    const source=el('source');source.src=mediaURL(lecture.path,'lecture.mp4');source.type='video/mp4';video.append(source);
    const captions=el('track');captions.kind='captions';captions.src=mediaURL(lecture.path,'captions.vtt');captions.srclang='ar';captions.label='العربية';captions.default=true;video.append(captions);
    const chaptersTrack=el('track');chaptersTrack.kind='chapters';chaptersTrack.src=mediaURL(lecture.path,'chapters.vtt');chaptersTrack.srclang='ar';chaptersTrack.label='فصول الفيديو';video.append(chaptersTrack);
    video.append(document.createTextNode('يمكنك فتح ملف الفيديو من رابط التنزيل أدناه.'));sec.append(video);
    const message=el('p','fine','ملف فيديو جاهز مع ترجمة عربية قابلة للتشغيل من زر الترجمة. ظهور مرئي مع تحريك الشفاه بالذكاء الاصطناعي، وتعليق صوتي عربي اصطناعي.');message.setAttribute('role','status');sec.append(message);
    video.addEventListener('error',()=>{message.textContent='تعذر تشغيل الفيديو في هذا المتصفح. استخدم رابط ملف MP4 أدناه لفتحه في مشغل آخر.';});
    const downloads=el('div','video-downloads');const mp4=link(`تنزيل الفيديو · ${(lecture.fileBytes/1000000).toFixed(1)} MB`,mediaURL(lecture.path,'lecture.mp4'),'button small primary');mp4.download=`execution-law-unit-${String(id).padStart(2,'0')}.mp4`;
    downloads.append(mp4,link('النص المكتوب',mediaURL(lecture.path,'transcript.txt'),'button small'),link('ترجمة SRT',mediaURL(lecture.path,'captions.srt'),'button small'));sec.append(downloads);
    const chapters=el('details','more video-chapters');chapters.append(el('summary','','انتقل إلى فصل داخل الفيديو'));const list=el('div','chapter-list');
    for(const chapter of lecture.chapters){const b=el('button','chapter-button');b.type='button';const stamp=el('span','chapter-time',`${Math.floor(chapter.start/60).toString().padStart(2,'0')}:${Math.floor(chapter.start%60).toString().padStart(2,'0')}`);stamp.dir='ltr';b.append(stamp,el('span','',chapter.title));b.addEventListener('click',()=>{const seek=()=>{video.currentTime=Math.min(chapter.start,Math.max(0,video.duration-.1));video.focus();};if(video.readyState)seek();else{video.addEventListener('loadedmetadata',seek,{once:true});video.load();}video.scrollIntoView({behavior:'auto',block:'center'});});list.append(b);}
    chapters.append(list);sec.append(chapters);root.append(sec);
  }
  if(u.supplementary)root.append(el('p','notice','محاضرة مكملة للمسار الأساسي، تجمع شرح الفيديو والقراءات الأصلية وأسئلة التحليل. ارجع إلى النص عند دراسة الشروط والمواعيد.'));
  const goals=el('section','block');goals.append(el('p','eyebrow','في هذه الوحدة تتدرب على'),el('h2','','أهداف التعلم المقترحة'));const ul=el('ul','objectives');u.objectives.forEach(t=>ul.append(el('li','',t)));goals.append(ul);root.append(goals);
  const topics=el('section','block');topics.append(el('h2','','محاور القراءة والتحليل'));u.topics.forEach(t=>{const item=el('article','topic');item.append(el('h3','',t.title),el('p','',t.text),link('الرجوع إلى النص الذي يقوم عليه هذا المحور',sourceURL(t.from,t.to,id),'source-link'));topics.append(item);});root.append(topics);
  function readingGroup(title,arr,folded=false){if(!arr.length)return;const sec=el(folded?'details':'section',folded?'more':'block');if(!folded)sec.id='readings';sec.append(el(folded?'summary':'h2','',title));const list=el('div','readings');arr.forEach(r=>{const item=el('article','reading');const body=el('div');body.append(el('h3','',r.title));if(r.focus)body.append(el('p','',r.focus));body.append(el('p','locator',locationLabel(r.from,r.to)));item.append(body,link('اقرأ النص',sourceURL(r.from,r.to,id),'button small'));list.append(item);});sec.append(list);root.append(sec);}
  readingGroup('القراءات الأساسية',u.readings);readingGroup('قراءات تمهيدية ومكملة',u.supporting,true);readingGroup('مسارات التوسع في المرجع',u.extensions,true);
  const q=el('section','block');q.id='questions';q.append(el('p','eyebrow','تدريب على بناء الإجابة من المصدر'),el('h2','','أسئلة التحليل الذاتي'),el('p','muted','دوّن إجابتك مع موضع الاستناد من الكتاب. هذه أسئلة قراءة ومناقشة، وليست اختباراً يرصد درجات أو يمنح اجتيازاً.'));
  u.questions.forEach((item,i)=>{const p=el('article','prompt');p.append(el('h3','',`سؤال ${i+1}`),el('p','',item.text),link('النص المرجعي للسؤال',sourceURL(item.from,item.to,id),'source-link'));q.append(p);});root.append(q);
  const notes=el('section','block');notes.id='notes';notes.append(el('h2','','دفتر القراءة'));const label=el('label','note-label','ملاحظاتك وإحالاتك إلى الكتاب');label.htmlFor='reading-notes';const field=el('textarea');field.id='reading-notes';field.placeholder='اكتب الفكرة، والتمييز القانوني، وموضع استنادك في النص…';const status=el('p','note-status');status.setAttribute('role','status');const key=`execution-law-course:reading:v1:unit-${id}`;
  try{field.value=localStorage.getItem(key)||'';status.textContent='ملاحظاتك محفوظة على هذا المتصفح فقط، ويمكنك الرجوع إليها أثناء المراجعة.';}catch{status.textContent='الحفظ المحلي غير متاح في هذا المتصفح. يمكنك نسخ ملاحظاتك يدوياً.';}
  field.addEventListener('input',()=>{try{localStorage.setItem(key,field.value);status.textContent='حُفظت الملاحظات على هذا المتصفح فقط.';}catch{status.textContent='تعذر الحفظ؛ انسخ ملاحظاتك قبل مغادرة الصفحة.';}});
  notes.append(label,field,status);root.append(notes);
  const bridge=el('section','notice');bridge.append(el('p','',u.bridge));root.append(bridge);
  if(u.format==='video'&&!lecture)root.append(el('p','fine','الفيديو قيد الإعداد؛ القراءات المرتبطة بهذه الوحدة متاحة الآن.'));
  const next=el('nav','next-row');next.setAttribute('aria-label','الانتقال بين الوحدات');if(id>1)next.append(link('الوحدة السابقة',unitURL(id-1),'button'));else next.append(link('المسار الكامل','index.html#units','button'));if(id<units.length)next.append(link('الوحدة التالية',unitURL(id+1),'button primary'));else next.append(link('العودة إلى المرجع الكامل','material.html','button primary'));root.append(next);
})();
