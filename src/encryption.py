import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

class FileEncryptor:
    def __init__(self):
        self.backend = default_backend()
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(password.encode())
    
    def encrypt_file(self, input_path: str, output_path: str, password: str) -> bool:
        """Encrypt file with AES-256-CBC"""
        try:
            # Generate random salt and IV
            salt = os.urandom(16)
            iv = os.urandom(16)
            
            # Derive key
            key = self.derive_key(password, salt)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # Pad data
            padder = padding.PKCS7(128).padder()
            
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                # Write salt and IV
                outfile.write(salt)
                outfile.write(iv)
                
                # Encrypt file in chunks
                while True:
                    chunk = infile.read(8192)
                    if len(chunk) == 0:
                        break
                    padded_chunk = padder.update(chunk)
                    encrypted_chunk = encryptor.update(padded_chunk)
                    outfile.write(encrypted_chunk)
                
                # Finalize
                final_padded = padder.finalize()
                final_encrypted = encryptor.update(final_padded) + encryptor.finalize()
                outfile.write(final_encrypted)
            
            return True
            
        except Exception as e:
            print(f"Encryption error: {e}")
            return False
    
    def decrypt_file(self, input_path: str, output_path: str, password: str) -> bool:
        """Decrypt file with AES-256-CBC"""
        try:
            with open(input_path, 'rb') as infile:
                # Read salt and IV
                salt = infile.read(16)
                iv = infile.read(16)
                
                # Derive key
                key = self.derive_key(password, salt)
                
                # Create cipher
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
                decryptor = cipher.decryptor()
                
                # Unpad data
                unpadder = padding.PKCS7(128).unpadder()
                
                with open(output_path, 'wb') as outfile:
                    # Decrypt file in chunks
                    while True:
                        chunk = infile.read(8192)
                        if len(chunk) == 0:
                            break
                        decrypted_chunk = decryptor.update(chunk)
                        unpadded_chunk = unpadder.update(decrypted_chunk)
                        outfile.write(unpadded_chunk)
                    
                    # Finalize
                    final_decrypted = decryptor.finalize()
                    final_unpadded = unpadder.update(final_decrypted) + unpadder.finalize()
                    outfile.write(final_unpadded)
            
            return True
            
        except Exception as e:
            print(f"Decryption error: {e}")
            return False
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
