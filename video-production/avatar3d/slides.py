"""Source-faithful Arabic lecture boards matching the approved 3D sample."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
W,H=1920,1080
NAVY='#10283e'; INK='#153047'; GOLD='#c5a265'; PAPER='#faf9f4'; MUTED='#617689'

def font(size,bold=False):
    return ImageFont.truetype(str(ROOT/'assets/fonts'/('Tajawal-Bold.ttf' if bold else 'Tajawal-Regular.ttf')),size)

def lines(text,size,width,bold=False):
    out=[];current='';f=font(size,bold)
    for word in text.split():
        nxt=(current+' '+word).strip()
        if current and f.getlength(nxt,direction='rtl')>width:out.append(current);current=word
        else:current=nxt
    if current:out.append(current)
    return out

def text(draw,s,x,y,size,color=INK,bold=False,anchor='ra'):
    draw.text((x,y),s,font=font(size,bold),fill=color,anchor=anchor,direction='rtl',language='ar')

def fit(draw,s,right,top,width,height,maximum=38,minimum=25,color=INK,bold=False):
    for size in range(maximum,minimum-1,-1):
        rows=lines(s,size,width,bold);step=round(size*1.48)
        if len(rows)*step<=height:break
    else:raise ValueError('Text cannot fit: '+s)
    for row in rows:text(draw,row,right,top,size,color,bold);top+=step
    return top

def slide(unit,scene,index,stage=0,thinking=False):
    im=Image.new('RGB',(W,H),NAVY);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,6),fill=GOLD)
    text(d,'مقرر التنفيذ الجبري',1780,38,36,'#f4f7fa',True)
    text(d,f'الوحدة {unit["id"]} · {unit["title"]}',1780,86,24,'#c4d0da')
    d.ellipse((1814,35,1870,91),outline=GOLD,width=1);text(d,'ت',1842,44,32,GOLD,True,'ma')
    text(d,'شاهد القاعدة · افهم الفارق · طبّق',610,49,24,'#d7bb86')
    # Left study rail is covered by the animated professor during appearances.
    d.rounded_rectangle((76,230,585,730),24,fill='#18354b',outline='#345066',width=2)
    text(d,'مسار الفكرة',540,269,25,'#d7bb86',True)
    d.text((105,322),str(index+1).zfill(2),font=font(98,True),fill='#d5b679')
    fit(d,scene['title'],535,455,395,195,38,29,'#eef2f5',True)
    text(d,f'من {len(unit["scenes"])} محاور',535,669,25,'#b9c9d5')
    text(d,'اقرأ النص، ثم ابنِ إجابتك.',585,839,29,'#e3e9ee')
    text(d,'المادة العلمية للمقرر',585,892,25,'#c4a96e')
    d.rounded_rectangle((693,146,1857,931),28,fill='#071a2a')
    d.rounded_rectangle((690,138,1850,923),28,fill=PAPER,outline='#d6d1c4',width=1)
    d.rounded_rectangle((710,138,1830,144),3,fill=GOLD)
    d.text((1790,177),f'{index+1:02} / {len(unit["scenes"]):02}',font=font(25,True),fill='#876735',anchor='ra',direction='ltr')
    kind={'compare':'قارن بين المفاهيم','sequence':'تتبّع الإجراءات','map':'نظّم العلاقات','case':'حلّل التطبيق','checklist':'افحص الشروط','presenter':'فكرة الوحدة','definition':'افهم القاعدة'}.get(scene['kind'],'اقرأ وحلّل')
    text(d,kind,1590,177,24,'#947f5c')
    title=scene['title'];size=58
    while len(lines(title,size,1048,True))>2 and size>44:size-=2
    title_lines=lines(title,size,1048,True)
    if len(title_lines)>2:raise ValueError('Title overflow: '+title)
    for k,row in enumerate(title_lines):text(d,row,1790,235+k*round(size*1.35),size,INK,True)
    top=max(378,235+len(title_lines)*round(size*1.35)+30)
    bottom=853
    if thinking:
        d.rounded_rectangle((746,top,1794,bottom),20,fill='#eee6d5',outline='#d3b981',width=2)
        text(d,'وقفة للتفكير',1755,top+28,30,'#8a6831',True)
        prompt=scene.get('prompt','اكتب الفارق الذي بُني عليه هذا الجزء من الدرس، وحدد موضع استنادك من الكتاب.')
        fit(d,prompt,1755,top+95,965,bottom-top-130,42,29,INK,True)
    elif scene['kind'] in ['compare','sequence','map']:
        bullets=scene['bullets'];count=len(bullets);gap=20;total=1048;bw=(total-gap*(count-1))/count
        for n,value in enumerate(bullets):
            right=1794-n*(bw+gap);left=right-bw;active=n==stage
            d.rounded_rectangle((left,top,right,bottom),20,fill='#fffaf0' if active else '#ffffff',outline=GOLD if active else '#dce2e3',width=3 if active else 2)
            d.rounded_rectangle((right-90,top+27,right-30,top+32),2,fill=GOLD)
            text(d,str(n+1).zfill(2),right-30,top+55,28,'#9e7b3e',True)
            fit(d,value,right-27,top+122,bw-54,bottom-top-155,38 if count<3 else 34,26,INK,True)
            if scene['kind']=='sequence' and n<count-1:
                x=left-gap/2;y=(top+bottom)/2
                d.line((x-7,y,x+7,y),fill=GOLD,width=3)
                d.polygon([(x-8,y),(x-1,y-6),(x-1,y+6)],fill=GOLD)
    else:
        values=scene['bullets'];gap=18;rh=(bottom-top-gap*(len(values)-1))/len(values)
        for n,value in enumerate(values):
            y=top+n*(rh+gap);active=n==stage
            d.rounded_rectangle((746,y,1794,y+rh),18,fill='#fffaf0' if active else '#fff',outline=GOLD if active else '#dce2e3',width=3 if active else 2)
            cy=y+rh/2;d.ellipse((1717,cy-24,1765,cy+24),outline=GOLD if active else '#cdd6db',width=2)
            text(d,str(n+1),1741,cy-16,26,'#96713a',True,'ma')
            fit(d,value,1685,y+max(20,(rh-66)/2),902,rh-28,38,27,INK,True)
    text(d,'نقرأ التفصيل والشروط في النص المرجعي للمقرر.',1785,880,23,MUTED)
    d.line((718,992,1815,992),fill='#455d6d',width=2)
    text(d,'شرح من المادة العلمية لمقرر التنفيذ الجبري',1815,1013,22,'#b7c7d2')
    a,b=scene['refs'];text(d,f'مواضع المصدر {a} إلى {b}',605,1013,22,'#b7c7d2')
    return im
