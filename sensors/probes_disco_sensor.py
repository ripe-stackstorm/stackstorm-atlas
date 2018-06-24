from collections import defaultdict
from datetime import datetime, timedelta

from ripe.atlas.cousteau import (
    AtlasStream,
)
from st2reactor.sensor.base import Sensor

ALL_PROBES_STATE_URL = "https://atlas.ripe.net/api/v2/probes/all"

STATUS_MAP = {
    1: "Connected",
    2: "Disconnected",
    3: "Abandoned",
    4: "NeverSeen"
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

        for asn_v4 in self._ases_v4_state:
            # self._logger.info(asn_v4)
            # self._logger.info(self._ases_v4_state)
            self._update_vstate(self._ases_v4_state[asn_v4])

        for asn_v6 in self._ases_v6_state:
            self._update_vstate(self._ases_v6_state[asn_v6])

        # return {p[0]: {"prb_id": p[0], "asn_v4": p[1], "asn_v6": p[2], "status": STATUS_MAP[p[12]]} for p in probes}

    def _update_vstate(self, vstate, prb_id=None, event=None):
        def _update_disco_list(prb_id, event):
            if event == "connect":
                vstate.setdefault(
                    "Disconnected", set()).discard(prb_id)
                vstate.setdefault(
                    "Connected", set()).add(prb_id)
                try:
                    del vstate.get("LastDisconnected", {})[prb_id]
                except KeyError:
                    pass
                self._logger.info(vstate.get("LastDisconnected"))

                for p in vstate.get("LastDisconnected", {}):
                    if vstate["LastDisconnected"][p] < datetime.now() - timedelta(minutes=30):
                        try:
                            del vstate.get("LastDisconnected", {})[p]
                        except KeyError:
                            pass

            if event == "disconnect":
                vstate.setdefault(
                    "Connected", set()).discard(prb_id)
                vstate.setdefault(
                    "Disconnected", set()).add(prb_id)

                # add the prb_id to the disconnected sliding window
                vstate.setdefault("LastDisconnected", {}).update(
                    {prb_id: datetime.now()})
                self._logger.info(vstate["LastDisconnected"])

                # check for late disconnected and delete those from the sliding window
                for p in vstate["LastDisconnected"]:
                    if vstate["LastDisconnected"][p] < datetime.now() - timedelta(minutes=30):
                        try:
                            del vstate.get("LastDisconnected", {})[p]
                        except KeyError:
                            pass

        if prb_id:
            _update_disco_list(prb_id, event)

        perc = 100.0 * float(len(vstate.get("Connected", []))) / float(
            len(vstate.get("Connected", [])) +
            len(vstate.get("Disconnected", []))
        )

        vstate["connection_percentage"] = perc
        # self._logger.info('new perc: {}'.format(perc))

        return perc

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
        asn_v4 = probe["probe"]["asn_v4"]
        asn_v6 = probe["probe"]["asn_v6"]
        if event == "disconnect":  # and p_state["status"] == "Connected":
            p_state["status"] = "Disconnected"
            if asn_v4:
                self._update_vstate(self._ases_v4_state[asn_v4], prb_id, event)
            if asn_v6:
                self._update_vstate(self._ases_v6_state[asn_v6], prb_id, event)
        elif event == "connect":  # and p_state["status"] == "Disconnected":
            p_state["status"] = "Connected"
            if asn_v4:
                self._update_vstate(self._ases_v4_state[asn_v4], prb_id, event)
            if asn_v6:
                self._update_vstate(self._ases_v6_state[asn_v6], prb_id, event)
        else:
            self._logger.info("probe {p} in wrong state".format(p=prb_id))

        if (event == "disconnect" and p_state["status"] == "Disconnected") or (
            event == "connect" and p_state["status"] == "Connected"
        ):
            self._logger.info("NO STATE CHANGE for probe {}".format(prb_id))
        self._logger.info(p_state)
        self._logger.info(probe["probe"])

        self._probes_state[probe["prb_id"]] = p_state

    def on_result_response(self, *args):
        """
        Process the result from the Atlas Ping Probe
        """
        probe_update = args[0]
        prb_id = probe_update['prb_id']
        event = probe_update['event']
        asn_v4 = probe_update['probe']["asn_v4"]
        asn_v6 = probe_update['probe']["asn_v6"]
        curr_asn_v4_conn = self._ases_v4_state.get(
            asn_v4, {}).get('connection_percentage')
        curr_asn_v6_conn = self._ases_v6_state.get(
            asn_v6, {}).get('connection_percentage')
        self._logger.info("Received a probe update for probe {prb_id} (asn v4:{asn_v4}, v6: {asn_v6}), event: \"{event}\"".format(
            prb_id=prb_id, event=event, asn_v4=asn_v4, asn_v6=asn_v6))
        # self._logger.info(probe_update)
        self._update_probe_status(probe_update)
        new_asn_v4_conn = self._ases_v4_state.get(
            asn_v4, {}).get('connection_percentage')
        new_asn_v6_conn = self._ases_v6_state.get(
            asn_v6, {}).get('connection_percentage')

        # Evaluate single probe disco
        if event == "connect" or event == 'disconnect':
            trigger = 'atlas.probes_disco'
            payload = {event: "probe with id {prb_id} {event}ed.".format(
                prb_id=prb_id, event=event)}
            trace_tag = "{prb_id}-{event}-{timestamp}".format(
                prb_id=prb_id, event=event, timestamp=probe_update['timestamp'])

            self.sensor_service.dispatch(
                trigger=trigger, payload=payload, trace_tag=trace_tag)

        # Evaluate ASes disco
        if event == "disconnect":
            trigger = 'atlas.probes_disco'

            # AS presence goes below 50 percent
            if curr_asn_v4_conn >= 50.0:
                if new_asn_v4_conn < 50.0:
                    self._logger.info('AWAS! asn_v4 {asn_v4} less than 50 percent connected!'.format(
                        asn_v4=asn_v4))
                    self.sensor_service.dispatch(
                        trigger=trigger,
                        payload={event: 'AWAS! asn_v4 {asn_v4} less than 50 percent connected!'.format(
                            asn_v4=asn_v4)},
                        trace_tag="{asn_v4}-lessthan-{timestamp}".format(
                            asn_v4=asn_v4, timestamp=probe_update['timestamp'])
                    )
                elif new_asn_v4_conn - curr_asn_v4_conn <= 19.0:
                    self._logger.info(
                        'NO! asn_v4 {asn_v4} going down significantly'.format(asn_v4=asn_v4))
                    self.sensor_service.dispatch(
                        trigger=trigger, payload={event: 'NO! asn_v4 {asn_v4} going down significantly'.format(asn_v4=asn_v4)}, trace_tag="{asn_v4}-down-{timestamp}".format(
                            asn_v4=asn_v4, timestamp=probe_update['timestamp']
                        )
                    )
                if curr_asn_v6_conn >= 50.0 and new_asn_v6_conn < 50.0:
                    self._logger.info('AWAS! asn_v6 {asn_v6} less than 50 percent connected!'.format(
                        asn_v6=asn_v6))
                    self.sensor_service.dispatch(
                        trigger=trigger,
                        payload={event: 'AWAS! asn_v6 {asn_v6} less than 50 percent connected!'.format(
                            asn_v6=asn_v6)},
                        trace_tag="{asn_v6}-lessthan-{timestamp}".format(
                            asn_v4=asn_v4, timestamp=probe_update['timestamp']
                        )
                    )

                elif new_asn_v6_conn and curr_asn_v6_conn and new_asn_v6_conn - curr_asn_v6_conn <= 19.0:
                    self._logger.info(
                        'NO! asn_v6 {asn_v6} going down significantly'.format(asn_v6=asn_v6))
                    self.sensor_service.dispatch(
                        trigger=trigger,
                        payload={event: 'NO! asn_v6 {asn_v6} going down significantly'.format(
                            asn_v6=asn_v6)},
                        trace_tag="{asn_v6}-down-{timestamp}"
                    )

            # no AS presence
            if curr_asn_v4_conn > 1.0 and new_asn_v4_conn < 1.0:
                self._logger.info('{asn_v4} completely offline'.format(
                    asn_v4=asn_v4))
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: '{asn_v4} completely offline'.format(
                        asn_v4=asn_v4)},
                    trace_tag="{asn_v4}-offline-{timestamp}".format(
                        asn_v4=asn_v4, timestamp=probe_update['timestamp'])
                )
            if curr_asn_v6_conn > 1.0 and new_asn_v6_conn < 1.0:
                self._logger.info('{asn_v6} completely offline'.format(
                    asn_v6=asn_v6))
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: '{asn_v6} completely offline'.format(
                        asn_v6=asn_v6)},
                    trace_tag="{asn_v6}-offline-{timestamp}".format(
                        asn_v6=asn_v6, timestamp=probe_update['timestamp'])
                )

            # AS picks up
            if new_asn_v4_conn and curr_asn_v4_conn and new_asn_v4_conn - curr_asn_v4_conn > 19.0:
                self._logger.info(
                    'YEAH! {asn_v4} seeing significant uptake in online probes'.format(asn_v4=asn_v4))
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: 'YEAH! {asn_v4} seeing significant uptake in online probes'.format(
                        asn_v4=asn_v4)},
                    trace_tag="{asn_v4}-uptake-{timestamp}".format(
                        asn_v4=asn_v4, timestamp=probe_update['timestamp'])
                )
            if new_asn_v6_conn and curr_asn_v6_conn and new_asn_v6_conn - curr_asn_v6_conn > 19.0:
                self._logger.info(
                    'YEAH! {asn_v6} seeing significant uptake in online probes'.format(asn_v6=asn_v6))
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: 'YEAH! {asn_v6} seeing significant uptake in online probes'.format(
                        asn_v6=asn_v6)},
                    trace_tag="{asn_v6}-uptake-{timestamp}".format(
                        asn_v6=asn_v6, timestamp=probe_update['timestamp'])
                )

            # Probes going down fast
            if len(self._ases_v4_state.get(asn_v4, {}).get('LastDisconnected')) >= 3:
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: 'OMG! {asn_v4} going down fast now'.format(
                        asn_v4=asn_v4)},
                    trace_tag="{asn_v4}-downfast-{timestamp}".format(
                        asn_v4=asn_v4, timestamp=probe_update['timestamp'])
                )
            if len(self._ases_v6_state.get(asn_v6, {}).get('LastDisconnected')) >= 3:
                self.sensor_service.dispatch(
                    trigger=trigger,
                    payload={event: 'OMG! {asn_v6} going down fast now'.format(
                        asn_v6=asn_v6)},
                    trace_tag="{asn_v6}-downfast-{timestamp}".format(
                        asn_v4=asn_v6, timestamp=probe_update['timestamp'])
                )

        self._logger.info('connection percentage for asn_v4 {asn_v4} {old} -> {new}'.format(
            asn_v4=asn_v4, old=curr_asn_v4_conn, new=new_asn_v4_conn))
        self._logger.info('connection percentage for asn_v6 {asn_v6} {old} -> {new}'.format(
            asn_v6=asn_v6, old=curr_asn_v6_conn, new=new_asn_v6_conn))
        self._logger.info('disconnect bin asn v4: {}'.format(
            self._ases_v4_state.get(asn_v4, {}).get('LastDisconnected')))
        self._logger.info('disconnect bin asn v6: {}'.format(
            self._ases_v6_state.get(asn_v6, {}).get('LastDisconnected')))

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
