'use strict';
(() => {
  const units = window.COURSE_UNITS;
  const book = window.BOOK_INDEX;
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => {const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
  const link = (label, href, cls='') => {const a=el('a',cls,label);a.href=href;return a;};
  const sourceURL = (from,to,unit) => `material.html?from=${from}&to=${to}${unit?'&unit='+unit:''}#p${String(from).padStart(4,'0')}`;
  const locationLabel = (a,b) => `مواضع المصدر ${a} إلى ${b}`;
  if (!Array.isArray(units)||!book) {const node=$('lesson-content')||$('unit-list');if(node)node.append(el('p','error','تعذر تحميل بيانات الوحدات. أعد تحميل الصفحة.'));return;}
  if(document.body.dataset.page==='home'){
    $('paragraph-count').textContent=book.paragraphCount;
    units.forEach(u=>{
      const row=el('article','unit-row');row.append(el('span','unit-number',String(u.id).padStart(2,'0')));
      const body=el('div');body.append(el('h3','',u.title),el('p','',u.subtitle));
      const meta=el('div','unit-meta');meta.append(el('span','tag',u.format==='video'?'قراءات الفيديو متاحة':'وحدة قرائية مقترحة'));
      meta.append(el('span','tag warm',`${u.readings.length} مقاطع أساسية`));body.append(meta);row.append(body,link('افتح الوحدة',`lesson.html?unit=${u.id}`,'button'));$('unit-list').append(row);
    });
    const mappings=[[1,2,3],[4,5,6],[7],[7],[7]];
    book.parts.forEach((part,i)=>{const row=el('tr');row.append(el('th','',part.title));row.firstChild.scope='row';const cell=el('td');mappings[i].forEach(n=>cell.append(link('الوحدة '+n,`lesson.html?unit=${n}`)));row.append(cell);const src=el('td');src.append(link('اقرأ الباب',sourceURL(part.p,part.end)));row.append(src);$('coverage-rows').append(row);});
    return;
  }
  const requested=new URLSearchParams(location.search).get('unit');
  const id=requested===null?1:Number(requested);
  const u=units.find(x=>x.id===id);
  if(!u){$('lesson-content').append(el('h1','','الوحدة غير موجودة'),link('العودة إلى المسار','index.html#units','button'));return;}
  document.title=u.title+' | التنفيذ الجبري';$('crumb').textContent=u.title;
  units.forEach(item=>{const a=link(`${item.id}. ${item.title}`,`lesson.html?unit=${item.id}`,item.id===id?'active':'');if(item.id===id)a.setAttribute('aria-current','page');$('lesson-navigation').append(a);});
  const root=$('lesson-content');
  const intro=el('header','lesson-intro');intro.append(el('span','tag',`الوحدة ${id} · ${u.format==='video'?'من المحاضرات الخمس':'قراءة مقترحة'}`),el('h1','',u.title),el('p','lead',u.overview));root.append(intro);
  if(u.proposed)root.append(el('p','notice','موضوع هذه المحاضرة القرائية مقترح لتنظيم المسار؛ لم تحدد خطة المشروع المرفقة موضوعي المحاضرتين القرائيتين.'));
  const goals=el('section','block');goals.append(el('p','eyebrow','في هذه الوحدة تتدرب على'),el('h2','','أهداف التعلم المقترحة'));const ul=el('ul','objectives');u.objectives.forEach(t=>ul.append(el('li','',t)));goals.append(ul);root.append(goals);
  const topics=el('section','block');topics.append(el('h2','','محاور القراءة والتحليل'));u.topics.forEach(t=>{const item=el('article','topic');item.append(el('h3','',t.title),el('p','',t.text),link('الرجوع إلى النص الذي يقوم عليه هذا المحور',sourceURL(t.from,t.to,id),'source-link'));topics.append(item);});root.append(topics);
  function readingGroup(title,arr,folded=false){if(!arr.length)return;const sec=el(folded?'details':'section',folded?'more':'block');sec.append(el(folded?'summary':'h2','',title));const list=el('div','readings');arr.forEach(r=>{const item=el('article','reading');const body=el('div');body.append(el('h3','',r.title));if(r.focus)body.append(el('p','',r.focus));body.append(el('p','locator',locationLabel(r.from,r.to)));item.append(body,link('اقرأ النص',sourceURL(r.from,r.to,id),'button small'));list.append(item);});sec.append(list);root.append(sec);}
  readingGroup('القراءات الأساسية',u.readings);readingGroup('قراءات تمهيدية ومكملة',u.supporting,true);readingGroup('مسارات التوسع في المرجع',u.extensions,true);
  const q=el('section','block');q.append(el('p','eyebrow','تدريب على بناء الإجابة من المصدر'),el('h2','','أسئلة التحليل الذاتي'),el('p','muted','دوّن إجابتك مع موضع الاستناد من الكتاب. هذه أسئلة قراءة ومناقشة، وليست اختباراً يرصد درجات أو يمنح اجتيازاً.'));
  u.questions.forEach((item,i)=>{const p=el('article','prompt');p.append(el('h3','',`سؤال ${i+1}`),el('p','',item.text),link('النص المرجعي للسؤال',sourceURL(item.from,item.to,id),'source-link'));q.append(p);});root.append(q);
  const notes=el('section','block');notes.append(el('h2','','دفتر القراءة'));const label=el('label','note-label','ملاحظاتك وإحالاتك إلى الكتاب');label.htmlFor='reading-notes';const field=el('textarea');field.id='reading-notes';field.placeholder='اكتب الفكرة، والتمييز القانوني، وموضع استنادك في النص…';const status=el('p','note-status');status.setAttribute('role','status');const key=`execution-law-course:reading:v1:unit-${id}`;
  try{field.value=localStorage.getItem(key)||'';status.textContent='ملاحظاتك محفوظة على هذا المتصفح فقط؛ لا تُرسل إلى الأستاذ ولا تدخل في التقييم.';}catch{status.textContent='الحفظ المحلي غير متاح في هذا المتصفح. يمكنك نسخ ملاحظاتك يدوياً.';}
  field.addEventListener('input',()=>{try{localStorage.setItem(key,field.value);status.textContent='حُفظت الملاحظات على هذا المتصفح فقط.';}catch{status.textContent='تعذر الحفظ؛ انسخ ملاحظاتك قبل مغادرة الصفحة.';}});
  notes.append(label,field,status);root.append(notes);
  const bridge=el('section','notice');bridge.append(el('p','',u.bridge));root.append(bridge);
  if(u.format==='video')root.append(el('p','fine','حالة الوسائط: هذه الوحدة مرتبطة بمادتها القرائية. الفيديو المخطط لمدة 20 دقيقة لم يُنتج أو يُنشر بعد.'));
  const next=el('nav','next-row');next.setAttribute('aria-label','الانتقال بين الوحدات');if(id>1)next.append(link('الوحدة السابقة',`lesson.html?unit=${id-1}`,'button'));else next.append(link('المسار الكامل','index.html#units','button'));if(id<units.length)next.append(link('الوحدة التالية',`lesson.html?unit=${id+1}`,'button primary'));else next.append(link('العودة إلى المرجع الكامل','material.html','button primary'));root.append(next);
})();
