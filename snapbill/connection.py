import simplejson as json

import requests

import urllib2, urllib
from urllib import urlencode

from util import Error, setConnection, classname, fetchPassword

import snapbill.objects
import snapbill.exceptions

class Connection(object):
  def __init__(self,username=None, password=None, server='api.snapbill.com', secure=True, headers={}, logger=None):

    # Try read the password from ~/.snapbill.cfg if available
    if password is None:
      (username, password) = fetchPassword(username)

    self.auth = (username, password)
    self.server = server
    self.secure = secure

    if secure: self.url = 'https://' + server
    else: self.url = 'http://' + server

    self._cache = {}
    self.logger = logger

    self.headers = {
        'Accept': 'application/json'
      }
    self.headers.update(headers)

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

  def request(self, uri, params=None, returnStream=False, parse=True):

    # Encode the params correctly
    if params is None:
      post = None
    else:
      # Convert data:{} into data-x
      if 'data' in params:
        for k,v in params['data'].iteritems():
          params['data-'+k] = v
        del params['data']

      post = self.encode_params(params)

    # Show some logging information
    self.debug('>>> '+self.url+uri+('?'+post if post else '') + (' '+str(self.headers) if self.headers else ''))

    # Setup correct headers for the request
    headers = self.headers.copy()
    if post is not None:
      headers.update({"content-type": "application/x-www-form-urlencoded"})

    kwargs = {'auth': self.auth, 'headers': headers}
    
    # Stream the request if requested
    if returnStream: kwargs['stream'] = True

    if post is not None:
      response = requests.post(self.url + uri, data=post, **kwargs)
    else:
      response = requests.get(self.url + uri, **kwargs)

    if returnStream:
      if self.logger:
        self.logger.debug('<<< [data stream]')

      if not parse:
        return response

      return (json.loads(x.decode('UTF-8')) for x in response.iter_lines())

    body = response.text.decode('UTF-8')

    if self.logger:
      if len(body) > 100: self.logger.debug('<<< '+body[:100]+'...')
      else: self.logger.debug('<<< '+body)

    if parse:
      data = json.loads(body)

      # Data has now been parsed from SnapBill
      if response.status_code // 100 == 2:
        return data
      elif response.status_code // 100 == 5:
        raise snapbill.exceptions.InternalError(response.status_code, body, 
            data['message']
          )
      elif response.status_code == 404:
        raise snapbill.exceptions.CommandNotFound(response.status_code, body, 
            data['message']
          )
      else:
        raise snapbill.exceptions.FormErrors(response.status_code, body, 
            data['message'], data['errors']
          )

    else:
      # Deal with responses of unparsed data
      if response.status_code // 100 == 2:
        return body
      elif response.status_code // 100 == 5:
        raise snapbill.exceptions.InternalError(response.status_code, body, 
            'SnapBill encountered an internal error while processing the request.'
          )
      else:
        raise snapbill.exceptions.HTTPError(response.status_code, body)


  def get(self, uri, returnStream=False, parse=True):
    return self.request(uri, None, returnStream, parse)

  def post(self, uri, params={}, returnStream=False, parse=True):
    return self.request(uri, params, returnStream, parse)

  def hasFactory(self, cls):
    return hasattr(snapbill.objects, classname(cls))

  def factory(self, cls, ident):
    constructor = getattr(snapbill.objects, classname(cls))
    return constructor(ident, connection=self)

  def add(self, cls, data):
    result = self.post('/v1/'+cls+'/add', data)
    return self.factory(cls, result[cls])

  def list(self, cls, data):
    return [self.factory(cls, obj) for obj in self.post('/v1/'+cls+'/list', data)['list']]


