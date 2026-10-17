"""Generate real audio-driven lip movement on the approved course portrait."""
from pathlib import Path
import json,subprocess,sys,urllib.request,shutil
ROOT=Path(__file__).resolve().parents[1]

def run(args,**kwargs):return subprocess.run([str(v)for v in args],check=True,**kwargs)

def animate(audio,out):
    import cv2,numpy as np
    work=ROOT/'engines/Wav2Lip';weight=work/'checkpoints/wav2lip_gan.pth'
    if not weight.exists():
        weight.parent.mkdir(parents=True,exist_ok=True)
        url='https://huggingface.co/camenduru/Wav2Lip/resolve/f510bc766073f2403ed92b5995231323ece0ac06/checkpoints/wav2lip_gan.pth'
        with urllib.request.urlopen(url,timeout=120) as response,weight.open('wb') as file:shutil.copyfileobj(response,file)
    source=(work/'inference.py').read_text();original='f[y1:y2, x1:x2] = p'
    replacement='''hh, ww = p.shape[:2]
\t\t\tyy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
\t\t\tvertical = np.clip((yy / hh - .48) / .14, 0, 1)
\t\t\tedge = np.minimum(np.minimum(xx, ww-1-xx)/max(1,ww*.12), np.minimum(yy,hh-1-yy)/max(1,hh*.08))
\t\t\talpha = (vertical * np.clip(edge,0,1))[...,None]
\t\t\tf[y1:y2, x1:x2] = (p * alpha + f[y1:y2,x1:x2] * (1-alpha)).astype(np.uint8)'''
    if original in source:(work/'inference.py').write_text(source.replace(original,replacement))
    image=ROOT/'assets/presenter/portrait.jpg';frame=cv2.imread(str(image));assert frame is not None
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    faces=cascade.detectMultiScale(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),1.08,6,minSize=(100,100));assert len(faces)
    x,y,w,h=max(faces,key=lambda b:int(b[2])*int(b[3]))
    box=[max(0,int(y-h*.05)),min(frame.shape[0],int(y+h*1.12)),max(0,int(x-w*.04)),min(frame.shape[1],int(x+w*1.04))]
    run([sys.executable,'inference.py','--checkpoint_path',weight,'--face',image,'--audio',audio,'--outfile',out,'--box',*box,'--wav2lip_batch_size','8','--fps','25'],cwd=work)
    motions=[]
    for second in [1,3,5]:
        cap=cv2.VideoCapture(str(out));cap.set(cv2.CAP_PROP_POS_MSEC,second*1000);ok,im=cap.read();cap.release();assert ok
        a,b,c,e=box;motions.append(im[int(a+(b-a)*.58):int(a+(b-a)*.93),int(c+(e-c)*.18):int(c+(e-c)*.82)].astype(float))
    differences=[float(np.mean(np.abs(a-b)))for a,b in zip(motions,motions[1:])];assert max(differences)>.5,'Neural mouth is static'
    return {'engine':'Wav2Lip','mouthMotionDifferences':differences,'faceBox':box}
