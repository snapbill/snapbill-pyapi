import requests.exceptions

class HTTPError(RuntimeError):
  def __init__(self, status_code, body):
    self.status_code = status_code
    self.body = body

class InternalError(HTTPError):
  def __init__(self, status_code, body, message):
    super(InternalError, self).__init__(status_code, body)

    self.message = message

  def __str__(self):
    return self.message

class CommandNotFound(HTTPError):
  def __init__(self, status_code, body, message):
    super(CommandNotFound, self).__init__(status_code, body)

    self.message = message

  def __str__(self):
    return self.message

class FormErrors(HTTPError):
  def __init__(self, status_code, body, message, errors):
    super(FormErrors, self).__init__(status_code, body)

    self.message = message
    self.errors = errors

  def __str__(self):
    s = self.message
    for (key, message) in self.errors.items():
      if key: message = "[%s]: %s" % (key, message)
      s+= "\n - %s" % message
    return s
