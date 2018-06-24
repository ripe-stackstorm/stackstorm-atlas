import time

from datetime import datetime

from ripe.atlas.cousteau import AtlasLatestRequest, Measurement
from st2reactor.sensor.base import PollingSensor


HARDCODED_MEASUREMENT_ID = 14682099

HOPS_NUMBER_CHANGED = "atlas.HopsNumberChanged"
RTT_NUMBER_CHANGED = "atlas.RTTMedianChanged"
FROM_FIELD_DIFFERENT_IN_ATTEMPTS = "atlas.FromFieldDifferentInAttempts"
FROM_FIELD_DIFFERENT_THAN_GENERAL = "atlas.FromFieldDifferentThanGeneral"
HOST_PARTIALLY_UNREACHABLE = "atlas.HostPartiallyUnreachable"
HOST_PARTIALLY_REACHABLE = "atlas.HostPartiallyReachable"

class RIPEAtlasPolling(PollingSensor):

    # List of statuses when the measurement is considered invalid
    # and the measurement needs to be re-created
    _stopped_statuses = ["Stopped"]
    # how long to consider a stale result valid (seconds)
    _measurement_delay_tolerance = 10

    # tolerance, in ms, of rtt
    _rtt_tolerance = -10 # TODO: roll back to 10 instead of -10

    def __init__(self, sensor_service, config):
        super(RIPEAtlasPolling, self).__init__(sensor_service=sensor_service,
                                               config=config)
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)
        self._previous_measurement = {}
        self._measurement = None

    def setup(self):
        # TODO: implement the actual measurement creation
        self._measurement = Measurement(id=self._config.get("measurement_id", HARDCODED_MEASUREMENT_ID))
        self._logger.info("Using measurement with ID %s", self._measurement.id)

    def poll(self):
        is_success, results = AtlasLatestRequest(msm_id=self._measurement.id,
                                                 probe_ids=self._config.get('probes')
                                                 ).create()
        if is_success:
            self._logger.info("Measurement reading successful, interpreting results")
            self._handle_results(results)
        else:
            self._handle_atlas_error()

    def _handle_results(self, results):
        if len(results) != len(self._previous_measurement):
            self._logger.warn("Different number of probes found compared to previous measurements: %s now vs %s historical",
                              len(results), len(self._previous_measurement))
        for probe_result in results:
            new_probe_result = probe_result
            if probe_result["prb_id"] in self._previous_measurement:
                self._compare_probe_stats(self._previous_measurement[probe_result["prb_id"]],
                                          new_probe_result)
            else:
                self._logger.info("This is the first time probe %s is seen, adding", probe_result["prb_id"])

            self._validate_from_fields(new_probe_result)

            self._previous_measurement[probe_result["prb_id"]] = new_probe_result

    def _compare_probe_stats(self, old_probe_result, new_probe_result, ingore_stale_results=True):
        # discard results if measurement was not made
        # measurement is not made if the stored timestamp is the same and the expected next
        # measurement is due in the future: stored timestamp + measurement interval + tolerance
        # is the speculated next update time
        measurements_stale_deadline = (new_probe_result["stored_timestamp"] +
                                       self._measurement.interval +
                                       self._measurement_delay_tolerance)
        now = int(time.time())
        # TODO: define alert for probable stale for more than stale deadline
        if all([new_probe_result["stored_timestamp"] == old_probe_result["stored_timestamp"],
                measurements_stale_deadline > now,
                ingore_stale_results]):
            self._logger.info("Measurements for probe %s not fresh enough. Expecting new measurements at latest at %s "
                              "Now: %s",
                              old_probe_result["prb_id"], measurements_stale_deadline, now)
            return

        payload_base = {
            "prb_id": old_probe_result["prb_id"],
            "timestamp": str(datetime.now())
        }
        if len(old_probe_result["result"]) != len(new_probe_result["result"]):
             self._send_trigger(trigger=HOPS_NUMBER_CHANGED,
                                payload=dict({"old_hops_number": len(old_probe_result["result"]),
                                              "new_hops_number": len(new_probe_result["result"])},
                                              **payload_base))
        # TODO: add detailed state, for host becoming reacheable / unreachable
        # inside the same result, per iteration of proble try
        if (self._probe_results_host_unreachable(old_probe_result["result"]) or
            self._probe_results_host_unreachable(new_probe_result["result"])):
            self._logger.warn("Host was unreacheable in current or previous attempt of probe %s",
                              old_probe_result["prb_id"])

            if (self._probe_results_host_unreachable(new_probe_result["result"]) and not
                self._probe_results_host_unreachable(old_probe_result["result"])):
                self._send_trigger(trigger=HOST_PARTIALLY_REACHABLE,
                                   payload=dict(**payload_base))

            if (self._probe_results_host_unreachable(old_probe_result["result"]) and not
                self._probe_results_host_unreachable(new_probe_result["result"])):
                self._send_trigger(trigger=HOST_PARTIALLY_UNREACHABLE,
                                   payload=dict(**payload_base))
            return

        self._logger.info("Looks like the results do not have unreachables %s\n%s",
                          old_probe_result["result"],
                          new_probe_result["result"])
        hops_comparison_result = self._compare_hops_median(old_probe_result, new_probe_result)
        if hops_comparison_result is not True:
            self._send_trigger(trigger=RTT_NUMBER_CHANGED,
                               payload=dict({"old_hops_median": hops_comparison_result[0],
                                             "new_hself.ops_median": hops_comparison_result[1]},
                                             **payload_base))

    def _validate_from_fields(self, new_probe_result):
        if self._probe_results_host_unreachable(new_probe_result["result"]):
            self._logger.info("Probe results contain cases when the target was not reached. Not validating `from` fields")
            return

        self._logger.info("Validating the consistency of the `from` fields from the probe result")
        froms = set([result_iteration['from']
                     for probe_result in new_probe_result['result']
                     for result_iteration in probe_result['result']])
        self._logger.info("Found unique `from` values: %s", froms)
        if len(froms) != 1:
            self._logger.info("Expected unique `from` field, found %s", froms)
            self._send_trigger(trigger=FROM_FIELD_DIFFERENT_IN_ATTEMPTS,
                               payload=dict({"hops_froms": repr(froms)},
                                             **payload_base))

        if len(froms.difference({new_probe_result["dst_addr"]})) != 0:
            self._logger.info("At least one of the from fields %s is not the same as the expected one %s",
                              froms, new_probe_result["dst_addr"])
            self._send_trigger(trigger=FROM_FIELD_DIFFERENT_THAN_GENERAL,
                               payload=dict({"expected_from_field": new_probe_result["dst_addr"],
                                             "found_from_fields": froms},
                                             **payload_base))

    def _probe_results_host_unreachable(self, probe_results):
        """ Checking if the marker for an unreachable host is present
            in the probe results. The expected item is {"x": "*"}.
            A host is considered unreachable if the marker is found.
        """
        self._logger.info("Checking if the probe results contain results that indicate that the host was not reached")
        unreacheable_marker = {"x": "*"}
        return any([unreacheable_marker in probe_result['result']
                    for probe_result in probe_results])

    def _compare_hops_median(self, old_probe_result, new_probe_result):
        self._logger.info("_compare_hops_median")
        self._logger.info("old_probe_result = %s", old_probe_result)
        self._logger.info("new_probe_result = %s", new_probe_result)
        old_rtt_median = old_probe_result.get("__rtt_median",
                            median([result_iteration['rtt']
                                    for probe_result in old_probe_result['result']
                                    for result_iteration in probe_result['result']]))
        new_rtt_median = median([result_iteration['rtt']
                                 for probe_result in new_probe_result['result']
                                 for result_iteration in probe_result['result']])
        # cache the rtt median for the new result
        new_probe_result["__rtt_median"] = new_rtt_median
        self._logger.info("Calculated RTT median: old %s new %s", old_rtt_median, new_rtt_median)
        if not (old_rtt_median - self._rtt_tolerance <=
                new_rtt_median <=
                old_rtt_median + self._rtt_tolerance):

            return old_rtt_median, new_rtt_median
        return True

    def _send_trigger(self, trigger, payload):
        self._logger.info("_send_trigger triggered with %s %s", trigger, payload)
        self._sensor_service.dispatch(trigger=trigger, payload=payload)

    def _handle_atlas_error():
        pass

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass

#TODO: move helper functions below to different module
def median(array):
    """Calculate median of the given list. Backport from Python 3
       statistics.median for python 3
    """
    array = sorted(array)
    half, odd = divmod(len(array), 2)
    if odd:
        return array[half]
    return (array[half - 1] + array[half]) / 2.0
