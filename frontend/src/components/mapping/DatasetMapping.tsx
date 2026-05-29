import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, Link2, Check, ChevronDown, ChevronRight, 
  Scale, ShieldAlert, Award, Compass, Timer, Beaker,
  Dna, Fingerprint, Layers, Activity, Zap, FileText
} from 'lucide-react';
import * as Select from '@radix-ui/react-select';
import * as Accordion from '@radix-ui/react-accordion';
import type { VariableMappings } from '../../types';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';

interface DatasetMappingProps {
  columns: string[];
  mappings: VariableMappings;
  setMappings: (mappings: VariableMappings) => void;
  handleSaveMappings: () => Promise<void>;
}

const mapOptions = [
  { value: 'none', label: 'Ignore Column' },
  // Chemical Identifiers
  { value: 'chemical_name', label: 'Chemical Name' },
  { value: 'chemical_id', label: 'Chemical ID / Compound ID' },
  { value: 'cas_number', label: 'CAS Number' },
  { value: 'canonical_smiles', label: 'Canonical SMILES' },
  { value: 'inchi', label: 'InChI / InChIKey' },
  // Chemical Properties / Descriptors
  { value: 'molecular_weight', label: 'Molecular Weight' },
  { value: 'logp', label: 'LogP / Partition Coefficient' },
  { value: 'pka', label: 'pKa / Dissociation Constant' },
  { value: 'tpsa', label: 'Topological Polar Surface Area (TPSA)' },
  { value: 'h_bond_donors', label: 'H-Bond Donors' },
  { value: 'h_bond_acceptors', label: 'H-Bond Acceptors' },
  // Biological & Ecotox Endpoints
  { value: 'endpoint', label: 'Biological / Assay Endpoint' },
  { value: 'value', label: 'Endpoint Value / Potency' },
  { value: 'unit', label: 'Measurement Unit' },
  { value: 'qualifier', label: 'Qualifier (e.g. >, <, =)' },
  { value: 'pXC50', label: 'pXC50 (Log Potency)' },
  { value: 'assay_type', label: 'Assay Type' },
  { value: 'target_gene', label: 'Target Gene / Protein' },
  { value: 'cell_line', label: 'Cell Line' },
  // Organism & Taxonomy
  { value: 'organism', label: 'Test Organism / Species' },
  { value: 'strain', label: 'Strain / Breed' },
  { value: 'life_stage', label: 'Life Stage (e.g., Adult, Larva)' },
  { value: 'trophic_level', label: 'Trophic Level' },
  // Experimental Conditions & Metadata
  { value: 'temperature', label: 'Temperature' },
  { value: 'ph', label: 'pH' },
  { value: 'study_year', label: 'Study Year' },
  { value: 'glp_compliant', label: 'GLP Compliant' },
  { value: 'source_database', label: 'Source Database' },
  { value: 'test_type', label: 'Test Type / Study Design' },
  // Exposure Metrics
  { value: 'exposure_time', label: 'Exposure Duration' },
  { value: 'exposure_route', label: 'Exposure Route (e.g., Oral, Inhalation)' },
  { value: 'test_medium', label: 'Test Medium (e.g., Soil, Water)' },
  // Environmental Fate
  { value: 'biodegradation', label: 'Biodegradation (%)' },
  { value: 'half_life', label: 'Half-Life (DT50)' },
  { value: 'bcf', label: 'Bioconcentration Factor (BCF)' },
  { value: 'koc', label: 'Organic Carbon Partition Coefficient (Koc)' },
  // Clinical / Patient
  { value: 'patient_id', label: 'Patient ID' },
  { value: 'age', label: 'Age' },
  { value: 'sex', label: 'Sex / Gender' },
  { value: 'clinical_phase', label: 'Clinical Phase' },
  { value: 'adverse_event', label: 'Adverse Event' },
  // Pharmacokinetics / ADME
  { value: 'clearance', label: 'Clearance (Cl)' },
  { value: 'bioavailability', label: 'Bioavailability (F%)' },
  { value: 'cmax', label: 'Max Concentration (Cmax)' },
  { value: 'tmax', label: 'Time of Max Concentration (Tmax)' },
  { value: 'vd', label: 'Volume of Distribution (Vd)' },
];

