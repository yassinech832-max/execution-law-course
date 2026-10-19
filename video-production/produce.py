"""Render a measured Arabic lecture: source -> speech -> captions -> 1080p MP4.

All AI speech is produced before publication. The student receives ordinary files.
"""
import argparse
import asyncio
import html
import hashlib
import json
import math
import os
import re
import runpy
import subprocess
import sys
import traceback
import urllib.request
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
W, H, FPS, SR, TARGET = 1920, 1080, 25, 24000, 1200
INK, GOLD, PAPER, MUTED = '#10283f', '#b18a46', '#f8f7f2', '#647585'
FONT = str(ROOT/'assets/fonts/Tajawal-Regular.ttf')
BOLD = str(ROOT/'assets/fonts/Tajawal-Bold.ttf')
NARRATION_PROFILE=json.loads((HERE/'narration-profile.json').read_text())
VOICE=NARRATION_PROFILE['voice']
SPEECH_RATE=NARRATION_PROFILE['rate']
SPEECH_PITCH=NARRATION_PROFILE['pitch']

def run(args, **kwargs):
    return subprocess.run([str(v) for v in args], check=True, **kwargs)

def progress(unit, description):
    token=os.environ.get('GITHUB_TOKEN')
    if not token:return
    repo=os.environ.get('GITHUB_REPOSITORY');sha=os.environ.get('GITHUB_SHA')
    if not repo or not sha:return
    payload=json.dumps({'state':'pending','context':f'course/video-{unit}','description':description[:140]}).encode()
    request=urllib.request.Request(f'https://api.github.com/repos/{repo}/statuses/{sha}',data=payload,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=15) as response:response.read()
    except Exception as exc:print('Progress update unavailable: '+type(exc).__name__,flush=True)

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)], text=True))

def load_source():
    paragraphs = []
    for n in range(1,7):
        s = (ROOT/f'material-{n:02}.js').read_text()
        paragraphs.extend(json.loads(s.split('.concat(',1)[1].rsplit(');',1)[0]))
    assert len(paragraphs) == 1920
    return paragraphs

def speakable(text):
    text = re.sub(r'^\s*\d+\s*[-–ـ]\s*', '', text)
    text = re.sub(r'\((?:مادة|المادة|م|المادتان|المادتين)\s[^)]*\)', '', text)
    number=r'\d[\d\s\-–،]*(?:و\s*\d[\d\s\-–،]*)*'
    text = re.sub(r'(?:لنص المادة|للمادة)\s+'+number, 'للنص المعروض في الكتاب، ', text)
    text = re.sub(r'(?:(?:نص )?المادة|المادتان|المادتين)\s+'+number, 'النص المعروض في الكتاب، ', text)
    text = re.sub(r'\(\s*\d+\s*[-–]\s*\d+\s*\)', '', text)
    text = re.sub(r'\s*[-–—]\s*', '، ', text)
    return re.sub(r'\s+', ' ', text.replace('..','.').replace('"','').replace('،،','،')).strip()

def narration_text(text):
    for plain,spoken in sorted(NARRATION_PROFILE['terms'],key=lambda item:len(item[0]),reverse=True):
        pattern=''.join(re.escape(char)+r'[\u064b-\u065f\u0670]*' for char in plain)+r'(?![\u0621-\u064a])'
        text=re.sub(pattern,lambda match:spoken,text)
    return text

def assemble(unit):
    source = load_source()
    overrides={954:'منح المشتري مهلة لا تزيد على خمسة أيام للدفع مكنة تدخل في سلطة قاضي التنفيذ الجوازية، وفق النصوص التي يناقشها المقرر. ويبين ترتيب هذه النصوص أن منح المهلة يقتصر على المشتري عند إجراء المزاد الأول، ولا ينطبق على المشتري عند إعادة البيع.'}
    for scene in unit['scenes']:
        assert 1 <= scene['refs'][0] <= scene['refs'][1] <= len(source)
        quoted = ' '.join(overrides.get(n,speakable(source[n-1]['text'])) for n in scene['ids'])
        body = ' '.join(v for v in [quoted,scene.get('tail','')] if v)
        scene['spoken'] = narration_text(' '.join(v for v in [scene.get('lead',''),body] if v))
        if scene.get('hold'):
            scene['parts'] = [narration_text(scene['lead']),None,narration_text(body)] if body else [narration_text(scene['lead']),None]
        else:
            scene['parts'] = [scene['spoken']]
    return unit

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def rtl(draw, text, x, y, size, color=INK, bold=False, anchor='ra'):
    draw.text((x,y),text,font=font(size,bold),fill=color,anchor=anchor,direction='rtl',language='ar',stroke_width=0)

