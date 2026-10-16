"""Test Arabic speech before rendering a complete lecture."""
import asyncio
import json
import subprocess
from pathlib import Path

OUT = Path('rendered/probe')
OUT.mkdir(parents=True, exist_ok=True)
TEXT = 'مرحباً بكم في مساق التنفيذ الجبري. نبدأ بالسند التنفيذي وشروط الحق الثابت فيه. لا يكفي أن يثبت الدين في أي ورقة، بل يجب أن يمنح القانون هذه الورقة قوة تنفيذية. ونميز في هذا الدرس بين تحقق وجود الحق، وتعيين مقداره، وحلول أدائه. ثم نطبق هذا التمييز على مثال واضح من الدراسة.'

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)], text=True))

async def main():
    report = {'sampleText': TEXT, 'engines': {}}
    try:
        import edge_tts
        communicate = edge_tts.Communicate(TEXT, 'ar-AE-HamdanNeural')
        await communicate.save(str(OUT/'edge.mp3'))
        report['engines']['edge'] = {'ok': True, 'duration': duration(OUT/'edge.mp3'), 'voice': 'ar-AE-HamdanNeural'}
    except Exception as exc:
        report['engines']['edge'] = {'ok': False, 'error': str(exc)[:500]}
    try:
        import wave
        from piper import PiperVoice
        subprocess.run(['python','-m','piper.download_voices','ar_JO-kareem-medium','--download-dir',str(OUT/'voice')], check=True)
        voice = PiperVoice.load(str(OUT/'voice/ar_JO-kareem-medium.onnx'))
        with wave.open(str(OUT/'piper.wav'), 'wb') as wav:
            voice.synthesize_wav(TEXT, wav)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'piper.wav'),'-c:a','libmp3lame','-b:a','96k',str(OUT/'piper.mp3')], check=True)
        report['engines']['piper'] = {'ok': True, 'duration': duration(OUT/'piper.mp3'), 'voice': 'ar_JO-kareem-medium'}
    except Exception as exc:
        report['engines']['piper'] = {'ok': False, 'error': str(exc)[:500]}
    # Recognition is a pronunciation signal, not a claim of human listening review.
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel('base', device='cpu', compute_type='int8', cpu_threads=2)
        for name, result in report['engines'].items():
            if result['ok']:
                segments, _ = model.transcribe(str(OUT/f'{name}.mp3'), language='ar', beam_size=3)
                result['transcript'] = ' '.join(s.text for s in segments)
    except Exception as exc:
        report['recognitionError'] = str(exc)[:500]
    (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if not any(r['ok'] for r in report['engines'].values()):
        raise RuntimeError('No Arabic speech engine completed the sample')

asyncio.run(main())
