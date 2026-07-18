import ctypes,os
from ctypes import wintypes
from pathlib import Path
class DATA_BLOB(ctypes.Structure): _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
def _blob(data:bytes):
    buf=ctypes.create_string_buffer(data); return DATA_BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte))),buf
class SecureStorage:
    def __init__(self,name): self.path=Path(os.getenv('LOCALAPPDATA',Path.home()))/'CryptoMinion'/name; self.path.parent.mkdir(parents=True,exist_ok=True)
    def save_text(self,text):
        data=text.encode()
        if os.name=='nt':
            inp,_=_blob(data); out=DATA_BLOB()
            if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(inp),'CryptoMinion',None,None,None,0,ctypes.byref(out)): raise OSError('DPAPI error')
            try: data=ctypes.string_at(out.pbData,out.cbData)
            finally: ctypes.windll.kernel32.LocalFree(out.pbData)
        self.path.write_bytes(data)
        try: os.chmod(self.path,0o600)
        except OSError: pass
    def load_text(self):
        if not self.path.exists(): return None
        data=self.path.read_bytes()
        if os.name=='nt':
            inp,_=_blob(data); out=DATA_BLOB()
            if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out)): return None
            try: data=ctypes.string_at(out.pbData,out.cbData)
            finally: ctypes.windll.kernel32.LocalFree(out.pbData)
        return data.decode()
