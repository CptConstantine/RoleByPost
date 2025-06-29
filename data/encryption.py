import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_encryption_key():
    """
    Generate or retrieve the encryption key for API keys.
    Uses environment variable for the master key.
    """
    master_key = os.getenv('ENCRYPTION_KEY')
    if not master_key:
        # Generate a new key if none exists (for development)
        # In production, this should be set as an environment variable
        master_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        print(f"Generated new encryption key: {master_key}")
        print("Set this as ENCRYPTION_KEY environment variable!")
    
    # Derive a consistent key from the master key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'pbp_bot_salt',  # Fixed salt for consistency
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    return key

def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.
    
    Args:
        api_key: The plaintext API key
        
    Returns:
        str: Base64 encoded encrypted API key
    """
    if not api_key:
        return ""
    
    key = get_encryption_key()
    f = Fernet(key)
    encrypted_key = f.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted_key).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key from storage.
    
    Args:
        encrypted_key: Base64 encoded encrypted API key
        
    Returns:
        str: Plaintext API key
    """
    if not encrypted_key:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted_key = f.decrypt(encrypted_bytes)
        return decrypted_key.decode()
    except Exception as e:
        print(f"Error decrypting API key: {e}")
        return ""