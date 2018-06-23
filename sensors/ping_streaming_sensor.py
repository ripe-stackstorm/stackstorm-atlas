from ripe.atlas.cousteau import (
  AtlasStream,
)

from st2reactor.sensor.base import Sensor

# Sample ping probe id
PING_PROBE_ID = 14625939


class PingStreamingSensor(Sensor):

    def __init__(self, sensor_service, config):
        super(PingStreamingSensor, self).__init__(sensor_service=sensor_service, config=config)
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)
        self._stop = False

    def setup(self):
		self.atlas_stream = AtlasStream()
		self.atlas_stream.connect()
		
		channel = "atlas_result"
		# Bind function we want to run with every result message received
		self.atlas_stream.bind_channel(channel, self.on_result_response)	

	def on_result_response(*args):
		"""
		Process the result from the Atlas Ping Probe
		"""

		self._logger.debug("Received a probe response")
		self._logger.debug(args[0])		

    def run(self):
    
    	# Subscribe to new stream for PING_PROBE_ID measurement results
		stream_parameters = {"msm": PING_PROBE_ID}
    
    	self._logger.debug("Starting Atlas stream for probe ID: {}".format(stream_parameters))
		while not self._stop:
			self.atlas_stream.start_stream(stream_type="result", **stream_parameters)	

    def cleanup(self):
    	self.atlas_stream.disconnect()

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass