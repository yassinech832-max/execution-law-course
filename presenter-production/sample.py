"""Produce an actual audio-driven presenter trial; never simulate speech with RMS."""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'presenter-output'
W,H,FPS=1920,1080,25
NAVY,GOLD,PAPER,INK='#10283f','#c7a15a','#f8f7f2','#142d43'
VOICE='ar-SA-HamedNeural'
PARTS=[
 'مرحباً بكم في مساق التَّنفيذ الجَبْري. نبدأ اليوم بالسَّنَد التَّنفيذي، بالاستناد إلى المادة العلمية لمقرر التنفيذ الجبري. هل يكفي أن يكون للدائن حقٌّ ثابت، حتى تبدأ إجراءات التنفيذ؟',
 'يوضح المقرر أن إثبات الحق وحده لا يكفي. فلا بد من سَنَدٍ أضفى عليه التشريع الصفة التنفيذية. وهنا نميز بين أمرين: الحقُّ الموضوعي، ومصدره كالعقد أو الفعل الضار؛ والحقُّ في التنفيذ الجبري، ومصدره السند التنفيذي. فوجود ورقة تثبت الدين لا يجعلها تلقائياً سنداً تنفيذياً.',
 'قبل متابعة الدرس، تأمل هذا السؤال: ما الفرق بين إثبات الحق، وامتلاك الحق في طلب الحماية التنفيذية؟ دوّن إجابتك، ثم ارجع إلى الفقرات المرتبطة بالوحدة.'
]
TITLES=['السَّنَد التَّنفيذي','حقّان ينبغي التمييز بينهما','سؤال قبل متابعة الدرس']
BULLETS=[['ورقة تثبت الحق','صفة يمنحها التشريع','طلب الحماية التنفيذية'],['الحق الموضوعي ومصدره','الحق في التنفيذ الجبري','السند التنفيذي مصدره'],['إثبات وجود الحق','الحق في طلب التنفيذ','ابن إجابتك من الكتاب']]

def run(args,**kwargs):
    return subprocess.run([str(x)for x in args],check=True,**kwargs)

def status(label,description,state='pending'):
    if not os.getenv('GITHUB_TOKEN'):return
    data=json.dumps({'state':state,'context':'presenter/'+label,'description':description[:140]}).encode()
    request=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=data,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=15)as r:r.read()
    except Exception:pass

