#!/usr/bin/python

"""Wrapper for M2Crypto (which is a wrapper for openssl)."""

import types
import os
import hmac
import struct
import cStringIO
from hashlib import sha256

from M2Crypto import EVP

from common import Globals
from common.utils.Basic import log_msg, log_ex, _ # pylint: disable-msg=W0611
from common.utils import Basic

IV_LENGTH = 16
HMAC_KEY_LENGTH = 32
MESSAGE_FORMAT = "!%ss%ss%ss" % (Globals.SYMMETRIC_KEY_BYTES, IV_LENGTH, HMAC_KEY_LENGTH) #value, iv, hmac

class SymmetricKey():
  """A wrapper around M2 that makes access to that class more
  Pythonic and incorporates an hmac; SymmetricKey will create a new key unless
  it is given an authBlob; an authBlob can be generated by the pack method on an 
  existing key."""
  
  def __init__(self, authBlob=None):
    """Initializes itself with the string of random data passed in, or generates
    its own random data if none is passed.
    @param authBlob: contains data to initialize a key
    @type authBlob: binary packed by self.pack()"""
    if authBlob == None:
      randomData = os.urandom(Globals.SYMMETRIC_KEY_BYTES)
      iv = os.urandom(IV_LENGTH)
      hmacKey = os.urandom(HMAC_KEY_LENGTH)
    else:
      randomData, iv, hmacKey = self.unpack(authBlob)
    self.alg='aes_256_cfb'
    self.iv = iv
    self.randomData = randomData
    self.hmacKey  = hmacKey
    self.value = randomData + iv
    self.reset()
    
  def reset(self):
    #self.key.IV = self.iv
    self.decryptCipher = EVP.Cipher(self.alg, self.randomData, self.iv, 0)
    self.encryptCipher = EVP.Cipher(self.alg, self.randomData, self.iv, 1)
    pass
  
  def pack(self):
    return struct.pack(MESSAGE_FORMAT, self.randomData, self.iv, self.hmacKey)
    
  def unpack(self, msg):
    return struct.unpack(MESSAGE_FORMAT, msg)
    
  def encrypt(self, msg):
    Basic.validate_type(msg, types.StringType)
    #make hmac
    mac = self.make_hmac(msg)
    
    inbuf = cStringIO.StringIO(mac + msg)
    outbuf = cStringIO.StringIO()
    outbuf.write(self.encryptCipher.update(inbuf.read()))
    outbuf.write(self.encryptCipher.final()) #no idea what this does because it is undocumented
    return outbuf.getvalue()
  
  def decrypt(self, encryptedMsg):
    Basic.validate_type(encryptedMsg, types.StringType)
    #decrypt the message
    inbuf = cStringIO.StringIO(encryptedMsg)
    outbuf = cStringIO.StringIO()
    outbuf.write(self.decryptCipher.update(inbuf.read()))
    outbuf.write(self.decryptCipher.final())
    msg = outbuf.getvalue()
    mac = msg[:32]
    msg = msg[32:]
    #validate the HMAC
    if self.make_hmac(msg) != mac:
      raise Exception('HMAC does not authenticate, is something bad going on?')
    return msg

  def make_hmac(self, msg):
    """creates an hmac out of msg using key
    @msg: message to mac"""
    return hmac.new(self.hmacKey, msg, sha256).digest()


if __name__=="__main__":
  k1 = SymmetricKey()
  k2 = SymmetricKey(k1.pack())
  print k2.decrypt(k1.encrypt("hey"))
  print k1.decrypt(k2.encrypt("again"))
  print k2.decrypt(k1.encrypt("hey"))
  print k1.decrypt(k2.encrypt("again"))