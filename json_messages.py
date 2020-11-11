""" Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility. """

import sys, logging, json
from socket import gethostname
from getpass import getuser


class Message:
	""" A class which encodes and decodes itself as JSON.
	Note: the __init__ function of any subclass you create must be able to be called with no
	arguments, as the "Message.peel_from_buffer" function creates an instance with no args
	before converting the JSON into class attributes. """

	terminator = b"\n"
	class_defs = {}	# dictionary of <class name>: <class definition>

	@classmethod
	def register(cls):
		"""Registers class definitions for the "Message.peel_from_buffer" function."""
		cls.class_defs[cls.__name__] = cls


	@classmethod
	def peel_from_buffer(cls, read_buffer):
		""" Select the relevant part of a Messenger's read buffer as a complete message bytearray.
		In the Message class in this module, the determination of message completeness is the
		presence of a carriage return message terminator in the buffer.
		Returns a tuple (Message, bytes_read) """
		pos = read_buffer.find(cls.terminator)
		if pos > -1:
			try:
				msg_data = read_buffer[:pos].decode('utf-8')
				logging.debug("Decoding Message: " + msg_data)
				payload = json.loads(msg_data)
			except Exception as e:
				logging.error(e)
			else:
				if payload[0] in cls.class_defs:
					msg = cls.class_defs[payload[0]]()
					for key, value in payload[1].items():
						setattr(msg, key, value)
					return msg, pos
				else:
					raise KeyError("%s is not a registered Message class" % payload[0])
		return None, 0


	def encoded(self):
		"""JSON-encode this message for sending over a network and such."""
		return bytearray(json.dumps([self.__class__.__name__, self.__dict__], separators=(',', ':')).encode() + self.terminator)


	def __str__(self):
		return self.encoded()



class Identify(Message):
	def __init__(self, username=None, hostname=None):
		self.username = username or getuser()
		self.hostname = hostname or gethostname()



class Join(Message):
	pass



class Retry(Message):
	pass



class Quit(Message):
	pass



Identify.register()
Join.register()
Retry.register()
Quit.register()


if __name__ == '__main__':

	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)

	# Test basic encoding/decoding:

	msg = Join()
	assert(isinstance(msg, Join))
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert(isinstance(msg, Join))
	assert(pos == len(encoded_message) - 1)

	msg = Identify()
	assert(isinstance(msg, Identify))
	assert(msg.username is not None)
	assert(msg.hostname is not None)
	username = msg.username
	hostname = msg.hostname
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert(isinstance(msg, Identify))
	assert(pos == len(encoded_message) - 1)
	assert(username == msg.username)
	assert(hostname == msg.hostname)

	# Test passing several messages in one buffer
	buff = Join().encoded()
	buff.extend(Identify().encoded())
	buff.extend(Retry().encoded())
	buff.extend(Quit().encoded())

	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert(isinstance(msg, Join))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert(isinstance(msg, Identify))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert(isinstance(msg, Retry))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert(isinstance(msg, Quit))


	print("OKAY")


