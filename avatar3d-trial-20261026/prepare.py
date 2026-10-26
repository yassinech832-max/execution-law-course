"""Prepare an independently reviewable 90-second lesson and a licensed 3D actor."""
from pathlib import Path
import asyncio,html,json,os,re,shutil,subprocess,sys,urllib.request,zipfile,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
OUT=ROOT/'avatar3d-output/prepared';OUT.mkdir(parents=True,exist_ok=True)
PIN='0943055db6ec570bcef9f2c8b41c9e5467c808f9'
BASE=f'https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/{PIN}/'
CHAR='Assets/Avatars/Professions/Business_Male_03/'
PARTS=[
 'مرحباً بكم في مقرر التنفيذ الجبري. نبدأ بسؤال: هل تكفي ورقة تثبت وجود الدين، حتى تبدأ إجراءات التنفيذ؟ يبين المقرر أن إثبات الحق وحده لا يكفي. فالسند التنفيذي كتابة منحها التشريع هذه الصفة، وفق شروطه الموضوعية والشكلية.',
 'ولفهم ذلك، نميز بين الحق الموضوعي والحق في التنفيذ الجبري. للحق الموضوعي مصادر متعددة، كالعقد والفعل الضار. أما الحق في التنفيذ الجبري فمصدره السند التنفيذي. لذلك، لا نجعل السؤال عن وجود الحق هو نفسه السؤال عن السند اللازم لاقتضائه جبراً.',
 'وعند قراءة أي واقعة، اسأل: هل يوجد حق ثابت؟ وفي أي كتابة ثبت؟ وهل منح التشريع هذه الكتابة الصفة التنفيذية؟ لا يكفي اتفاق الأطراف وحده لإضافة سند جديد إلى السندات التي يعترف بها التشريع. تأمل الآن: ما الفرق بين ورقة تثبت الدين، وسند يتيح طلب الحماية التنفيذية؟ دوّن إجابتك، ثم ارجع إلى النص المرجعي.'
]
TITLES=['لماذا يلزم سند تنفيذي؟','حقّان ينبغي التمييز بينهما','ثلاثة أسئلة قبل طلب التنفيذ']
def run(args,**kw):return subprocess.run([str(v) for v in args],check=True,**kw)
def download(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(url,timeout=180) as response,path.open('wb') as file:shutil.copyfileobj(response,file)
def status(message,state='pending'):
 if not os.getenv('GITHUB_TOKEN'):return
 data=json.dumps({'state':state,'context':'avatar3d/preparation','description':message[:140]}).encode()
 req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=data,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=15) as r:r.read()
 except Exception:pass
