import time

from ripe.atlas.cousteau import (
  AtlasStream,
)

from st2reactor.sensor.base import Sensor

# Sample ping probe id
PING_PROBE_ID = 5001

TIME_STEP = 5
TIMEOUT = 300


class PingStreamingSensor(Sensor):

    def __init__(self, sensor_service, config):
        super(PingStreamingSensor, self).__init__(sensor_service=sensor_service, config=config)
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)
        self._timeout = TIMEOUT
        self._elapsed_time = 0

    def setup(self):
        self.atlas_stream = AtlasStream()	

    def on_result_response(*args):
        """
        Process the result from the Atlas Ping Probe
        """
        self._logger.info("Received a probe response after {}s".format(self._elapsed_time))
        self._logger.info(args[0])
        self._elapsed_time = 0

    def run(self):
        self.atlas_stream.connect()
        channel = "atlas_probestatus"
        # Bind function we want to run with every result message received
        self.atlas_stream.bind_channel(channel, self.on_result_response)    
    
        # Subscribe to new stream for PING_PROBE_ID measurement results
        # self._logger.info("Starting Atlas stream for probe ID: {}".format(PING_PROBE_ID))
        stream_parameters = {"enrichProbes": True}
        self.atlas_stream.start_stream(stream_type="probestatus", **stream_parameters)
        self.atlas_stream.timeout()
        
        while self._elapsed_time < self._timeout:
            self._logger.info("Sleeping for {}s".format(TIME_STEP))
            time.sleep(TIME_STEP)
            self._elapsed_time += TIME_STEP
            self._logger.info("No response after {}s".format(self._elapsed_time))
            self.atlas_stream.timeout()

    def cleanup(self):
        self._logger.info("Giving up after {}s, no response received!".format(self._elapsed_time))
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