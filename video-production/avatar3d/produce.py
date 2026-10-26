"""Rebuild seven offline lectures while preserving published audio and source text."""
from pathlib import Path
import argparse,hashlib,json,math,os,re,runpy,shutil,subprocess,sys,traceback,urllib.request,wave
from PIL import Image
from slides import slide
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'video-production'))
import produce as original

def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def plain(s):return re.sub(r'\s+',' ',re.sub(r'[\u064b-\u065f\u0670\u0640]','',s)).strip()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def status(n,text,state='pending'):
    if not os.environ.get('GITHUB_TOKEN'):return
    req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=json.dumps({'state':state,'context':f'course/avatar3d-{n}','description':text[:140]}).encode(),headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:r.read()
    except Exception as e:print('Status update unavailable',type(e).__name__,flush=True)

def prepare(n):
    source=ROOT/'media'/f'unit-{n:02}';out=ROOT/'rendered-3d'/f'unit-{n:02}';work=out/'work';work.mkdir(parents=True,exist_ok=True)
    unit=original.assemble(runpy.run_path(str(ROOT/'video-production'/f'unit_{n:02}.py'))['UNIT'])
    previous=json.loads((source/'report.json').read_text());timeline=previous['chapters']
    transcript=unit['title']+'\n\n'+'\n\n'.join(s['title']+'\n'+s['spoken'] for s in unit['scenes'])+'\n'
    assert plain(transcript)==plain((source/'transcript.txt').read_text()),'Published wording changed'
    assert previous['voice']=='ar-KW-FahedNeural' and previous['durationSeconds']==1200
    assert len(timeline)==len(unit['scenes'])
    assert all(t['title']==s['title'] for t,s in zip(timeline,unit['scenes']))
    for name in ['transcript.txt','captions.srt','captions.vtt','chapters.vtt']:shutil.copy2(source/name,out/name)
    appearances=[];offset=0
    for i,t in enumerate(timeline):
        if unit['scenes'][i]['kind']=='presenter' or i in [4,9]:
            length=original.appearance_length(i,len(timeline),t['end']-t['start'])
            assert abs(length*25-round(length*25))<1e-6
            appearances.append({'index':i,'start':t['start'],'seconds':length,'offset':offset});offset+=length
    entries=[];student=[];thumbs=[]
    for i,(scene,timing) in enumerate(zip(unit['scenes'],timeline)):
        student.extend([scene['title'],*scene['bullets']]);t0,t1=timing['start'],timing['end']
        appearance=next((a for a in appearances if a['index']==i),None)
        points=sorted(set([t0,t1]+([t0+appearance['seconds']] if appearance else [])+[t0+(t1-t0)*f for f in [1/3,2/3]]+[p for hold in timing['holds'] for p in hold]))
        for j,(a,b) in enumerate(zip(points,points[1:])):
            thinking=any(c<=a+.001<d for c,d in timing['holds']);stage=min(2,int(3*(a-t0)/max(1,t1-t0)))
            image=work/f'scene-{i:02}-{j:02}.png';slide(unit,scene,i,stage,thinking).save(image)
            entries += [f"file '{image.resolve()}'",f'duration {b-a:.9f}']
            if thinking:student.append(scene.get('prompt','اكتب الفارق الذي بُني عليه هذا الجزء من الدرس، وحدد موضع استنادك من الكتاب.'))
        thumbs.append(slide(unit,scene,i,i%3).resize((480,270),Image.Resampling.LANCZOS))
    entries[-1]=f'duration {float(entries[-1].split()[1])+1200-timeline[-1]["end"]:.9f}'
    entries.append(entries[-2]);(work/'images.txt').write_text('\n'.join(entries)+'\n')
    sheet=Image.new('RGB',(1920,270*math.ceil(len(thumbs)/4)),'#10283e')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*480,(i//4)*270))
    sheet.save(out/'contact-sheet.jpg',quality=90)
    (out/'student-visible.txt').write_text('\n'.join(student))
    for i in [0,min(4,len(unit['scenes'])-1),len(unit['scenes'])-1]:slide(unit,unit['scenes'][i],i,0).save(out/f'slide-review-{i:02}.jpg',quality=91)
    runtime=ROOT/'avatar3d-output/runtime';runtime.mkdir(parents=True,exist_ok=True)
    (runtime/'performance.json').write_text(json.dumps({'unit':n,'appearances':appearances},indent=2))
    audio=[];sr=16000
    for i,a in enumerate(appearances):
        p=work/f'speech-{i}.wav'
        run(['ffmpeg','-v','error','-y','-ss',f'{a["start"]:.9f}','-i',source/'lecture.mp4','-t',a['seconds'],'-vn','-ar',sr,'-ac','1',p])
        with wave.open(str(p),'rb') as w:
            data=w.readframes(w.getnframes());expected=round(a['seconds']*sr)*2;data=(data+b'\0'*expected)[:expected];audio.append(data)
    with wave.open(str(work/'speech.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(audio))
    status(n,'Arabic boards ready; synchronizing the 3D professor to the original D audio')
    run([ROOT/'avatar3d-runtime/rhubarb/rhubarb','-r','phonetic','-f','json','--extendedShapes','GHX','-o',runtime/'mouth.json',work/'speech.wav'])
    (out/'preparation.json').write_text(json.dumps({'unit':n,'sourceCommit':os.environ.get('SOURCE_MAIN'),'appearances':appearances,'audioSource':str(source/'lecture.mp4'),'publishedTextPreserved':True,'sidecarHashes':{name:sha(source/name) for name in ['transcript.txt','captions.srt','captions.vtt','chapters.vtt']}},indent=2))
    return unit,previous,appearances

def audio_hash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()

def compose(n):
    source=ROOT/'media'/f'unit-{n:02}';out=ROOT/'rendered-3d'/f'unit-{n:02}';work=out/'work'
    previous=json.loads((source/'report.json').read_text());prep=json.loads((out/'preparation.json').read_text());appearances=prep['appearances']
    status(n,'3D appearances rendered; composing the complete 20:00 lesson')
    command=['ffmpeg','-v','warning','-y','-filter_complex_threads','1','-f','concat','-safe','0','-i',work/'images.txt']
    for i,a in enumerate(appearances):command+=['-itsoffset',f'{a["start"]:.9f}','-i',work/f'actor-{i}.mp4']
    audio_index=1+len(appearances);sub_index=audio_index+1;command+=['-i',source/'lecture.mp4','-i',out/'captions.srt']
    filters=['[0:v]fps=25,format=yuv420p[base]'];prior='base'
    for i,a in enumerate(appearances,1):
        dest=f'v{i}';filters.append(f"[{prior}][{i}:v]overlay=0:88:eof_action=pass:repeatlast=0:enable='gte(t,{a['start']:.9f})*lt(t,{a['start']+a['seconds']:.9f})'[{dest}]");prior=dest
    license_text=(ROOT/'avatar3d-output/runtime/THIRD_PARTY_LICENSE.txt').read_text()
    command+=['-filter_complex',';'.join(filters),'-map',f'[{prior}]','-map',f'{audio_index}:a:0','-map',f'{sub_index}:s:0','-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','22','-pix_fmt','yuv420p','-r','25','-c:a','copy','-c:s','mov_text','-metadata:s:s:0','language=ara','-metadata:s:a:0','language=ara','-metadata','title='+previous['title'],'-metadata','copyright=3D model: Copyright (c) 2020 Microsoft; MIT License','-metadata','comment='+license_text,'-movflags','+faststart','-t','1200','-threads','2',out/'lecture.mp4']
    run(command)
    status(n,'Checking 20:00 duration, original audio, decoding and captions')
    info=probe(out/'lecture.mp4');v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert float(info['format']['duration'])==1200 and float(v['duration'])==1200
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1920,1080,'25/1',30000)
    assert abs(float(a['duration'])-1200)<.03
    assert (out/'lecture.mp4').stat().st_size<95_000_000
    assert audio_hash(source/'lecture.mp4')==audio_hash(out/'lecture.mp4'),'Published audio altered'
    assert all(sha(out/name)==digest for name,digest in prep['sidecarHashes'].items())
    run(['ffmpeg','-v','error','-i',out/'lecture.mp4','-map','0:v:0','-map','0:a:0','-f','null','-'])
    for j,t in enumerate([2,30,previous['chapters'][4]['start']+2,previous['chapters'][9]['start']+2,previous['chapters'][-1]['start']+2]):
        name='poster.jpg' if j==0 else f'frame-{j:02}.jpg'
        run(['ffmpeg','-v','error','-y','-ss',f'{t:.6f}','-i',out/'lecture.mp4','-frames:v','1','-q:v','2',out/name])
    pictures=[]
    for name in ['poster.jpg','frame-01.jpg','frame-02.jpg','frame-03.jpg','frame-04.jpg']:
        with Image.open(out/name) as im:pictures.append(im.resize((640,360)))
    sheet=Image.new('RGB',(1920,720),'#10283e')
    for i,im in enumerate(pictures):sheet.paste(im,((i%3)*640,(i//3)*360))
    sheet.save(out/'qa-frames.jpg',quality=91)
    avatar=json.loads((out/'avatar-evidence.json').read_text());assert avatar['true3D'] and avatar['bones']>=20 and avatar['mouthCues']>100
    report={k:v for k,v in previous.items() if k not in ['speakingPortrait','sampleRecognition','finalVideoFrameSamples','visualReviewContactSheet','reviewCommit']}
    report.update({'status':'PASS','sourceCommit':os.environ.get('GITHUB_SHA'),'sourceMain':os.environ.get('SOURCE_MAIN'),'style':'approved-3d-professor-20261027','true3D':True,'avatar':avatar,'originalAudioPreserved':True,'originalAudioHash':audio_hash(source/'lecture.mp4'),'publishedTextPreserved':True,'sidecarsPreserved':True,'fileBytes':(out/'lecture.mp4').stat().st_size,'sha256':sha(out/'lecture.mp4'),'decodeCheck':'PASS','visualReviewContactSheet':'qa-frames.jpg','humanListeningReview':False})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    shutil.copy2(ROOT/'avatar3d-output/runtime/THIRD_PARTY_LICENSE.txt',out/'THIRD_PARTY_LICENSE.txt')
    status(n,'20:00; approved 3D professor; original D audio and source text preserved','success')

def retain(n):
    out=ROOT/'rendered-3d'/f'unit-{n:02}';branch=f'avatar3d-release-unit-{n}-20261027';target=Path(f'/tmp/avatar3d-retain-{n}')
    fetched=subprocess.run(['git','fetch','origin',branch],cwd=ROOT).returncode==0
    if target.exists():run(['git','worktree','remove','--force',target],cwd=ROOT)
    run(['git','worktree','add','--detach',target,'origin/'+branch if fetched else os.environ['GITHUB_SHA']],cwd=ROOT)
    if not fetched:
        run(['git','checkout','--orphan',branch],cwd=target);run(['git','rm','-rf','.'],cwd=target)
    dest=target/'media'/f'unit-{n:02}';dest.mkdir(parents=True,exist_ok=True)
    for p in out.iterdir():
        if p.is_file() and p.suffix in ['.mp4','.json','.jpg','.txt','.vtt','.srt','.log']:shutil.copy2(p,dest/p.name)
    run(['git','add',str(dest.relative_to(target))],cwd=target)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=target).returncode:
        run(['git','-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m',f'Retain the complete approved 3D lecture for unit {n}'],cwd=target)
        run(['git','push','origin',f'HEAD:refs/heads/{branch}'],cwd=target)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','compose','retain']);parser.add_argument('unit',type=int);args=parser.parse_args()
    try:globals()[args.phase](args.unit)
    except Exception as e:
        out=ROOT/'rendered-3d'/f'unit-{args.unit:02}';out.mkdir(parents=True,exist_ok=True)
        (out/'failure.json').write_text(json.dumps({'status':'FAIL','unit':args.unit,'error':str(e),'traceback':traceback.format_exc()}));status(args.unit,str(e),'failure');raise
