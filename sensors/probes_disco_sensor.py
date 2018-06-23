from ripe.atlas.cousteau import (
    AtlasStream,
)
from st2reactor.sensor.base import Sensor

class ProbesDiscoSensor(Sensor):

    def __init__(self, sensor_service, config):
        super(ProbesDiscoSensor, self).__init__(
            sensor_service=sensor_service, config=config)
        self._logger = self.sensor_service.get_logger(
            name=self.__class__.__name__)
        self._stop = False
        self.atlas_stream = AtlasStream()

    def setup(self):
        pass
       
    def on_result_response(self, *args):
        """
        Process the result from the Atlas Ping Probe
        """
        self._logger.info("Received a probe response")
        self._logger.info(args[0])

    def run(self):
        self._logger.info("Started from here")
        stream_parameters = {"enrichProbes": True}
        self.atlas_stream.connect()
        channel = "atlas_probestatus"
        # Bind function we want to run with every result message received
        self.atlas_stream.bind_channel(channel, self.on_result_response)
        self.atlas_stream.start_stream(
                stream_type="probestatus", **stream_parameters)
        self.atlas_stream.timeout()

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
