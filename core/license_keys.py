import base64, hashlib, hmac, re, secrets
_PATTERN=re.compile(r'^KM-(?:[A-Z2-7]{4}-){7}[A-Z2-7]{4}$')
def generate_license_key()->str:
    encoded=base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')
    return 'KM-'+'-'.join(encoded[i:i+4] for i in range(0,len(encoded),4))
def normalize_license_key(value:str)->str: return value.strip().upper().replace(' ','')
def validate_license_key_format(value:str)->bool: return bool(_PATTERN.fullmatch(normalize_license_key(value)))
def license_key_digest(normalized_key:str, server_pepper:bytes)->str:
    return hmac.new(server_pepper,normalized_key.encode(),hashlib.sha256).hexdigest()
def mask_key(last4:str)->str: return 'KM-••••-••••-••••-••••-••••-••••-••••-'+last4
