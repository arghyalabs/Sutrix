import logging
from typing import List

logger = logging.getLogger("sdo.backend.architecture.ontology")

class OntologyRouter:
    """
    Validates and manages the dynamic scientific hierarchy paths.
    Maps selected ontology columns to ensure valid subdataset creation.
    """
    @staticmethod
    def validate_hierarchy(df_columns: List[str], requested_hierarchy: List[str]) -> List[str]:
        """
        Ensures that the requested hierarchy variables actually exist in the dataset.
        Returns a validated list of columns to use for recursion.
        """
        valid_hierarchy = []
        for col in requested_hierarchy:
            if col in df_columns:
                valid_hierarchy.append(col)
            else:
                logger.warning(f"OntologyRouter: Hierarchy variable '{col}' not found in dataset. Skipping.")
        return valid_hierarchy
