from pathlib import Path
import json,os,shutil,subprocess,sys,time,urllib.request,traceback
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'quality-output/hybrid';OUT.mkdir(parents=True,exist_ok=True)
def run(args,**kw):subprocess.run([str(v) for v in args],check=True,**kw)
def status(message,state='pending'):
    data=json.dumps({'context':'quality/hybrid','state':state,'description':message[:140]}).encode()
    req=urllib.request.Request(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/statuses/{os.environ["GITHUB_SHA"]}',data=data,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:response.read()
    except Exception:pass
def download(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=180) as response,path.open('wb') as file:shutil.copyfileobj(response,file)
def duration(path):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],text=True))
try:
    import cv2,numpy as np,torch
    start=time.time();torch.set_num_threads(4);work=ROOT/'engines/SadTalker';audio=ROOT/'quality-output/audio/intro.wav';length=duration(audio)
    for name in ['SadTalker_V0.0.2_256.safetensors','mapping_00229-model.pth.tar']:
        status('Loading head-motion model')
        download('https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/'+name,work/'checkpoints'/name)
    for name in ['alignment_WFLW_4HG.pth','detection_Resnet50_Final.pth']:
        download('https://github.com/xinntao/facexlib/releases/download/v0.1.0/'+name,work/'gfpgan/weights'/name)
    renderer=work/'src/facerender/animate.py';code=renderer.read_text()
    original="frame_num = x['frame_num']"
    replacement="""original_frame_num = x['frame_num']
        indices = torch.linspace(0, original_frame_num - 1, min(26, original_frame_num), device=self.device).round().long()
        target_semantics = target_semantics[:, indices]
        if yaw_c_seq is not None: yaw_c_seq = yaw_c_seq[:, indices]
        if pitch_c_seq is not None: pitch_c_seq = pitch_c_seq[:, indices]
        if roll_c_seq is not None: roll_c_seq = roll_c_seq[:, indices]
        frame_num = len(indices)"""
    assert original in code
    code=code.replace(original,replacement).replace('fps=float(25)','fps=float(frame_num * 25 / original_frame_num)').replace('frames = frame_num','frames = original_frame_num')
    renderer.write_text(code)
    status('Rendering 26 neural head-motion keyframes for the complete narration')
    run([sys.executable,'inference.py','--driven_audio',audio,'--source_image',ROOT/'assets/presenter/portrait.jpg','--result_dir',OUT/'neural','--cpu','--size','256','--batch_size','1','--preprocess','crop','--expression_scale','0.65'],cwd=work)
    files=list((OUT/'neural').glob('*.mp4'));assert len(files)==1
    shutil.copy2(files[0],OUT/'keyframes.mp4')
    status('Interpolating head motion before full-rate lip synchronization')
    motion=OUT/'motion.mp4'
    run(['ffmpeg','-v','error','-y','-i',files[0],'-an','-vf','minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,tpad=stop_mode=clone:stop_duration=1','-t',length,'-c:v','libx264','-crf','17','-pix_fmt','yuv420p',motion])
    lip=ROOT/'engines/Wav2Lip';weight=lip/'checkpoints/wav2lip_gan.pth'
    download('https://huggingface.co/camenduru/Wav2Lip/resolve/f510bc766073f2403ed92b5995231323ece0ac06/checkpoints/wav2lip_gan.pth',weight)
    infer=lip/'inference.py';code=infer.read_text();original='f[y1:y2, x1:x2] = p'
    replacement='''hh, ww = p.shape[:2]
\t\t\tyy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
\t\t\tvertical = np.clip((yy / hh - .48) / .14, 0, 1)
\t\t\tedge = np.minimum(np.minimum(xx, ww-1-xx)/max(1,ww*.12), np.minimum(yy,hh-1-yy)/max(1,hh*.08))
\t\t\talpha = (vertical * np.clip(edge,0,1))[...,None]
\t\t\tf[y1:y2, x1:x2] = (p * alpha + f[y1:y2,x1:x2] * (1-alpha)).astype(np.uint8)'''
    assert original in code;infer.write_text(code.replace(original,replacement))
    cap=cv2.VideoCapture(str(motion));ok,frame=cap.read();cap.release();assert ok
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    faces=cascade.detectMultiScale(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),1.04,4,minSize=(36,36));assert len(faces),'No face in neural head sample'
    x,y,w,h=max(faces,key=lambda b:int(b[2])*int(b[3]))
    box=[max(0,int(y-h*.05)),min(frame.shape[0],int(y+h*1.12)),max(0,int(x-w*.04)),min(frame.shape[1],int(x+w*1.04))]
    status('Refining mouth movement at 25 frames per second with the original narration')
    run([sys.executable,'inference.py','--checkpoint_path',weight,'--face',motion,'--audio',audio,'--outfile',OUT/'portrait.mp4','--box',*box,'--wav2lip_batch_size','8','--fps','25'],cwd=lip)
    result=OUT/'portrait.mp4';assert abs(duration(result)-length)<.25
    run(['ffmpeg','-v','error','-i',result,'-f','null','-'])
    samples=[]
    for n,t in enumerate([1,3,5,7]):
        run(['ffmpeg','-v','error','-y','-ss',t,'-i',result,'-frames:v','1',OUT/f'frame-{n}.jpg'])
        samples.append(cv2.imread(str(OUT/f'frame-{n}.jpg')).astype(float))
    movement=[float(np.mean(np.abs(a-b))) for a,b in zip(samples,samples[1:])]
    assert max(movement)>.5
    report={'status':'PASS','engine':'SadTalker 26 keyframes + motion interpolation + Wav2Lip 25fps','nativeSize':256,'neuralKeyframes':26,'durationSeconds':duration(result),'renderSeconds':time.time()-start,'frameDifferences':movement,'audioFile':'intro.wav','source':'مقرر التنفيذ الجبري'}
    (OUT/'report.json').write_text(json.dumps(report));status('Hybrid portrait comparison completed','success')
except Exception as exc:
    (OUT/'report.json').write_text(json.dumps({'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}));status(str(exc),'failure');raise
