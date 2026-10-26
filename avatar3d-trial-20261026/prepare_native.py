"""Use the licensed native 3D rig directly, with portable PNG texture maps."""
from pathlib import Path
import json,os,shutil,subprocess,urllib.request,traceback
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'avatar3d-output/prepared';OUT.mkdir(parents=True,exist_ok=True)
PIN='0943055db6ec570bcef9f2c8b41c9e5467c808f9';BASE=f'https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/{PIN}/';CHAR='Assets/Avatars/Professions/Business_Male_03/'
def download(url,file):
 file.parent.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(url,timeout=120) as r,file.open('wb') as f:shutil.copyfileobj(r,f)
def status(text,state='pending'):
 data=json.dumps({'state':state,'context':'avatar3d/preparation','description':text[:140]}).encode()
 req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=data,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as r:r.read()
try:
 status('Preparing the native licensed 3D rig without converter dependencies')
 subprocess.run(['git','fetch','origin','avatar3d-assets-20261026'],check=True,cwd=ROOT)
 for name in ['narration.wav','lesson.json','mouth.json','captions.srt','captions.vtt','transcript.txt','THIRD_PARTY_LICENSE.txt']:
  (OUT/name).write_bytes(subprocess.check_output(['git','show','origin/avatar3d-assets-20261026:preview/'+name],cwd=ROOT))
 lesson=json.loads((OUT/'lesson.json').read_text());assert lesson['durationSeconds']==90 and lesson['voice']=='D'
 download(BASE+CHAR+'Export/Business_Male_03_facial.fbx',OUT/'professor.fbx')
 for kind in ['talk','explain']:
  filename='m_gestic_talk_neutral_01.max.fbx' if kind=='talk' else 'm_gestic_presentation_right_01.max.fbx'
  download(BASE+'Assets/Animations/all_animations_max_motextr_static/'+filename,OUT/(kind+'.fbx'))
 for name in ['m020_body_color','m020_body_normal','m020_body_specular','m020_head_color','m020_head_normal','m020_head_specular','m020_opacity_color']:
  raw=OUT/(name+'.tga');download(BASE+CHAR+'Textures/'+name+'.tga',raw)
  with Image.open(raw) as im:
   im.thumbnail((2048,2048),Image.Resampling.LANCZOS);im.save(OUT/(name+'.png'))
  raw.unlink()
 model={'sourceFormat':'FBX','actor':'Business Male 03','sourceRepository':'microsoft/Microsoft-Rocketbox','sourceCommit':PIN,'license':'MIT','motions':['talk.fbx','explain.fbx'],'textures':[f.name for f in OUT.glob('*.png')],'status':'PASS','preparationCommit':os.environ['GITHUB_SHA']}
 (OUT/'model-report.json').write_text(json.dumps(model,indent=2));(OUT/'ready.json').write_text(json.dumps({'status':'PASS','sourceCommit':os.environ['GITHUB_SHA'],'format':'FBX'}))
 status('Native 3D professor, textures, motion captures and D narration are ready','success')
except Exception as exc:
 (OUT/'failure.json').write_text(json.dumps({'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}));status(str(exc),'failure');raise
