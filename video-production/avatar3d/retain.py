"""Retain completed output or actionable diagnostics even when setup fails."""
from pathlib import Path
import json,os,shutil,subprocess,sys,urllib.request
root=Path(__file__).resolve().parents[2];n=int(sys.argv[1]);out=root/'rendered-3d'/f'unit-{n:02}';out.mkdir(parents=True,exist_ok=True)
logs=root/'avatar3d-setup.log'
if logs.exists():(out/'setup-diagnostics.log').write_text(logs.read_text(errors='replace')[-18000:])
report=json.loads((out/'report.json').read_text()) if (out/'report.json').exists() else {}
if report.get('status')!='PASS':
    stage=(root/'avatar3d-setup-stage.txt').read_text() if (root/'avatar3d-setup-stage.txt').exists() else 'Production'
    if not (out/'failure.json').exists():(out/'failure.json').write_text(json.dumps({'status':'FAIL','unit':n,'stage':stage,'error':stage+' did not complete','sourceCommit':os.environ['GITHUB_SHA']},indent=2))
    if os.environ.get('GITHUB_TOKEN'):
        req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=json.dumps({'state':'failure','context':f'course/avatar3d-{n}','description':(stage+' did not complete')[:140]}).encode(),headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=15) as response:response.read()
        except Exception as error:print('Failure status unavailable',type(error).__name__)
branch=f'avatar3d-release-unit-{n}-20261027';target=Path(f'/tmp/avatar3d-retain-{n}')
def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
fetched=subprocess.run(['git','fetch','origin',branch],cwd=root).returncode==0
if target.exists():run(['git','worktree','remove','--force',target],cwd=root)
run(['git','worktree','add','--detach',target,'origin/'+branch if fetched else os.environ['GITHUB_SHA']],cwd=root)
if not fetched:
    run(['git','checkout','--orphan',branch],cwd=target);run(['git','rm','-rf','.'],cwd=target)
dest=target/'media'/f'unit-{n:02}';dest.mkdir(parents=True,exist_ok=True)
for p in out.iterdir():
    if p.is_file() and p.suffix in ['.mp4','.json','.jpg','.txt','.vtt','.srt','.log']:shutil.copy2(p,dest/p.name)
run(['git','add',str(dest.relative_to(target))],cwd=target)
if subprocess.run(['git','diff','--cached','--quiet'],cwd=target).returncode:
    run(['git','-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m',f'Retain the complete approved 3D lecture for unit {n}'],cwd=target)
    run(['git','push','origin',f'HEAD:refs/heads/{branch}'],cwd=target)
