import base64,re
from core.license_keys import *
from core.security import sign_activation_token,verify_activation_token
from core.config import get_settings
def test_key_generation_and_format():
 keys={generate_license_key() for _ in range(1000)}; assert len(keys)==1000; assert all(validate_license_key_format(k) for k in keys)
def test_normalization_and_invalid():
 k=generate_license_key(); assert normalize_license_key(' '+k.lower()+' ')==k; assert not validate_license_key_format('KM-XXXX')
def test_hmac_digest():
 k=generate_license_key(); assert license_key_digest(k,b'pepper')==license_key_digest(k,b'pepper'); assert license_key_digest(k,b'pepper')!=license_key_digest(generate_license_key(),b'pepper')
def test_ed25519_and_tamper():
 cfg=get_settings(); payload={'device_hash':'abc','issued_at':1,'expires_at':None,'offline_until':9999999999,'features':[]}; token=sign_activation_token(payload,cfg.ed25519_private_key); assert verify_activation_token(token,cfg.ed25519_public_key,'abc')['device_hash']=='abc'
 import pytest
 with pytest.raises(ValueError): verify_activation_token(token+'x',cfg.ed25519_public_key)
 with pytest.raises(ValueError): verify_activation_token(token,cfg.ed25519_public_key,'other')
