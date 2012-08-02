import simplejson as json
import urllib2, urllib, base64, struct
from urllib import urlencode
from StringIO import StringIO
import subprocess
import re
try:
  import avro.io, avro.datafile
except ImportError, e:
  pass


def classname(name):
  return '_'.join([x[:1].upper() + x[1:].lower() for x in name.split('_')])

def __pad(string, multiple, char):
  # Count how many letters passed the last multiple
  N = len(string) % multiple
  # Pad on the left if needed
  if N: return ((multiple - N) * char) + string
  else: return string


def extend(*args):
  base = None
  for k in args:
    if base is None: base = k
    else: base.update(k)
  return base


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

global currentConnection
currentConnection = None

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


def ensureConnection(connection):
  'Ensure an api connection (use current if available)'
  if connection: return connection
  elif currentConnection: return currentConnection
  else:
    raise Exception('SnapBill API is currently not connected')

class SnapBill_Object(object):
  def __new__(cls, id, connection=None):
    connection = ensureConnection(connection)

    if type(id) is dict:
      if 'xid' in id: vid = decodeXid(id['xid'])[1]
      elif 'code' in id: vid = id['code']
      else: vid = id['id']
    else: vid = id

    obj = connection.cache(cls.__name__, vid)

    if obj:
      # If we were passed data, gather it
      if type(id) is dict:
        obj.gather(id)
    else:
      # Create a new object from supplied data
      obj = super(SnapBill_Object, cls).__new__(cls)
      connection.cache(cls.__name__, vid, obj)

    return obj

  def __init__(self, id, connection=None):
    # May be called multiple times due to __new__-based cache
    if 'data' in self.__dict__: return

    # Initialise basic values
    self.data = {}
    self.connection = ensureConnection(connection)

    # Pull out the id, and gather known values
    if type(id) is dict:
      self.gather(id)
    else:
      if isXid(id):
        (rid, oid) = decodeXid(id)
        self.gather({'id': oid, 'xid': id, 'account': {'id': rid}})
      else: self.gather({'id': id})

    self.fetched = False

  def gather(self, data):
    '''
    Collect additional data for the object, and check it matches the known data
    '''
    for k in data:
      v = data[k]

      # If we should actually be loading in an object for this
      if self.connection.hasFactory(classname(k)):
        if v: v = self.connection.factory(classname(k), v)
        else: v = None

      if k in self.data and self.data[k] != v:
        raise Exception('Gathered data for '+k+' of '+str(data[k])+' does not match existing value of '+str(self.data[k]))
      self.data[k] = v

  def post(self, command):
    if 'xid' in self.data: vid = self.data['xid']
    elif 'id' in self.data: vid = self.data['id']
    elif 'code' in self.data: vid = self.data['code']
    else: raise Exception('Could not find id for object')

    return self.connection.post('/v1/'+self.type+'/'+str(vid)+command)

  def fetch(self):
    '''
    Fetch complete list of data from the api
    '''
    result = self.post('/get')
    self.gather(result[self.type]) 
    self.fetched = True

  def __getitem__(self, key):
    return self.__getattr__(key)

  def __getattr__(self, key):
    if key in self.data:
      return self.data[key]
    elif key+'_id' in self.data:
      return globals()[classname(key)](self.data[key+'_id'])
    elif not self.fetched:
      self.connection.debug('Missing '+self.type+'.'+str(key)+'; fetching full object')
      self.fetch()
      return self.__getattr__(key)

    raise AttributeError(key+" on "+self.type+" #"+str(self.id)+" not found.")


class Batch(SnapBill_Object):
  '''
  Batch representing a group of payments
  '''
  def __init__(self, id, connection=None):
    super(Batch, self).__init__(id, connection=connection)
    self.type = 'batch'

  def download(self):
    # Load the avro data from snapbill
    records = self.connection.post('/v1/batch/'+str(self.xid)+'/download', format='json', returnStream=True, parse=True)

    # Gather additional batch data as available
    self.gather(records.next())

    return (Payment(record, connection=self.connection) for record in records)


  def xml(self):
    return self.connection.post('/v1/batch/'+str(self.xid)+'/xml', format='xml', parse=False)

  def set_state(self, state):
    self.connection.submit('/v1/batch/'+str(self.xid)+'/set_state', {'state': state})

  def update(self, data):
    self.connection.submit('/v1/batch/'+str(self.xid)+'/update', data)

  @staticmethod
  def list(connection=None, **search): 

    if 'account' in search and type(search['account']) is list:
      search['account'] = ','.join([str(x['id']) for x in search['account']])

    if 'state' in search and not type(search['state']) is list:
      search['state'] = [search['state']]

    return ensureConnection(connection).list('batch', **search)

class Client(SnapBill_Object):
  '''
  Single client in SnapBill
  '''
  def __init__(self, id, connection=None):
    super(Client, self).__init__(id, connection)
    self.type = 'client'

  def add_service(self, **data):
    result = self.connection.submit('/v1/client/'+str(self.id)+'/add_service', data)
    return Service(result['id'])

  def set_payment(self, data):
    self.connection.submit('/v1/client/'+str(self.id)+'/set_payment', data)

  @staticmethod
  def add(connection=None, **data):
    return ensureConnection(connection).add('client', **data)

