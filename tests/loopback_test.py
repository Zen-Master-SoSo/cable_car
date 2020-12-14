import pytest, threading, time
from socket import socket
from cable_car.loopback import LoopbackClient, LoopbackServer
from cable_car.json_messages import *
from cable_car.messenger import Messenger


def test_loopback():
	global test_enable, client_id, server_id

	test_enable = True
	client_id = None
	server_id = None


	def on_connect(sock):
		logging.debug("Conected %s:%s" % (sock.getsockname()))


	def _test_client():
		global test_enable, client_id
		client = LoopbackClient()
		client.timeout = 10.0
		client.on_connect_function = on_connect
		client.connect()
		assert isinstance(client.socket, socket)
		if isinstance(client.socket, socket):
			msgr = Messenger(client.socket)
			msgr.send(MsgIdentify())
			while test_enable:
				msgr.xfer()
				msg = msgr.get()
				if msg is None:
					continue
				assert isinstance(msg, MsgIdentify)
				client_id = msg
				break


	def _test_server():
		global test_enable, server_id
		server = LoopbackServer()
		server.timeout = 10.0
		server.on_connect_function = on_connect
		server.connect()
		assert isinstance(server.socket, socket)
		if isinstance(server.socket, socket):
			msgr = Messenger(server.socket)
			msgr.send(MsgIdentify())
			while test_enable:
				msgr.xfer()
				msg = msgr.get()
				if msg is None:
					continue
				assert isinstance(msg, MsgIdentify)
				server_id = msg
				break


	def _test_timeout():
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


	# Create threads:
	client_thread = threading.Thread(target=_test_client)
	server_thread = threading.Thread(target=_test_server)
	timeout_thread = threading.Thread(target=_test_timeout)

	# Start threads:
	client_thread.start()
	server_thread.start()
	timeout_thread.start()

	# Wait for threads to exit:
	client_thread.join()
	server_thread.join()
	test_enable = False
	timeout_thread.join()
	assert client_id is not None
	assert server_id is not None


if __name__ == "__main__":
	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)
	test_loopback()
