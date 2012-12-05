import snapbill
from snapbill.util import ensureConnection
from snapbill.xid import isXid, decodeXid

class Base(object):
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
      obj = super(Base, cls).__new__(cls)
      connection.cache(cls.__name__, vid, obj)

    return obj

  def __init__(self, id, connection=None):
    # May be called multiple times due to __new__-based cache
    if 'data' in self.__dict__: return

    # Initialise basic values
    self._data = {}
    self.connection = ensureConnection(connection)
    self._type = self.__class__.__name__.lower()

    # Pull out the id, and gather known values
    if type(id) is dict:
      self.gather(id)
    else:
      if isXid(id):
        (rid, oid) = decodeXid(id)
        self.gather({'id': oid, 'xid': id, 'account': {'id': rid}})
      else: self.gather({'id': id})

    self.fetched = False

  def gather(self, data, overwrite=False):
    '''
    Collect additional data for the object, and check it matches the known data
    '''
    for k in data:
      v = data[k]

      # If we should actually be loading in an object for this
      if self.connection.hasFactory(k):
        if v: v = self.connection.factory(k, v)
        else: v = None

      if (not overwrite) and (k != "depth") and (k in self._data) and (self._data[k] != v):
        raise Exception('Gathered data for '+k+' of '+str(data[k])+' does not match existing value of '+str(self._data[k]))

      self._data[k] = v

  def dump(self):
    'Returns a dict of all known properties so far'
    return self._data.copy()

  def get_uri(self):
    if 'xid' in self._data: vid = self._data['xid']
    elif 'id' in self._data: vid = self._data['id']
    elif 'code' in self._data: vid = self._data['code']
    else: raise Exception('Could not find id for object')

    return '/v1/'+self._type+'/'+str(vid)

  def post(self, uri, data={}):
    return self.connection.post(self.get_uri()+uri, data)

  def fetch(self):
    '''
    Fetch complete list of data from the api
    '''
    result = self.post('/get')
    self.gather(result[self._type]) 
    self.fetched = True

  def __getitem__(self, key):
    return self.__getattr__(key)

  def __getattr__(self, key):
    if key in self._data:
      return self._data[key]
    elif key+'_id' in self._data:
      return self.connection.factory(key, self._data[key+'_id'])
    elif not self.fetched:
      self.connection.debug('Missing '+self._type+'.'+str(key)+'; fetching full object')
      self.fetch()
      return self.__getattr__(key)

    raise AttributeError(key+" on "+self._type+" #"+str(self.id)+" not found.")


