import json
import shutil
import subprocess
import sys
from pathlib import Path

from review import review

root=Path(__file__).resolve().parents[1]
queue=json.loads((root/'video-production/queue.json').read_text())
for unit in queue['units']:
    out=root/'rendered'/f'unit-{unit:02}';out.mkdir(parents=True,exist_ok=True)
    try:
        if queue.get('mode')=='review':
            subprocess.run(['git','fetch','origin','video-production-output'],check=True)
            for name in ['lecture.mp4','captions.vtt','captions.srt','chapters.vtt','transcript.txt','poster.jpg','report.json']:
                data=subprocess.check_output(['git','show',f'origin/video-production-output:media/unit-{unit:02}/{name}'])
                (out/name).write_bytes(data)
        else:
            subprocess.run(['git','fetch','origin','video-production-output'],check=True)
            prefix=f'media/unit-{unit:02}/voice-cache/'
            cached=subprocess.check_output(['git','ls-tree','-r','--name-only','origin/video-production-output'],text=True).splitlines()
            work=out/'work';work.mkdir(exist_ok=True)
            for name in cached:
                if name.startswith(prefix) and name.endswith(('.mp3','.json')):
                    (work/Path(name).name).write_bytes(subprocess.check_output(['git','show',f'origin/video-production-output:{name}']))
            subprocess.run([sys.executable,str(root/'video-production/produce.py'),'--unit',str(unit)],check=True)
        review(out)
    except Exception as exc:
        report=json.loads((out/'report.json').read_text())if(out/'report.json').exists()else{'unit':unit}
        report['status']='FAIL'
        report.setdefault('error',str(exc))
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        raise
