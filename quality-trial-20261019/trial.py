"""Isolated Arabic legal narration and genuine portrait animation comparison."""
import argparse,asyncio,importlib.util,json,os,re,shutil,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'quality-output'
PLAIN='السند التنفيذي مصدر الحق في التنفيذ الجبري. ونميز بين الحق الموضوعي والحق في التنفيذ. ومن مصطلحات المقرر: الصيغة التنفيذية، ومحل التنفيذ، وحجز ما للمدين لدى الغير، والبيع الجبري، وتوزيع حصيلة التنفيذ.'
CAREFUL='السَّنَدُ التَّنْفِيذِيُّ مَصْدَرُ الْحَقِّ فِي التَّنْفِيذِ الْجَبْرِيِّ. وَنُمَيِّزُ بَيْنَ الْحَقِّ الْمَوْضُوعِيِّ وَالْحَقِّ فِي التَّنْفِيذِ. وَمِنْ مُصْطَلَحَاتِ الْمُقَرَّرِ: الصِّيغَةُ التَّنْفِيذِيَّةُ، وَمَحَلُّ التَّنْفِيذِ، وَحَجْزُ مَا لِلْمَدِينِ لَدَى الْغَيْرِ، وَالْبَيْعُ الْجَبْرِيُّ، وَتَوْزِيعُ حَصِيلَةِ التَّنْفِيذِ.'
INTRO='مَرْحَبًا بِكُمْ فِي مُقَرَّرِ التَّنْفِيذِ الْجَبْرِيِّ. نَبْدَأُ بِالسَّنَدِ التَّنْفِيذِيِّ، وَنُمَيِّزُ بَيْنَ الْحَقِّ الْمَوْضُوعِيِّ وَالْحَقِّ فِي التَّنْفِيذِ.'
TERMS=['السند التنفيذي','التنفيذ الجبري','الحق الموضوعي','الصيغة التنفيذية','محل التنفيذ','حجز ما للمدين لدى الغير','البيع الجبري','توزيع حصيلة التنفيذ']
def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],text=True))
def seconds(path):return float(probe(path)['format']['duration'])
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def plain(text):return re.sub(r'[\u064b-\u065f\u0670\u0640]','',text).replace('أ','ا').replace('إ','ا').replace('آ','ا')
async def speak(text,voice,path,rate='+0%',pitch='+0Hz'):
 import edge_tts
 for attempt in range(3):
  try:
   cues=[]
   with path.open('wb') as file:
    async for part in edge_tts.Communicate(text,voice,rate=rate,pitch=pitch,boundary='WordBoundary',receive_timeout=120).stream():
     if part['type']=='audio':file.write(part['data'])
     elif part['type'] in ('WordBoundary','SentenceBoundary'):cues.append({'start':part['offset']/1e7,'end':(part['offset']+part['duration'])/1e7,'text':part['text']})
   assert path.stat().st_size>2000
   return cues
  except Exception:
   if attempt==2:raise
   await asyncio.sleep(2)
