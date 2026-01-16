import logging

logger = logging.getLogger(__name__)

class BeaconParser:
    """
    Parses metadata adhering to the BEACN Protocol and standard Cardano formats.
    Acts as the first line of defense against spam (filtering invalid labels).
    """

    # --- Allowlisted Protocols ---
    LABEL_MSG = "674"      # CIP-20 Standard (Messages/Blogs)
    LABEL_NFT = "721"      # CIP-25 Standard (NFTs/Media)
    LABEL_SCROLL = "888"   # Ledger Scrolls Custom Protocol

    @staticmethod
    def parse_registration(tx_json):
        """
        Looks for the 'LS:Register' pattern in a transaction.
        Robustly handles formatting errors so one bad scroll doesn't crash the registry.
        """
        try:
            # We strictly look for label 777 for registrations
            metadata = tx_json.get("metadata", {}).get(BeaconParser.LABEL_SCROLL, {})
            
            # Handle both list-style (["msg", ...]) and dict-style JSON
            msg_list = []
            if isinstance(metadata, dict):
                msg_list = metadata.get("msg", [])
            elif isinstance(metadata, list):
                msg_list = metadata

            if not msg_list:
                return None
            
            # 1. Check Protocol Signature
            if len(msg_list) > 0 and msg_list[0] == "LS:Register":
                data = {}
                
                # 2. Extract Fields safely
                for item in msg_list:
                    if not isinstance(item, str): 
                        continue
                        
                    # Split only on the first colon to preserve colons in values (e.g. descriptions)
                    parts = item.split(":", 1)
                    if len(parts) < 2: 
                        continue
                        
                    key = parts[0].strip().lower()
                    val = parts[1].strip()
                    
                    # Map known keys to our internal schema
                    if key == "project":
                        data["project"] = val  # Fixed: Matches main.py expectation
                    elif key == "policyid":
                        data["policy_id"] = val
                    elif key == "startslot":
                        try:
                            data["start_slot"] = int(val)
                        except ValueError:
                            data["start_slot"] = 0 # Default to 0 if malformed
                    elif key == "structure":
                        data["structure"] = val
                    elif key == "description":
                        data["description"] = val

                # 3. Validation (Must have Name and ID)
                if "project" in data and "policy_id" in data:
                    return data

        except Exception as e:
            # Log debug only so we don't spam the user console with parse errors
            logger.debug(f"Failed to parse registration candidate: {e}")
            return None
            
        return None

    @staticmethod
    def extract_metadata(tx_json):
        """
        Extracts known content types from a transaction.
        returns: The raw metadata payload (dict or list) OR None if it's spam.
        """
        if not tx_json or "metadata" not in tx_json:
            return None

        md = tx_json["metadata"]
        if not md:
            return None

        # --- Priority 1: Custom Scroll Protocol (888) ---
        if BeaconParser.LABEL_SCROLL in md:
            payload = md[BeaconParser.LABEL_SCROLL]
            # If it's the "msg" wrapper style, unwrap it for the processor
            if isinstance(payload, dict) and "msg" in payload:
                return payload["msg"]
            return payload

        # --- Priority 2: Standard Messages (674) ---
        # Good for simple text scrolls / blogs
        if BeaconParser.LABEL_MSG in md:
            payload = md[BeaconParser.LABEL_MSG]
            if isinstance(payload, dict) and "msg" in payload:
                return payload["msg"]
            return payload

        # --- Priority 3: NFTs (721) ---
        # Good for documents/images
        if BeaconParser.LABEL_NFT in md:
            return md[BeaconParser.LABEL_NFT]

        # --- SPAM FILTER ---
        # If the transaction has metadata but not on our allowlist, ignore it.
        return None