def wrap(text, size, width, bold=False):
    f = font(size,bold)
    lines, line = [], ''
    for word in text.split():
        candidate = (line+' '+word).strip()
        if f.getlength(candidate,direction='rtl') > width and line:
            lines.append(line); line=word
        else:
            line=candidate
    if line: lines.append(line)
    return lines

def paragraph(draw, text, right, y, size, width, color=INK, bold=False, spacing=1.5):
    for line in wrap(text,size,width,bold):
        rtl(draw,line,right,y,size,color,bold);y += int(size*spacing)
    return y

def scales(draw, x, y, size=260):
    c=GOLD;s=size/260
    pt=lambda a,b:(int(x+a*s),int(y+b*s))
    draw.line([pt(130,5),pt(130,235)],fill=c,width=5)
    draw.line([pt(44,65),pt(216,65)],fill=c,width=5)
    draw.line([pt(75,238),pt(185,238)],fill=c,width=7)
    for center in [55,205]:
        draw.line([pt(center,65),pt(center-40,155),pt(center+40,155),pt(center,65)],fill=c,width=4)
        draw.arc([pt(center-40,125),pt(center+40,185)],0,180,fill=c,width=4)

def appearance_length(index, total, duration):
    return min(duration,18 if index==0 else 10 if index==total-1 else 7)


def slide(unit, scene, i, stage=0, thinking=False, portrait=None):
    im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,16),fill=INK)
    rtl(d,'التنفيذ الجبري',1810,60,32,INK,True)
    rtl(d,f'الوحدة {unit["id"]}  ·  {unit["subtitle"]}',1810,116,25,MUTED)
    d.line((110,181,1810,181),fill='#d5ded8',width=2)
    d.rounded_rectangle((74,230,540,935),radius=30,fill=INK)
    d.text((120,264),f'{i+1:02d} / {len(unit["scenes"]):02d}',font=font(35,True),fill='#e7c995')
    if portrait is None:portrait=scene['kind']=='presenter' or i in [4,9]
    if portrait:
        scales(d,178,395,260)
        rtl(d,'مقرر التنفيذ الجبري',505,337,25,'#d6e3dc')
    else:
        scales(d,178,395,260)
        paragraph(d,'اقرأ القاعدة\nثم حلّل تطبيقها'.replace('\n',' '),490,744,30,370,'#d6e3dc',True)
    title_y=235
    title_lines=wrap(scene['title'],54,1170,True)
    if len(title_lines)>2:raise ValueError('Title exceeds two lines: '+scene['title'])
    for title in title_lines:
        rtl(d,title,1800,title_y,54,INK,True);title_y+=80
    top=max(410,title_y+40)
    if thinking:
        d.rounded_rectangle((620,top,1810,875),radius=24,fill='#eee4ce',outline='#dbc298',width=2)
        rtl(d,'وقفة للتفكير',1758,top+32,28,GOLD,True)
        prompt=scene.get('prompt','اكتب الفارق الذي بني عليه هذا الجزء من الدرس، وحدد موضع استنادك من الكتاب.')
        paragraph(d,prompt,1758,top+100,42,1070,INK,True)
    elif scene['kind'] in ['compare','sequence','map']:
        bullets=scene['bullets'];bw=360;gap=34
        for n,text in enumerate(bullets):
            right=1810-n*(bw+gap);left=right-bw
            active=n==stage
            d.rounded_rectangle((left,top,right,top+345),radius=22,fill='#e9efe6' if active else '#ffffff',outline=GOLD if active else '#d5ded8',width=3 if active else 2)
            d.text((left+30,top+25),str(n+1).zfill(2),font=font(33,True),fill=GOLD)
            paragraph(d,text,right-28,top+103,36,bw-56,INK,True)
            if scene['kind']=='sequence' and n<len(bullets)-1:
                cx=left-15;cy=top+170;d.line((cx-12,cy,cx+12,cy),fill=GOLD,width=4);d.polygon([(cx-12,cy),(cx-3,cy-9),(cx-3,cy+9)],fill=GOLD)
    else:
        for n,text in enumerate(scene['bullets']):
            y=top+n*142;active=n==stage
            d.rounded_rectangle((625,y,1810,y+120),radius=17,fill='#e9efe6' if active else '#fff',outline=GOLD if active else '#d5ded8',width=3 if active else 1)
            d.ellipse((1732,y+34,1782,y+84),fill=INK if active else '#e9eee7')
            rtl(d,str(n+1),1757,y+42,24,'#fff' if active else INK,True,anchor='ma')
            paragraph(d,text,1690,y+26,36,1000,INK,True,spacing=1.25)
    d.line((110,972,1810,972),fill='#d5ded8',width=2)
    rtl(d,'مقرر التنفيذ الجبري · المادة العلمية',1800,998,22,MUTED)
    a,b=scene['refs'];d.text((110,1003),f'SOURCE {a}–{b}',font=font(20),fill=MUTED)
    return im

