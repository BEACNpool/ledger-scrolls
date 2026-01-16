import subprocess
import json
import logging
import signal

logger = logging.getLogger(__name__)

class OuraDriver:
    def __init__(self, network="mainnet"):
        self.network = network
        # Ensure 'oura' is installed and in your PATH
        self.binary = "oura"

    def stream_address(self, address, start_slot=None):
        """
        Streams unfiltered chain events (Oura v2 watch has no CLI filter).
        Address filtering would need to be done in Python post-processing.
        """
        cmd = [
            self.binary, "watch",
            "Tcp:relays-new.cardano-mainnet.iohk.io:3001",  # Public relay (can change to others if flaky)
            "--magic", self.network.upper(),               # e.g., MAINNET
        ]
        
        # Optional: Jump to start_slot (needs real block hash!)
        if start_slot is not None:
            # REPLACE THIS WITH A REAL BLOCK HASH from the slot (from cexplorer.io or cardanoscan.io)
            # Example: get hash for slot 115000450 or closest
            block_hash = "0000000000000000000000000000000000000000000000000000000000000000"  # DUMMY - MUST CHANGE!
            cmd.extend(["--since", f"{start_slot},{block_hash}"])
        
        return self._run_process(cmd)

    def stream_policy(self, policy_id, start_slot=None):
        """
        Streams unfiltered chain events (no CLI filter in v2).
        Policy filtering would need to be done in Python post-processing.
        """
        cmd = [
            self.binary, "watch",
            "Tcp:relays-new.cardano-mainnet.iohk.io:3001",
            "--magic", self.network.upper(),
        ]
        
        if start_slot is not None:
            # REPLACE THIS WITH A REAL BLOCK HASH!
            block_hash = "0000000000000000000000000000000000000000000000000000000000000000"  # DUMMY - MUST CHANGE!
            cmd.extend(["--since", f"{start_slot},{block_hash}"])
        
        return self._run_process(cmd)

    def _run_process(self, cmd):
        """
        Executes the Oura subprocess and yields JSON events.
        Handles cleanup automatically when the loop ends.
        """
        logger.info(f"Exec Oura: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture stderr for debugging
            text=True,
            bufsize=1  # Line buffered to get data immediately
        )
        try:
            # Yields JSON objects one by one as they come in from P2P
            for line in process.stdout:
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # Sometimes Oura prints status messages that aren't JSON
                    continue
                
        except GeneratorExit:
            # This block runs if the consumer (main.py) stops the loop
            logger.debug("Closing Oura stream...")
            raise
            
        finally:
            # Rigorous cleanup to prevent zombie processes
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # Log any errors from the subprocess if it crashed
            stderr_out = process.stderr.read()
            if stderr_out and "error" in stderr_out.lower():
                logger.error(f"Oura process error: {stderr_out.strip()}")
