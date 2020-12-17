"""
Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility.
"""

import sys, logging, json
from socket import gethostname
from getpass import getuser


class Message:
	"""
	A class which encodes and decodes itself as a series of compact bytes.
	The format of each message is:
		Byte
		--------    ----------------------------------------------------------------------
		   0        Message length
		   1        Single-digit class code, identifying the Message class to instantiate
		2 .. len    (optional) Encoded data which is unique to the subclass
		--------    ----------------------------------------------------------------------

	## Creating subclasses:

	You must allow the __init__ function of any subclass you create to be called
	with no arguments, as the "peel_from_buffer" function will create an instance
	without arguments before calling "decode" to convert the encoded data back into
	class attributes.

	If you subclass Message, and the subclass has custom attributes, you need to
	implement both "encode" and "decode" functions in that class. The "encode"
	function must return a bytearray from the attributes of the subclass, (in
	whatever format seems appropriate to you), while the "decode" function must
	take the encoded bytearray and restore the class attributes back from the given
	bytes.

	For an example, see the "MsgIdentify" class defined in this module.

	"""

	registry = {} # dictionary of <code>: <class definition>


	@classmethod
	def register_messages(cls):
		"""
		Register all classes which subclass Message in the current scope.
		"""
		for subclass in Message.__subclasses__():
			Message.registry[subclass.code] = subclass


	@classmethod
	def is_registered(cls, code):
		"""
		Tests that a subclass is registered. (Used by unit tests.)
		"""
		return code in cls.registry


	@classmethod
	def register(cls):
		"""
		Registers a class, allowing it to be available in "peel_from_buffer".
		"""
		cls.registry[cls.code] = cls


	@classmethod
	def peel_from_buffer(cls, read_buffer):
		"""
		Selects a portion of a Messenger's read buffer as a message.
		The length of the message is indicated by the first byte read.

		Returns a tuple (Message, bytes_read).
		"""
		if(len(read_buffer) and len(read_buffer) >= read_buffer[0]):
			if read_buffer[1] in cls.registry:
				message = cls.registry[read_buffer[1]]()
				logging.debug('Decoding %d-byte message "%s"' % (read_buffer[0], message.__class__.__name__))
				if read_buffer[0] > 2:
					message.decode(read_buffer[2:read_buffer[0]])
				return message, read_buffer[0]
			else:
				raise Exception("%d is not a registered Message code" % read_buffer[1])
		return None, 0


	def __init__(self, **kwargs):
		"""
		Used both when constructing a Message class with custom attributes, and
		basically ignored when instantiating a Message class while decoding.

		Do not change the function signature. Any subclass of Message must accept no
		arguments, as the "Message.peel_from_buffer" function creates an instance with
		no arguments before setting class attributes from encoded data using the
		"decode" function.
		"""
		for varname, value in kwargs.items():
			setattr(self, varname, value)


	def encoded(self):
		"""
		Called from Messenger, prepends the byte length and class code to the return
		value of this class' "encode" function. Do not extend this function. Extend the
		"encode" function in your subclass instead.
		"""
		encoded_data = self.encode()
		message_len = len(encoded_data) + 2
		logging.debug('Encoded %d-byte message "%s"' % (message_len, self.__class__.__name__))
		payload = bytearray([message_len, self.code])
		return payload + encoded_data if encoded_data else payload


	def encode(self):
		"""
		Returns this Message class' attributes as a bytearray.
		If your message requires complex types which json cannot encode, implement this
		function as well as "decode".
		"""
		return bytearray()


	def decode(self, msg_data):
		"""
		Default function which does nothing. Extend in your subclass to populate class
		attributes.
		"""
		pass


	def __str__(self):
		return self.__class__.__name__



class MsgIdentify(Message):
	code = 0x1

	def __init__(self, username=None, hostname=None):
		self.username = username or getuser()
		self.hostname = hostname or gethostname()


	def encode(self):
		"""
		Encode as "username@hostname".
		"""
		return ("%s@%s" % (self.username, self.hostname)).encode('ASCII')


	def decode(self, msg_data):
		"""
		Decode username and hostname from message data.
		"""
		self.username, self.hostname = msg_data.decode().split("@")



class MsgJoin(Message):
	code = 0x2
	pass



class MsgRetry(Message):
	code = 0x3
	pass



class MsgQuit(Message):
	code = 0x4
	pass



