from typing import Optional, Dict, Any
from sqlalchemy import or_, select
import logging

from .models import CompoundRegistry, DescriptorRegistry, EnrichmentHistory, FailedFetch
from .session import SessionLocal

logger = logging.getLogger("sdo.backend.database")

class DatabaseManager:
    """Handles CRUD operations for the centralized compound database."""
    
    @staticmethod
    def get_compound_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
        """Check if compound exists by searching InChIKey, SMILES, CID, Name, or CAS."""
        with SessionLocal() as session:
            stmt = select(CompoundRegistry).where(
                or_(
                    CompoundRegistry.inchi_key == identifier,
                    CompoundRegistry.canonical_smiles == identifier,
                    CompoundRegistry.pubchem_cid == identifier,
                    CompoundRegistry.cas_number == identifier,
                    CompoundRegistry.compound_name == identifier
                )
            ).limit(1)
            result = session.execute(stmt)
            compound = result.scalar_one_or_none()
            
            if compound:
                # Eagerly load descriptors and api_enrichment while the session is open
                desc_stmt = select(DescriptorRegistry).where(DescriptorRegistry.compound_id == compound.id)
                desc_res = session.execute(desc_stmt)
                descriptor = desc_res.scalar_one_or_none()
                
                api_stmt = select(EnrichmentHistory).where(EnrichmentHistory.compound_id == compound.id)
                api_res = session.execute(api_stmt)
                api_data = api_res.scalar_one_or_none()
                
                # Make sure fields are loaded in-memory before session closes to prevent DetachedInstanceError
                session.expunge_all()
                
                return {
                    "compound": compound,
                    "descriptor": descriptor,
                    "api_enrichment": api_data
                }
            return None

    @staticmethod
    def save_compound(compound_data: Dict[str, Any], descriptor_data: Dict[str, Any] = None, api_data: Dict[str, Any] = None) -> CompoundRegistry:
        """Save a new compound or update existing to the database."""
        with SessionLocal() as session:
            # Check if exists by InChIKey to avoid duplicates
            inchi_key = compound_data.get("inchi_key")
            compound = None
            if inchi_key:
                stmt = select(CompoundRegistry).where(CompoundRegistry.inchi_key == inchi_key).limit(1)
                result = session.execute(stmt)
                compound = result.scalar_one_or_none()
            
            if not compound:
                # Check by SMILES as secondary
                smiles = compound_data.get("canonical_smiles")
                if smiles:
                    stmt = select(CompoundRegistry).where(CompoundRegistry.canonical_smiles == smiles).limit(1)
                    result = session.execute(stmt)
                    compound = result.scalar_one_or_none()

            if not compound:
                compound = CompoundRegistry(**compound_data)
                session.add(compound)
                session.flush() # get ID
            else:
                # Update missing fields
                for k, v in compound_data.items():
                    if v and not getattr(compound, k):
                        setattr(compound, k, v)
                        
            if descriptor_data:
                desc_stmt = select(DescriptorRegistry).where(DescriptorRegistry.compound_id == compound.id).limit(1)
                desc_res = session.execute(desc_stmt)
                descriptor = desc_res.scalar_one_or_none()
                
                if not descriptor:
                    descriptor = DescriptorRegistry(compound_id=compound.id, **descriptor_data)
                    session.add(descriptor)
                else:
                    for k, v in descriptor_data.items():
                        if v is not None:
                            setattr(descriptor, k, v)
                            
            if api_data:
                api_stmt = select(EnrichmentHistory).where(EnrichmentHistory.compound_id == compound.id).limit(1)
                api_res = session.execute(api_stmt)
                api_enrichment = api_res.scalar_one_or_none()
                
                if not api_enrichment:
                    api_enrichment = EnrichmentHistory(compound_id=compound.id, **api_data)
                    session.add(api_enrichment)
                else:
                    for k, v in api_data.items():
                        if v is not None:
                            setattr(api_enrichment, k, v)
                            
            session.commit()
            
            # Refresh to hold state fully detached
            session.refresh(compound)
            session.expunge_all()
            return compound

    @staticmethod
    def log_failed_fetch(identifier: str, identifier_type: str, source: str, error_message: str):
        """Log a failed enrichment fetch or descriptor calculation."""
        with SessionLocal() as session:
            failed_fetch = FailedFetch(
                identifier=identifier,
                identifier_type=identifier_type,
                source=source,
                error_message=error_message
            )
            session.add(failed_fetch)
            session.commit()
