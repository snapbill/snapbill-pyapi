import snapbill
from snapbill.util import ensureConnection

class Batch(snapbill.Base):
  '''
  Batch representing a group of payments
  '''
  def __init__(self, id, connection=None):
    super(Batch, self).__init__(id, connection=connection)
    self.type = 'batch'

  def set_state(self, state):
    self.connection.post('/v1/batch/'+str(self.xid)+'/set_state', {'state': state})

  def update(self, data):
    result = self.post('/update', data)
    self.gather(result['batch'], overwrite=True)
    return result

  @staticmethod
  def list(search, connection=None): 

    if 'account' in search and type(search['account']) is list:
      search['account'] = ','.join([str(x['id']) for x in search['account']])

    if 'state' in search and not type(search['state']) is list:
      search['state'] = [search['state']]

    return ensureConnection(connection).list('batch', search)

class User(snapbill.Base):
  '''
  SnapBill wrapper object representing login details for a specific client or staff member
  '''
  def __init__(self, id, connection=None):
    super(User, self).__init__(id, connection)
    self.type = 'user'

  @staticmethod
  def list(search, connection=None): 
    return ensureConnection(connection).list('user', search)

  @staticmethod
  def login(username, password, connection=None): 
    users = User.list({"username": username, "password": password}, connection=connection)
    if len(users) > 1: raise Exception("Failure during login (received multiple users)")
    elif users: return users[0]
    else: return None

class Client(snapbill.Base):
  '''
  Single client in SnapBill
  '''
  def __init__(self, id, connection=None):
    super(Client, self).__init__(id, connection)
    self.type = 'client'

  def add_user(self, data):
    result = self.post('/add_user', data)
    return User(result['user'])

  def add_service(self, data):
    result = self.post('/add_service', data)
    return Service(result['service'])

  def set_payment(self, data):
    return self.post('/set_payment', data)

  def update(self, data):
    result = self.post('/update', data)
    self.gather(result['client'], overwrite=True)
    return result

  @staticmethod
  def add(data, connection=None):
    return ensureConnection(connection).add('client', data)

class File(snapbill.Base):
  '''
  Uploaded file
  '''
  def __init__(self, id, connection=None):
    super(File, self).__init__(id, connection)
    self.type = 'file'

  @staticmethod
  def add(data, connection=None):
    return ensureConnection(connection).add('file', data)

class Payment(snapbill.Base):
  '''
  Single payment from a client
  '''
  def __init__(self, id, connection=None):
    super(Payment, self).__init__(id, connection)
    self.type = 'payment'

  def error(self, message):
    return self.connection.post('/v1/payment/'+str(self.xid)+'/error', {'message': message}, parse=False)

  @staticmethod
  def list(search, connection=None):
    if 'client' in search and type(search['client']) is Client:
      search['client_id'] = search['client'].id
      del search['client']

    return ensureConnection(connection).list('payment', search)

class Payment_Details(snapbill.Base):
  '''
  Payment details of a client (bank account / credit card)
  '''
  def __init__(self, id, connection=None):
    super(Payment_Details, self).__init__(id, connection)
    self.type = 'payment_details'

class Payment_Method(snapbill.Base):
  def __init__(self, id, connection=None):
    super(Payment_Method, self).__init__(id, connection)
    self.type = 'payment_method'

class Service_Type(snapbill.Base):
  '''
  Group of a type of service
  '''
  def __init__(self, id, connection=None):
    super(Service_Type, self).__init__(id, connection=connection)
    self.type = 'service_type'

  @staticmethod
  def list(search, connection=None): 
    return ensureConnection(connection).list('service_type', search)

class Service(snapbill.Base):
  '''
  Single recurring service belonging to a client
  '''
  def __init__(self, id, connection=None):
    super(Service, self).__init__(id, connection)
    self.type = 'service'

class Currency(snapbill.Base):
  '''
  Details about a specific currency
  '''
  def __init__(self, id, connection=None):
    super(Currency, self).__init__(id, connection)
    self.type = 'currency'

class Account(snapbill.Base):
  '''
  Master account with own set of clients
  '''
  def __init__(self, id, connection=None):
    super(Account, self).__init__(id, connection=connection)
    self.type = 'account'

  @staticmethod
  def list(search, connection=None): 
    return ensureConnection(connection).list('account', search)