export const DatasetMapping: React.FC<DatasetMappingProps> = ({
  columns, mappings, setMappings, handleSaveMappings
}) => {
  const intelligence = useWorkspaceStore(state => state.mappingIntelligence) || {};

  const handleSelect = (col: string, val: string) => {
    setMappings({ ...mappings, [col]: val as any });
  };

  const datasetClassification = useMemo(() => {
    const values = Object.values(mappings);
    const colsLower = columns.map(c => c.toLowerCase());
    
    if (colsLower.some(c => c.includes('biodeg') || c.includes('bcf'))) return "Environmental Fate Dataset";
    if (colsLower.some(c => c.includes('oecd') || c.includes('reach'))) return "OECD Regulatory Dataset";
    if (colsLower.some(c => c.includes('fish') || c.includes('daphnia'))) return "Aquatic Toxicity Dataset";
    if (colsLower.some(c => c.includes('rat') || c.includes('human'))) return "Bioassay / Clinical Dataset";
    if (values.includes('canonical_smiles') && values.includes('value')) return "ADMET Dataset";
    
    return "Bioassay Dataset";
  }, [mappings, columns]);

  const safetyWarnings = useMemo(() => {
    const warnings: string[] = [];
    let hasHuman = false, hasFish = false, hasLC50 = false, hasOral = false, hasNOEC = false, hasDuration = false;

    Object.entries(mappings).forEach(([col, role]) => {
      if (role === 'none' || !role) return;
      const colLower = col.toLowerCase();
      if (colLower.includes('human') || colLower.includes('clinical')) hasHuman = true;
      if (colLower.includes('fish') || colLower.includes('zebrafish')) hasFish = true;
      if (colLower.includes('lc50')) hasLC50 = true;
      if (colLower.includes('noec')) hasNOEC = true;
      if (role === 'duration' || colLower.includes('96h')) hasDuration = true;
      if (colLower.includes('oral') || colLower.includes('diet')) hasOral = true;
    });

    if (hasHuman && hasLC50) warnings.push("Detected LC50 endpoint alongside Human species mappings. LC50 is standardly reserved for ecotoxicology.");
    if (hasFish && hasOral) warnings.push("Fish test species mapped with Oral route (aquatic organisms usually exposed via water).");
    if (hasNOEC && !hasDuration) warnings.push("Detected NOEC chronic threshold without an explicit study Exposure Duration.");

    return warnings;
  }, [mappings]);

  // Semantic Grouping
  const columnGroups = useMemo(() => {
    const groups = { 
      unmapped: [] as string[], 
      identifiers: [] as string[], 
      physchem: [] as string[],
      endpoints: [] as string[], 
      taxonomy: [] as string[], 
      exposure: [] as string[], 
      envfate: [] as string[],
      clinical: [] as string[],
      adme: [] as string[],
      metadata: [] as string[],
      ignored: [] as string[] 
    };
    columns.forEach(col => {
      const val = mappings[col];
      if (!val) groups.unmapped.push(col);
      else if (val === 'none') groups.ignored.push(col);
      else if (['chemical_name', 'chemical_id', 'cas_number', 'canonical_smiles', 'inchi'].includes(val)) groups.identifiers.push(col);
      else if (['molecular_weight', 'logp', 'pka', 'tpsa', 'h_bond_donors', 'h_bond_acceptors'].includes(val)) groups.physchem.push(col);
      else if (['endpoint', 'value', 'unit', 'qualifier', 'pXC50', 'assay_type', 'target_gene', 'cell_line'].includes(val)) groups.endpoints.push(col);
      else if (['organism', 'strain', 'life_stage', 'trophic_level'].includes(val)) groups.taxonomy.push(col);
      else if (['exposure_time', 'exposure_route', 'test_medium', 'temperature', 'ph'].includes(val)) groups.exposure.push(col);
      else if (['study_year', 'glp_compliant', 'source_database', 'test_type'].includes(val)) groups.metadata.push(col);
      else if (['biodegradation', 'half_life', 'bcf', 'koc'].includes(val)) groups.envfate.push(col);
      else if (['patient_id', 'age', 'sex', 'clinical_phase', 'adverse_event'].includes(val)) groups.clinical.push(col);
      else if (['clearance', 'bioavailability', 'cmax', 'tmax', 'vd'].includes(val)) groups.adme.push(col);
      else groups.unmapped.push(col);
    });
    return groups;
  }, [columns, mappings]);

  const renderColumnItem = (col: string) => {
    const mappedValue = mappings[col] || 'none';
    const isMapped = mappedValue !== 'none' && mappedValue !== undefined;
    const intel = intelligence[col] || {};
    
    return (
      <div key={col} className={`flex flex-col gap-4 p-5 rounded-2xl border transition-all duration-300 ${isMapped ? 'bg-white/[0.01] border-white/[0.08]' : 'bg-transparent border-white/[0.03] hover:border-white/[0.08]'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className={`w-4.5 h-4.5 ${isMapped ? 'text-cyan-400' : 'text-muted'}`} />
            <span className={`text-sm font-semibold tracking-tight ${isMapped ? 'text-white' : 'text-secondary'}`}>{col}</span>
          </div>

          <Select.Root value={mappedValue} onValueChange={(val) => handleSelect(col, val)}>
            <Select.Trigger className={`flex items-center justify-between w-64 px-3 py-2 rounded-xl text-xs font-semibold border transition-all outline-none focus:ring-2 focus:ring-cyan-500/30
              ${isMapped ? 'bg-cyan-500/10 border-cyan-500/25 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.05)]' : 'bg-white/[0.03] border-white/[0.06] text-secondary hover:bg-white/[0.06]'}
            `}>
              <Select.Value placeholder="Select Mapping..." />
              <Select.Icon><ChevronDown className="w-3.5 h-3.5 opacity-50" /></Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="overflow-hidden bg-[#0a0d18] border border-white/[0.08] rounded-2xl shadow-2xl z-50 animate-in fade-in">
                <Select.Viewport className="p-1">
                  {mapOptions.map(opt => (
                    <Select.Item key={opt.value} value={opt.value} className={`flex items-center px-4 py-2.5 text-xs font-semibold rounded-xl cursor-pointer outline-none select-none transition-colors ${opt.value === 'none' ? 'text-muted focus:bg-white/[0.04]' : 'text-secondary focus:bg-cyan-500/10 focus:text-cyan-400'}`}>
                      <Select.ItemText>{opt.label}</Select.ItemText>
                      <Select.ItemIndicator className="ml-auto"><Check className="w-3.5 h-3.5 text-cyan-400" /></Select.ItemIndicator>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>
        
        {isMapped && intel.confidence !== undefined && (
          <div className="border-t border-white/[0.04] pt-4 space-y-3">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 flex-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-muted w-16 shrink-0">AI Conf.</span>
                <div className="flex-1 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${intel.confidence > 0.8 ? 'bg-emerald-500' : intel.confidence > 0.5 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${intel.confidence * 100}%` }} />
                </div>
                <span className="text-xs font-mono text-secondary w-8 text-right shrink-0">{Math.round(intel.confidence * 100)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const AccordionSection = ({ title, icon: Icon, columns }: any) => {
    if (columns.length === 0) return null;
    return (
      <Accordion.Item value={title} className="glass rounded-[2rem] mb-4 border border-white/[0.06] overflow-hidden">
        <Accordion.Header>
          <Accordion.Trigger className="flex items-center justify-between w-full p-6 bg-white/[0.01] hover:bg-white/[0.02] transition-colors outline-none group">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400">
                <Icon className="w-5 h-5" />
              </div>
              <div className="text-left">
                <h3 className="text-white font-medium">{title}</h3>
                <p className="text-xs text-muted">{columns.length} Columns</p>
              </div>
            </div>
            <ChevronDown className="w-5 h-5 text-muted transition-transform duration-300 group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content className="p-6 pt-0 border-t border-white/[0.06] space-y-4 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in">
          {columns.map(renderColumnItem)}
        </Accordion.Content>
      </Accordion.Item>
    );
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-3">Variable Mapping</h1>
        <p className="text-secondary text-sm max-w-md mx-auto">
          Bind your dataset columns to toxicological primitives. SDO's mapping intelligence handles complex ecotox ontologies automatically.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <div className="glass p-5 rounded-2xl border-cyan-500/10 bg-cyan-500/[0.01] flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Inferred Dataset Type</span>
            <h4 className="text-sm font-bold text-white flex items-center gap-1.5 mt-1"><Award className="w-4 h-4 text-cyan-400 shrink-0" />{datasetClassification}</h4>
          </div>
        </div>
        <div className="glass p-5 rounded-2xl border-violet-500/10 bg-violet-500/[0.01] col-span-2">
          <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider block mb-1">Regulatory Standards Compatibility</span>
          <div className="flex flex-wrap gap-2 mt-2.5">
            <span className="px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[10px] font-medium text-white flex items-center gap-1"><Scale className="w-3 h-3 text-cyan-400" /> OECD Series</span>
            <span className="px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[10px] font-medium text-white flex items-center gap-1"><Scale className="w-3 h-3 text-violet-400" /> REACH / ECHA</span>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {safetyWarnings.length > 0 && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="glass p-5 rounded-2xl border-rose-500/20 bg-rose-500/[0.02] mb-6 shadow-[0_0_15px_rgba(244,63,94,0.1)]">
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4.5 h-4.5 text-rose-400 shrink-0 animate-pulse" />
              <h4 className="text-xs font-bold text-rose-400 uppercase tracking-wider">Toxicological Safety Alerts</h4>
            </div>
            <ul className="space-y-2 text-xs text-secondary leading-normal">
              {safetyWarnings.map((warning, index) => <li key={index} className="flex items-start gap-2"><span className="text-rose-500/80 mt-0.5">•</span><span>{warning}</span></li>)}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      <Accordion.Root type="multiple" defaultValue={['Unmapped Columns', 'Chemical Identifiers', 'Biological Endpoints']}>
        <AccordionSection title="Unmapped Columns" icon={Layers} columns={columnGroups.unmapped} />
        <AccordionSection title="Chemical Identifiers" icon={Fingerprint} columns={columnGroups.identifiers} />
        <AccordionSection title="Physicochemical Properties" icon={Beaker} columns={columnGroups.physchem} />
        <AccordionSection title="Biological Endpoints" icon={Activity} columns={columnGroups.endpoints} />
        <AccordionSection title="Organism & Taxonomy" icon={Dna} columns={columnGroups.taxonomy} />
        <AccordionSection title="Exposure Metrics" icon={Timer} columns={columnGroups.exposure} />
        <AccordionSection title="Environmental Fate" icon={Compass} columns={columnGroups.envfate} />
        <AccordionSection title="Pharmacokinetics & ADME" icon={Zap} columns={columnGroups.adme} />
        <AccordionSection title="Clinical Research" icon={ShieldAlert} columns={columnGroups.clinical} />
        <AccordionSection title="Experimental Metadata" icon={FileText} columns={columnGroups.metadata} />
        <AccordionSection title="Ignored Columns" icon={Link2} columns={columnGroups.ignored} />
      </Accordion.Root>

      <div className="flex justify-end mt-8">
        <button onClick={handleSaveMappings} className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-white font-bold text-sm shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all">
          Confirm & Proceed <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
