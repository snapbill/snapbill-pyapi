import base64
import struct
import re

def __pad(string, multiple, char):
  # Count how many letters passed the last multiple
  N = len(string) % multiple
  # Pad on the left if needed
  if N: return ((multiple - N) * char) + string
  else: return string


def __decodeXidPart(part):
  # Pad the part to the left with A=0 for b64decode to either 4 or 8 bytes
  part = __pad(part, 4, 'A')
  # Decode it as a binary string
  decoded = base64.urlsafe_b64decode(part)
  # Pad the binary string to size of an integer
  decoded = '\0'*(4-len(decoded)) + decoded
  # Unpack the binary string
  return struct.unpack('!I', decoded)[0]

def __encodeXidPart(part):
  # First pack it as an integer
  packed = struct.pack('!I', part)
  # Ensure its three bytes or six long (=> 4 in base64)
  packed = __pad(packed.lstrip('\0'), 3, '\0')
  # Encode according to base64
  encoded = base64.urlsafe_b64encode(packed)
  # Return stripped
  return encoded.lstrip('A')

def decodeXid(xid):
  return tuple([__decodeXidPart(x) for x in str(xid).split(':')])

def encodeXid(accountId, id):
  return ':'.join([__encodeXidPart(int(x)) for x in (accountId, id)])

def isXid(xid):
  if (type(xid) is str or type(xid) is unicode) and (re.match(r'^[A-Za-z0-9-_]+:[A-Za-z0-9-_]+$', xid)):
    return True
  else:
    return False

