"""
Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility.
"""

import sys, logging, json
from socket import gethostname
from getpass import getuser


class Message:
	"""
	A class which encodes JSON messages for network transport and other uses.
	.

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

	"""

	terminator = b"\n"
	registry = {}	# dictionary of <class name>: <class definition>

	@classmethod
	def register_messages(cls):
		"""
		Register all classes which subclass Message in the current scope.
		"""
		for subclass in Message.__subclasses__():
			Message.registry[subclass.__name__] = subclass


	@classmethod
	def is_registered(cls, subclass):
		"""
		Tests that a subclass is registered. (Used by unit tests.)
		"""
		return subclass in cls.registry


	@classmethod
	def register(cls):
		"""
		Registers a class, allowing it to be available in "peel_from_buffer".
		"""
		cls.registry[cls.__name__] = cls


	@classmethod
	def peel_from_buffer(cls, read_buffer):
		"""
		Selects a portion of a Messenger's read buffer as a message.
		The length of the message is determined by the position of the first carriage
		return in the buffer.

		Returns a tuple (Message, bytes_read).
		"""
		pos = read_buffer.find(cls.terminator)
		if pos > -1:
			try:
				message_data = read_buffer[:pos].decode('utf-8')
				logging.debug("Decoding message: " + message_data)
				payload = json.loads(message_data)
			except Exception as e:
				logging.error(e)
			else:
				if payload[0] in cls.registry:
					message = cls.registry[payload[0]]()
					message.decode_attributes(payload[1])
					return message, pos
				else:
					raise KeyError("%s is not a registered Message class" % payload[0])
		return None, 0


	def __init__(self, **kwargs):
		"""
		Used both when constructing a Message class with custom attributes, and
		basically ignored when instantiating a Message class while decoding.

		Do not change the function signature. Any subclass of Message must accept no
		arguments, as the "Message.peel_from_buffer" function creates an instance with
		no arguments before setting class attributes from encoded data using the
		"decode_attributes" function.
		"""
		for varname, value in kwargs.items():
			setattr(self, varname, value)


	def encoded(self):
		"""
		Returns a json-encoded representation of this Message.
		DO NOT OVERRIDE THIS FUNCTION. Use "encoded_attributes" to customize how your Message is encoded.
		"""
		message = json.dumps([self.__class__.__name__, self.encoded_attributes()], separators=(',', ':'))
		logging.debug("Encoded message: " + message)
		return bytearray(message.encode() + self.terminator)


	def encoded_attributes(self):
		"""
		Used when encoding a Message class with custom attributes to a json-encoded
		message. The purpose of this function is to take more complex attributes and
		convert them into built-in types which won't confuse the json encoder.

		Returns a dict containing this Message's attributes simplified for encoding.

		If your message requires complex types which json cannot encode, implement this
		function as well as "decode_attributes".
		"""
		return self.__dict__


	def decode_attributes(self, attributes):
		"""
		Used when going from a json-encoded message back to a Message class with custom
		attributes. This is a default implementation which can work if all attributes
		are built-in types. If your message uses complex types which json cannot
		encode, then implement custom functions, both "encoded_attributes" and
		"decode_attributes".
		"""
		for key, value in attributes.items():
			setattr(self, key, value)


	def __str__(self):
		return json.dumps([self.__class__.__name__, self.encoded_attributes()], separators=(',', ':'))



class MsgIdentify(Message):

	def __init__(self, **kwargs):
		Message.__init__(self, **kwargs)
		if not hasattr(self, "username"): self.username = getuser()
		if not hasattr(self, "hostname"): self.hostname = gethostname()



class MsgJoin(Message):
	pass



class MsgRetry(Message):
	pass



class MsgQuit(Message):
	pass



if __name__ == '__main__':
	import logging
	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG,
		format="[%(filename)24s:%(lineno)3d] %(message)s"
	)
	Message.register_messages()
	assert Message.is_registered("MsgIdentify")
	assert Message.is_registered("MsgJoin")
	assert Message.is_registered("MsgRetry")
	assert Message.is_registered("MsgQuit")

