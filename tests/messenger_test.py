import pytest, logging, threading, time, sys, importlib
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from cable_car.messenger import Messenger


def client():
	global test_enable
	sock = socket(AF_INET, SOCK_STREAM)
	sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	sock.settimeout(3)
	time.sleep(0.25)
	logging.debug("Client connecting")
	try:
		sock.connect(('127.0.0.1', 8222))
	except Exception as e:
		sock.close()
		logging.error(e)
		test_enable = False
	logging.debug("Client connected")
	assert do_comms(sock)
	logging.debug("client exiting")


def server():
	global test_enable
	logging.debug("Server listening")
	sock = socket(AF_INET, SOCK_STREAM)
	sock.setblocking(0)
	sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	sock.bind(('127.0.0.1', 8222))
	sock.listen()
	while test_enable:
		try:
			sock, address_pair = sock.accept()
		except BlockingIOError as be:
			pass
		except Exception as e:
			logging.error(e)
			test_enable = False
		else:
			break
	logging.debug("Server connected")
	assert do_comms(sock)
	logging.debug("server exiting")


def do_comms(sock):
	messages = importlib.import_module("cable_car.%s_messages" % transport)
	Message = getattr(messages, "Message")
	MsgIdentify = getattr(messages, "MsgIdentify")
	msgr = Messenger(sock, transport)
	msgr.id_sent = False
	msgr.id_received = False
	while test_enable:
		msgr.xfer()
		msg = msgr.get()
		if msg is not None:
			if(isinstance(msg, MsgIdentify)):
				msgr.id_received = True
		if msgr.id_sent:
			if msgr.id_received:
				return True
		else:
			msgr.send(MsgIdentify())
			msgr.id_sent = True


def watchdog():
	global test_enable, timed_out
	quitting_time = time.time() + 10.0
	while test_enable:
		if time.time() >= quitting_time:
			timed_out = True
			break
		time.sleep(0.05)
	test_enable = False
	logging.debug("watchdog exiting")



def test_messenger_json():
	global transport
	transport = "json"
	doit()


def test_messenger_byte():
	global transport
	transport = "byte"
	doit()


def doit():
	global test_enable

	# Create threads:
	client_thread = threading.Thread(target=client)
	server_thread = threading.Thread(target=server)
	timeout_thread = threading.Thread(target=watchdog)

	# Start threads:
	test_enable = True
	client_thread.start()
	server_thread.start()
	timeout_thread.start()

	# Wait for threads to exit:
	client_thread.join()
	server_thread.join()
	test_enable = False
	timeout_thread.join()



if __name__ == "__main__":
	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)
	test_messenger_json()
	test_messenger_byte()
