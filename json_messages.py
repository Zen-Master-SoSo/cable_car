"""Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility."""

import sys, logging, json
from socket import gethostname
from getpass import getuser
from cable_car.network_messenger import Message


class JSON_Message(Message):

	terminator = b"\n"


	@classmethod
	def from_buffer(cls, read_buffer):
		""" Select a part of the NetworkMessenger's read buffer as a complete message bytearray,
		based upon the presence of a carriage return message terminator in the buffer.
		Returns a tuple (Message, bytes_read) """
		pos = read_buffer.find(cls.terminator)
		if pos > -1:
			return JSON_Message.decode(read_buffer[:pos]), pos
		return None, 0


	@classmethod
	def decode(cls, msg):
		"""Returns an Message from a JSON-encoded data."""
		try:
			logging.debug(msg.decode('utf-8'))
			payload = json.loads(msg.decode('utf-8'))
		except Exception as e:
			logging.error(e)
		else:
			if payload[0] in Message.class_defs:
				msg = Message.class_defs[payload[0]]({})
				for key, value in payload[1].items():
					setattr(msg, key, value)
				return msg
			else:
				raise KeyError("%s is not a registered message" % payload[0])

	def encode(self):
		"""JSON-encode this message for sending over a network and such."""
		return json.dumps([self.__class__.__name__, self.__dict__], separators=(',', ':')).encode() + self.terminator

	def __str__(self):
		return self.encode()



class Identify(JSON_Message):
	def __init__(self, username=None, hostname=None):
		self.username = username or getuser()
		self.hostname = hostname or gethostname()



class Join(JSON_Message):
	pass



class Retry(JSON_Message):
	pass



class Quit(JSON_Message):
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

	msg = Join()
	assert(isinstance(msg, Message))
	assert(isinstance(msg, Join))
	join_msg = msg.encode()

	msg = JSON_Message.decode(join_msg)
	assert(isinstance(msg, Join))
	assert(isinstance(msg, Message))

	msg = Identify()
	assert(isinstance(msg, Message))
	assert(isinstance(msg, Identify))
	assert(msg.username is not None)
	assert(msg.hostname is not None)
	username = msg.username
	hostname = msg.hostname
	identify_msg = msg.encode()

	msg = JSON_Message.decode(identify_msg)
	assert(isinstance(msg, Message))
	assert(isinstance(msg, Identify))
	assert(msg.username is not None)
	assert(msg.hostname is not None)
	assert(username == msg.username)
	assert(hostname == msg.hostname)

	print("OKAY")


