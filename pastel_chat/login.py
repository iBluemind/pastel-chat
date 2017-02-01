import base64
from config import RSA_PRIVATE_KEY_BASE64
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto import Random
from Crypto.PublicKey import RSA


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]


class AESCipher(object):
    def __init__(self, key):
        self.key = key

    def encrypt(self, raw):
        raw = pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(raw)

    def decrypt(self, enc, iv):
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc))


class RSACryptor(object):
    def __init__(self, private_key):
        self.private_key = self._create_private_key(private_key)

    def _create_private_key(self, private_key):
        return PKCS1_OAEP.new(RSA.importKey(private_key))

    def decrypt(self, encrypted):
        return self.private_key.decrypt(encrypted)


class PastelLoginHelper(object):

    def __init__(self, encoded_email, encoded_password, encoded_aes_key, encoded_aes_iv):
        self.encoded_email = encoded_email
        self.encoded_password = encoded_password
        self.encoded_aes_key = encoded_aes_key
        self.encoded_aes_iv = encoded_aes_iv

    def _base64_decode(self, encoded):
        return base64.b64decode(encoded)

    def _decrypt_rsa(self, private_key, encrypted):
        rsa_cipher = RSACryptor(private_key)
        decrypted = rsa_cipher.decrypt(encrypted)
        return decrypted

    def _decrypt_aes(self, key, iv,  encrypted):
        aes_cipher = AESCipher(key)
        decrypted = aes_cipher.decrypt(encrypted, iv)
        return decrypted
        
    def decrypt(self):
        encrypted_email = self._base64_decode(self.encoded_email)
        encrypted_password = self._base64_decode(self.encoded_password)
        encrypted_aes_key = self._base64_decode(self.encoded_aes_key)
        aes_iv = self._base64_decode(self.encoded_aes_iv)
        decoded_rsa_private_key = self._base64_decode(RSA_PRIVATE_KEY_BASE64)

        decrypted_aes_key = self._decrypt_rsa(decoded_rsa_private_key, encrypted_aes_key)
        decrypted_email = self._decrypt_aes(decrypted_aes_key, aes_iv, encrypted_email)
        decrypted_password = self._decrypt_aes(decrypted_aes_key, aes_iv, encrypted_password)
        
        return decrypted_email, decrypted_password
    