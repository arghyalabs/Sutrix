from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CompoundRegistry(Base):
    __tablename__ = 'compound_registry'
    id = Column(Integer, primary_key=True, autoincrement=True)
    compound_name = Column(String, index=True)
    canonical_smiles = Column(String, index=True)
    inchi_key = Column(String, unique=True, index=True)
    cas_number = Column(String, index=True)
    pubchem_cid = Column(String, index=True)
    molecular_formula = Column(String)
    molecular_weight = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    descriptors = relationship("DescriptorRegistry", back_populates="compound", uselist=False)
    enrichment = relationship("EnrichmentHistory", back_populates="compound", uselist=False)
    workflow_outputs = relationship("WorkflowOutput", back_populates="compound")

class DescriptorRegistry(Base):
    __tablename__ = 'descriptor_registry'
    compound_id = Column(Integer, ForeignKey('compound_registry.id'), primary_key=True)
    logp = Column(Float)
    tpsa = Column(Float)
    h_bond_donors = Column(Integer)
    h_bond_acceptors = Column(Integer)
    rotatable_bonds = Column(Integer)
    fingerprints = Column(String)  
    molecular_descriptors_json = Column(JSON)
    
    compound = relationship("CompoundRegistry", back_populates="descriptors")

class EnrichmentHistory(Base):
    __tablename__ = 'enrichment_history'
    compound_id = Column(Integer, ForeignKey('compound_registry.id'), primary_key=True)
    pubchem_data = Column(JSON)
    chembl_data = Column(JSON)
    pubmed_data = Column(JSON)
    fetch_status = Column(String)
    last_fetched = Column(DateTime, default=datetime.utcnow)
    
    compound = relationship("CompoundRegistry", back_populates="enrichment")

class FailedFetch(Base):
    __tablename__ = 'failed_fetches'
    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String, index=True)
    identifier_type = Column(String) # e.g. "SMILES", "InChIKey", "Name"
    source = Column(String) # e.g. "PubChem", "ChEMBL", "RDKit"
    error_message = Column(Text)
    failed_at = Column(DateTime, default=datetime.utcnow)

class WorkflowOutput(Base):
    __tablename__ = 'workflow_outputs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String, index=True)
    compound_id = Column(Integer, ForeignKey('compound_registry.id'))
    segregation_category = Column(String)
    endpoint = Column(String)
    export_reference = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    compound = relationship("CompoundRegistry", back_populates="workflow_outputs")
