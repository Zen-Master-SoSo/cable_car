"""
Provides the Messenger class which sends and receives encoded Message objects.
.

Currently, the Messenger supports two transports; "json" or "byte". The "json"
transport is a lot easier to implement, but requires more network bandwidth and
may be slow for very busy network games. In contrast, the "byte" transport is
very lightweight, but requires that you write message encoding and decoding
routines for every message class which will pass information.

"json" messages may still require custom encoding and decoding if your messages
use attributes which are not python built-in types. For example, if you create
a json message class which uses a custom class as an attribute, you need to
convert the custom class into python built-in types when encoding, and recreate
the custom class from the python built-in types when reconstructing the message
on the receiving end.

"""

import logging, socket, importlib
from select import select



class Messenger:
	""" Sends and receives encoded Message objects across the network.
	See messenger module for notes on transport options. """

	buffer_size		= 1024
	instance_count	= 0


	def __init__(self, sock, transport="json"):
		"""
		Instantiate a Messenger which communicates over the given socket.
		sock - an opened TCP socket to communicate with.
		transport - a string identifying the transport class to use.
		"""
		global Message
		self.__sock = sock
		self.transport = transport
		module = importlib.import_module("cable_car.%s_messages" % self.transport)
		Message = getattr(module, "Message")
		Message.register_messages()
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
		if not self.closed:
			logging.debug("Messenger %d saying SHUT_RDWR" % self._instance_id)
			self.__sock.shutdown(socket.SHUT_RDWR)
			self.closed = True


	def shutdown(self):
		if self.closed: return
		watchdog = 0
		while len(self.__write_buffer) and watchdog < 100:
			self.xfer()
			watchdog += 1
		self.close()


	def xfer(self):
		"""Do read/write operations.
		Call this function regularly to send/receive encoded/decoded Message class objects. """

		if self.closed:
			logging.debug("Messenger %d xfer when closed!" % self._instance_id)
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
			except ConnectionResetError:
				self.closed = True
			except IOError as e:
				logging.error(e)
				self.close()
			else:
				if len(data):
					logging.debug("Read %d bytes on Messenger %d" % (len(data), self._instance_id))
					self.__read_buffer += data

		# Write data if necessary:
		if writable_sockets and len(self.__write_buffer):
			try:
				bytes_sent = self.__sock.send(self.__write_buffer)
				logging.debug("Wrote %d bytes on Messenger %d" % (bytes_sent, self._instance_id))
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
			self.__read_buffer = self.__read_buffer[byte_len:]
			return message
		return None


	def send(self, message):
		"""Appends an encoded message to the write buffer."""
		self.__write_buffer += message.encoded()



