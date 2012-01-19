import logging
import xml.dom.minidom as minidom

from handlers import Upstream, DummyResponse, ExceptionResponse, is_uuid
from handlers import TODO, TODO_PATH
import calibre, qxml


class TODO_RemoveItems (Upstream):
	_DUMMY_BODY = b'<?xml version="1.0" encoding="UTF-8"?><response><status>SUCCESS</status></response>'

	def __init__(self):
		Upstream.__init__(self, TODO, TODO_PATH + 'removeItems?', 'POST')

	def call(self, request, device):
		if device.is_provisional():
			return DummyResponse(data = self._DUMMY_BODY)

		with minidom.parseString(request.body) as doc:
			if self.process_xml(doc, device):
				xml = doc.toxml('UTF-8')
				request.update_body(xml)

		return self.call_upstream(request, device)

	def process_xml(self, doc, device):
		x_request = qxml.get_child(doc, 'request')
		x_items = qxml.get_child(x_request, 'items')

		was_updated = False
		for x_item in qxml.list_children(x_items, 'item'):
			if x_item.getAttribute('action') in ('GET', 'DOWNLOAD') and x_item.getAttribute('type') in ['EBOK', 'PDOC']:
				key = x_item.getAttribute('key')
				if is_uuid(key):
					x_items.removeChild(x_item)
					was_updated = True

					complete = x_item.getAttribute('complete_status')
					book = calibre.book(key)
					if complete == 'COMPLETED':
						if book:
							book.mark_downloaded_by(device)
						else:
							logging.warn("%s successfully downloaded missing book %s", device, book)
					elif complete == 'FAILED':
						logging.warn("device failed to download book %s %s", key, book)
					else:
						logging.warn("%s: unknown downloaded status %s for book %s", device, complete, book)

		if not len(x_items.childNodes):
			raise ExceptionResponse(data = self._DUMMY_BODY)

		return was_updated
