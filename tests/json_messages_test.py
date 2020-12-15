from cable_car.json_messages import *

class SimpleMessage(Message):
	pass


class ComplexMessage(Message):
	pass



def test_class_registration():
	Message.register_messages()
	assert Message.is_registered("MsgIdentify")
	assert Message.is_registered("MsgJoin")
	assert Message.is_registered("MsgQuit")
	assert Message.is_registered("MsgRetry")
	assert Message.is_registered("SimpleMessage")
	assert Message.is_registered("ComplexMessage")



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


