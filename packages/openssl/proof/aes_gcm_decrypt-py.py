from openssl import sha256, aes_gcm_encrypt, aes_gcm_decrypt
key = bytes.fromhex(sha256(b"This is super secret"))
iv = b"123456789012"
enc = aes_gcm_encrypt(b"hello curl", key, iv)
