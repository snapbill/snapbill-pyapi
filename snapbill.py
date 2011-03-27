import simplejson as json
import urllib2, urllib, base64, struct

#url = 'http://api/v1/batches/list.json'
#
#values = URL({'state': 'ready'})
#request = urllib2.Request(url, values)
#
#base64string = base64.encodestring('%s:%s' % (config.get('api', 'user'), config.get('api', 'password')))[:-1]
#request.add_header("Authorization", "Basic %s" % base64string)
#
#response = urllib2.urlopen(request)
#print json.load(response)

def classname(name):
  return '_'.join([x[:1].upper() + x[1:].lower() for x in name.split('_')])

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

def encodeXid(resellerId, id):
  return ':'.join([__encodeXidPart(x) for x in (resellerId, id)])

global currentApi
currentApi = None

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

class SnapBill_Object(object):
  def __new__(cls, id, api=None):
    if not api: api = currentApi

    if type(id) is dict: vid = id['id']
    else: vid = id

    obj = api.cache(cls.__name__, vid)
    if not obj:
      obj = super(SnapBill_Object, cls).__new__(cls)
      api.cache(cls.__name__, vid, obj)

    return obj

  def __init__(self, id, api=None):
    if not api: api = currentApi

    # May be called multiple times due to __new__-based cache
    if 'id' in self.__dict__: return

    if type(id) is dict:
      self.id = id['id']
      self.data = id
    else:
      self.id = id
      self.data = {'id': id}
    self.fetched = False
    self.api = api

  def __getattribute__(self, name):
    try: return super(SnapBill_Object, self).__getattribute__(name)
    except AttributeError, exception: pass # keep exception for later, in case
    
    try:
      id = self[name+'_id']
      return globals()[classname(name)](id)
    except KeyError: pass

    raise exception

  def fetch(self):
    result = self.api.post('/v1/'+self.type+'/'+str(self.id)+'/get')
    self.data = result[self.type]
    self.fetched = True

  def __getitem__(self, key):
    if not key in self.data and not self.fetched: self.fetch()
    return self.data[key]

  def __getattr__(self, key):
    if not key in self.data and not self.fetched: self.fetch()
    return self.data[key]

class Reseller(SnapBill_Object):
  def __init__(self, id, api=None):
    super(Reseller, self).__init__(id, api=api)
    self.type = 'reseller'

  @staticmethod
  def list(api=None, **search): 
    if not api: api = currentApi
    return api.list('reseller', api=api, **search)

class Batch(SnapBill_Object):
  def __init__(self, id, api=None):
    super(Batch, self).__init__(id, api=api)
    self.type = 'batch'

  def xml(self):
    return self.api.post('/v1/batch/'+str(self.id)+'/xml', format='xml', parse=False)

  def update(self, data):
    self.api.submit('/v1/batch/'+str(self.id)+'/update', data)

  @staticmethod
  def list(api=None, **search): 
    if not api: api = currentApi
    if 'reseller' in search and type(search['reseller']) is list:
      search['reseller_id'] = ','.join([str(x['id']) for x in search['reseller']])
      del search['reseller']

    return api.list('batch', api=api, **search)

class Payment(SnapBill_Object):
  def __init__(self, id, api=None):
    super(Payment, self).__init__(id, api)
    self.type = 'payment'

  def error(self, message):
    return self.api.post('/v1/payment/'+str(self.id)+'/error', {'message': message}, format='xml', parse=False)

  @staticmethod
  def list(api=None, **search):
    if not api: api = currentApi
    if 'client' in search and type(search['client']) is Client:
      search['client_id'] = search['client'].id
      del search['client']

    return api.list('payment', api=api, **search)

class Client(SnapBill_Object):
  def __init__(self, id, api=None):
    super(Client, self).__init__(id, api)
    self.type = 'client'

  def add_service(self, **data):
    result = self.api.submit('/v1/client/'+str(self.id)+'/add_service', data)
    return Service(result['id'])

  def set_payment(self, data):
    self.api.submit('/v1/client/'+str(self.id)+'/set_payment', data)

  @staticmethod
  def add(api=None, **data):
    if not api: api = currentApi
    return api.add('client', **data)


class Service(SnapBill_Object):
  def __init__(self, id, api=None):
    super(Service, self).__init__(id, api)
    self.type = 'service'

class API:
  def __init__(self,username, password, server, secure=True, headers={}):
    self.username = username
    self.password = password
    if secure: self.url = 'https://' + server
    else: self.url = 'http://' + server

    self._cache = {}
    self.headers = headers

    global currentApi
    currentApi = self

  def cache(self, cls, id, obj=None):
    if obj is None:
      if cls in self._cache and id in self._cache[cls]:
        return self._cache[cls][id]
      else:
        return None

    else:
      if not cls in self._cache: self._cache[cls] = {}
      self._cache[cls][id] = obj


  def post(self, uri, param={}, format='json', parse=True):
    print self.headers, uri, param

    # Could be in __init__ but gets forgotten somehow
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password('SnapBill API', self.url, self.username, self.password)
    auth_handler = urllib2.HTTPBasicAuthHandler(password_manager)
    self.opener = urllib2.build_opener(auth_handler)

    request = urllib2.Request(self.url+uri+'.'+format, headers=self.headers)
    try: 
      u =	self.opener.open(request, urllib.urlencode(param))
    except urllib2.URLError, e:
      print 'URLError - retry'
      u =	self.opener.open(request, urllib.urlencode(param))

    #except urllib.error.HTTPError as e:
    #u = e
    response = u.read().decode('UTF-8')

    if len(response) > 100: print '<<<', response[:100]+'...'
    else: print '<<<', response
    if parse:
      if format == 'json': response = json.loads(response)

    return response

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

  @staticmethod
  def add(cls, api=None, **data):
    if not api: api = currentApi
    result = api.submit('/v1/'+cls+'/add', data)
    return globals()[classname(cls)](result['id'])

  @staticmethod
  def list(cls, api=None, **data):
    if not api: api = currentApi
    constructor = globals()[classname(cls)]
    return [constructor(o, api=api) for o in api.post('/v1/'+cls+'/list', data)['list']]
