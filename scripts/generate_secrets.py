import base64,secrets
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
priv=Ed25519PrivateKey.generate(); pub=priv.public_key()
values={'SERVER_PEPPER':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),'ED25519_PRIVATE_KEY':base64.b64encode(priv.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode(),'ED25519_PUBLIC_KEY':base64.b64encode(pub.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()}
p=Path('.env'); text=p.read_text('utf-8') if p.exists() else Path('.env.example').read_text('utf-8')
for k,v in values.items():
    import re; text=re.sub(rf'(?m)^{k}=.*$',f'{k}={v}',text)
p.write_text(text,'utf-8'); print('Секреты записаны в .env. Никому не передавайте этот файл.')