def graphics():
    spec=importlib.util.spec_from_file_location('course_production',ROOT/'video-production/produce.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],text=True))

async def voice(text,voice,path):
    import edge_tts
    words=[]
    for attempt in range(3):
        try:
            words=[]
            with path.open('wb')as file:
                async for part in edge_tts.Communicate(text,voice,rate='-5%',boundary='WordBoundary',receive_timeout=120).stream():
                    if part['type']=='audio':file.write(part['data'])
                    elif part['type']=='WordBoundary':words.append({'start':part['offset']/1e7,'end':(part['offset']+part['duration'])/1e7,'text':part['text']})
            assert words and path.stat().st_size>1000
            return words
        except Exception:
            if attempt==2:raise
            await asyncio.sleep(2)

async def prepare():
    import numpy as np
    g=graphics();out=OUT/'audio';out.mkdir(parents=True,exist_ok=True)
    status('audio','Preparing careful Arabic narration and word timings')
    recordings=[];raw=0
    for i,text in enumerate(PARTS):
        path=out/f'part-{i}.mp3';words=await voice(text,VOICE,path)
        wav=out/f'part-{i}.wav';run(['ffmpeg','-v','error','-y','-i',path,'-ar',24000,'-ac',1,wav])
        samples=g.read_wav(wav);seconds=len(samples)/24000;raw+=seconds
        recordings.append((wav,words,seconds))
    tempo=raw/59.0
    assert .82<=tempo<=1.18,f'Editorial pacing required: {tempo:.3f}; raw={raw:.2f}'
    clock=0;sound=[];cues=[];chapters=[]
    for i,(path,words,seconds)in enumerate(recordings):
        start=clock;n=round(seconds/tempo*24000);paced=out/f'paced-{i}.wav'
        run(['ffmpeg','-v','error','-y','-i',path,'-af',f'atempo={tempo:.9f},apad=whole_len={n},atrim=end_sample={n}',paced])
        samples=g.read_wav(paced);sound.append(samples)
        ratio=len(samples)/24000/seconds
        cues.extend(g.group_captions([{'start':clock+w['start']*ratio,'end':clock+w['end']*ratio,'text':w['text']}for w in words]))
        clock+=len(samples)/24000;sound.append(np.zeros(4800,dtype=np.int16));clock+=.2
        chapters.append({'start':start,'end':clock,'title':TITLES[i]})
    samples=np.concatenate(sound);samples=np.pad(samples,(0,60*24000-len(samples)));g.save_wav(out/'narration.wav',samples)
    # Exact text timings are retained, without broadening the course's legal claims.
    g.write_captions(cues,out)
    (out/'transcript.txt').write_text('\n\n'.join(PARTS)+'\n')
    report={'status':'PASS','voice':VOICE,'naturalSpeechSeconds':raw,'tempo':tempo,'durationSeconds':60,'captions':cues,'chapters':chapters,'sourceRange':[37,40]}
    (out/'audio-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    run(['ffmpeg','-v','error','-y','-i',out/'narration.wav','-t','12','-ar','16000','-ac','1',out/'intro.wav'])
    comparison='السَّنَد التَّنفيذي هو مصدر الحق في التنفيذ الجَبْري. لا يكفي إثبات الدين وحده؛ بل يجب أن يمنح التشريعُ السندَ هذه الصفة.'
    for name in ['ar-AE-HamdanNeural','ar-EG-ShakirNeural']:
        await voice(comparison,name,out/(name+'.mp3'))
    status('audio',f'60.000s Arabic narration; natural pacing {tempo:.3f}; captions prepared','success')

def download(url,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists()and path.stat().st_size>100000:return
    with urllib.request.urlopen(url,timeout=120)as response,path.open('wb')as file:shutil.copyfileobj(response,file)
    assert path.stat().st_size>100000

def slide(index,cue=None):
    from PIL import Image,ImageDraw
    g=graphics();im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,15),fill=GOLD)
    d.rounded_rectangle((58,85,708,946),radius=32,fill=NAVY)
    # This panel becomes a diagram when the presenter appears only in the intro.
    g.scales(d,240,365,270)
    g.paragraph(d,'فهم القاعدة أساس التطبيق',650,760,35,520,'#f6ead0',True)
    g.rtl(d,'التنفيذ الجبري  /  الوحدة الأولى',1816,95,31,NAVY,True)
    g.rtl(d,'عينة تعليمية بصورتك • صوت اصطناعي',1816,151,25,'#647585')
    y=255
    for line in g.wrap(TITLES[index],64,1030,True):g.rtl(d,line,1816,y,64,NAVY,True);y+=91
    for n,text in enumerate(BULLETS[index]):
        y=455+n*135
        d.rounded_rectangle((785,y,1824,y+106),radius=18,fill='#ffffff',outline='#dfdfd7',width=2)
        d.ellipse((1745,y+28,1794,y+77),fill=GOLD)
        g.rtl(d,str(n+1),1769,y+34,27,NAVY,True,anchor='ma')
        g.paragraph(d,text,1708,y+24,39,875,INK,True,spacing=1.2)
    d.rectangle((0,1040,W,H),fill=NAVY)
    g.rtl(d,'المصدر: مقرر التنفيذ الجبري • مقرر المادة • مواضع 37–40',1818,1048,20,'#ffffff')
    if cue:
        d.rounded_rectangle((76,951,1844,1030),radius=14,fill=NAVY)
        lines=g.wrap(cue,33,1670,False)
        for n,line in enumerate(lines[:2]):g.rtl(d,line,1807,960+n*37,33,'#ffffff')
    return im

def compose(engine,portrait,portrait_seconds):
    from PIL import Image,ImageDraw
    out=OUT/engine;out.mkdir(parents=True,exist_ok=True);audio=OUT/'audio';g=graphics()
    report=json.loads((audio/'audio-report.json').read_text());cues=report['captions'];chapters=report['chapters']
    boundaries=sorted(set([0.0,60.0]+[p for c in cues for p in [c['start'],c['end']]]+[c['start']for c in chapters]))
    work=out/'frames';work.mkdir(exist_ok=True);lines=[]
    for n,(start,end)in enumerate(zip(boundaries,boundaries[1:])):
        if end-start<.001:continue
        index=max(i for i,c in enumerate(chapters)if c['start']<=start+.001)
        text=next((c['text']for c in cues if c['start']<=start+.001<c['end']),None)
        path=work/f'{n:03}.png';slide(index,text).save(path);lines.extend([f"file '{path.resolve()}'",f'duration {end-start:.9f}'])
    lines.append(lines[-2]);(work/'frames.txt').write_text('\n'.join(lines)+'\n')
    # Neural output is cropped by the video editor; the source photograph stays intact.
    if engine=='wav2lip':portrait_filter='crop=650:900:180:40,scale=580:804'
    else:portrait_filter='scale=580:580,pad=580:804:0:110:color=0x10283f'
    filters=f'[0:v]fps=25,format=yuv420p[base];[1:v]{portrait_filter},setsar=1[face];[base][face]overlay=92:128:eof_action=pass:repeatlast=0:enable=\'between(t,0,{portrait_seconds:.4f})\'[v];[2:a]loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000[a]'
    run(['ffmpeg','-v','warning','-y','-filter_complex_threads','1','-f','concat','-safe','0','-i',work/'frames.txt','-i',portrait,'-i',audio/'narration.wav','-i',audio/'captions.srt','-filter_complex',filters,'-map','[v]','-map','[a]','-map','3:s','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-c:s','mov_text','-metadata:s:s:0','language=ara','-movflags','+faststart','-t','60','-threads','2',out/'sample.mp4'])
    info=probe(out/'sample.mp4');v=next(s for s in info['streams']if s['codec_type']=='video')
    assert float(info['format']['duration'])==60.0 and int(v['nb_frames'])==1500
    run(['ffmpeg','-v','error','-i',out/'sample.mp4','-f','null','-'])
    for name in ['captions.vtt','captions.srt','transcript.txt']:shutil.copy2(audio/name,out/name)
    thumb=out/'poster.jpg';run(['ffmpeg','-v','error','-y','-ss','2','-i',out/'sample.mp4','-frames:v','1',thumb])
    sheet=Image.new('RGB',(1920,580),PAPER);d=ImageDraw.Draw(sheet)
    for n,t in enumerate([1,3,5,9,15,28,42,56]):
        path=work/f'qa-{n}.png';run(['ffmpeg','-v','error','-y','-ss',t,'-i',out/'sample.mp4','-frames:v','1',path]);sheet.paste(Image.open(path).resize((480,270)),((n%4)*480,(n//4)*290))
        d.text(((n%4)*480+12,(n//4)*290+274),f'{t}s',fill=NAVY)
    sheet.save(out/'qa-frames.jpg',quality=91)
    report.update({'status':'PASS','engine':engine,'durationSeconds':60.0,'resolution':[1920,1080],'fps':25,'frames':1500,'fileBytes':int(info['format']['size']),'actualNeuralPortraitSeconds':portrait_seconds,'sourceCommit':os.getenv('GITHUB_SHA'),'limitations':'The narration is synthetic, not the professor’s recorded voice.'})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def wav2lip():
    import cv2
    import numpy as np
    work=ROOT/'engines/Wav2Lip';out=OUT/'wav2lip';out.mkdir(parents=True,exist_ok=True)
    status('wav2lip','Loading audio-driven lip synchronization model on free CPU')
    download('https://huggingface.co/camenduru/Wav2Lip/resolve/f510bc766073f2403ed92b5995231323ece0ac06/checkpoints/wav2lip_gan.pth',work/'checkpoints/wav2lip_gan.pth')
    image=cv2.imread(str(HERE/'presenter.jpg'));assert image is not None
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    faces=cascade.detectMultiScale(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),1.08,6,minSize=(100,100))
    assert len(faces),'No reliable frontal face detected in the supplied portrait'
    x,y,w,h=max(faces,key=lambda b:int(b[2])*int(b[3]));box=[max(0,int(y-h*.05)),min(image.shape[0],int(y+h*1.12)),max(0,int(x-w*.04)),min(image.shape[1],int(x+w*1.04))]
    (out/'face-box.json').write_text(json.dumps([int(v)for v in box]))
    # Keep eyes, forehead and outer face from the real photo; feather only the
    # lower-face neural prediction to avoid a rectangular replacement seam.
    source=(work/'inference.py').read_text()
    original='f[y1:y2, x1:x2] = p'
    replacement='''hh, ww = p.shape[:2]
\t\t\tyy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
\t\t\tvertical = np.clip((yy / hh - .48) / .14, 0, 1)
\t\t\tedge = np.minimum(np.minimum(xx, ww-1-xx)/max(1,ww*.12), np.minimum(yy,hh-1-yy)/max(1,hh*.08))
\t\t\talpha = (vertical * np.clip(edge,0,1))[...,None]
\t\t\tf[y1:y2, x1:x2] = (p * alpha + f[y1:y2,x1:x2] * (1-alpha)).astype(np.uint8)'''
    assert original in source;(work/'inference.py').write_text(source.replace(original,replacement))
    status('wav2lip','Generating 1500 frames from the real portrait and Arabic speech')
    start=time.time();raw=out/'portrait.mp4'
    run([sys.executable,'inference.py','--checkpoint_path','checkpoints/wav2lip_gan.pth','--face',HERE/'presenter.jpg','--audio',OUT/'audio/narration.wav','--outfile',raw,'--box',*box,'--wav2lip_batch_size','8','--fps','25'],cwd=work)
    # Motion is checked on decoded pixels of the actual generated mouth.
    motion=[]
    for t in [1,3,5,9]:
        cap=cv2.VideoCapture(str(raw));cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read();cap.release();assert ok
        a,b,c,e=box;motion.append(frame[int(a+(b-a)*.58):int(a+(b-a)*.93),int(c+(e-c)*.18):int(c+(e-c)*.82)].astype(float))
    differences=[float(np.mean(np.abs(a-b)))for a,b in zip(motion,motion[1:])]
    assert max(differences)>.5,'The generated mouth is static'
    report=compose('wav2lip',raw,60.0);report.update({'neuralRenderSeconds':time.time()-start,'mouthMotionDifferences':differences,'faceBox':box})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    status('wav2lip','60.000s; real audio-driven lips; Arabic captions; decode PASS','success')

def sadtalker():
    work=ROOT/'engines/SadTalker';out=OUT/'sadtalker';out.mkdir(parents=True,exist_ok=True)
    status('sadtalker','Preparing genuine neural head and lip animation on free CPU')
    for name in ['SadTalker_V0.0.2_256.safetensors','mapping_00229-model.pth.tar']:
        download('https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/'+name,work/'checkpoints'/name)
    for name in ['alignment_WFLW_4HG.pth','detection_Resnet50_Final.pth']:
        download('https://github.com/xinntao/facexlib/releases/download/v0.1.0/'+name,work/'gfpgan/weights'/name)
    # Pinning below keeps the upstream model's numpy and torchvision interfaces.
    status('sadtalker','Animating a 12-second introduction with head motion and lip sync')
    start=time.time()
    run([sys.executable,'inference.py','--driven_audio',OUT/'audio/intro.wav','--source_image',HERE/'presenter.jpg','--result_dir',out/'neural','--cpu','--size','256','--batch_size','1','--preprocess','crop','--expression_scale','0.8'],cwd=work)
    files=list((out/'neural').glob('*.mp4'));assert len(files)==1
    report=compose('sadtalker',files[0],12.0);report['neuralRenderSeconds']=time.time()-start
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    status('sadtalker','60.000s lesson sample; 12s neural head/lips; decode PASS','success')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['audio','wav2lip','sadtalker']);args=parser.parse_args()
    os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('MKL_NUM_THREADS','2')
    try:
        if args.mode=='audio':asyncio.run(prepare())
        elif args.mode=='wav2lip':wav2lip()
        else:sadtalker()
    except Exception as exc:
        out=OUT/args.mode;out.mkdir(parents=True,exist_ok=True)
        (out/'report.json').write_text(json.dumps({'status':'FAIL','engine':args.mode,'error':str(exc),'traceback':traceback.format_exc()},ensure_ascii=False,indent=2))
        status(args.mode,(type(exc).__name__+': '+str(exc))[:140],'failure');raise
