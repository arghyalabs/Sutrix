from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.SaltRemover import SaltRemover

class SMILESCleaner:
    """
    Cleans and canonicalizes SMILES strings using RDKit.
    Handles salt removal and neutralization.
    """
    def __init__(self):
        self.remover = SaltRemover()

    def clean(self, smiles):
        """
        Cleans a SMILES string:
        - Removes salts
        - Neutralizes charges
        - Canonicalizes
        """
        if not smiles or not isinstance(smiles, str):
            return None
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return None
                
            # Remove salts
            mol = self.remover.StripMol(mol)
            
            # Neutralize (simple version)
            mol = self._neutralize_atoms(mol)
            
            # Return canonical SMILES
            return Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
        except Exception:
            return None

    def _neutralize_atoms(self, mol):
        """
        Simple neutralization logic for common groups.
        """
        pattern = Chem.MolFromSmarts("[+1!h0!$([*]~[-1,-2,-3,-4]),-1!$([*]~[+1,+2,+3,+4])]")
        at_matches = mol.GetSubstructMatches(pattern)
        at_matches_list = [y[0] for y in at_matches]
        if len(at_matches_list) > 0:
            for at_idx in at_matches_list:
                atom = mol.GetAtomWithIdx(at_idx)
                chg = atom.GetFormalCharge()
                hcount = atom.GetTotalNumHs()
                atom.SetFormalCharge(0)
                atom.SetNumExplicitHs(hcount - chg)
        return mol

    def get_inchi_data(self, smiles):
        """
        Generates InChI and InChIKey from SMILES.
        """
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None, None
            
        inchi = Chem.MolToInchi(mol)
        inchikey = Chem.InchiToInchiKey(inchi)
        return inchi, inchikey

    def get_formula(self, smiles):
        """
        Generates molecular formula from SMILES.
        """
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
        return AllChem.CalcMolFormula(mol)
