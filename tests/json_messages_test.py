import pytest
from cable_car.json_messages import *

def test_classes_registered():
	pass

def test_class_encode_decode():
	msg = Join()
	assert isinstance(msg, Join)
	encoded_message = msg.encoded()

	buff = encoded_message
	msg, pos = Message.peel_from_buffer(buff)
	assert isinstance(msg, Join)
	assert pos == len(encoded_message) - 1

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
	assert pos == len(encoded_message) - 1
	assert username == msg.username
	assert hostname == msg.hostname

def test_multiple_messages_in_buffer():
	# Test passing several messages in one buffer
	buff = Join().encoded()
	buff.extend(Identify().encoded())
	buff.extend(Retry().encoded())
	buff.extend(Quit().encoded())

	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, Join)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, Identify)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, Retry)
	msg, byte_len = Message.peel_from_buffer(buff)
	buff = buff[byte_len + 1:]
	assert isinstance(msg, Quit)

