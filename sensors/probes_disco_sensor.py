from collections import defaultdict

from ripe.atlas.cousteau import (
    AtlasStream,
)
from st2reactor.sensor.base import Sensor

ALL_PROBES_STATE_URL = "https://atlas.ripe.net/api/v2/probes/all"

STATUS_MAP = {
    1: "Connected",
    2: "Disconnected"
}

import requests


class ProbesDiscoSensor(Sensor):

    def __init__(self, sensor_service, config):
        super(ProbesDiscoSensor, self).__init__(
            sensor_service=sensor_service, config=config)
        self._logger = self.sensor_service.get_logger(
            name=self.__class__.__name__)
        self._probes_state = {}
        self._ases_v4_state = {}
        self._ases_v6_state = {}
        self.atlas_stream = AtlasStream()

    def setup(self):
        r = requests.get(ALL_PROBES_STATE_URL)
        if r.status_code == 200:
            self._create_state_dicts(r.json()["probes"])
            # self._logger.info(self._create_probes_dict(r.json()["probes"]))
            self._logger.info(self._ases_v4_state[3333])
            self._logger.info(self._ases_v6_state[3333])

    def _create_state_dicts(self, probes):
        """
        #         [
        #   *   0           probe.pk,
        #   *   1           probe.asn_v4 if probe.asn_v4 else 0,
        #   *   2           probe.asn_v6 if probe.asn_v6 else 0,
        #   *   3           probe.prb_country_code.code,
        #   *   4           1 if probe.is_anchor else 0,
        #   *   5           1 if probe.prb_public else 0,
        #   *   6          lat,
        #   *   7          lng,
        #   *   8           probe.prefix_v4 if probe.prefix_v4 else 0,
        #   *   9           probe.prefix_v6 if probe.prefix_v6 else 0,
        #   *   10          probe.address_v4 if probe.prb_public and probe.address_v4 else 0,
        #   *   11           probe.address_v6 if probe.prb_public and probe.address_v6 else 0,
        #   *   12          probe.status,
        #   *   13         int(probe.status_since.strftime("%s")) if probe.status_since is not None else None
        #   *  ]
        """
        for p in probes:
            status = STATUS_MAP[p[12]]
            self._probes_state[p[0]] = {"prb_id": p[0], "asn_v4": p[1],
                                        "asn_v6": p[2], "status": status}

            if p[1] and self._ases_v4_state.get(p[1]):
                self._ases_v4_state[p[1]].setdefault(status, set()).add(p[0])
            elif p[1] and p[1] != 0:
                self._ases_v4_state[p[1]] = {status: set([p[0]])}

            if p[2] and self._ases_v6_state.get(p[2]):
                self._ases_v6_state[p[2]].setdefault(status, set()).add(p[0])
            elif p[2] and p[2] != 0:
                self._ases_v6_state[p[1]] = {status: set([p[0]])}

        # return {p[0]: {"prb_id": p[0], "asn_v4": p[1], "asn_v6": p[2], "status": STATUS_MAP[p[12]]} for p in probes}

    def _update_probe_status(self, probe):
        """
        {u'prefix_v4': u'41.74.136.0/21',
        u'first_connected': 1428072503,
        u'is_anchor': False,
        u'status_name': u'Connected',
        u'prefix_v6': None,
        u'status_id': 1,
        u'address_v6': None,
        u'long': -23.6185,
        u'address_v4': None,
        u'country_code': u'CV',
        u'is_public': False,
        u'lat': 15.1075,
        u'asn_v4': 37517,
        u'asn_v6': None,
        u'status_since': 1528289054,
        u'id': 20981,
        u'tags': [u'system-v3', u'system-resolves-a-correctly', u'system-resolves-aaaa-correctly', u'system-ipv4-works', u'system-auto-geoip-country', u'system-ipv4-capable', u'system-ipv4-rfc1918', u'system-ipv4-stable-1d'], u'total_uptime': 80039845},
        u'controller': u'ctr-ams01',
        u'asn': 37517,
        u'prefix': u'165.90.96.0/20',
        u'prb_id': 20981,
        u'type': u'connection',
        u'event': u'disconnect'}
        """
        p_state = self._probes_state.get(probe["prb_id"])
        event = probe["event"]
        prb_id = probe["prb_id"]
        probe_p = probe["probe"]
        asn_v4 = probe["probe"]["asn_v4"]
        asn_v6 = probe["probe"]["asn_v6"]
        if event == "disconnect" and p_state["status"] == "Connected":
            p_state["status"] = "Disconnected"
            if asn_v4:
                self._ases_v4_state[asn_v4].setdefault(
                    "Connected", set()).remove(prb_id)
                self._ases_v4_state[asn_v4].setdefault(
                    "Disconnected", set()).add(prb_id)
            if asn_v6:
                self._ases_v6_state["asn_v6"].setdefault(
                    "Connected", set()).remove(prb_id)
                self._ases_v6_state["asn_v6"].setdefault(
                    "Disconnected", set()).add(prb_id)
        elif event == "connect" and p_state["status"] == "Disconnected":
            p_state["status"] = "Connected"
            if asn_v4:
                self._ases_v4_state["asn_v4"].setdefault(
                    "Disconnected", set()).remove(prb_id)
                self._ases_v4_state["asn_v4"].setdefault(
                    "Connected", set()).add(prb_id)
            if asn_v6:
                self._ases_v6_state["asn_v6"].setdefault(
                    "Disconnected", set()).remove(prb_id)
                self._ases_v6_state["asn_v6"].setdefault(
                    "Connected", set()).add(prb_id)

        self._logger.info(p_state)
        self._logger.info(probe["probe"])
        self._logger.info(self._ases_v4_state.get(probe_p.get("asn_v4")))
        self._logger.info(self._ases_v6_state.get(probe_p.get("asn_v6")))
        self._probes_state[probe["prb_id"]] = p_state

    def on_result_response(self, *args):
        """
        Process the result from the Atlas Ping Probe
        """
        probe_update = args[0]
        prb_id = probe_update['prb_id']
        event = probe_update['event']
        self._logger.info("Received a probe response")
        self._logger.info(probe_update)
        self._update_probe_status(probe_update)

        if event == "connect" or event == 'disconnect':
            trigger = 'atlas.probes_disco'
            payload = self._probes_state[prb_id]
            trace_tag = "{prb_id}-{event}-{timestamp}".format(
                prb_id=prb_id, event=event, timestamp=probe_update['timestamp'])

        self.sensor_service.dispatch(
            trigger=trigger, payload=payload, trace_tag=trace_tag)

    def run(self):
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
