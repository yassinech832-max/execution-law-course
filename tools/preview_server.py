"""Local course preview with byte-range support for MP4 seeking."""
import argparse
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.vtt':'text/vtt','.mp4':'video/mp4'}

    def end_headers(self):
        self.send_header('Accept-Ranges','bytes')
        super().end_headers()

    def send_head(self):
        self._range=None
        value=self.headers.get('Range')
        path=Path(self.translate_path(self.path))
        if not value or not path.is_file():return super().send_head()
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',value.strip())
        size=path.stat().st_size
        if not match:return super().send_head()
        a,b=match.groups()
        start=int(a)if a else max(0,size-int(b or size))
        end=min(int(b),size-1)if a and b else size-1
        if start>=size or end<start:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return None
        file=path.open('rb');file.seek(start);self._range=(start,end)
        self.send_response(206)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers();return file

    def copyfile(self, source, outputfile):
        if self._range is None:return super().copyfile(source,outputfile)
        remaining=self._range[1]-self._range[0]+1
        try:
            while remaining:
                data=source.read(min(65536,remaining))
                if not data:break
                outputfile.write(data);remaining-=len(data)
        except (BrokenPipeError,ConnectionResetError):pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',default='.');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    import functools
    ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(Handler,directory=args.directory)).serve_forever()
