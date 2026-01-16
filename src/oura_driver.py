import subprocess
import json
import logging

class OuraDriver:
    def __init__(self, network="mainnet"):
        self.network = network
        # Ensure 'oura' is installed and in your PATH
        self.binary = "oura" 

    def stream_address(self, address):
        """
        Filters the chain for a specific address (The Registry).
        """
        cmd = [
            self.binary, "watch",
            self.network,
            "--filter", f"address={address}"
        ]
        return self._run_process(cmd)

    def stream_policy(self, policy_id, start_slot):
        """
        The Magic: Starts reading chain from specific slot, filtering by Policy ID.
        """
        cmd = [
            self.binary, "watch",
            self.network,
            "--since", str(start_slot),
            "--filter", f"policy={policy_id}"
        ]
        return self._run_process(cmd)

    def _run_process(self, cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Yields JSON objects one by one as they come in from P2P
        for line in process.stdout:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
