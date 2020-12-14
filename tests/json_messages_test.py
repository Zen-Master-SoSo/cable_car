from cable_car.json_messages import *

class DummyMessage(Message):
	pass

def test_class_registration():
	Message.register_messages()
	assert Message.is_registered("MsgIdentify")
	assert Message.is_registered("MsgJoin")
	assert Message.is_registered("MsgQuit")
	assert Message.is_registered("DummyMessage")

def test_class_encode_decode():
	msg = MsgJoin()
	assert isinstance(msg, MsgJoin)
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, MsgJoin)
	assert pos == len(encoded_message) - 1

def test_class_encode_decode_with_data():
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
	assert pos == len(encoded_message) - 1
	assert username == msg.username
	assert hostname == msg.hostname

	msg = DummyMessage(a=100, b=200)
	assert isinstance(msg, DummyMessage)
	assert hasattr(msg, "a")
	assert hasattr(msg, "b")
	assert 100 == msg.a
	assert 200 == msg.b

	encoded_message = msg.encoded()
	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, DummyMessage)
	assert pos == len(encoded_message) - 1
	assert hasattr(msg, "a")
	assert hasattr(msg, "b")
	assert 100 == msg.a
	assert 200 == msg.b

def test_multiple_messages_in_buffer():
	# Test passing several messages in one buffer
	buff = MsgJoin().encoded()
	buff.extend(MsgIdentify().encoded())
	buff.extend(MsgRetry().encoded())
	buff.extend(MsgQuit().encoded())

	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, MsgJoin)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, MsgIdentify)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, MsgRetry)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, MsgQuit)

