"""Recover words independently; this is not a human pronunciation rating."""
from pathlib import Path
import json,re
from faster_whisper import WhisperModel
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'quality-output/asr';OUT.mkdir(parents=True,exist_ok=True)
EXPECTED='السند التنفيذي مصدر الحق في التنفيذ الجبري. ونميز بين الحق الموضوعي والحق في التنفيذ. ومن مصطلحات المقرر: الصيغة التنفيذية، ومحل التنفيذ، وحجز ما للمدين لدى الغير، والبيع الجبري، وتوزيع حصيلة التنفيذ.'
TERMS=['السند التنفيذي','التنفيذ الجبري','الحق الموضوعي','الصيغة التنفيذية','محل التنفيذ','حجز ما للمدين لدى الغير','البيع الجبري','توزيع حصيلة التنفيذ']
def normal(s):
 s=re.sub(r'[\u064b-\u065f\u0670\u0640]','',s).replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ى','ي')
 return ' '.join(re.sub(r'[^\w\s]',' ',s).split())
def distance(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  new=[i]
  for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
  row=new
 return row[-1]
model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2)
report={'status':'PASS','method':'Independent Arabic ASR without a text prompt','humanListeningReview':False,'expected':EXPECTED,'results':[],'limitation':'Recognized words do not establish vowel accuracy, naturalness or perfect lip sync.'}
for label in ['A','B','C','D','neural']:
 path=OUT/(label+'.mp3')
 if not path.exists():path=OUT/(label+'.wav')
 if not path.exists():continue
 segments,_=model.transcribe(str(path),language='ar',beam_size=5,word_timestamps=True)
 segments=list(segments);transcript=' '.join(s.text for s in segments)
 words=[{'start':w.start,'end':w.end,'text':w.word,'probability':w.probability} for s in segments for w in (s.words or [])]
 recovered=[term for term in TERMS if normal(term) in normal(transcript)]
 report['results'].append({'id':label,'transcript':transcript,'terms':recovered,'termCount':len(recovered),'wordErrorRate':distance(normal(EXPECTED).split(),normal(transcript).split())/len(normal(EXPECTED).split()),'words':words})
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
