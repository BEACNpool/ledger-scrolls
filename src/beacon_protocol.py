class BeaconParser:
    """
    Parses metadata adhering to the BEACN Protocol (Label 777).
    """
    
    @staticmethod
    def parse_registration(tx_json):
        """
        Looks for the 'LS:Register' pattern in a transaction.
        """
        try:
            metadata = tx_json.get("metadata", {}).get("777", {})
            if not metadata:
                return None
                
            msg_list = metadata.get("msg", [])
            
            # Protocol Check
            if len(msg_list) > 0 and msg_list[0] == "LS:Register":
                # Rough parsing logic based on your JSON example
                # Expecting: ["LS:Register", "Project: Name", "PolicyID: ...", "StartSlot: ...", "Structure: ..."]
                project_data = {}
                
                for item in msg_list:
                    if item.startswith("Project:"):
                        project_data["name"] = item.split(":")[1].strip()
                    if item.startswith("PolicyID:"):
                        project_data["policy_id"] = item.split(":")[1].strip()
                    if item.startswith("StartSlot:"):
                        project_data["start_slot"] = int(item.split(":")[1].strip())
                    if item.startswith("Structure:"):
                        project_data["structure"] = item.split(":")[1].strip()
                        
                return project_data
        except Exception as e:
            # Malformed metadata, ignore
            return None
        return None

    @staticmethod
    def extract_metadata(tx_json):
        """
        Extracts general metadata from a content transaction for the AI to process.
        """
        # Adjust '721' or your specific content label here
        return tx_json.get("metadata")
