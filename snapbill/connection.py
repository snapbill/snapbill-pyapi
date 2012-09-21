import simplejson as json
import urllib2, urllib
from urllib import urlencode

from util import SnapBill_Exception, setConnection, classname
import snapbill.objects

class Connection(object):
  def __init__(self,username, password, server='api.snapbill.com', secure=True, headers={}, logger=None):
    self.username = username
    self.password = password
    self.server = server
    self.secure = secure

    if secure: self.url = 'https://' + server
    else: self.url = 'http://' + server

    self._cache = {}
    self.headers = headers
    self.logger = logger

    setConnection(self)

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
    return hasattr(snapbill.objects, classname(cls))

  def factory(self, cls, ident):
    constructor = getattr(snapbill.objects, classname(cls))
    return constructor(ident, connection=self)

  def add(self, cls, **data):
    result = self.post('/v1/'+cls+'/add', data)

    if 'status' in result and result['status'] == 'error':
      raise SnapBill_Exception(result['message'], result['errors'])

    return self.factory(cls, result[cls])

  def list(self, cls, **data):
    return [self.factory(cls, obj) for obj in self.post('/v1/'+cls+'/list', data)['list']]


