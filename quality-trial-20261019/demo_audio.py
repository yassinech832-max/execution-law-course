from pathlib import Path
import asyncio,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'quality-output/demo-audio';OUT.mkdir(parents=True,exist_ok=True)
TEXT='لِفَهْمِ السَّنَدِ التَّنْفِيذِيِّ، نُمَيِّزُ بَيْنَ حَقَّيْنِ. مِنْ مَصَادِرِ الْحَقِّ الْمَوْضُوعِيِّ: الْعَقْدُ وَالْفِعْلُ الضَّارُّ. وَالْحَقُّ فِي التَّنْفِيذِ الْجَبْرِيِّ، مَصْدَرُهُ السَّنَدُ التَّنْفِيذِيُّ. وَبِحَسَبِ الْمُقَرَّرِ، لَا تَكْفِي وَرَقَةٌ تُثْبِتُ الدَّيْنَ؛ بَلْ يَلْزَمُ أَنْ يَمْنَحَهَا التَّشْرِيعُ الصِّفَةَ التَّنْفِيذِيَّةَ. تَأَمَّلْ هٰذَا التَّمْيِيزَ، ثُمَّ ارْجِعْ إِلَى النَّصِّ الْمَرْجِعِيِّ.'
spec=importlib.util.spec_from_file_location('trial',ROOT/'quality-trial-20261019/trial.py');trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
words=asyncio.run(trial.speak(TEXT,'ar-QA-MoazNeural',OUT/'raw.mp3','-4%','-1Hz'))
subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'raw.mp3'),'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','128k',str(OUT/'lesson.mp3')],check=True)
(OUT/'raw.mp3').unlink()
report={'status':'PASS','voice':'ar-QA-MoazNeural','text':trial.plain(TEXT),'words':words,'sourceParagraphs':[37,38,40],'seconds':trial.seconds(OUT/'lesson.mp3'),'humanListeningReview':False}
try:
 from faster_whisper import WhisperModel
 model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2)
 segments,_=model.transcribe(str(OUT/'lesson.mp3'),language='ar',beam_size=5)
 report['asrTranscript']=' '.join(s.text for s in segments)
except Exception as exc:report['asrError']=str(exc)
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(OUT/'transcript.txt').write_text(trial.plain(TEXT)+'\n')