async def speak(text, path):
    metadata=path.with_suffix('.json')
    if path.exists() and metadata.exists():return json.loads(metadata.read_text())
    import edge_tts
    boundaries=[]
    for attempt in range(2):
        try:
            communicate=edge_tts.Communicate(text,VOICE,rate=SPEECH_RATE,pitch=SPEECH_PITCH,boundary='WordBoundary',receive_timeout=120)
            with path.open('wb') as audio:
                async for chunk in communicate.stream():
                    if chunk['type']=='audio':audio.write(chunk['data'])
                    elif chunk['type']=='WordBoundary':boundaries.append({'start':chunk['offset']/1e7,'end':(chunk['offset']+chunk['duration'])/1e7,'text':html.unescape(chunk['text'])})
            if path.stat().st_size<1000 or not boundaries:raise ValueError('Speech or word timing missing')
            metadata.write_text(json.dumps(boundaries,ensure_ascii=False))
            return boundaries
        except Exception:
            boundaries=[]
            if attempt:raise
            await asyncio.sleep(5)

def save_wav(path, samples):
    with wave.open(str(path),'wb')as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(samples.astype('<i2').tobytes())

def read_wav(path):
    with wave.open(str(path),'rb')as w:
        assert w.getframerate()==SR and w.getnchannels()==1
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()

def group_captions(words):
    groups=[];group=[]
    for word in words:
        candidate=' '.join(w['text'] for w in group+[word])
        if group and (len(candidate)>68 or word['end']-group[0]['start']>6.0):
            groups.append({'start':group[0]['start'],'end':group[-1]['end']+.12,'text':' '.join(w['text']for w in group)});group=[]
        group.append(word)
    if group:groups.append({'start':group[0]['start'],'end':group[-1]['end']+.12,'text':' '.join(w['text']for w in group)})
    return groups

def stamp(seconds, comma=False):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02}{"," if comma else "."}{ms:03}'

def write_captions(cues, out):
    for index,cue in enumerate(cues):
        cue['start']=max(0,cue['start']);cue['end']=min(TARGET,cue['end'])
        if index+1<len(cues):cue['end']=min(cue['end'],cues[index+1]['start']-.01)
        assert cue['end']>cue['start']
    srt='\n\n'.join(f'{n}\n{stamp(c["start"],True)} --> {stamp(c["end"],True)}\n{c["text"]}'for n,c in enumerate(cues,1))+'\n'
    vtt='WEBVTT\n\n'+'\n\n'.join(f'{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}'for c in cues)+'\n'
    (out/'captions.srt').write_text(srt);(out/'captions.vtt').write_text(vtt)

