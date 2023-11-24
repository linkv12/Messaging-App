# Implementation by Shamgar Otherson D.

import random
import json


class ElGamal:
    # * Static class variable
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

        # * Public modulo
        # * Public base
        self.public_modulo = self.generate_public_modulo()
        self.public_base = self.generate_public_base()

        # * Flag len -> 8
        self.pub_key_bytes = bytes("5eg", "UTF-16")
        self.encrypted_message_bytes = bytes("2eg", "UTF-16")

        # * Key, private, public etc.
        self.private_key = self.generate_private_key()
        self.base_public_key = self.generate_base_public_key()
        self.public_key = self.generate_publlic_key()

    # * Variable generation
    def generate_public_modulo(self):
        """
        Generate public modulo
        A very large prime number

        :param self:            Attributes Instance

        :return:                public modulo
        """

        p_mod = random.randint(pow(10, 20), pow(10, 50))
        p_mod_prime = self.is_prime(p_mod, 13)

        while not p_mod_prime:
            p_mod = random.randint(pow(10, 20), pow(10, 50))
            p_mod_prime = self.is_prime(p_mod, 13)

        return p_mod

    def generate_public_base(self):
        """
        Generate public base
        A primitive root of public modulo

        :param self:            Attributes Instance

        :return:                public base
        """

        p_base = random.randint(pow(10, 20), self.public_modulo)
        while self.gcd(p_base, self.public_modulo) != 1:
            p_base = random.randint(pow(10, 20), self.public_modulo)

        return p_base

    # * KEY
    def generate_private_key(self):
        """
        Generate private key
        a random number between 2 to publoc modulo -1

        :param self:            Attributes Instance

        :return:                private key
        """
        return random.randint(2, self.public_modulo - 1)

    def generate_base_public_key(self):
        """
        Generate base public key
        A modular exponentiation of public base, private key and public modulo

        :param self:            Attributes Instance

        :return:                base public key
        """
        return pow(self.public_base, self.private_key, self.public_modulo)

    def generate_publlic_key(self):
        """
        Generate public key
        A dictionary that contain public modulo, public base and base public key

        :param self:            Attributes Instance

        :return:                public key, a dict
        """
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
        """
        Encrypt text through a class method
        with message and public key as parameter

        :param cls:         Class Instances
        :param message:     String to be enrypted
        :param public_key:  Public key used for encryption

        :return:            list that contain cipher_1 and cipher_2 in that order
        """
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
        """
        Decrypt cipher to raw string

        :param self:        Attributes Instance
        :param ciphers:     ciphers is a list that contain cipher_1 and cipher_2

        :return:            message, decrypted
        """
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
        """
        Pack public key to bytes using json library

        :param self:        Attributes Instance
        :param encoding:    encoding method for str

        :return:            packed public key a bytes object
        """

        encoded_pub_key = (
            json.dumps(self.public_key).encode(encoding) + self.pub_key_bytes
        )
        return encoded_pub_key

    @classmethod
    def unpack_public_key(cls, encoded_pub_key, encoding="utf-8"):
        """
        Unpack bytes object that is presumed to be public key

        :param cls:                 Class Instances
        :param encoded_pub_key:     packed public key, bytes object
        :param encoding:            encoding method that used for packing public key

        :return:                    dict object a proper public key
        """
        # still contain pub_key_bytes,
        # already verified ending with b""5eg"
        encoded_pub_key = encoded_pub_key[:-8].decode(encoding)
        pub_key = json.loads(encoded_pub_key)
        return pub_key

    @classmethod
    def pack_encrypted_message(cls, ciphers: list, encoding="utf-8"):
        """
        Pack encrypted message, in form of ciphers

        :param cls:                 Class Instances
        :param ciphers:             list object contain cipher_1 and cipher_2
        :param encoding:            encoding method

        :return:                    packed ciphers a bytes object
        """

        # ciphers -> [cipher1, cipher2]

        # we pack it to send
        packed_ciphers = (
            json.dumps(ciphers).encode(encoding) + cls.encrypted_message_bytes
        )
        return packed_ciphers

    @classmethod
    def unpack_encrypted_message(cls, packed_ciphers, encoding="utf-8"):
        """
        Unpack encrypted message, in form of bytes

        :param cls:                 Class Instances
        :param packed_ciphers:      bytes object contain cipher_1 and cipher_2
        :param encoding:            encoding method

        :return:                    ciphers
        """
        # does it need to be class method instead of using instance method?
        packed_ciphers = packed_ciphers[:-8].decode(encoding)
        ciphers = json.loads(packed_ciphers)
        return ciphers

    @classmethod
    def pack_to_bytes_message(cls, message, public_key, encoding="utf-8"):
        """
        Unpack encrypted message, in form of bytes

        :param cls:                 Class Instances
        :param message:             String to be enrypted
        :param public_key:          Public key used for encryption
        :param encoding:            encoding method

        :return:                    pack encrypted bytes
        """
        ciphers = ElGamal.encrypt(message, public_key)
        return ElGamal.pack_encrypted_message(ciphers, encoding=encoding)

    # * UTILS
    def gcd(self, a, b):
        """
        Find greatest common divisor
        From 2 number

        :param self:        Attributes Instance
        :param a:           int number
        :param b:           int number

        :return:            int, greatest common divisor
        """
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
