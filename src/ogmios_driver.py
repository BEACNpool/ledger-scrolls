import logging
from ogmios import Client  

logger = logging.getLogger(__name__)

class OgmiosDriver:
    def __init__(self, config):
        self.host = config.get('ogmios_host', 'localhost')
        self.port = config.get('ogmios_port', 1337)
        self.client = Client(host=self.host, port=self.port)

    def stream_address(self, address, start_slot=None):
        # Use chainSync for streaming, filter client-side
        request = {
            "type": "jsonwsp/request",
            "version": "1.0",
            "servicename": "ogmios",
            "methodname": "findIntersect",
            "args": {"points": [f"slot:{start_slot}"] if start_slot else ["tip"]}
        }
        self.client.send(request)
        while True:
            response = self.client.receive()
            if 'block' in response and address in str(response):  # Simple filter
                yield response

    def stream_policy(self, policy_id, start_slot=None):
        request = {
            "type": "jsonwsp/request",
            "version": "1.0",
            "servicename": "ogmios",
            "methodname": "findIntersect",
            "args": {"points": [f"slot:{start_slot}"] if start_slot else ["tip"]}
        }
        self.client.send(request)
        while True:
            response = self.client.receive()
            if 'block' in response and policy_id in str(response):  # Simple filter
                yield response

    def __del__(self):
        self.client.close()
