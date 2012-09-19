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

class Client(snapbill.Base):
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

class File(snapbill.Base):
  '''
  Uploaded file
  '''
  def __init__(self, id, connection=None):
    super(File, self).__init__(id, connection)
    self.type = 'file'

  @staticmethod
  def add(connection=None, **data):
    return ensureConnection(connection).add('file', **data)

class Payment(snapbill.Base):
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
  def list(connection=None, **search): 
    return ensureConnection(connection).list('account', **search)

