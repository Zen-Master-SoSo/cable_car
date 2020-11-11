""" Provides the Messenger class which sends and receives encoded Message objects """

import logging, socket
from select import select


class Messenger:
	"""Sends and receives encoded Message objects across the network.
	In order to use this class you must also import a Message class from one of the available
	options. Presently, the only two available are "json_messages" and "byte_messages". I.e.:

		from cable_car.json_messages import Message

	"""

	buffer_size		= 1024
	instance_count	= 0

	def __init__(self, sock):
		"""Instantiate a Messenger which communicates over the given socket.
		Pass an opened TCP socket to communicate with."""
		self.__sock = sock
		self.__sock.setblocking(0)
		self.local_ip = sock.getsockname()[0]
		self.remote_ip = sock.getpeername()[0]
		self.__read_buffer = bytearray()
		self.__write_buffer = bytearray()
		Messenger.instance_count += 1
		self._instance_id = Messenger.instance_count
		logging.debug("Instantiated Messenger %d" % self._instance_id)
		self.closed = False


	def close(self):
		logging.debug("Messenger %d saying SHUT_RDWR" % self._instance_id)
		self.__sock.shutdown(socket.SHUT_RDWR)
		self.closed = True


	def xfer(self):
		"""Do read/write operations.
		Call this function regularly to send/receive encoded/decoded Message class objects. """

		if self.closed:
			logging.debug("Messenger %d trying to do transfers when closed!" % self._instance_id)
			return False

		# Do select()
		sockets = [self.__sock]
		try:
			readable_sockets, writable_sockets, errored_sockets = select(sockets, sockets, [], 0)
		except IOError as e:
			logging.error(e)
			self.close()

		# If this socket errored, close for now. TODO: Continuous improvement wrt error-checking
		if errored_sockets:
			logging.error("Messenger %d socket returned as errored from select()" % self._instance_id)
			return self.close()

		# Read data if there anything there:
		if readable_sockets:
			try:
				data = self.__sock.recv(self.buffer_size)
			except BlockingIOError:
				pass
			except BrokenPipeError:
				self.closed = True
			except IOError as e:
				logging.error(e)
				self.close()
			else:
				if len(data):
					logging.debug("Messenger %d read %d bytes" % (self._instance_id, len(data)))
					self.__read_buffer += data

		# Write data if necessary:
		if writable_sockets and len(self.__write_buffer):
			try:
				bytes_sent = self.__sock.send(self.__write_buffer)
				logging.debug("Messenger %d wrote %d bytes" % (self._instance_id, bytes_sent))
			except BrokenPipeError:
				self.closed = True
			except IOError as e:
				logging.error(e)
			else:
				self.__write_buffer = self.__write_buffer[bytes_sent:]


	def get(self):
		"""Returns a Message object if there is data available, otherwise returns None """
		message, byte_len = Message.peel_from_buffer(self.__read_buffer)
		if byte_len:
			self.__read_buffer = self.__read_buffer[byte_len + 1:]
			return message
		return None


	def send(self, message):
		"""Appends an encoded message to the write buffer."""
		self.__write_buffer += message.encoded()



if __name__ == '__main__':

	import optparse, time, threading, sys

	p = optparse.OptionParser()
	p.add_option('--loopback', '-l', action='store_true')
	p.add_option('--verbose', '-v', action='store_true')
	p.add_option('--transport', type='string', default='JSON')
	options, arguments = p.parse_args()

	if options.transport == "JSON":
		from cable_car.json_messages import *
	elif options.transport == "bytes":
		from cable_car.byte_messages import *
	else:
		raise ValueError("%s is not a valid transport" % options.transport)

	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG if options.verbose else logging.ERROR,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)


	def _test_client():
		global _test_enable
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.settimeout(3)
		time.sleep(0.25)
		logging.debug("Client connecting")
		try:
			sock.connect(('127.0.0.1', 8222))
		except Exception as e:
			sock.close()
			logging.error(e)
			_test_enable = False
		logging.debug("Client connected")
		_test_comms(sock)
		logging.debug("Exiting _test_client")


	def _test_server():
		global _test_enable
		logging.debug("Server listening")
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setblocking(0)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(('127.0.0.1', 8222))
		sock.listen()
		while _test_enable:
			try:
				sock, address_pair = sock.accept()
			except BlockingIOError as be:
				pass
			except Exception as e:
				logging.error(e)
				_test_enable = False
			else:
				break
		logging.debug("Server connected")
		_test_comms(sock)
		logging.debug("Exiting _test_server")


	def _test_comms(sock):
		msgr = Messenger(sock)
		msgr.id_sent = False
		msgr.id_received = False
		while _test_enable:
			msgr.xfer()
			msg = msgr.get()
			if msg is not None:
				assert(isinstance(msg, Message))
				if(isinstance(msg, Identify)):
					msgr.id_received = True
			if msgr.id_sent:
				if msgr.id_received:
					return
			else:
				msgr.send(Identify())
				msgr.id_sent = True


	def _test_timeout():
		global _test_enable
		_quitting_time = time.time() + 10.0
		while _test_enable:
			if time.time() >= _quitting_time: break
			time.sleep(0.1)
		_test_enable = False
		logging.debug("Exiting _test_timeout")


	# Create threads:
	client_thread = threading.Thread(target=_test_client)
	server_thread = threading.Thread(target=_test_server)
	timeout_thread = threading.Thread(target=_test_timeout)
	# Start threads:
	_test_enable = True
	client_thread.start()
	server_thread.start()
	timeout_thread.start()
	# Wait for threads to exit:
	client_thread.join()
	server_thread.join()
	_test_enable = False
	timeout_thread.join()

	print("OKAY")

