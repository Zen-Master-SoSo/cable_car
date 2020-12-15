from cable_car.byte_messages import *


class SimpleMessage(Message):
	code = 0x10

	def encode(self):
		"""
		Encode string, number
		"""
		return self.foo.encode("ASCII")


	def decode(self, msg_data):
		"""
		Read string and number from message data.
		"""
		self.foo = msg_data.decode()
		assert isinstance(self.foo, str)



class ComplexMessage(Message):
	code = 0x11

	def encode(self):
		"""
		Encode string, number
		"""
		return bytearray([self.number]) + self.string.encode("ASCII")


	def decode(self, msg_data):
		"""
		Read string and number from message data.
		"""
		self.number = msg_data[0]
		assert isinstance(self.number, int)
		self.string = msg_data[1:].decode()
		assert isinstance(self.string, str)



def test_register_messages():
	Message.register_messages()
	assert Message.is_registered(MsgIdentify.code)
	assert Message.is_registered(MsgJoin.code)
	assert Message.is_registered(MsgQuit.code)
	assert Message.is_registered(MsgRetry.code)
	assert Message.is_registered(SimpleMessage.code)
	assert Message.is_registered(ComplexMessage.code)


def test_encode_decode():
	msg = MsgJoin()
	assert isinstance(msg, MsgJoin)
	encoded_message = msg.encoded()
	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, MsgJoin)
	assert pos == len(encoded_message)


def test_encode_decode_with_data():

	Message.register_messages()

	msg = MsgIdentify()
	assert isinstance(msg, MsgIdentify)
	assert msg.username is not None
	assert msg.hostname is not None
	username = msg.username
	hostname = msg.hostname
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, MsgIdentify)
	assert pos == len(encoded_message)
	assert username == msg.username
	assert hostname == msg.hostname

	msg = SimpleMessage(foo="bar")
	assert msg.foo == "bar"
	encoded_message = msg.encoded()
	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, SimpleMessage)
	assert msg.foo == "bar"

	msg = ComplexMessage(string="foo", number=123)
	assert msg.string == "foo"
	assert msg.number == 123
	encoded_message = msg.encoded()
	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, ComplexMessage)
	assert msg.string == "foo"
	assert msg.number == 123


def test_multiple_messages_in_buffer():

	Message.register_messages()

	# Test passing several messages in one buffer
	buff = MsgJoin().encoded()
	buff.extend(MsgIdentify().encoded())
	buff.extend(SimpleMessage(foo="looks like a penguin to me").encoded())
	buff.extend(ComplexMessage(string="foo", number=123).encoded())
	buff.extend(MsgRetry().encoded())
	buff.extend(MsgJoin().encoded())
	buff.extend(MsgRetry().encoded())
	buff.extend(MsgJoin().encoded())
	buff.extend(MsgQuit().encoded())

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgJoin))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgIdentify))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, SimpleMessage))
	assert msg.foo == "looks like a penguin to me"
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, ComplexMessage))
	assert msg.string == "foo"
	assert msg.number == 123
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgRetry))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgJoin))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgRetry))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgJoin))
	buff = buff[byte_len:]

	msg, byte_len = Message.peel_from_buffer(buff)
	assert(isinstance(msg, MsgQuit))
	buff = buff[byte_len:]

	assert len(buff) == 0


if __name__ == "__main__":
	import logging
	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG,
		format="[%(filename)24s:%(lineno)3d] %(message)s"
	)
	test_multiple_messages_in_buffer()



