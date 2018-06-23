from datetime import datetime
from ripe.atlas.cousteau import AtlasResultsRequest

from st2common.runners.base_action import Action

__all__ = [
    'AtlasGetMeasurementResult'
]


class AtlasGetMeasurementResult(Action):
    def run(self, measurement_id, start=None, stop=None, probe_ids=[]):
        """
        # self.config['<key>'] is useful for retrieving API keys, etc.
        # not needed for this action, so everything is a parameter
        """

        is_success, m_results = AtlasResultsRequest(
            msm_id=measurement_id,
            start=start,
            stop=stop,
            probe_ids=probe_ids
        ).create()

        # m_results is a list of dictionaries, one per probe
        # each dict contains measurement from that probe

        # Let's average all the averages together for fun
        avgs = [result['avg'] for result in m_results]
        avg = float(sum(avgs)) / max(len(avgs), 1)

        # Provide calculated average as well as the raw results
        # from cousteau
        action_results = {
            "raw_results": m_results,
            "latency_avg": avg
        }

        return (is_success, action_results)
