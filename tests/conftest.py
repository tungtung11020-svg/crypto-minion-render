import base64,os
os.environ['SERVER_PEPPER']='test-pepper-32-bytes-minimum-value'
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
p=Ed25519PrivateKey.generate(); os.environ['ED25519_PRIVATE_KEY']=base64.b64encode(p.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode(); os.environ['ED25519_PUBLIC_KEY']=base64.b64encode(p.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
