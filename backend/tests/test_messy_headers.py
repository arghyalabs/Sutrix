from backend.core.schema_intelligence import SchemaIntelligenceEngine

def run_messy_header_test():
    """
    Tests the Semantic Schema Intelligence Engine against notorious vendor CSV headers.
    """
    messy_columns = [
        "InChI_Key_String",
        "Assay_pXC50_Value (uM)",
        "Tox21_Active_Status",
        "96h_LC50_Fathead_Minnow_mg/L",
        "Molecular__Weight___",
        "Cyp3a4_Clearance_Rate",
        "Unknown_Vendor_ID_Field"
    ]
    
    print("\n[TEST] Running AI Schema Inference on Messy Headers...")
    results = SchemaIntelligenceEngine.infer_schema(messy_columns)
    
    for res in results:
        print(f"\nHeader: '{res['column']}'")
        print(f"Mapped to: {res['mapped_to'].upper()}")
        print(f"Confidence: {res['confidence']}")
        print(f"Reasoning: {res['reasons']}")
        
    # Assertions
    assert results[0]["mapped_to"] == "inchi"
    assert results[1]["mapped_to"] in ["value", "assay"]
    assert results[2]["mapped_to"] == "classification_target" or results[2]["mapped_to"] == "toxicology"
    assert results[3]["mapped_to"] == "endpoint" # Ecotox override!
    assert "96h" in str(results[3]["reasons"])
    assert "fish" in str(results[3]["reasons"])
    assert results[4]["mapped_to"] == "molecular_weight"
    assert results[5]["mapped_to"] == "metabolism"
    assert results[6]["mapped_to"] == "none"
    
    print("\n[SUCCESS] AI Semantic Engine handles messy CSVs deterministically.")

if __name__ == "__main__":
    run_messy_header_test()
