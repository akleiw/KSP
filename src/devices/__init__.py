import logging, uuid

from devices.device import Device as _Device
import devices.db as _db
import devices.certificate as _certificate


def _update(device, ip_address = None, cookie = None):
	if ip_address == device.last_ip \
			and (not cookie or cookie == device.last_cookie or cookie.startswith(device.last_cookie)):
			# only bother writing to the db if any of them changed
		return device
	device.last_ip = ip_address
	if cookie:
		device.last_cookie = cookie[:64]
	_db.update(device)
	return device

def _make_context(device):
	"""
	Ensures creation of a SSL context for the device.
	If the device has no current PKCS12 certificate, loads it from the file 'db/<device_serial>.p12'
	"""
	if not device.p12:
		device.p12 = _certificate.load_p12bytes(device.serial)
	device.context = _certificate.make_context(device.serial, device.p12)
	if not device.context:
		device.mark_context_failed()
		return False
	return True

def get(serial):
	"""gets a device by serial"""
	return _devices.get(serial)

def update(device, cookie = None, fiona_id = None, pkcs12_bytes = None):
	if cookie:
		device.last_cookie = cookie[:64]
	if fiona_id:
		device.fiona_id = fiona_id
	if pkcs12_bytes:
		test_context = _certificate.make_context(device.serial, pkcs12_bytes)
		if not test_context:
			logging.error("%s tried to update PKCS12 key with invalid data -- ignored")
		else:
			logging.warn("%s updated its PKCS12 client key", device)
			device.p12 = pkcs12_bytes
			# Even though we're updating the client certificate, active connections will still work with the old one.
			# Actually, the old certificate will still be able to open new connections for an unknown amount of time.
			# So there's no point in destroying the current SSL context and creating a new one.
	_db.update(device)

def detect(ip_address, cookie = None):
	"""
	guess the device that made a request
	if no matching device exists in our database, one may be created on the spot
	"""
	for d in _devices.values():
		if (cookie and (cookie == d.last_cookie or cookie.startswith(d.last_cookie))) \
				or ip_address == d.last_ip: # match from most specific to less specific field
			if d.context_failed():
				# let's give it another chance... maybe the user put the proper .p12 into place
				if not _make_context(d):
					return d
				_db.insert(d)
			return _update(d, ip_address, cookie)
	# create new provisional device
	d = _Device(last_ip = ip_address, last_cookie = cookie)
	_devices[d.serial] = d
	logging.warn("failed to identify device from %s, created a provisional device %s", ip_address, d)
	return d

def confirm_device(device, serial):
	"""we've found the serial of a provisional device"""
	if not device.is_provisional():
		raise Exception("tried to confirm an already known device, wtf", device, serial)

	# first we check if the device has been previously seen, but we just could not identify it
	# (for example, the device might connect from a different IP and may have changed its cookie in the meantime)
	already_registered = _devices[serial]
	if already_registered:
		# yay, update ip and serial
		logging.info("identified provisional device %s as %s", device, already_registered)
		_update(already_registered, device.last_ip, device.last_cookie)
		del _devices[device.serial]
		return already_registered

	device.serial = serial
	if not _make_context(device):
		return None

	logging.warn("registered device %s", device)
	_db.insert(device)
	return device

def save_all():
	_db.update_all(_devices.values())


### module initialization
def __load_all():
	_all = {}
	for d in _db.load_all():
		if _make_context(d):
			_all[d.serial] = d
		else:
			logging.warn("not loading device %s, SSL context failed")
	return _all
_devices = __load_all()
del __load_all