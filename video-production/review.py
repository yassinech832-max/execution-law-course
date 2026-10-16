"""Inspect samples decoded from the finished video, not source artwork alone."""
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

def review(out):
    report=json.loads((out/'report.json').read_text())
    if report.get('status')!='PASS':raise ValueError('The rendering report has not passed')
    movie=out/'lecture.mp4';temp=out/'review-work';temp.mkdir(exist_ok=True)
    points=[2,30,250,535,760,905,1020,1165]
    sheet=Image.new('RGB',(1920,580),'#f7f5ef');draw=ImageDraw.Draw(sheet)
    for n,second in enumerate(points):
        frame=temp/f'frame-{n:02}.png'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(second),'-i',str(movie),'-frames:v','1',str(frame)],check=True)
        image=Image.open(frame).convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
        x=(n%4)*480;y=(n//4)*290;sheet.paste(image,(x,y))
        draw.text((x+12,y+273),f'{second//60:02}:{second%60:02}',fill='#153b3d',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13))
    sheet.save(out/'qa-frames.jpg',quality=90)
    samples=[]
    from faster_whisper import WhisperModel
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2)
    for n,second in enumerate([12,550,1025]):
        audio=temp/f'audio-{n}.wav'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(second),'-t','18','-i',str(movie),'-vn','-ar','16000','-ac','1',str(audio)],check=True)
        segments,_=model.transcribe(str(audio),language='ar',beam_size=5)
        samples.append({'start':second,'seconds':18,'recognizedText':' '.join(s.text.strip()for s in segments)})
    report['sampleRecognition']=samples
    report['finalVideoFrameSamples']=points
    report['visualReviewContactSheet']='qa-frames.jpg'
    report['reviewCommit']=os.environ.get('GITHUB_SHA')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('REVIEW '+json.dumps({'unit':report['unit'],'samples':samples},ensure_ascii=False),flush=True)

if __name__=='__main__':
    import sys
    review(Path(sys.argv[1]))
