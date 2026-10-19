from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys,time,urllib.request,traceback
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'quality-output/sadtalker256';OUT.mkdir(parents=True,exist_ok=True)
def run(args,**kw):subprocess.run([str(x) for x in args],check=True,**kw)
def status(text,state='pending'):
 payload=json.dumps({'context':'quality/head-motion','state':state,'description':text[:140]}).encode()
 request=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=payload,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(request,timeout=15) as response:response.read()
 except Exception:pass
def download(url,file):
 file.parent.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(url,timeout=180) as response,file.open('wb') as out:shutil.copyfileobj(response,out)
try:
 import torch
 torch.set_num_threads(4);start=time.time();work=ROOT/'engines/SadTalker'
 for name in ['SadTalker_V0.0.2_256.safetensors','mapping_00229-model.pth.tar']:
  status('Loading compact head-motion weights: '+name)
  download('https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/'+name,work/'checkpoints'/name)
 for name in ['alignment_WFLW_4HG.pth','detection_Resnet50_Final.pth']:
  download('https://github.com/xinntao/facexlib/releases/download/v0.1.0/'+name,work/'gfpgan/weights'/name)
 status('Rendering the real narration with neural head and eye movement')
 run([sys.executable,'inference.py','--driven_audio',ROOT/'quality-output/audio/intro.wav','--source_image',ROOT/'assets/presenter/portrait.jpg','--result_dir',OUT/'neural','--cpu','--size','256','--batch_size','1','--preprocess','crop','--expression_scale','0.75'],cwd=work)
 files=list((OUT/'neural').glob('*.mp4'));assert len(files)==1
 shutil.copy2(files[0],OUT/'portrait.mp4')
 run(['ffmpeg','-v','error','-y','-i',OUT/'portrait.mp4','-f','null','-'])
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(OUT/'portrait.mp4')],text=True))
 assert abs(duration-9.84)<.25
 for n,t in enumerate([1,3,5,7]):run(['ffmpeg','-v','error','-y','-ss',t,'-i',OUT/'portrait.mp4','-frames:v','1',OUT/f'frame-{n}.jpg'])
 report={'status':'PASS','engine':'SadTalker','nativeSize':256,'durationSeconds':duration,'renderSeconds':time.time()-start,'source':'مقرر التنفيذ الجبري','audioFile':'intro.wav'}
 (OUT/'report.json').write_text(json.dumps(report));status('Real head-motion comparison completed','success')
except Exception as exc:
 (OUT/'report.json').write_text(json.dumps({'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}));status(str(exc),'failure');raise
