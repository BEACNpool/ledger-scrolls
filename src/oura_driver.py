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
            self.network
        ]
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])
        return self._run_process(cmd, address_filter=address.lower())

    def stream_policy(self, policy_id, start_slot=None):
        cmd = [
            self.binary, "watch",
            self.network
        ]
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])
        return self._run_process(cmd, policy_filter=policy_id.lower())

    def _run_process(self, cmd, address_filter=None, policy_filter=None):
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
                    tx = json.loads(line)

                    # Add slot info if available
                    if 'block' in tx and 'slot' in tx['block']:
                        tx['slot'] = tx['block']['slot']

                    # Client-side filtering
                    tx_str = json.dumps(tx).lower()
                    if address_filter and address_filter in tx_str:
                        yield tx
                    elif policy_filter and policy_filter in tx_str:
                        yield tx
                    elif address_filter is None and policy_filter is None:
                        yield tx  # No filter = yield all
                    # Else skip if no match

                except json.JSONDecodeError:
                    continue

        finally:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
            stderr_out = process.stderr.read()
            if stderr_out and "error" in stderr_out.lower():
                logger.error(f"Oura error: {stderr_out.strip()}")
