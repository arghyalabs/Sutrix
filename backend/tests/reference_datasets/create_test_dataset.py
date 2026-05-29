import os
import pandas as pd
import numpy as np

def generate_reference_datasets(output_dir: str = "backend/tests/reference_datasets"):
    """
    Generates synthetic QSAR, Toxicology, and Messy datasets in multiple formats
    (CSV, XLSX, TSV, Parquet) for E2E and unit validation testing.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Toxicology Dataset (OECD Guidelines compliant schema)
    tox_data = {
        "SMILES": [
            "CC(=O)Oc1ccccc1C(=O)O", "c1ccccc1", "CCO", "CN(C)C(=O)NC1=CC=C(C=C1)Cl",
            "CC(=O)NC1=CC=C(O)C=C1", "O=C1NC(=O)C(C)(C)S1", "CC1=CC=C(C=C1)S(=O)(=O)NC(=O)NC2CCCCC2",
            "C1=CC(=CC=C1O)O", "C1=CC=C2C(=C1)C=CC3=C2C=CC4=C3C=CC5=C4C=CC6=C5C=CC7=C6C=CC8=C7C=CC9=C8C=C1"
        ],
        "CAS": [
            "50-78-2", "71-43-2", "64-17-5", "330-54-1",
            "103-90-2", "80-73-9", "64-77-7", "123-31-9", "191-24-2"
        ],
        "Species": ["rat", "mouse", "fish", "rat", "mouse", "fish", "rat", "mouse", "fish"],
        "Duration": [24, 48, 96, 24, 48, 96, 24, 48, 96],
        "LC50": [120.5, 45.2, 3400.0, 12.3, 230.0, 8.5, 95.0, 3.2, 0.45],
        "NOEC": [10.0, 2.5, 500.0, 1.0, 50.0, 0.5, 10.0, 0.1, 0.01],
        "ExposureType": ["water", "oral", "water", "oral", "oral", "water", "oral", "oral", "water"],
        "OECDGuideline": ["OECD 203", "OECD 401", "OECD 203", "OECD 401", "OECD 401", "OECD 203", "OECD 401", "OECD 401", "OECD 203"]
    }
    # Standardize arrays to same length
    tox_df = pd.DataFrame(tox_data)
    
    # 2. QSAR Dataset
    qsar_data = {
        "SMILES": [
            "CC(=O)Oc1ccccc1C(=O)O", "c1ccccc1", "CCO", "CN(C)C(=O)NC1=CC=C(C=C1)Cl",
            "CC(=O)NC1=CC=C(O)C=C1", "O=C1NC(=O)C(C)(C)S1", "CC1=CC=C(C=C1)S(=O)(=O)NC(=O)NC2CCCCC2",
            "C1=CC(=CC=C1O)O", "C1=CC=C2C(=C1)C=CC3=C2C=CC4=C3C=CC5=C4C=CC6=C5C=CC7=C6C=CC8=C7C=CC9=C8C=C1"
        ],
        "pIC50": [4.5, 3.2, 2.1, 5.8, 4.1, 6.2, 4.9, 5.1, 7.3],
        "MW": [180.16, 78.11, 46.07, 233.1, 151.16, 145.18, 368.47, 110.11, 452.5],
        "TPSA": [63.6, 0.0, 20.2, 32.2, 49.3, 58.4, 75.3, 40.5, 0.0],
        "LogP": [1.19, 2.13, -0.31, 2.68, 0.91, 0.45, 2.3, 0.59, 6.8],
        "HBA": [4, 0, 1, 2, 2, 3, 4, 2, 0],
        "HBD": [1, 0, 1, 1, 2, 1, 2, 2, 0]
    }
    qsar_df = pd.DataFrame(qsar_data)
    
    # 3. Messy Dataset (with anomalous columns, spacing and lowercase headers)
    messy_data = {
        "chem_struct": [
            "CC(=O)Oc1ccccc1C(=O)O", "c1ccccc1", "CCO", "CN(C)C(=O)NC1=CC=C(C=C1)Cl",
            "CC(=O)NC1=CC=C(O)C=C1", "O=C1NC(=O)C(C)(C)S1", "CC1=CC=C(C=C1)S(=O)(=O)NC(=O)NC2CCCCC2"
        ],
        "fish_sp": ["rainbow trout", "fathead minnow", "bluegill", "rainbow trout", "fathead minnow", "bluegill", "rainbow trout"],
        "96h lc50 mg/L": ["< 0.05", "> 100.0", "3400 mg/L", "12.3", "230.0", "~ 8.5", "95.0"],
        "cas no": ["50-78-2", "71-43-2", "64-17-5", "330-54-1", "103-90-2", "80-73-9", "64-77-7"],
        "tox val": [120.5, 45.2, 3400.0, 12.3, 230.0, 8.5, 95.0]
    }
    messy_df = pd.DataFrame(messy_data)
    
    # Export formats
    datasets = {
        "toxicology": tox_df,
        "qsar": qsar_df,
        "messy": messy_df
    }
    
    for name, df in datasets.items():
        # CSV
        df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)
        # TSV
        df.to_csv(os.path.join(output_dir, f"{name}.tsv"), sep="\t", index=False)
        # Parquet
        df.to_parquet(os.path.join(output_dir, f"{name}.parquet"), index=False)
        # Excel
        try:
            df.to_excel(os.path.join(output_dir, f"{name}.xlsx"), index=False)
        except Exception as e:
            print(f"Excel generation skipped for {name}: {e}")
            
    print(f"Compliance Alert: Test reference datasets successfully generated in {output_dir}.")

if __name__ == "__main__":
    generate_reference_datasets()
