"""Record bounded setup progress without third-party Python dependencies."""
from pathlib import Path
import json,os,sys,urllib.request
root=Path(__file__).resolve().parents[2]
text=sys.argv[1];(root/'avatar3d-setup-stage.txt').write_text(text)
if os.environ.get('GITHUB_TOKEN'):
    req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=json.dumps({'state':'pending','context':'course/avatar3d-'+os.environ['VIDEO_UNIT'],'description':text[:140]}).encode(),headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:response.read()
    except Exception as error:print('Setup progress unavailable',type(error).__name__)