async def main():
 sys.path.insert(0,str(ROOT/'video-production'));import produce as g
 assert g.VOICE=='ar-KW-FahedNeural' and g.NARRATION_PROFILE['id']=='D'
 work=ROOT/'avatar3d-work';work.mkdir(exist_ok=True);asset=work/'actor';asset.mkdir(exist_ok=True)
 status('Preparing a licensed suit-clad 3D character and facial animation data')
 names=['Export/Business_Male_03_facial.fbx']+[f'Textures/m020_{part}_{kind}.tga' for part in ['body','head'] for kind in ['color','normal']]+['Textures/m020_opacity_color.tga']
 for name in names:download(BASE+CHAR+name,asset/name)
 motions=['m_gestic_talk_neutral_01.max.fbx','m_gestic_presentation_right_01.max.fbx']
 for name in motions:download(BASE+'Assets/Animations/all_animations_max_motextr_static/'+name,asset/name)
 download(BASE+'LICENSE.md',OUT/'THIRD_PARTY_LICENSE.txt')
 blender=Path(shutil.which('blender')).resolve();env=dict(os.environ);env['OCIO']=str(blender.parent/'3.6/datafiles/colormanagement/config.ocio')
 run([blender,'--background','--factory-startup','--python-exit-code','1','--python',HERE/'convert.py','--',asset,OUT],stdout=sys.stdout,stderr=sys.stderr,env=env)
 assert (OUT/'professor.glb').exists() and (OUT/'model-report.json').exists(),'3D conversion did not produce a rigged model'
 status('Generating voice D with source-grounded lesson text and word timings')
 raw=[];total=0
 for i,text in enumerate(PARTS):
  path=work/f'part-{i}.mp3';words=await g.speak(g.narration_text(text),path)
  wav=path.with_suffix('.wav');run(['ffmpeg','-v','error','-y','-i',path,'-ar','24000','-ac','1',wav])
  samples=g.read_wav(wav);duration=len(samples)/24000;raw.append((wav,words,duration));total+=duration
 tempo=total/83.4;assert .78<=tempo<=1.28,('Editorial pacing required',tempo,total)
 sound=[np.zeros(9600,dtype=np.int16)];clock=.4;cues=[];scenes=[];allwords=[]
 for i,(wav,words,duration) in enumerate(raw):
  start=clock;count=round(duration/tempo*24000);paced=work/f'paced-{i}.wav'
  run(['ffmpeg','-v','error','-y','-i',wav,'-af',f'atempo={tempo:.9f},apad=whole_len={count},atrim=end_sample={count}',paced]);samples=g.read_wav(paced)
  ratio=len(samples)/24000/duration;timed=[{'start':clock+w['start']*ratio,'end':clock+w['end']*ratio,'text':w['text']} for w in words]
  allwords.extend(timed);cues.extend(g.group_captions(timed));sound.append(samples);clock+=len(samples)/24000
  scenes.append({'start':start if i else 0,'speechEnd':clock,'end':clock+.4,'title':TITLES[i],'text':PARTS[i]})
  sound.append(np.zeros(9600,dtype=np.int16));clock+=.4
 combined=np.concatenate(sound);assert len(combined)<90*24000
 combined=np.pad(combined,(0,90*24000-len(combined)));g.save_wav(work/'raw.wav',combined)
 analysis=subprocess.run(['ffmpeg','-v','info','-i',str(work/'raw.wav'),'-af','loudnorm=I=-18:TP=-2:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 measured=json.loads(analysis.stderr[analysis.stderr.rfind('{'):]);gain=-18-float(measured['input_i'])
 run(['ffmpeg','-v','error','-y','-i',work/'raw.wav','-af',f'volume={gain:.4f}dB','-ar','24000','-ac','1',OUT/'narration.wav'])
 g.write_captions(cues,OUT);scenes[-1]['end']=90
 (OUT/'transcript.txt').write_text('\n\n'.join(PARTS)+'\n')
 report={'status':'PASS','voice':'D','voiceId':g.VOICE,'durationSeconds':90,'tempo':tempo,'scenes':scenes,'words':allwords,'sourceParagraphs':[37,38,40],'source':'المادة العلمية لمقرر التنفيذ الجبري','humanListeningReview':False,'actor':'Microsoft Rocketbox Business Male 03','actorLicense':'MIT','actorSourceCommit':PIN,'sourceCommit':os.getenv('GITHUB_SHA')}
 (OUT/'lesson.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 status('Deriving mouth positions from the actual Arabic narration')
 archive=work/'rhubarb.zip';download('https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-Linux.zip',archive)
 with zipfile.ZipFile(archive) as z:z.extractall(work/'rhubarb')
 executable=next((work/'rhubarb').rglob('rhubarb'));executable.chmod(0o755)
 run(['ffmpeg','-v','error','-y','-i',OUT/'narration.wav','-ar','16000','-ac','1',work/'phonetic.wav'])
 run([executable,'-r','phonetic','-f','json','-o',OUT/'mouth.json',work/'phonetic.wav'])
 mouth=json.loads((OUT/'mouth.json').read_text());assert len(mouth['mouthCues'])>100
 report['mouthCues']=len(mouth['mouthCues']);(OUT/'lesson.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 status('3D model, 90-second D narration and phonetic mouth timings ready','success')
if __name__=='__main__':
 try:asyncio.run(main())
 except Exception as exc:
  (OUT/'failure.json').write_text(json.dumps({'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}));status(str(exc),'failure');raise
