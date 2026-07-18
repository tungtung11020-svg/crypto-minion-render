import base64, hashlib, json, os, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

def sha256_text(value:str)->str: return hashlib.sha256(value.encode()).hexdigest()
def encrypt_delivery_secret(value:str, pepper:str)->str:
    nonce=os.urandom(12); key=hashlib.sha256(pepper.encode()).digest()
    return _b64e(nonce+AESGCM(key).encrypt(nonce,value.encode(),b'km-delivery-v1'))
def decrypt_delivery_secret(value:str, pepper:str)->str:
    raw=_b64d(value); key=hashlib.sha256(pepper.encode()).digest()
    return AESGCM(key).decrypt(raw[:12],raw[12:],b'km-delivery-v1').decode()
def _b64e(v:bytes)->str: return base64.urlsafe_b64encode(v).rstrip(b'=').decode()
def _b64d(v:str)->bytes: return base64.urlsafe_b64decode(v+'='*(-len(v)%4))
def sign_activation_token(payload:dict, private_key_b64:str)->str:
    body=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    sig=Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)).sign(body)
    return _b64e(body)+'.'+_b64e(sig)
def verify_activation_token(token:str, public_key_b64:str, device_hash:str|None=None, now:int|None=None)->dict:
    try:
        body64,sig64=token.split('.',1); body=_b64d(body64)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)).verify(_b64d(sig64),body)
        data=json.loads(body)
    except (ValueError,InvalidSignature,UnicodeDecodeError,json.JSONDecodeError) as e:
        raise ValueError('Не удалось проверить подпись лицензии') from e
    current=now or int(time.time())
    if device_hash and data.get('device_hash')!=device_hash: raise ValueError('Лицензия выпущена для другого устройства')
    if data.get('expires_at') and current>data['expires_at']: raise ValueError('Лицензия просрочена')
    if current>data['offline_until']: raise ValueError('Требуется онлайн-проверка лицензии')
    return data
