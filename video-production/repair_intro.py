"""Revise an introduction while preserving the measured 20-minute lecture."""
import asyncio,json,os,re,runpy,shutil,subprocess,sys,traceback
from pathlib import Path
import numpy as np
import produce as g
from review import review
ROOT=g.ROOT
sys.path.insert(0,str(ROOT/'presenter-production'))
from lipsync import animate

def seconds(stamp):
 h,m,s=stamp.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)

async def repair(n):
 out=ROOT/'rendered'/f'unit-{n:02}';work=out/'work';work.mkdir(parents=True,exist_ok=True)
 branch=f'course-release-unit-{n}';g.run(['git','fetch','origin',branch]);prefix=f'media/unit-{n:02}/'
 for name in ['lecture.mp4','captions.srt','captions.vtt','chapters.vtt','transcript.txt','poster.jpg','contact-sheet.jpg','report.json']:
  (out/name).write_bytes(subprocess.check_output(['git','show',f'origin/{branch}:{prefix}{name}']))
 report=json.loads((out/'report.json').read_text());assert report['status']=='PASS' and report['durationSeconds']==1200
 unit=g.assemble(runpy.run_path(str(ROOT/f'video-production/unit_{n:02}.py'))['UNIT']);text=unit['scenes'][0]['spoken']
 assert not any(word in text for word in ['أستاذ','دكتور','خليل','شامي'])
 end=report['chapters'][0]['end'];target=end-.3
 g.progress(n,'Refining the neutral course introduction and its exact lip synchronization')
 mp3=work/'new-intro.mp3';words=await g.speak(text,mp3)
 raw=work/'raw-intro.wav';g.run(['ffmpeg','-v','error','-y','-i',mp3,'-ar',g.SR,'-ac','1',raw]);natural=len(g.read_wav(raw))/g.SR
 pace=natural/target;count=round(target*g.SR);paced=work/'paced-intro.wav'
 g.run(['ffmpeg','-v','error','-y','-i',raw,'-af',f'atempo={pace:.9f},apad=whole_len={count},atrim=end_sample={count}',paced])
 old=work/'previous.mp4';shutil.move(out/'lecture.mp4',old)
 oldwav=work/'previous.wav';g.run(['ffmpeg','-v','error','-y','-i',old,'-vn','-ar',g.SR,'-ac','1','-af','apad=whole_dur=1200,atrim=duration=1200',oldwav])
 audio=g.read_wav(oldwav);assert len(audio)==1200*g.SR
 intro=g.read_wav(paced).astype(float)
 old_rms=np.sqrt(np.mean(audio[:count].astype(float)**2));new_rms=np.sqrt(np.mean(intro**2));intro=np.clip(intro*old_rms/max(1,new_rms),-32000,32000).astype(np.int16)
 audio[:count]=intro;audio[count:round(end*g.SR)]=0;g.save_wav(work/'narration.wav',audio)
 cues=[]
 for block in (out/'captions.srt').read_text().strip().split('\n\n'):
  lines=block.splitlines();start,stop=lines[1].split(' --> ')
  if seconds(start)>=end-.001:cues.append({'start':seconds(start),'end':seconds(stop),'text':' '.join(lines[2:])})
 ratio=target/natural;newcues=g.group_captions([{'start':w['start']*ratio,'end':w['end']*ratio,'text':w['text']}for w in words])
 cues=newcues+cues;g.write_captions(cues,out)
 sections=(out/'transcript.txt').read_text().strip().split('\n\n');sections[1]=unit['scenes'][0]['title']+'\n'+text;(out/'transcript.txt').write_text('\n\n'.join(sections)+'\n')
 g.save_wav(work/'face-audio.wav',audio[:18*g.SR]);evidence=animate(work/'face-audio.wav',work/'face.mp4')
 analysis=subprocess.run(['ffmpeg','-v','info','-i',str(work/'narration.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 measured=json.loads(analysis.stderr[analysis.stderr.rfind('{'):])
 loud=f'loudnorm=I=-16:TP=-1.5:LRA=9:measured_I={measured["input_i"]}:measured_TP={measured["input_tp"]}:measured_LRA={measured["input_lra"]}:measured_thresh={measured["input_thresh"]}:offset={measured["target_offset"]}:linear=true'
 filters=f"[1:v]crop=600:900:150:70,scale=440:660,setsar=1[face];[0:v][face]overlay=87:302:eof_action=pass:repeatlast=0:enable='between(t,0,18)'[v];[2:a]{loud},aresample=48000[a]"
 g.run(['ffmpeg','-v','warning','-y','-filter_complex_threads','1','-i',old,'-i',work/'face.mp4','-i',work/'narration.wav','-i',out/'captions.srt','-filter_complex',filters,'-map','[v]','-map','[a]','-map','3:s','-map_metadata','-1','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','96k','-c:s','mov_text','-metadata:s:s:0','language=ara','-metadata:s:a:0','language=ara','-metadata','title='+unit['title'],'-movflags','+faststart','-t','1200','-threads','2',out/'lecture.mp4'])
 info=g.probe(out/'lecture.mp4');video=next(s for s in info['streams']if s['codec_type']=='video');sound=next(s for s in info['streams']if s['codec_type']=='audio')
 assert float(info['format']['duration'])==1200 and int(video['nb_frames'])==30000 and video['width']==1920 and video['height']==1080
 assert abs(float(sound['duration'])-1200)<.03 and int(info['format']['size'])<95000000
 g.run(['ffmpeg','-v','error','-i',out/'lecture.mp4','-map','0:v:0','-map','0:a:0','-f','null','-'])
 g.run(['ffmpeg','-v','error','-y','-ss','2','-i',out/'lecture.mp4','-frames:v','1',out/'poster.jpg'])
 original_natural=report['naturalSpeechSeconds'];original_tempo=report['tempo']
 report['naturalSpeechSeconds']=round(original_natural-target*original_tempo+natural,3)
 report['tempo']=round(report['naturalSpeechSeconds']/(original_natural/original_tempo),6)
 report.update({'captionCues':len(cues),'fileBytes':int(info['format']['size']),'sourceCommit':os.environ.get('GITHUB_SHA'),'loudnessMeasurement':measured})
 report['speakingPortrait']['mouthMotionDifferences']=evidence['mouthMotionDifferences']
 report['introRevision']={'description':'Neutral course wording without references to an instructor','durationSeconds':end,'speechSeconds':target,'naturalSeconds':natural,'tempo':pace,'bodyTimingsPreserved':True}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 review(out)

if __name__=='__main__':
 n=int(sys.argv[1])
 try:asyncio.run(repair(n))
 except Exception as exc:
  out=ROOT/'rendered'/f'unit-{n:02}';out.mkdir(parents=True,exist_ok=True)
  (out/'report.json').write_text(json.dumps({'status':'FAIL','unit':n,'error':str(exc),'traceback':traceback.format_exc()},ensure_ascii=False,indent=2));raise
