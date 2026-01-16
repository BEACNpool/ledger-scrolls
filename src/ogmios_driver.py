import logging
from ogmios import OgmiosClient  # From ogmios-python lib

logger = logging.getLogger(__name__)

class OgmiosDriver:
    def __init__(self, host="ws://localhost:1337", network="mainnet"):
        self.client = OgmiosClient(host)

    def stream_from_slot(self, start_slot, filter_key="777"):
        response = self.client.query_ledger_state(start_slot=start_slot)
        for event in response.stream():
            metadata = event.get("metadata", {})
            if filter_key in metadata:
                yield metadata[filter_key]

    # Add similar to stream_policy, etc.
