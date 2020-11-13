""" Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility. """

import sys, logging, json
from socket import gethostname
from getpass import getuser


class Message:
	"""A class which encodes and decodes itself as a series of compact bytes.
	The format of each message is:
		Byte
		--------    ----------------------------------------------------------------------
		   0        Message length
		   1        Single-digit class code, identifying the Message class to instantiate
		2 .. len    (optional) Encoded data which is unique to the subclass
		--------    ----------------------------------------------------------------------
	Some requirements when creating subclasses:

	The __init__ function of any subclass you create must be able to be called with no
	arguments, as the "Message.peel_from_buffer" function creates an instance with no args
	before converting the JSON into class attributes.

	Each subclass must define an "encode" function which returns a bytearray.

	Each subclass must define a "decode_data" function which uses the data passed to it
	from the "peel_from_buffer" method to populate attributes of the subclass.
	For an example, see the "Identify" class defined in this module.
	"""

	class_defs = {} # dictionary of <code>: <class definition>


	@classmethod
	def register_messages(cls):
		"""
		Registers all class definitions classes which subclass Message in the current scope.
		"""
		for subclass in Message.__subclasses__():
			Message.class_defs[subclass.__name__] = subclass


	@classmethod
	def is_registered(cls, subclass):
		"""
		Registers all class definitions classes which subclass Message in the current scope.
		"""
		return subclass in cls.class_defs


	@classmethod
	def register(cls):
		"""Registers a subclass of Message so that instances may be constructed by the Message class."""
		cls.class_defs[cls.code] = cls


	@classmethod
	def peel_from_buffer(cls, read_buffer):
		""" Select the relevant part of a Messenger's read buffer as a complete message bytearray.
		In the Message class defined in this moduel, message completeness is  determined by the
		number of bytes to read from the buffer, determined by the first byte of the message."
		Returns a tuple (Message, bytes_read) """
		if(len(read_buffer) and len(read_buffer) >= read_buffer[0]):
			logging.debug("Received %d-byte message" % read_buffer[0])
			if read_buffer[1] in cls.class_defs:
				msg = cls.class_defs[read_buffer[1]]()
				if read_buffer[0] > 2:
					msg.decode_data(read_buffer[2:])
				return msg, read_buffer[0]
			else:
				raise KeyError("%d is not a registered Message code" % read_buffer[1])
		return None, 0


	def encoded(self):
		"""Called from Messenger, prepends the byte length and class code to the return value of
		this class' "encode" function. Do not extend this function. Extend the "encode" function in
		your subclass instead."""
		encoded_data = self.encode()
		data_len = len(encoded_data)
		logging.debug("Encoded %d-bytes of message data" % data_len)
		payload = bytearray([data_len + 2, self.code])
		return payload + encoded_data if data_len else payload


	def encode(self):
		"""Default function which returns an empty bytearray. This is the function to extend in your subclass."""
		return bytearray()


	def decode_data(self, msg_data):
		"""Default function which does nothing. Extend in your subclass to populate class attributes."""
		pass


	def __str__(self):
		return self.__class__.__name__



class Identify(Message):
	code = 0x1
	def __init__(self, username=None, hostname=None):
		self.username = username or getuser()
		self.hostname = hostname or gethostname()


	def decode_data(self, msg_data):
		"""Read username and hostname from message data."""
		self.username, self.hostname = msg_data.decode().split("@")


	def encode(self):
		"""Encode username@hostname."""
		return ("%s@%s" % (self.username, self.hostname)).encode('ASCII')


class Join(Message):
	code = 0x2
	pass



class Retry(Message):
	code = 0x3
	pass



class Quit(Message):
	code = 0x4
	pass



Identify.register()
Join.register()
Retry.register()
Quit.register()

