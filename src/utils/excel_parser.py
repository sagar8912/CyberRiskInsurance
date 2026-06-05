import os
import pandas as pd

class ExcelParser:
    def __init__(self, filepath="data/cyber_rater_modifier_summary.xlsx"):
        self.filepath = filepath
        self.modifiers = {}
        self.load_modifiers()

    def load_modifiers(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Excel modifiers file not found at: {self.filepath}")
        
        # Load Sheet1 (assuming it is the main sheet)
        df = pd.read_excel(self.filepath, sheet_name=0)
        
        # Strip string values to avoid key errors
        df.columns = [col.strip() for col in df.columns]
        
        for _, row in df.iterrows():
            name = str(row.get("Modifier Name", "")).strip()
            if not name:
                continue
            
            self.modifiers[name] = {
                "name": name,
                "description": str(row.get("Description", "")).strip(),
                "target_parameter": str(row.get("Target Parameter", "")).strip(),
                "research_needed": str(row.get("Cyber Insurance Research Needed", "")).strip()
            }

    def get_modifier(self, name):
        """Get description, target parameter and research needed for a given modifier name."""
        return self.modifiers.get(name)

    def get_all_names(self):
        """Return list of all parsed modifier names."""
        return list(self.modifiers.keys())