async def audio():
 out=OUT/'audio';out.mkdir(parents=True,exist_ok=True)
 baseline=PLAIN
 for ordinary,spoken in [('السند التنفيذي','السَّنَد التَّنفيذي'),('التنفيذ الجبري','التَّنفيذ الجَبْري'),('الصيغة التنفيذية','الصِّيغة التَّنفيذية'),('الحجز التحفظي','الحَجْز التَّحَفُّظي'),('البيع الجبري','البَيع الجَبْري')]:baseline=baseline.replace(ordinary,spoken)
 configs=[('A','ar-SA-HamedNeural',baseline,'+4%','+0Hz'),('B','ar-SA-HamedNeural',CAREFUL,'-6%','-1Hz'),('C','ar-QA-MoazNeural',CAREFUL,'-4%','-1Hz'),('D','ar-KW-FahedNeural',CAREFUL,'-4%','+0Hz')]
 report={'status':'PASS','source':'مقرر التنفيذ الجبري','sourceParagraphs':[37,38,40],'text':PLAIN,'candidates':[],'humanListeningReview':False,'note':'ASR checks word recovery; it does not prove correct vowels or naturalness.'}
 for label,voice,text,rate,pitch in configs:
  item={'id':label,'voice':voice,'rate':rate,'pitch':pitch}
  try:
   raw=out/(label+'-raw.mp3');cues=await speak(text,voice,raw,rate,pitch)
   run(['ffmpeg','-v','error','-y','-i',raw,'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','128k',out/(label+'.mp3')]);raw.unlink()
   item.update({'status':'PASS','seconds':seconds(out/(label+'.mp3')),'words':cues})
  except Exception as exc:item.update({'status':'FAIL','error':str(exc)})
  report['candidates'].append(item);save(out/'report.json',report)
 # All candidates read the same legal text. A is the production baseline.
 try:
  from faster_whisper import WhisperModel
  model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2)
  for item in report['candidates']:
   if item['status']!='PASS':continue
   segments,_=model.transcribe(str(out/(item['id']+'.mp3')),language='ar',beam_size=5,initial_prompt=PLAIN)
   transcript=' '.join(s.text for s in segments);item['asrTranscript']=transcript
   item['recoveredTerms']=[term for term in TERMS if plain(term) in plain(transcript)]
 except Exception as exc:report['recognitionError']=str(exc)
 eligible=[i for i in report['candidates'] if i['id']!='A' and i['status']=='PASS']
 assert eligible,'No alternative narration completed'
 # Lexical fidelity selects a trial voice, subject to the user's listening review.
 chosen=max(eligible,key=lambda i:(len(i.get('recoveredTerms',[])),{'B':2,'C':3,'D':1}[i['id']]))
 report['selectedTrial']=chosen['id'];report['selectionBasis']='Recovered legal terms, then preference for a new formal voice; not a human quality rating.'
 intro=out/'intro-raw.mp3';report['introWords']=await speak(INTRO,chosen['voice'],intro,chosen['rate'],chosen['pitch'])
 run(['ffmpeg','-v','error','-y','-i',intro,'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','16000','-ac','1',out/'intro.wav']);intro.unlink()
 report['introSeconds']=seconds(out/'intro.wav');report['introText']=plain(INTRO)
 (out/'transcript.txt').write_text(PLAIN+'\n\n'+plain(INTRO)+'\n')
 save(out/'report.json',report)
 print(json.dumps({k:v for k,v in report.items() if k!='candidates'},ensure_ascii=False),flush=True)
def download(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():
  with urllib.request.urlopen(url,timeout=180) as response,path.open('wb') as file:shutil.copyfileobj(response,file)
def neural(engine):
 out=OUT/engine;out.mkdir(parents=True,exist_ok=True);audio=OUT/'audio/intro.wav';start=time.time()
 if engine=='wav2lip':
  spec=importlib.util.spec_from_file_location('course_lips',ROOT/'presenter-production/lipsync.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  report=module.animate(audio,out/'portrait.mp4')
 else:
  work=ROOT/'engines/SadTalker'
  for name in ['SadTalker_V0.0.2_512.safetensors','mapping_00229-model.pth.tar']:
   download('https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/'+name,work/'checkpoints'/name)
  for name in ['alignment_WFLW_4HG.pth','detection_Resnet50_Final.pth']:
   download('https://github.com/xinntao/facexlib/releases/download/v0.1.0/'+name,work/'gfpgan/weights'/name)
  run([sys.executable,'inference.py','--driven_audio',audio,'--source_image',ROOT/'assets/presenter/portrait.jpg','--result_dir',out/'neural','--cpu','--size','512','--batch_size','1','--preprocess','crop','--expression_scale','0.75','--pose_style','0'],cwd=work)
  files=list((out/'neural').glob('*.mp4'));assert len(files)==1,files
  shutil.copy2(files[0],out/'portrait.mp4');report={'engine':'SadTalker','nativeSize':512,'motion':'Neural head, eyelids and lips from the actual narration'}
 source=probe(out/'portrait.mp4');duration=float(source['format']['duration'])
 assert abs(duration-seconds(audio))<.25
 run(['ffmpeg','-v','error','-y','-i',out/'portrait.mp4','-f','null','-'])
 run(['ffmpeg','-v','error','-y','-i',out/'portrait.mp4','-vf','scale=512:-2','-c:v','libx264','-preset','slow','-crf','23','-c:a','aac','-b:a','96k','-movflags','+faststart',out/'preview.mp4'])
 for n,t in enumerate([1,3,5,7]):run(['ffmpeg','-v','error','-y','-ss',t,'-i',out/'portrait.mp4','-frames:v','1',out/f'frame-{n}.jpg'])
 report.update({'status':'PASS','durationSeconds':duration,'renderSeconds':time.time()-start,'source':'مقرر التنفيذ الجبري','audioFile':'intro.wav','notHumanRecordedVoice':True})
 save(out/'report.json',report)
 print(json.dumps(report),flush=True)
if __name__=='__main__':
 mode=sys.argv[1]
 try:
  if mode=='audio':asyncio.run(audio())
  else:neural(mode)
 except Exception as exc:
  report_path=OUT/mode/'report.json';previous=json.loads(report_path.read_text()) if report_path.exists() else {};previous.update({'status':'FAIL','engine':mode,'error':str(exc),'traceback':traceback.format_exc()});save(report_path,previous);raise
