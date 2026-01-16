import logging
import json

class HailoProcessor:
    def __init__(self):
        self.logger = logging.getLogger("HailoAI")
        self.use_hardware = False  # Set to True only if Hailo hardware is physically present
        self._initialize_hardware()

    def _initialize_hardware(self):
        """
        Attempts to initialize the Hailo-10H chip.
        Fails gracefully to CPU mode if hardware is missing.
        """
        try:
            # Placeholder for actual SDK import
            # from hailo_platform import VDevice
            if self.use_hardware:
                self.logger.info("Initializing Raspberry Pi AI HAT+...")
                # self.device = VDevice()
                self.logger.info("Hailo-10H Ready.")
            else:
                self.logger.info("No AI hardware detected. Using CPU-based reconstruction.")
        except Exception as e:
            self.logger.warning(f"Hardware init failed ({e}). Fallback to CPU mode.")
            self.use_hardware = False

    def process(self, raw_data, structure="default"):
        """
        Reconstructs human-readable content from raw blockchain fragments.
        """
        try:
            # 1. Base Case: If it's a simple string, return it.
            if isinstance(raw_data, str):
                return raw_data

            # 2. Stitching: Join 64-char chunks (standard Cardano metadata format)
            decoded_text = ""
            if isinstance(raw_data, list):
                decoded_text = self._stitch_text(raw_data)
            elif isinstance(raw_data, dict):
                # If it's a dict, we might want to dump it as JSON or find a specific key
                decoded_text = json.dumps(raw_data, indent=2)

            # 3. Formatting based on Schema/Structure
            if structure.lower() == "json":
                # Ensure it's valid JSON for display
                try:
                    obj = json.loads(decoded_text)
                    return json.dumps(obj, indent=2)
                except:
                    return decoded_text # Return raw if it fails to parse

            elif structure.lower() in ["book", "text", "article"]:
                # Future: This is where you'd run an LLM to summarize or fix typos
                return decoded_text

            # Default fallback
            return decoded_text

        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            return f"[Error decoding content: {raw_data}]"

    def _stitch_text(self, data_list):
        """
        Helper: Recombines a list of strings into a single block of text.
        Handles nested lists if necessary.
        """
        result = []
        for item in data_list:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                # Recursive call for nested arrays
                result.append(self._stitch_text(item))
            elif isinstance(item, dict):
                # If we encounter a dict inside a list (rare), dump it
                result.append(json.dumps(item))
        
        # Join without spaces because the 64-char split often happens mid-word
        return "".join(result)
