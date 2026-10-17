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
 'مرحباً بكم في مساق التَّنفيذ الجَبْري. نبدأ اليوم بالسَّنَد التَّنفيذي، بالاستناد إلى كتاب الوجيز في قانون التنفيذ الجبري، للأستاذ الدكتور أحمد خليل. هل يكفي أن يكون للدائن حقٌّ ثابت، حتى تبدأ إجراءات التنفيذ؟',
 'يوضح المؤلف أن إثبات الحق وحده لا يكفي. فلا بد من سَنَدٍ أضفى عليه التشريع الصفة التنفيذية. وهنا نميز بين أمرين: الحقُّ الموضوعي، ومصدره كالعقد أو الفعل الضار؛ والحقُّ في التنفيذ الجبري، ومصدره السند التنفيذي. فوجود ورقة تثبت الدين لا يجعلها تلقائياً سنداً تنفيذياً.',
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

if __name__=='__main__':
    try:
        asyncio.run(prepare())
        run(['ffmpeg','-v','error','-y','-i',OUT/'audio/narration.wav','-c:a','aac','-b:a','96k','-t','60',OUT/'audio/arabic-voice-preview.m4a'])
        assert float(probe(OUT/'audio/arabic-voice-preview.m4a')['format']['duration'])==60.0
    except Exception as exc:
        status('audio',type(exc).__name__+': '+str(exc),'failure')
        raise
