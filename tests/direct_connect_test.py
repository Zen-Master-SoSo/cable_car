import pytest, logging, threading, time, sys
from socket import socket
from cable_car.direct_connect import DirectClient, DirectServer
from cable_car.messenger import Messenger


def client():
	global test_enable, trans
	loopback_client = DirectClient()
	loopback_client.timeout = 10.0
	loopback_client.connect()
	logging.debug("loopback_client.connect() returned")
	assert isinstance(loopback_client.socket, socket)
	loopback_client.socket.setblocking(False)
	data = ""
	try:
		data = loopback_client.socket.recv(1024)
		assert data != ""
	except BlockingIOError as e:
		pass
	logging.debug("Client OKAY.")


def server():
	global test_enable
	loopback_server = DirectServer()
	loopback_server.timeout = 10.0
	loopback_server.connect()
	logging.debug("loopback_server.connect() returned")
	assert isinstance(loopback_server.socket, socket)
	loopback_server.socket.setblocking(False)
	data = ""
	try:
		data = loopback_server.socket.recv(1024)
		assert data != ""
	except BlockingIOError as e:
		pass
	logging.debug("Server OKAY.")


def watchdog():
	global test_enable
	quitting_time = time.time() + 5.0
	timed_out = False
	while test_enable:
		if time.time() >= quitting_time:
			timed_out = True
			break
		time.sleep(0.05)
	test_enable = False
	assert not timed_out


def test_direct_json():
	global transport
	transport = "json"
	doit()


def test_direct_byte():
	global transport
	transport = "byte"
	doit()


def doit():
	global test_enable
	test_enable = True

	# Create threads:
	client_thread = threading.Thread(target=client)
	server_thread = threading.Thread(target=server)
	timeout_thread = threading.Thread(target=watchdog)

	# Start threads:
	server_thread.start()
	time.sleep(0.25)
	client_thread.start()
	timeout_thread.start()

	# Wait for threads to exit:
	client_thread.join()
	server_thread.join()
	test_enable = False
	timeout_thread.join()


if __name__ == "__main__":
	logging.basicConfig(
		level = logging.DEBUG,
		format = "%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)
	test_direct_json()
	test_direct_byte()
