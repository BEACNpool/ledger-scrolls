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
        Filters the chain for a specific address.
        Supports optional start_slot to allow 'Time Travel' or efficiency.
        """
        cmd = [
            self.binary, "watch",
            self.network,
            "--filter", f"address={address}"
        ]
        
        # If a start slot is provided, we tell Oura to go back in time
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])
        
        return self._run_process(cmd)

    def stream_policy(self, policy_id, start_slot=None):
        """
        Filters the chain for a specific Policy ID (Mint/Burn events).
        """
        cmd = [
            self.binary, "watch",
            self.network,
            "--filter", f"policy={policy_id}"
        ]
        
        if start_slot is not None:
            cmd.extend(["--since", str(start_slot)])

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
            stderr=subprocess.PIPE, # Capture stderr for debugging
            text=True,
            bufsize=1 # Line buffered to get data immediately
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
            # rigorous cleanup to prevent zombie processes
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # Log any errors from the subprocess if it crashed
            stderr_out = process.stderr.read()
            if stderr_out and "error" in stderr_out.lower():
                logger.error(f"Oura process error: {stderr_out.strip()}")
