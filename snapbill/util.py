import os
import ConfigParser

import snapbill

global currentConnection
currentConnection = None

def setConnection(connection):
  global currentConnection
  currentConnection = connection

def ensureConnection(connection):
  'Ensure an api connection (use current if available)'
  # If a connection was provided, use than one
  if connection:
    return connection
  # If there was a connection already open, use that
  elif currentConnection:
    return currentConnection
  # Finally try create a new connection
  else:
    return snapbill.Connection()

def fetchPassword(username=None):
  paths = [
    os.path.expanduser('~/.snapbill.cfg'),
    ".snapbill.cfg",
  ]

  config = ConfigParser.RawConfigParser()
  for path in paths: config.read(path)

  section = username if username else 'default'


  if username is None:
    username = config.get(section, 'username')

  password = config.get(section, 'password')

  return (username, password)


def classname(name):
  """
  Converts an api object name into its associate class
  
  Capitilises the first letter, and each letter after an underscore
  """
  return '_'.join([x[:1].upper() + x[1:].lower() for x in name.split('_')])

class Error(Exception):
  def __init__(self, message, errors):
    self.message = message
    self.errors = errors

  def __str__(self):
    s = self.message
    for (key, message) in self.errors.items():
      if key: message = "[%s]: %s" % (key, message)
      s+= "\n - %s" % message
    return s
