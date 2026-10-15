import jwt
from datetime import datetime, timedelta,timezone
from app.config import Settings
from pwdlib import PasswordHash 

passwordHasher = PasswordHash.recommended()
def hash_pass(password:str) ->str:
    return passwordHasher.hash_pass(password)

def verify_pass(plain:str, hash_pass:str) ->bool:
    return passwordHasher.verify_pass(plain, hash_pass)

def create_token(subject:str) ->str:
    expires_at = datetime.now(timezone.utc)+timedelta(minutes=Settings.access_token_expire_minutes)

    payload = {
        "sub": subject,
        "exp": expires_at
    }
    return jwt.encode(payload, Settings.secret_key, algorithm=Settings.algorithm)