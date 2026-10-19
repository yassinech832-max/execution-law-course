"""Retain only isolated trial output branches; never update the live course."""
from pathlib import Path
import os,shutil,json,subprocess
mode=os.environ['TRIAL_MODE'];root=Path.cwd();source=root/'quality-output'/mode
dest=Path('/tmp')/('quality-output-'+mode);dest.mkdir(parents=True,exist_ok=True)
if source.exists():
 for file in source.iterdir():
  if file.is_file() and file.suffix in ['.mp3','.mp4','.wav','.jpg','.txt','.json','.vtt','.srt']:shutil.copy2(file,dest/file.name)
log=root/'trial.log'
if log.exists():(dest/'diagnostics.txt').write_text(log.read_text()[-16000:])
if not (dest/'report.json').exists():(dest/'report.json').write_text(json.dumps({'status':'FAIL','engine':mode,'error':'Setup or rendering did not complete','log':'diagnostics.txt'}))
report=json.loads((dest/'report.json').read_text());branch='quality-'+mode+'-20261019'
def run(*args,check=True):return subprocess.run(list(args),check=check)
if run('git','fetch','origin',branch,check=False).returncode==0:
 run('git','checkout','-B',branch,'origin/'+branch);run('git','rm','-r','--ignore-unmatch','preview')
else:
 run('git','checkout','--orphan',branch);run('git','rm','-rf','--cached','.')
out=root/'preview';out.mkdir(exist_ok=True)
for file in dest.iterdir():shutil.copy2(file,out/file.name)
run('git','add','preview')
run('git','-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m','Retain isolated '+mode+' quality comparison')
run('git','push','origin','HEAD:'+branch)
print(json.dumps({'branch':branch,'status':report['status'],'files':[p.name for p in dest.iterdir()]}))
