import random
import json


class ElGamal:
    # Static class variable
    encrypted_message_bytes = bytes("2eg", "UTF-16")
    pub_key_bytes = bytes("5eg", "UTF-16")

    def __init__(self):
        """
        ElGamal for 2
        based on : https://justcryptography.com/elgamal-cryptosystem/
            and https://en.wikipedia.org/wiki/ElGamal_encryption
        reffences: https://www.geeksforgeeks.org/elgamal-encryption-algorithm/
        using modular exponentiation as cyclic group
        ON Diffe-Hellman -> public_modulo = prime
        public_base = primitive root of public_modulo

        :param self:            Attributes Instance
        """

        self.public_modulo = self.generate_public_modulo()
        self.public_base = self.generate_public_base()

        # flag len -> 8
        self.pub_key_bytes = bytes("5eg", "UTF-16")
        self.encrypted_message_bytes = bytes("2eg", "UTF-16")

        self.private_key = self.generate_private_key()
        self.base_public_key = self.generate_base_public_key()
        self.public_key = self.generate_publlic_key()

    # * Variable generation
    def generate_public_modulo(self):
        p_mod = random.randint(pow(10, 20), pow(10, 50))
        p_mod_prime = self.is_prime(p_mod, 13)

        while not p_mod_prime:
            p_mod = random.randint(pow(10, 20), pow(10, 50))
            p_mod_prime = self.is_prime(p_mod, 13)

        return p_mod

    def generate_public_base(self):
        p_base = random.randint(pow(10, 20), self.public_modulo)
        while self.gcd(p_base, self.public_modulo) != 1:
            p_base = random.randint(pow(10, 20), self.public_modulo)

        return p_base

    # * KEY
    def generate_private_key(self):
        return random.randint(2, self.public_modulo - 1)

    def generate_base_public_key(self):
        # modular exponentiation of public_base^private_key mod public_modulo
        return pow(self.public_base, self.private_key, self.public_modulo)

    def generate_publlic_key(self):
        # public key is tuple of public_modulo[the bigest number]
        #                        public_base is primitive root of public_modulo
        #                        base_public_key is pow(public_base, private_key, public modulo)
        pub_key = {
            "public_modulo": self.public_modulo,
            "public_base": self.public_base,
            "base_public_key": self.base_public_key,
        }

        return pub_key

    # * Encryption & Decryption
    @classmethod
    def encrypt(cls, message: str, public_key: dict):
        # pow (public_base, private_key, public_modulo)
        base_pub_key = public_key["base_public_key"]
        emphereal_key = random.randint(1, public_key["public_modulo"] - 1)
        # shared_secret = power(base_pub_key, emphereal, modulo)
        shared_secret = pow(base_pub_key, emphereal_key, public_key["public_modulo"])

        cipher_1 = pow(
            public_key["public_base"], emphereal_key, public_key["public_modulo"]
        )
        cipher_2 = []

        # reversible map function aka multiplication and division
        for ch in message:
            cipher_2.append(shared_secret * ord(ch))
        return [cipher_1, cipher_2]

    def decrypt(self, ciphers: list):
        # calculate shared key
        cipher_1, cipher_2 = ciphers
        shared_secret = self.power(cipher_1, self.private_key, self.public_modulo)

        msg = ""
        for i in range(0, len(cipher_2)):
            msg = msg + (chr(int(cipher_2[i] / shared_secret)))
        return msg

    # * Pack & unpack
    # * pack -> bytes
    def pack_public_key(self, encoding="utf-8"):
        encoded_pub_key = (
            json.dumps(self.public_key).encode(encoding) + self.pub_key_bytes
        )
        return encoded_pub_key

    @classmethod
    def unpack_public_key(cls, encoded_pub_key, encoding="utf-8"):
        # still contain pub_key_bytes,
        # already verified ending with b""5eg"
        encoded_pub_key = encoded_pub_key[:-8].decode(encoding)
        pub_key = json.loads(encoded_pub_key)
        return pub_key

    @classmethod
    def pack_encrypted_message(cls, ciphers: list, encoding="utf-8"):
        # ciphers -> [cipher1, cipher2]

        # we pack it to send
        packed_ciphers = (
            json.dumps(ciphers).encode(encoding) + cls.encrypted_message_bytes
        )
        return packed_ciphers

    @classmethod
    def unpack_encrypted_message(cls, packed_ciphers, encoding="utf-8"):
        packed_ciphers = packed_ciphers[:-8].decode(encoding)
        ciphers = json.loads(packed_ciphers)
        return ciphers

    @classmethod
    def pack_to_bytes_message(cls, message, public_key, encoding="utf-8"):
        ciphers = ElGamal.encrypt(message, public_key)
        return ElGamal.pack_encrypted_message(ciphers)

    # * UTILS
    def gcd(self, a, b):
        if a < b:
            return self.gcd(b, a)
        elif a % b == 0:
            return b
        else:
            return self.gcd(b, a % b)

    def miller_test(self, d, n):
        # Pick a random number in [2..n-2]
        # Corner cases make sure that n > 4
        if n <= 4:
            n = random.randint(5, 13)

        a = 2 + random.randint(1, n - 4)

        # Compute a^d % n
        x = pow(a, d, n)

        if x == 1 or x == n - 1:
            return True

        # Keep squaring x while one
        # of the following doesn't
        # happen
        # (i) d does not reach n-1
        # (ii) (x^2) % n is not 1
        # (iii) (x^2) % n is not n-1
        while d != n - 1:
            x = (x * x) % n
            d *= 2

            if x == 1:
                return False
            if x == n - 1:
                return True

        # Return composite
        return False

    def is_prime(self, prime_candidate, precision):
        if prime_candidate <= 1 or prime_candidate == 4:
            return False
        if prime_candidate <= 3:
            return True

        # Find r such that n =
        # 2^d * r + 1 for some r >= 1
        d = prime_candidate - 1
        while d % 2 == 0:
            d //= 2

        # Iterate given number of 'k' times
        for i in range(precision):
            if self.miller_test(d, prime_candidate) == False:
                return False

        return True


if __name__ == "__main__":
    eg_1 = ElGamal()

    pac_pub = eg_1.pack_public_key()
    pub_key = eg_1.unpack_public_key(pac_pub)

    print(pub_key == eg_1.public_key)
    # enc mess

    mess = "heyoooo!"
    enc_ = eg_1.encrypt(mess, pub_key)
    pac_mess = ElGamal.pack_encrypted_message(ciphers=enc_)
    enc_u = eg_1.unpack_encrypted_message(pac_mess)

    print(enc_u == enc_)
