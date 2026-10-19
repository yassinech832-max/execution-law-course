"""Rebuild the complete narration without changing the published lesson wording."""
from pathlib import Path
import asyncio,hashlib,json,re,runpy,subprocess,sys,traceback
import produce as g
from review import review
def plain(text):return re.sub(r'\s+',' ',re.sub(r'[\u064b-\u065f\u0670\u0640]','',text)).strip()
def main(n):
    out=g.ROOT/'rendered'/f'unit-{n:02}';out.mkdir(parents=True,exist_ok=True)
    unit=g.assemble(runpy.run_path(str(g.HERE/f'unit_{n:02}.py'))['UNIT'])
    previous=subprocess.check_output(['git','show',f'origin/main:media/unit-{n:02}/transcript.txt'],text=True)
    current=unit['title']+'\n\n'+'\n\n'.join(s['title']+'\n'+s['spoken']for s in unit['scenes'])+'\n'
    assert plain(previous)==plain(current),'Published lesson wording changed; narration-only update must preserve every word'
    assert g.VOICE=='ar-KW-FahedNeural' and g.NARRATION_PROFILE['id']=='D'
    asyncio.run(g.produce(unit,out))
    report=json.loads((out/'report.json').read_text())
    report['publishedTextPreserved']=True
    report['normalizedTranscriptSHA256']=hashlib.sha256(plain(current).encode()).hexdigest()
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    review(out)
if __name__=='__main__':
    n=int(sys.argv[1])
    try:main(n)
    except Exception as exc:
        out=g.ROOT/'rendered'/f'unit-{n:02}';out.mkdir(parents=True,exist_ok=True)
        report=json.loads((out/'report.json').read_text()) if (out/'report.json').exists() else {'unit':n}
        report.update({'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()})
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));raise
