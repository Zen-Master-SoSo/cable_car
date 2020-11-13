import pytest
from cable_car.broadcast_connector import BroadcastConnector

def test():

	my_ip = BroadcastConnector.get_my_ip()
	assert isinstance(my_ip, str)

	bc = BroadcastConnector()
	bc.verbose = True
	bc.allow_loopback = True
	bc.timeout = 2.0
	bc.connect()
	assert my_ip in bc.addresses()


