import simplejson as json
import urllib2, urllib

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

global snapbill

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
  def __new__(cls, id):
    if type(id) is dict: vid = id['id']
    else: vid = id

    obj = snapbill.cache(cls.__name__, vid)
    if not obj:
      obj = super(SnapBill_Object, cls).__new__(cls)
      snapbill.cache(cls.__name__, vid, obj)

    return obj

  def __init__(self, id):
    # May be called multiple times due to __new__-based cache
    if 'id' in self.__dict__: return

    if type(id) is dict:
      self.id = id['id']
      self.data = id
    else:
      self.id = id
      self.data = {'id': id}
    self.fetched = False

  def __getattribute__(self, name):
    try: return super(SnapBill_Object, self).__getattribute__(name)
    except AttributeError, exception: pass # keep exception for later, in case
    
    try:
      id = self[name+'_id']
      return globals()[classname(name)](id)
    except KeyError: pass

    raise exception

  def fetch(self):
    global snapbill
    result = snapbill.post('/v1/'+self.type+'/'+str(self.id)+'/get')
    self.data = result[self.type]
    self.fetched = True

  def __getitem__(self, key):
    if not key in self.data and not self.fetched: self.fetch()
    return self.data[key]

class Reseller(SnapBill_Object):
  def __init__(self, id):
    super(Reseller, self).__init__(id)
    self.type = 'reseller'

  @staticmethod
  def list(**search): 
    global snapbill
    return snapbill.list('reseller', **search)

class Batch(SnapBill_Object):
  def __init__(self, id):
    super(Batch, self).__init__(id)
    self.type = 'batch'

  def xml(self):
    global snapbill
    return snapbill.post('/v1/batch/'+str(self.id)+'/xml', format='xml', parse=False)

  def update(self, data):
    global snapbill
    snapbill.submit('/v1/batch/'+str(self.id)+'/update', data)

  @staticmethod
  def list(**search): 
    global snapbill

    if 'reseller' in search and type(search['reseller']) is list:
      search['reseller_id'] = ','.join([str(x['id']) for x in search['reseller']])
      del search['reseller']

    return snapbill.list('batch', **search)

class Batch_Client(SnapBill_Object):
  def __init__(self, id):
    super(Batch_Client, self).__init__(id)
    self.type = 'batch_client'

  def error(self, message):
    global snapbill
    return snapbill.post('/v1/batch_client/'+str(self.id)+'/error', {'message': message}, format='xml', parse=False)

  @staticmethod
  def list(**search):
    if 'client' in search and type(search['client']) is Client:
      search['client_id'] = search['client'].id
      del search['client']
    if 'batch' in search and type(search['batch']) is Batch:
      search['batch_id'] = search['batch'].id
      del search['batch']

    global snapbill
    return [Batch_Client(b) for b in snapbill.post('/v1/batch_client/list', search)['list']]

class Client(SnapBill_Object):
  def __init__(self, id):
    super(Client, self).__init__(id)
    self.type = 'client'

  def add_service(self, **data):
    global snapbill
    result = snapbill.submit('/v1/client/'+str(self.id)+'/add_service', data)
    return Service(result['id'])

  def set_payment(self, data):
    global snapbill
    snapbill.submit('/v1/client/'+str(self.id)+'/set_payment', data)

  @staticmethod
  def add(**data):
    global snapbill
    return snapbill.add('client', **data)


class Service(SnapBill_Object):
  def __init__(self, id):
    super(Service, self).__init__(id)
    self.type = 'service'

class API:
  def __init__(self,username, password, server, secure=True):
    self.username = username
    self.password = password
    if secure: self.url = 'https://' + server
    else: self.url = 'http://' + server

    self._cache = {}

    global snapbill
    snapbill = self

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
    print uri, param

    # Could be in __init__ but gets forgotten somehow
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password('SnapBill API', self.url, self.username, self.password)
    auth_handler = urllib2.HTTPBasicAuthHandler(password_manager)
    self.opener = urllib2.build_opener(auth_handler)

    try: 
      u =	self.opener.open(self.url+uri+'.'+format, urllib.urlencode(param))
    except urllib2.URLError, e:
      print 'URLError - retry'
      u =	self.opener.open(self.url+uri+'.'+format, urllib.urlencode(param))
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
  def add(cls, **data):
    global snapbill
    result = snapbill.submit('/v1/'+cls+'/add', data)
    return globals()[classname(cls)](result['id'])

  @staticmethod
  def list(cls, **data):
    global snapbill
    constructor = globals()[classname(cls)]
    return [constructor(o) for o in snapbill.post('/v1/'+cls+'/list', data)['list']]
