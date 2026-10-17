'use strict';
(() => {
  const book=window.BOOK_INDEX, text=window.EXECUTION_MATERIAL;
  const $=id=>document.getElementById(id);
  const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;};
  if(!book||!Array.isArray(text)||text.length!==book.paragraphCount){$('source-content').append(el('p','error','لم يكتمل تحميل النص. أعد تحميل الصفحة قبل القراءة.'));return;}
  const total=text.length, pageSize=45;
  let params=new URLSearchParams(location.search);
  const integer=(value,fallback)=>{const n=Number(value);return Number.isInteger(n)&&n>0?n:fallback;};
  let from=Math.min(integer(params.get('from'),1),total),to=Math.min(integer(params.get('to'),total),total);if(to<from)[from,to]=[to,from];
  let unit=integer(params.get('unit'),0),q=params.get('q')||'',page=integer(params.get('page'),1)-1;
  let matches=[];
  const normalize=s=>s.normalize('NFKC').replace(/[\u064B-\u065F\u0670\u0640]/g,'').replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي').toLowerCase().trim();
  const id=n=>'p'+String(n).padStart(4,'0');
  const hashNumber=()=>Number(location.hash.match(/^#p(\d+)$/)?.[1]);
  function writeURL(){const p=new URLSearchParams();if(from!==1||to!==total){p.set('from',from);p.set('to',to);}if(unit>=1&&unit<=7)p.set('unit',unit);if(q)p.set('q',q);if(page)p.set('page',page+1);const query=p.toString();history.replaceState(null,'',location.pathname+(query?'?'+query:'')+location.hash);}
  function updateMatches(jump=true){const needle=normalize(q);matches=[];for(let i=from;i<=to;i++){if(!needle||normalize(text[i-1].text).includes(needle))matches.push(i);}if(jump){const target=hashNumber();const ix=matches.indexOf(target);if(ix>=0)page=Math.floor(ix/pageSize);}const max=Math.max(0,Math.ceil(matches.length/pageSize)-1);page=Math.min(Math.max(0,page),max);render();}
  function renderPager(root){root.replaceChildren();const previous=el('button','','المقطع السابق'),next=el('button','','المقطع التالي');previous.type=next.type='button';previous.disabled=page===0;next.disabled=(page+1)*pageSize>=matches.length;
    const move=delta=>{page+=delta;history.replaceState(null,'',location.pathname+location.search);render();$('source-content').focus();$('source-content').scrollIntoView({behavior:'auto',block:'start'});};previous.addEventListener('click',()=>move(-1));next.addEventListener('click',()=>move(1));root.append(previous,el('span','page-counter',matches.length?`مقطع ${page+1} من ${Math.ceil(matches.length/pageSize)}`:'لا توجد نتائج'),next);}
  function render(){writeURL();const root=$('source-content');root.replaceChildren();const visible=matches.slice(page*pageSize,(page+1)*pageSize);const needle=normalize(q);
    $('reading-range').textContent=(from===1&&to===total)?'نطاق القراءة: الكتاب كاملاً، بما فيه المراجع والفهرس.':`نطاق القراءة المحدد: مواضع المصدر ${from} إلى ${to}.`;
    $('search-status').textContent=needle?`${matches.length} نتيجة في نطاق القراءة الحالي. يعثر البحث على الكلمات مع اختلاف التشكيل وأشكال الألف.`:`${matches.length} فقرة في النطاق. المعروض الآن ${visible.length} فقرة. إجمالي المرجع ${total} فقرة.`;
    if(!visible.length)root.append(el('p','empty','لم يظهر تطابق في هذا المقطع. امسح عبارة البحث أو افتح الكتاب كاملاً لتوسيع النطاق.'));
    visible.forEach(n=>{const level=book.levels[String(n)];const a=el('article','source-paragraph'+(level?' heading':''));a.id=id(n);const ref=el('a','para-ref',`موضع المصدر ${n}`);ref.href='#'+id(n);ref.setAttribute('aria-label','رابط مباشر إلى موضع المصدر '+n);a.append(ref);const headingTag=level?(level<=1?'h2':level<=3?'h3':'h4'):'p';a.append(el(headingTag,'',text[n-1].text));root.append(a);});
    renderPager($('pager-top'));renderPager($('pager-bottom'));const anchor=$(location.hash.slice(1));if(anchor)requestAnimationFrame(()=>anchor.scrollIntoView({behavior:'auto',block:'start'}));
  }
  $('search').value=q;$('search-form').addEventListener('submit',event=>{event.preventDefault();q=$('search').value;page=0;history.replaceState(null,'',location.pathname+location.search);updateMatches(false);});
  $('reset-reader').addEventListener('click',()=>{from=1;to=total;q='';page=0;$('search').value='';history.replaceState(null,'',location.pathname);updateMatches(false);});
  if(unit>=1&&unit<=7){const a=el('a','button small','العودة إلى الوحدة '+unit);a.href='lesson.html?unit='+unit+'&v=20261017-course';$('reader-return').append(a);}
  const toc=$('toc');toc.append(el('h2','','فهرس المرجع'));
  const headings=book.headings.filter(h=>h.level<=3);let current=toc;
  headings.forEach(h=>{if(h.level===1){const d=el('details');d.open=from>=h.p&&from<=h.end;const s=el('summary','',h.title);d.append(s);toc.append(d);current=d;}const a=el('a','',h.title);a.href=`material.html?from=${h.p}&to=${h.end}#${id(h.p)}`;if(h.level===3)a.style.paddingRight='24px';current.append(a);});
  const originalTOC=el('a','','الفهرس الأصلي في الملف');originalTOC.href=`material.html?from=${book.tocStart}&to=${total}#${id(book.tocStart)}`;toc.append(originalTOC);
  window.addEventListener('hashchange',()=>{const target=hashNumber(),ix=matches.indexOf(target);if(ix>=0&&Math.floor(ix/pageSize)!==page){page=Math.floor(ix/pageSize);render();}});
  updateMatches();
})();