def render_portraits(samples, selections, cache):
    sys.path.insert(0,str(ROOT/'presenter-production'))
    from lipsync import animate
    combined=np.concatenate([samples[round(start*SR):round((start+length)*SR)] for start,length in selections])
    audio=cache/'portrait-speech.wav';save_wav(audio,combined)
    raw=cache/'neural-portrait.mp4';evidence=animate(audio,raw)
    results=[];offset=0.0
    for n,(start,length) in enumerate(selections):
        destination=cache/f'presenter-{n:02}.mp4'
        run(['ffmpeg','-v','error','-y','-ss',offset,'-i',raw,'-t',length,'-vf','crop=600:900:150:70,scale=440:660,setsar=1','-an','-c:v','libx264','-preset','veryfast','-crf','20',destination])
        results.append((start,length,destination));offset+=length
    evidence['actualNeuralPortraitSeconds']=sum(length for _,length in selections)
    evidence['appearances']=[{'start':start,'seconds':length}for start,length in selections]
    return results,evidence


async def produce(unit, out):
    out.mkdir(parents=True,exist_ok=True);cache=out/'work';cache.mkdir(exist_ok=True)
    raw_parts=[];raw_total=0
    for i,scene in enumerate(unit['scenes']):
        if i%4==0:progress(unit['id'],f'Preparing speech {i+1}/{len(unit["scenes"])}')
        parts=[]
        for n,text in enumerate(scene['parts']):
            if text is None:
                parts.append({'hold':scene['hold']});continue
            if not text.strip():continue
            digest=hashlib.sha256((VOICE+SPEECH_RATE+SPEECH_PITCH+text).encode()).hexdigest()[:12]
            path=cache/f'speech-{i:02}-{n:02}-{digest}.mp3'
            words=await speak(text,path)
            wav=path.with_suffix('.wav')
            run(['ffmpeg','-v','error','-y','-i',path,'-ar',SR,'-ac','1',wav])
            samples=read_wav(wav);seconds=len(samples)/SR
            parts.append({'path':wav,'seconds':seconds,'words':words,'text':text});raw_total+=seconds
            print(f'VOICE scene={i+1} part={n+1} seconds={seconds:.3f}',flush=True)
            await asyncio.sleep(.4)
        raw_parts.append(parts)
    hold_total=sum(s.get('hold',0)for s in unit['scenes']);gap=.3;tail=1.0
    spoken_target=TARGET-hold_total-gap*len(unit['scenes'])-tail
    tempo=raw_total/spoken_target
    if not .82<=tempo<=1.32:raise ValueError(f'Narration needs editorial revision: tempo={tempo:.3f}, natural_seconds={raw_total:.2f}')
    progress(unit['id'],f'Speech complete; pacing {tempo:.3f}; composing 1200 seconds')
    audio=[];cues=[];timeline=[];clock=0
    for i,(scene,parts)in enumerate(zip(unit['scenes'],raw_parts)):
        start=clock;hold_ranges=[]
        for n,part in enumerate(parts):
            if 'hold'in part:
                seconds=part['hold'];hold_ranges.append([clock,clock+seconds]);cues.append({'start':clock,'end':clock+seconds,'text':'وقفة للتفكير — '+str(seconds)+' ثوانٍ'})
                samples=np.zeros(round(seconds*SR),dtype=np.int16)
            else:
                target_wav=cache/f'paced-{i:02}-{n:02}.wav'
                exact_samples=round(part['seconds']/tempo*SR)
                run(['ffmpeg','-v','error','-y','-i',part['path'],'-af',f'atempo={tempo:.9f},apad=whole_len={exact_samples},atrim=end_sample={exact_samples}',target_wav])
                samples=read_wav(target_wav)
                ratio=(len(samples)/SR)/part['seconds']
                words=[{'start':clock+w['start']*ratio,'end':clock+w['end']*ratio,'text':w['text']}for w in part['words']]
                cues.extend(group_captions(words))
            audio.append(samples);clock+=len(samples)/SR
        audio.append(np.zeros(round(gap*SR),dtype=np.int16));clock+=gap
        timeline.append({'start':start,'end':clock,'holds':hold_ranges,'title':scene['title'],'refs':scene['refs']})
    combined=np.concatenate(audio)
    desired=TARGET*SR
    if len(combined)>desired-round(.4*SR):raise ValueError('Speech exceeds the safe end margin')
    combined=np.pad(combined,(0,desired-len(combined)))
    save_wav(cache/'narration.wav',combined)
    write_captions(cues,out)
    transcript='\n\n'.join(s['title']+'\n'+s['spoken']for s in unit['scenes'])
    (out/'transcript.txt').write_text(unit['title']+'\n\n'+transcript+'\n')
    (out/'chapters.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{stamp(s["start"])} --> {stamp(s["end"])}\n{s["title"]}'for s in timeline)+'\n')
    # Each scene reveals emphasis in three stages; the thought pause has its own frame.
    entries=[]
    for i,(scene,timing)in enumerate(zip(unit['scenes'],timeline)):
        presenter=scene['kind']=='presenter' or i in [4,9]
        avatar_end=timing['start']+min(timing['end']-timing['start'],appearance_length(i,len(unit['scenes']),timing['end']-timing['start']))
        points=sorted(set([timing['start'],timing['end']]+([avatar_end]if presenter else [])+[timing['start']+(timing['end']-timing['start'])*f for f in [1/3,2/3]]+[p for pair in timing['holds']for p in pair]))
        for n,(a,b)in enumerate(zip(points,points[1:])):
            thinking=any(c<=a+.001<d for c,d in timing['holds'])
            stage=min(2,int(3*(a-timing['start'])/max(1,timing['end']-timing['start'])))
            image=cache/f'scene-{i:02}-{n:02}.png';slide(unit,scene,i,stage,thinking,presenter and a<avatar_end-.001).save(image)
            entries.extend([f"file '{image.resolve()}'",f'duration {b-a:.9f}'])
    if clock<TARGET:entries[-1]=f'duration {float(entries[-1].split()[1])+TARGET-clock:.9f}'
    entries.append(entries[-2]);(cache/'images.txt').write_text('\n'.join(entries)+'\n')
    slide(unit,unit['scenes'][0],0).save(out/'poster.jpg',quality=92)
    # Retain a contact sheet for actual visual inspection, without video decoding.
    thumbs=[]
    for i,scene in enumerate(unit['scenes']):
        im=slide(unit,scene,i,i%3).resize((480,270),Image.Resampling.LANCZOS);thumbs.append(im)
    sheet=Image.new('RGB',(1920,270*math.ceil(len(thumbs)/4)),PAPER)
    for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*480,(i//4)*270))
    sheet.save(out/'contact-sheet.jpg',quality=88)
    selections=[]
    for i,timing in enumerate(timeline):
        if unit['scenes'][i]['kind']=='presenter' or i in [4,9]:
            length=appearance_length(i,len(timeline),timing['end']-timing['start'])
            selections.append((timing['start'],length))
    progress(unit['id'],'Animating real portrait for the introduction and transitions')
    appearances,portrait_evidence=render_portraits(combined,selections,cache)
    command=['ffmpeg','-v','warning','-y','-filter_complex_threads','1','-f','concat','-safe','0','-i',cache/'images.txt']
    for start,length,path in appearances:command+=['-itsoffset',f'{start:.6f}','-i',path]
    audio_input=len(appearances)+1;subtitle_input=audio_input+1
    command+=['-i',cache/'narration.wav','-i',out/'captions.srt']
    filters=['[0:v]fps=25,format=yuv420p[base]'];previous='base'
    for n,(start,length,path)in enumerate(appearances,1):
        name=f'v{n}';filters.append(f"[{previous}][{n}:v]overlay=87:302:eof_action=pass:repeatlast=0:enable='between(t,{start:.6f},{start+length:.6f})'[{name}]");previous=name
    # Two-pass loudness measurement keeps the speech level consistent across files.
    analysis=subprocess.run(['ffmpeg','-v','info','-i',str(cache/'narration.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    measured=json.loads(analysis.stderr[analysis.stderr.rfind('{'):])
    loud=f'loudnorm=I=-16:TP=-1.5:LRA=9:measured_I={measured["input_i"]}:measured_TP={measured["input_tp"]}:measured_LRA={measured["input_lra"]}:measured_thresh={measured["input_thresh"]}:offset={measured["target_offset"]}:linear=true'
    filters.append(f'[{audio_input}:a]{loud},aresample=48000[a]')
    command+=['-filter_complex',';'.join(filters),'-map',f'[{previous}]','-map','[a]','-map',f'{subtitle_input}:s','-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','22','-pix_fmt','yuv420p','-r',FPS,'-c:a','aac','-b:a','96k','-c:s','mov_text','-metadata:s:s:0','language=ara','-metadata:s:a:0','language=ara','-metadata','title='+unit['title'],'-movflags','+faststart','-t',TARGET,'-threads','2',out/'lecture.mp4']
    run(command)
    progress(unit['id'],'Video encoded; checking duration, decoding, and captions')
    info=probe(out/'lecture.mp4');video=next(s for s in info['streams']if s['codec_type']=='video');sound=next(s for s in info['streams']if s['codec_type']=='audio')
    assert abs(float(info['format']['duration'])-TARGET)<.002,info['format']['duration']
    assert abs(float(video['duration'])-TARGET)<.002
    assert video['width']==W and video['height']==H and video['r_frame_rate']=='25/1'
    assert abs(float(sound['duration'])-TARGET)<.03
    assert int(info['format']['size'])<95_000_000,'Video exceeds repository file budget'
    assert len(cues)>100 and max(c['end']for c in cues)<=TARGET
    run(['ffmpeg','-v','error','-i',out/'lecture.mp4','-map','0:v:0','-map','0:a:0','-f','null','-'])
    silence=subprocess.run(['ffmpeg','-v','info','-i',str(out/'lecture.mp4'),'-af','silencedetect=n=-45dB:d=3','-vn','-f','null','-'],capture_output=True,text=True,check=True)
    lengths=[float(v)for v in re.findall(r'silence_duration: ([0-9.]+)',silence.stderr)]
    assert max(lengths,default=0)<18,'Unplanned prolonged silence detected'
    report={'status':'PASS','unit':unit['id'],'title':unit['title'],'durationSeconds':float(info['format']['duration']),'videoDurationSeconds':float(video['duration']),'audioDurationSeconds':float(sound['duration']),'frames':video.get('nb_frames'),'resolution':[W,H],'fps':25,'voice':VOICE,'naturalSpeechSeconds':round(raw_total,3),'tempo':round(tempo,6),'plannedThinkingSeconds':hold_total,'captionCues':len(cues),'maximumDetectedSilenceSeconds':max(lengths,default=0),'fileBytes':int(info['format']['size']),'source':'مقرر التنفيذ الجبري','chapters':timeline,'loudnessMeasurement':measured,'decodeCheck':'PASS'}
    report['sourceCommit']=os.environ.get('GITHUB_SHA')
    report['narrationProfile']={key:NARRATION_PROFILE[key] for key in ['id','voice','rate','pitch','selectedBy']}
    report['pronunciationTerms']=len(NARRATION_PROFILE['terms'])
    report['speakingPortrait']=portrait_evidence
    run(['ffmpeg','-v','error','-y','-ss','2','-i',out/'lecture.mp4','-frames:v','1',out/'poster.jpg'])
    assert not any(name in transcript for name in ['أحمد خليل','ياسين شامي','شامي ياسين'])
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('COMPLETE '+json.dumps({k:v for k,v in report.items()if k not in ['chapters','loudnessMeasurement']},ensure_ascii=False),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--unit',type=int,default=1);parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    unit=assemble(runpy.run_path(str(HERE/f'unit_{args.unit:02}.py'))['UNIT']);out=ROOT/'rendered'/f'unit-{args.unit:02}'
    out.mkdir(parents=True,exist_ok=True)
    if args.preview:
        for i in [0,1,7,len(unit['scenes'])-1]:slide(unit,unit['scenes'][i],i).save(out/f'preview-{i:02}.png')
        print(json.dumps({'unit':args.unit,'words':sum(len(s['spoken'].split())for s in unit['scenes']),'scenes':len(unit['scenes'])}))
        return
    try:asyncio.run(produce(unit,out))
    except Exception as exc:
        (out/'report.json').write_text(json.dumps({'status':'FAIL','unit':args.unit,'error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc()},ensure_ascii=False,indent=2));raise

if __name__=='__main__':main()
