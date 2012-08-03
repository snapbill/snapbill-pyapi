import snapbill

global currentConnection
currentConnection = None

def setConnection(connection):
  global currentConnection
  currentConnection = connection

def ensureConnection(connection):
  'Ensure an api connection (use current if available)'
  if connection: return connection
  elif currentConnection: return currentConnection
  else:
    raise Exception('SnapBill API is currently not connected')


def classname(name):
  """
  Converts an api object name into its associate class
  
  Capitilises the first letter, and each letter after an underscore
  """
  return '_'.join([x[:1].upper() + x[1:].lower() for x in name.split('_')])

class SnapBill_Exception(Exception):
  def __init__(self, message, errors):
    self.message = message
    self.errors = errors

  def __str__(self):
    s = self.message
    for (k,x) in self.errors.items(): s+= "\n" + ' - '+x
    return s

  def print_errors(self):
    for (k,x) in self.errors.items(): print (' - '+x)
