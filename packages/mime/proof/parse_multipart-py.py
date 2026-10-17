import io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mime.api import parse_multipart
class I(io.BytesIO):
    def rewind(self): self.seek(0)
body=(b'--x\r\nContent-Disposition: form-data; name="a"\r\n\r\none\r\n'
      b'--x\r\nContent-Disposition: form-data; name="f"; filename="a.txt"\r\n'
      b'Content-Type: text/plain\r\n\r\nhello\r\n--x--\r\n')
z=parse_multipart({'CONTENT_TYPE':'multipart/form-data; boundary=x','CONTENT_LENGTH':len(body),'rook.input':I(body)})
z['f'][0]['datapath']='FILE'
print(z)
