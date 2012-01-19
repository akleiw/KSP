from http.client import responses as HTTP_MESSAGES

from content import date_header, str_headers, str_


class DummyResponse (object):
	"""an HTTP response for downloading book files"""
	def __init__(self, status = 200, headers = None, data = None):
		self.status = status
		self.reason = HTTP_MESSAGES[status]
		self.body = data
		self.length = 0 if data is None else len(data)

		self.headers = dict( {} if headers is None else headers )
		self.headers['Server'] = 'Amazon Web Server'
		self.headers['Date'] = date_header()
		# if data is not None:
		self.headers['Content-Length'] = str(self.length)
		self.will_close = 'close' == self.headers.get('Connection')

	def write_to(self, stream_out):
		if not self.body:
			return 0
		stream_out.write(self.body)
		return self.length

	def __str__(self):
		hstr = str_headers(self.headers.items())
		t = "[DUMMY] %d %s (%d) %s" % (self.status, self.reason, self.length, hstr)
		if self.body:
			t += "\n" + str_(self.body)
		return t


class ExceptionResponse (Exception):
	"""
	an exception wrapping a response
	used to return a response out-of-order
	"""
	def __init__(self, *args, **kwargs):
		self.response = DummyResponse(*args, **kwargs)


class Dummy (object):
	"""
	dummy response, ignores the call
	while returning an empty response
	"""
	def __init__(self, service, path, command = None):
		if not path:
			raise Exception("path required", self)
		self.service = service
		self.expected_path = path
		self.expected_command = command

	def accept(self, request):
		"""returns True if this handler can process the given request"""
		if not request.path.startswith(self.expected_path):
			return False
		if self.expected_command:
			if request.command != self.expected_command:
				return False
		return True

	def call(self, request, device):
		"""produces a response for this request"""
		return DummyResponse()
