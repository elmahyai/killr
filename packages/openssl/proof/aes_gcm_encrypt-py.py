from openssl import sha256, aes_gcm_encrypt
key = bytes.fromhex(sha256(b"This is super secret"))
iv = b"123456789012"
