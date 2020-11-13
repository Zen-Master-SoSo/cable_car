import pytest
from cable_car.byte_messages import *

class DummyMessage(Message):
	pass

def test_class_registration():
	Message.register_messages()
	assert Message.is_registered("Identify")
	assert Message.is_registered("Join")
	assert Message.is_registered("Quit")
	assert Message.is_registered("DummyMessage")

def test_class_encode_decode():
	msg = Join()
	assert isinstance(msg, Join)
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, Join)
	assert pos == len(encoded_message)

def test_class_encode_decode_with_data():
	msg = Identify()
	assert isinstance(msg, Identify)
	assert msg.username is not None
	assert msg.hostname is not None
	username = msg.username
	hostname = msg.hostname
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, Identify)
	assert pos == len(encoded_message)
	assert username == msg.username
	assert hostname == msg.hostname

def test_multiple_messages_in_buffer():

	# Test passing several messages in one buffer
	buff = Join().encoded()
	buff.extend(Identify().encoded())
	buff.extend(Retry().encoded())
	buff.extend(Quit().encoded())

	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len:]
	assert(isinstance(msg, Join))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len:]
	assert(isinstance(msg, Identify))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len:]
	assert(isinstance(msg, Retry))
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len:]
	assert(isinstance(msg, Quit))


