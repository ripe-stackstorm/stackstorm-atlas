import numpy as np

from ripe.atlas.cousteau import (
  AtlasStream,
)

from st2reactor.sensor.base import Sensor

# Sample ping probe id
PING_PROBE_ID = 5001

PERCENTILE = 75
TARGET_RTT_PERCENTILE = 50 

MIN_SAMPLE_COUNT = 10



class PingStreamingSensor(Sensor):

    def __init__(self, sensor_service, config):
        super(PingStreamingSensor, self).__init__(sensor_service=sensor_service, config=config)
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)

    def setup(self):
        self.atlas_stream = AtlasStream()

    def on_result_response(self, *args):
        """
        Process the result from the Atlas Ping Probe
        """
        self._logger.info("Received a probe response for measurement {}".format(PING_PROBE_ID))
        
        round_trip_times = self._get_round_trip_times(args)
        if len(round_trip_times) < MIN_SAMPLE_COUNT:
            self._logger.info("Not enough samples in this result, sample count = {}".format(len(round_trip_times)))
            return

        percentile = self._rtt_percentile(round_trip_times)
        if percentile > TARGET_RTT_PERCENTILE:
            self._dispatch_exceed_rtt_trigger(percentile)
        
    def _get_round_trip_times(self, args):
        round_trip_times = []
        for result in args[0]['result']:
            if 'result' in result.keys():
                for probe_result in result['result']:
                    try:
                        round_trip_times.append(probe_result['rtt'])
                    except KeyError:
                         self._logger.info("No rtt data in this result")
        return round_trip_times
        
    def _rtt_percentile(self, round_trip_times):
        self._logger.info("RTT samples: {}".format(round_trip_times))
        rtt_array = np.array(round_trip_times)
        percentile = np.percentile(rtt_array, PERCENTILE)
        self._logger.info("RTT p{}: {}".format(PERCENTILE, percentile))
        
        return percentile
        
    def _dispatch_exceed_rtt_trigger(self, percentile):
        self._logger.info("Target rtt p{} of {}s exceeded, rtt p{} = {}s".format(
            PERCENTILE, TARGET_RTT_PERCENTILE, PERCENTILE, percentile))
        trigger = "atlas.rtt_p{}_exceeded".format(PERCENTILE)
        payload = {
            'percentile': PERCENTILE,
            'rtt': float(percentile),
        }
        self._sensor_service.dispatch(trigger=trigger, payload=payload)

    def run(self):
        stream_parameters = {"msm": 5001}
        self.atlas_stream.connect()
        channel = "atlas_result"
        # Bind function we want to run with every result message received
        self.atlas_stream.bind_channel(channel, self.on_result_response)
        self.atlas_stream.start_stream(
                stream_type="result", **stream_parameters)
        self.atlas_stream.timeout()

    def cleanup(self):
        self._logger.info("Good bye cruel world...")
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