class File(SnapBill_Object):
  '''
  Uploaded file
  '''
  def __init__(self, id, connection=None):
    super(File, self).__init__(id, connection)
    self.type = 'file'

  @staticmethod
  def add(connection=None, **data):
    return ensureConnection(connection).add('file', **data)

class Payment(SnapBill_Object):
  '''
  Single payment from a client
  '''
  def __init__(self, id, connection=None):
    super(Payment, self).__init__(id, connection)
    self.type = 'payment'

  def error(self, message):
    return self.connection.post('/v1/payment/'+str(self.xid)+'/error', {'message': message}, format='xml', parse=False)

  @staticmethod
  def list(connection=None, **search):
    if 'client' in search and type(search['client']) is Client:
      search['client_id'] = search['client'].id
      del search['client']

    return ensureConnection(connection).list('payment', **search)

class Payment_Details(SnapBill_Object):
  '''
  Payment details of a client (bank account / credit card)
  '''
  def __init__(self, id, connection=None):
    super(Payment_Details, self).__init__(id, connection)
    self.type = 'payment_details'

class Payment_Method(SnapBill_Object):
  def __init__(self, id, connection=None):
    super(Payment_Method, self).__init__(id, connection)
    self.type = 'payment_method'

class Service(SnapBill_Object):
  '''
  Single recurring service belonging to a client
  '''
  def __init__(self, id, connection=None):
    super(Service, self).__init__(id, connection)
    self.type = 'service'

class Account(SnapBill_Object):
  '''
  Master account with own set of clients
  '''
  def __init__(self, id, connection=None):
    super(Account, self).__init__(id, connection=connection)
    self.type = 'account'

  @staticmethod
  def list(connection=None, **search): 
    return ensureConnection(connection).list('account', **search)

class Connection(object):
  def __init__(self,username, password, server, secure=True, headers={}, logger=None):
    self.username = username
    self.password = password
    self.server = server
    self.secure = secure

    if secure: self.url = 'https://' + server
    else: self.url = 'http://' + server

    self._cache = {}
    self.headers = headers
    self.logger = logger

    global currentConnection
    currentConnection = self

  def cache(self, cls, id, obj=None):
    if obj is None:
      if cls in self._cache and id in self._cache[cls]:
        return self._cache[cls][id]
      else:
        return None

    else:
      if not cls in self._cache: self._cache[cls] = {}
      self._cache[cls][id] = obj


  def encode_params(self, param):
    '''
    urlencode params with flattening out lists and accepting encoded strings
    '''
    if type(param) is dict:
      # Append [] to any list types
      items = [(k+'[]', v) if type(v) is list else (k,v)
                for (k,v) in param.items()]
      
      return urlencode(items, True)
    elif type(param) is list:
      return '&'.join([self.encode_params(p) for p in param])
    elif type(param) is str:
      return param
    else: raise Exception("Unknown param type: "+str(type(param)))

  def debug(self, message):
    if not self.logger: return
    if len(message) > 100: self.logger.debug(message[:100] + '...')
    else: self.logger.debug(message)

  def post(self, uri, params={}, format='json', returnStream=False, parse=True):
    # Encode the params correctly
    post = self.encode_params(params)

    # Show some logging information
    self.debug('>>> '+self.url+uri+'?'+post+(' '+str(self.headers) if self.headers else ''))

    # Could be in __init__ but gets forgotten somehow
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password('SnapBill API', self.url, self.username, self.password)
    auth_handler = urllib2.HTTPBasicAuthHandler(password_manager)
    self.opener = urllib2.build_opener(auth_handler)

    request = urllib2.Request(self.url+uri+'.'+format, headers=self.headers)
    try: 
      response = self.opener.open(request, post)
    except urllib2.HTTPError, e:
      self.debug("HTTPError("+str(e.code)+"): "+str(e))
      raise e

    if returnStream:
      if self.logger:
        self.logger.debug('<<< [data stream]')

      if not parse:
        return response
      elif format is 'json':
        return (json.loads(x.decode('UTF-8')) for x in response)
      elif format is 'avro':
        if not avro:
          raise Exception('Required avro module was not found.')
        return avro.datafile.DataFileReader(response, avro.io.DatumReader())
      else:
        raise Exception('Could not parse format '+format+' as stream')

    #except urllib.error.HTTPError as e:
    #u = e
    data = response.read().decode('UTF-8')

    if self.logger:
      if len(data) > 100: self.logger.debug('<<< '+data[:100]+'...')
      else: self.logger.debug('<<< '+data)

    if parse:
      if format == 'json': data = json.loads(data)

    return data

  def submit(self, uri, param={}):
    # Convert data:{} into data-x
    if 'data' in param:
      for k,v in param['data'].iteritems():
        param['data-'+k] = v
      del param['data']

    result = self.post(uri,param)
    if result['status'] == 'error':
      raise SnapBill_Exception(result['message'], result['errors'])
    else:
      return result

  def hasFactory(self, cls):
    return (cls in globals())

  def factory(self, cls, ident):
    constructor = globals()[cls]
    return constructor(ident, connection=self)

  def add(self, cls, **data):
    result = self.post('/v1/'+cls+'/add', data)

    if 'status' in result and result['status'] == 'error':
      raise SnapBill_Exception(result['message'], result['errors'])

    return self.factory(classname(cls), results[cls])

  def list(self, cls, **data):
    return [self.factory(classname(cls), obj) for obj in self.post('/v1/'+cls+'/list', data)['list']]
