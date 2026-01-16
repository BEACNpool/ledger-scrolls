import subprocess
import json
import logging
import signal

logger = logging.getLogger(__name__)

class OuraDriver:
    def __init__(self, network="mainnet"):
        self.network = network
        self.binary = "oura"

    def stream_address(self, address, start_slot=None):
        cmd = [
            self.binary, "watch",
            "Tcp:relays-new.cardano-mainnet.iohk.io:3001",
            "--magic", self.network.upper(),
        ]
        if start_slot is not None:
            # For production: Use Blockfrost or explorer to get hash (see lookup_hash function below)
            block_hash = self.lookup_block_hash(start_slot)  # Add this function
            cmd.extend(["--since", f"{start_slot},{block_hash}"])
        return self._run_process(cmd, filter_func=lambda event: address in event.get("address", ""))

    def stream_policy(self, policy_id, start_slot=None):
        cmd = [
            self.binary, "watch",
            "Tcp:relays-new.cardano-mainnet.iohk.io:3001",
            "--magic", self.network.upper(),
        ]
        if start_slot is not None:
            block_hash = self.lookup_block_hash(start_slot)
            cmd.extend(["--since", f"{start_slot},{block_hash}"])
        return self._run_process(cmd, filter_func=lambda event: policy_id in event.get("policy", "") or "777" in event.get("metadata", {}))

    def _run_process(self, cmd, filter_func=None):
        logger.info(f"Exec Oura: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        try:
            for line in process.stdout:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if filter_func is None or filter_func(event):
                        yield event
                except json.JSONDecodeError:
                    continue
        except GeneratorExit:
            logger.debug("Closing Oura stream...")
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
            stderr_out = process.stderr.read()
            if stderr_out and "error" in stderr_out.lower():
                logger.error(f"Oura process error: {stderr_out.strip()}")

    def lookup_block_hash(self, slot):
        # Simple curl to Blockfrost or explorer (use config key)
        from config import blockfrost_key
        if not blockfrost_key:
            logger.error("Blockfrost key missing for hash lookup.")
            return "0000000000000000000000000000000000000000000000000000000000000000"  # Dummy fallback
        import requests
        url = f"https://cardano-mainnet.blockfrost.io/api/v0/blocks/slot/{slot - 1}"  # Closest before
        headers = {"project_id": blockfrost_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data["hash"]
        else:
            logger.error("Hash lookup failed.")
            return "0000000000000000000000000000000000000000000000000000000000000000"
