#!/usr/bin/python
import sys, argparse, logging, time, psutil
from socket import gethostname
from cable_car.broadcast_connector import BroadcastConnector
from cable_car.messenger import Messenger
from cable_car.json_messages import Message

BYTE_SIZES	= [
	(1 << 50, 'Pb'),
	(1 << 40, 'Tb'),
	(1 << 30, 'Gb'),
	(1 << 20, 'Mb'),
	(1 << 10, 'kb'),
	(1, '')
]

def byte_size(n):
	""" Returns a human-readable byte size (e.g. "50kb") """
	for factor, suffix in BYTE_SIZES:
		if n > factor: break
	return str(int(n / factor)) + suffix


class MachineMonitor(BroadcastConnector):

	udp_port				= 8226
	tcp_port				= 8227
	broadcast_interval		= 3.0
	timeout					= 0.0
	messengers				= []


	def __init__(self):
		self.on_connect_function = self.connected


	def connected(self, sock):
		msgr = Messenger(sock, "json")
		msgr.send(MsgStats())
		msgr.next_update = time.time() + self.broadcast_interval
		self.messengers.append(msgr)


	def run(self):
		self._start_connector_threads()
		try:
			while self._connect_enable:
				for msgr in self.messengers:
					if time.time() >= msgr.next_update:
						msgr.send(MsgStats())
					msgr.xfer()
					stat = msgr.get()
					if stat is not None:
						stat.dump()
					time.sleep(0.25)
		except KeyboardInterrupt:
			self._connect_enable = False


class MsgStats(Message):

	def __init__(self, none=None):
		self.host = gethostname()
		self.cpu_percent = psutil.cpu_percent()
		self.load_avg = psutil.getloadavg()
		self.memory_percent = psutil.virtual_memory().percent
		self.memory_total = psutil.virtual_memory().total
		self.swap_percent = psutil.swap_memory().percent
		self.swap_total = psutil.swap_memory().total
		temps = psutil.sensors_temperatures()
		if temps and "coretemp" in temps:
			self.temp = temps["coretemp"][0].current

	def dump(self):
		print("-" * 46)
		print("           Host: %s" % self.host)
		print("    CPU percent: %s" % self.cpu_percent)
		print("   Load average: %s" % self.load_avg)
		print(" Memory percent: %s" % self.memory_percent)
		print("   Memory total: %s" % byte_size(self.memory_total))
		print("   Swap percent: %s" % self.swap_percent)
		print("     Swap total: %s" % byte_size(self.swap_total))
		if "temp" in self.__dict__:
			print("    Temperature: %s" % self.temp)


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('--loopback', '-l', action='store_true')
	p.add_argument('--verbose', '-v', action='store_true')
	options = p.parse_args()
	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG if options.verbose else logging.ERROR,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)
	mon = MachineMonitor()
	mon.allow_loopback = options.loopback
	sys.exit(mon.run())
