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
            self.network,
            "--filter", f"address={address}"
        ]
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])
        return self._run_process(cmd)

    def stream_policy(self, policy_id, start_slot=None):
        cmd = [
            self.binary, "watch",
            self.network,
            "--filter", f"policy={policy_id}"
        ]
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])
        return self._run_process(cmd)

    def _run_process(self, cmd):
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
                    # Add slot if available from Oura output
                    if 'block' in tx and 'slot' in tx['block']:
                        tx['slot'] = tx['block']['slot']
                    yield tx
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
