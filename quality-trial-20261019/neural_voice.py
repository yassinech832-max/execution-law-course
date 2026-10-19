"""Compare a new open multilingual voice without paid inference services."""
from pathlib import Path
import json,os,subprocess,time,traceback,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'quality-output/neural-tts';OUT.mkdir(parents=True,exist_ok=True)
TEXT='السند التنفيذي مصدر الحق في التنفيذ الجبري. ونميز بين الحق الموضوعي والحق في التنفيذ. ومن مصطلحات المقرر: الصيغة التنفيذية، ومحل التنفيذ، وحجز ما للمدين لدى الغير، والبيع الجبري، وتوزيع حصيلة التنفيذ.'
def status(message,state='pending'):
 if not os.getenv('GITHUB_TOKEN'):return
 body=json.dumps({'state':state,'context':'quality/neural-tts','description':message[:140]}).encode()
 request=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=body,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(request,timeout=15) as response:response.read()
 except Exception:pass
def save(report):(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
try:
 import torch,soundfile as sf
 from chatterbox.mtl_tts import ChatterboxMultilingualTTS
 torch.set_num_threads(4);torch.manual_seed(42)
 status('Loading the open Arabic-capable multilingual voice on free CPU')
 start=time.time();model=ChatterboxMultilingualTTS.from_pretrained(device='cpu')
 status('Model loaded; generating Arabic legal terminology for comparison')
 wave=model.generate(TEXT,language_id='ar',exaggeration=.25,cfg_weight=.35,temperature=.65,repetition_penalty=1.4)
 sf.write(OUT/'raw.wav',wave.squeeze().cpu().numpy(),model.sr)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'raw.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','128k',str(OUT/'neural.mp3')],check=True)
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(OUT/'neural.mp3')],text=True))
 assert 8<duration<90,duration
 (OUT/'raw.wav').unlink();(OUT/'transcript.txt').write_text(TEXT+'\n')
 report={'status':'PASS','model':'ResembleAI/chatterbox','language':'ar','seconds':duration,'renderSeconds':time.time()-start,'text':TEXT,'voiceReference':'Model built-in reference, not the user voice','humanListeningReview':False,'qualityRating':'Unrated; compare by listening'}
 save(report);status('Arabic trial generated; pronunciation and naturalness still require listening','success')
except Exception as exc:
 save({'status':'FAIL','model':'ChatterboxMultilingual','error':str(exc),'traceback':traceback.format_exc()});status(str(exc),'failure');raise
