from pathlib import Path
import subprocess,shutil,os,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'avatar3d-output/rendered';WORK=Path('/tmp/avatar3d-render-retain');BRANCH='avatar3d-preview-output-20261026'
def run(args,**kw):return subprocess.run([str(v) for v in args],check=True,**kw)
if not WORK.exists():
 subprocess.run(['git','fetch','origin',BRANCH],cwd=ROOT)
 run(['git','worktree','add','--detach',WORK,'HEAD'],cwd=ROOT)
 exists=subprocess.run(['git','show-ref','--verify','--quiet','refs/remotes/origin/'+BRANCH],cwd=ROOT).returncode==0
 if exists:run(['git','checkout','-B',BRANCH,'origin/'+BRANCH],cwd=WORK)
 else:
  run(['git','checkout','--orphan',BRANCH],cwd=WORK);run(['git','rm','-rf','--cached','.'],cwd=WORK)
dest=WORK/'preview';dest.mkdir(exist_ok=True)
for f in OUT.iterdir():
 if f.is_file() and f.suffix in ['.jpg','.json','.srt','.vtt','.txt','.bin','.log']:shutil.copy2(f,dest/f.name)
run(['git','add','preview'],cwd=WORK)
if subprocess.run(['git','diff','--cached','--quiet'],cwd=WORK).returncode:
 run(['git','-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m','Retain the independent 3D lesson preview and measured rendering evidence'],cwd=WORK)
 run(['git','push','origin','HEAD:'+BRANCH],cwd=WORK)
