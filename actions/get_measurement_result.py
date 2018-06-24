from datetime import datetime
from ripe.atlas.cousteau import AtlasResultsRequest

from st2common.runners.base_action import Action

__all__ = [
    'AtlasGetMeasurementResult'
]


class AtlasGetMeasurementResult(Action):
    def run(self, measurement_id, probe_id):
        """
        # self.config['<key>'] is useful for retrieving API keys, etc.
        # not needed for this action, so everything is a parameter
        """

        is_success, m_results = AtlasResultsRequest(
            msm_id=measurement_id,
            # start=start,
            # stop=stop,
            probe_ids=[probe_id]
        ).create()

        action_results = {
            "last_result": m_results[-1]
        }

        return (is_success, action_results)
