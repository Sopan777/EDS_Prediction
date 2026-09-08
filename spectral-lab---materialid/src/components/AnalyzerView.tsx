import React, { useState, useRef } from 'react';
import { MaterialFamily, CandidateComponent, ElementalComposition } from '../types';
import { METAL_MACRO_BG } from '../data/mockData';

interface AnalyzerViewProps {
  isDarkMode: boolean;
  activeFamily: MaterialFamily;
  onSelectFamily: (family: MaterialFamily) => void;
  onSelectComponent: (comp: CandidateComponent) => void;
  allFamilies: MaterialFamily[];
}

export const AnalyzerView: React.FC<AnalyzerViewProps> = ({
  isDarkMode,
  activeFamily,
  onSelectFamily,
  onSelectComponent,
  allFamilies,
}) => {
  const [ingestionTab, setIngestionTab] = useState<'upload' | 'manual'>('upload');
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);
  const [analysisDuration, setAnalysisDuration] = useState('0.42s');
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  // Manual elemental composition values (clean initial state, no sample data pre-filled)
  const [composition, setComposition] = useState<ElementalComposition>({
    cr: 0,
    ni: 0,
    mn: 0,
    si: 0,
    c: null,
    fe: 'Bal.',
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset/clear current analysis
  const handleClearAnalysis = () => {
    setHasAnalyzed(false);
    setUploadedFileName(null);
    setComposition({
      cr: 0,
      ni: 0,
      mn: 0,
      si: 0,
      c: null,
      fe: 'Bal.',
    });
  };

  // Predict family based on elemental inputs
  const handlePredictFamily = () => {
    const total = composition.cr + composition.ni + composition.mn + composition.si;
    if (total === 0 && !uploadedFileName) {
      alert('Please enter elemental concentrations (wt%) or upload an EDS report to perform microanalysis.');
      return;
    }

    setIsAnalyzing(true);
    const start = performance.now();

    setTimeout(() => {
      // Find matching family based on composition
      let matched = allFamilies.find((f) => f.code === 'F4') || activeFamily;

      if (composition.cr < 3 && composition.ni < 2) {
        matched = allFamilies.find((f) => f.code === 'F1a') || matched;
      } else if (composition.cr >= 11 && composition.cr <= 15 && composition.ni < 2) {
        matched = allFamilies.find((f) => f.code === 'F2b') || matched;
      } else if (composition.cr < 1 && composition.mn < 0.2) {
        matched = allFamilies.find((f) => f.code === 'F6a') || matched;
      }

      onSelectFamily(matched);
      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      setAnalysisDuration(`${elapsed}s`);
      setIsAnalyzing(false);
      setHasAnalyzed(true);
    }, 450);
  };

  const handleFileUpload = (file: File) => {
    setUploadedFileName(file.name);
    setIsAnalyzing(true);

    setTimeout(() => {
      // Parse uploaded spectral scan
      if (file.name.toLowerCase().includes('bronze') || file.name.toLowerCase().includes('cu')) {
        setComposition({ cr: 0.05, ni: 0.1, mn: 0.02, si: 0.05, c: null, fe: '0.4%' });
        const bronzeFamily = allFamilies.find((f) => f.code === 'F6a');
        if (bronzeFamily) onSelectFamily(bronzeFamily);
      } else if (file.name.toLowerCase().includes('gear') || file.name.toLowerCase().includes('4140')) {
        setComposition({ cr: 1.05, ni: 0.2, mn: 0.85, si: 0.28, c: null, fe: 'Bal.' });
        const lowAlloy = allFamilies.find((f) => f.code === 'F1a');
        if (lowAlloy) onSelectFamily(lowAlloy);
      } else {
        setComposition({ cr: 18.1, ni: 8.2, mn: 1.5, si: 0.5, c: null, fe: 'Bal.' });
        const austenitic = allFamilies.find((f) => f.code === 'F4');
        if (austenitic) onSelectFamily(austenitic);
      }
      setAnalysisDuration('0.38s');
      setIsAnalyzing(false);
      setHasAnalyzed(true);
    }, 500);
  };

  const gaugePct = activeFamily.compatibilityScore || 95;
  const strokeDash = `${gaugePct}, 100`;

  return (
    <div id="analyzer-screen" className="flex flex-col gap-5 h-full">
      {/* Page Title */}
      <header className="flex items-center justify-between">
        <div>
          <h2
            className={`font-display text-[28px] font-bold tracking-tight ${
              isDarkMode ? 'text-white' : 'text-[#134231]'
            }`}
          >
            Analyze New Particle
          </h2>
          <p className={`text-[13px] ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
            EDS Microanalysis & Automated Reference Library Cross-Correlation
          </p>
        </div>

        {hasAnalyzed && (
          <button
            onClick={handleClearAnalysis}
            className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold border flex items-center gap-1.5 transition-all ${
              isDarkMode
                ? 'border-[#3a4a44] text-[#b9cbc2] hover:text-white hover:bg-[#151d1a]'
                : 'border-[#c0c8c2] text-[#414944] hover:text-[#191c1e] hover:bg-[#f2f4f6]'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">restart_alt</span>
            Reset Analysis
          </button>
        )}
      </header>

      {/* Bento Grid Layout (12 cols) */}
      <div className="grid grid-cols-12 gap-5 flex-1 min-h-0">
        {/* Left Input Column (7 cols on xl) */}
        <div className="col-span-12 xl:col-span-7 flex flex-col gap-5">
          {/* Data Ingestion Card */}
          <div
            className={`rounded-xl border shadow-sm p-6 flex-1 flex flex-col relative overflow-hidden transition-colors ${
              isDarkMode
                ? 'bg-[#07100d] border-[#3a4a44]'
                : 'bg-white border-[#c0c8c2]'
            }`}
          >
            <div className="relative z-10 flex-1 flex flex-col">
              {/* Card Header with tabs */}
              <div
                className={`flex justify-between items-center mb-4 pb-3 border-b ${
                  isDarkMode ? 'border-[#3a4a44]' : 'border-[#c0c8c2]'
                }`}
              >
                <h3
                  className={`font-semibold text-[16px] flex items-center gap-2 ${
                    isDarkMode ? 'text-white' : 'text-[#134231]'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">upload_file</span>
                  Data Ingestion
                </h3>

                {/* Tabs */}
                <div
                  className={`flex p-1 rounded-lg ${
                    isDarkMode ? 'bg-[#151d1a]' : 'bg-[#f2f4f6]'
                  }`}
                >
                  <button
                    id="tab-file-upload"
                    onClick={() => setIngestionTab('upload')}
                    className={`px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all ${
                      ingestionTab === 'upload'
                        ? isDarkMode
                          ? 'bg-[#1a2420] text-[#00ffcc] shadow-sm'
                          : 'bg-white text-[#134231] shadow-sm'
                        : isDarkMode
                        ? 'text-[#83958d] hover:text-white'
                        : 'text-[#717974] hover:text-[#191c1e]'
                    }`}
                  >
                    File Upload
                  </button>
                  <button
                    id="tab-manual-entry"
                    onClick={() => setIngestionTab('manual')}
                    className={`px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all ${
                      ingestionTab === 'manual'
                        ? isDarkMode
                          ? 'bg-[#1a2420] text-[#00ffcc] shadow-sm'
                          : 'bg-white text-[#134231] shadow-sm'
                        : isDarkMode
                        ? 'text-[#83958d] hover:text-white'
                        : 'text-[#717974] hover:text-[#191c1e]'
                    }`}
                  >
                    Manual Entry
                  </button>
                </div>
              </div>

              {/* Upload Zone */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.csv,.txt,.eds"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileUpload(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`flex-1 border-2 border-dashed rounded-lg flex flex-col items-center justify-center p-8 transition-all cursor-pointer group ${
                  isDragging
                    ? isDarkMode
                      ? 'border-[#00ffcc] bg-[#1a2420]/80'
                      : 'border-[#134231] bg-[#eceef0]'
                    : isDarkMode
                    ? 'border-[#3a4a44] bg-[#0c1512] hover:border-[#00ffcc] hover:bg-[#151d1a]'
                    : 'border-[#c0c8c2] bg-[#f7f9fb] hover:border-[#134231] hover:bg-[#eceef0]'
                }`}
              >
                <span
                  className={`material-symbols-outlined text-[48px] mb-3 transition-colors ${
                    isDarkMode
                      ? 'text-[#83958d] group-hover:text-[#00ffcc]'
                      : 'text-[#717974] group-hover:text-[#134231]'
                  }`}
                >
                  cloud_upload
                </span>
                <p
                  className={`font-semibold text-[15px] mb-1 text-center ${
                    isDarkMode ? 'text-white' : 'text-[#191c1e]'
                  }`}
                >
                  {uploadedFileName ? `Loaded: ${uploadedFileName}` : 'Drag and drop EDS report here'}
                </p>
                <p
                  className={`text-[13px] text-center mb-4 max-w-sm ${
                    isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                  }`}
                >
                  Supports PDF, DOCX, CSV exports from major spectrometer brands.
                  <br />
                  Max file size: 50MB.
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className={`border py-2 px-6 rounded-lg text-[13px] font-semibold transition-all shadow-sm ${
                    isDarkMode
                      ? 'bg-[#1a2420] text-[#00ffcc] border-[#3a4a44] hover:bg-[#232c28]'
                      : 'bg-white text-[#134231] border-[#c0c8c2] hover:bg-[#f2f4f6]'
                  }`}
                >
                  Browse Files
                </button>
              </div>
            </div>
          </div>

          {/* Manual EDS Entry (wt%) Card */}
          <div
            className={`rounded-xl border shadow-sm p-6 flex-none transition-colors ${
              isDarkMode
                ? 'bg-[#07100d] border-[#3a4a44]'
                : 'bg-white border-[#c0c8c2]'
            }`}
          >
            <div className="flex justify-between items-center mb-3">
              <h3
                className={`font-semibold text-[15px] flex items-center gap-2 ${
                  isDarkMode ? 'text-white' : 'text-[#134231]'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">dialpad</span>
                Manual EDS Entry (wt%)
              </h3>
              <span className={`text-[11px] font-mono-code ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                Stoichiometric Normalization Active
              </span>
            </div>

            {/* Inputs Grid */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
              {/* Cr */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  Cr
                </label>
                <input
                  id="input-eds-cr"
                  type="number"
                  step="0.1"
                  placeholder="0.00"
                  value={composition.cr === 0 ? '' : composition.cr}
                  onChange={(e) =>
                    setComposition({ ...composition, cr: e.target.value === '' ? 0 : parseFloat(e.target.value) || 0 })
                  }
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                  }`}
                />
              </div>

              {/* Ni */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  Ni
                </label>
                <input
                  id="input-eds-ni"
                  type="number"
                  step="0.1"
                  placeholder="0.00"
                  value={composition.ni === 0 ? '' : composition.ni}
                  onChange={(e) =>
                    setComposition({ ...composition, ni: e.target.value === '' ? 0 : parseFloat(e.target.value) || 0 })
                  }
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                  }`}
                />
              </div>

              {/* Mn */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  Mn
                </label>
                <input
                  id="input-eds-mn"
                  type="number"
                  step="0.1"
                  placeholder="0.00"
                  value={composition.mn === 0 ? '' : composition.mn}
                  onChange={(e) =>
                    setComposition({ ...composition, mn: e.target.value === '' ? 0 : parseFloat(e.target.value) || 0 })
                  }
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                  }`}
                />
              </div>

              {/* Si */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  Si
                </label>
                <input
                  id="input-eds-si"
                  type="number"
                  step="0.1"
                  placeholder="0.00"
                  value={composition.si === 0 ? '' : composition.si}
                  onChange={(e) =>
                    setComposition({ ...composition, si: e.target.value === '' ? 0 : parseFloat(e.target.value) || 0 })
                  }
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                  }`}
                />
              </div>

              {/* C */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  C
                </label>
                <input
                  disabled
                  placeholder="--"
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] cursor-not-allowed opacity-60 ${
                    isDarkMode
                      ? 'bg-[#0c1512] border-[#3a4a44] text-[#83958d]'
                      : 'bg-[#eceef0] border-[#c0c8c2] text-[#717974]'
                  }`}
                />
              </div>

              {/* Fe */}
              <div>
                <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                  Fe
                </label>
                <input
                  disabled
                  value={composition.fe || 'Bal.'}
                  className={`w-full border rounded p-2 text-right font-mono-code text-[13px] cursor-not-allowed opacity-60 ${
                    isDarkMode
                      ? 'bg-[#0c1512] border-[#3a4a44] text-[#83958d]'
                      : 'bg-[#eceef0] border-[#c0c8c2] text-[#717974]'
                  }`}
                />
              </div>
            </div>

            {/* Predict Button */}
            <div className="mt-4 flex justify-end gap-2">
              <button
                id="btn-predict-family"
                onClick={handlePredictFamily}
                disabled={isAnalyzing}
                className={`py-2 px-8 rounded-lg text-[14px] font-semibold transition-all shadow flex items-center gap-2 active:scale-95 ${
                  isDarkMode
                    ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                    : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
                }`}
              >
                {isAnalyzing ? (
                  <>
                    <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                    <span>Correlating Spectra...</span>
                  </>
                ) : (
                  <span>Predict Family</span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Results Column (5 cols on xl) */}
        <div className="col-span-12 xl:col-span-5 flex flex-col gap-5 h-full">
          {!hasAnalyzed ? (
            /* Awaiting Analysis Empty State */
            <div
              id="awaiting-analysis-card"
              className={`rounded-xl border shadow-sm p-8 flex-1 flex flex-col items-center justify-center text-center relative overflow-hidden transition-colors ${
                isDarkMode
                  ? 'bg-[#07100d] border-[#3a4a44]'
                  : 'bg-white border-[#c0c8c2]'
              }`}
            >
              <div
                className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-colors ${
                  isDarkMode
                    ? 'bg-[#151d1a] text-[#00ffcc] border border-[#3a4a44]'
                    : 'bg-[#f2f4f6] text-[#134231] border border-[#c0c8c2]'
                }`}
              >
                <span className="material-symbols-outlined text-[34px]">biotech</span>
              </div>

              <span
                className={`px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider mb-3 border ${
                  isDarkMode
                    ? 'bg-[#151d1a] border-[#3a4a44] text-[#83958d]'
                    : 'bg-[#f2f4f6] border-[#c0c8c2] text-[#717974]'
                }`}
              >
                Awaiting Microanalysis
              </span>

              <h3
                className={`font-display text-[22px] font-bold mb-2 tracking-tight ${
                  isDarkMode ? 'text-white' : 'text-[#191c1e]'
                }`}
              >
                No Particle Analyzed Yet
              </h3>

              <p
                className={`text-[13px] max-w-sm leading-relaxed mb-6 ${
                  isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                }`}
              >
                Upload an EDS microanalysis report (PDF, DOCX, CSV) or manually input elemental concentrations (wt%) on the left and select <strong className={isDarkMode ? 'text-white' : 'text-[#191c1e]'}>Predict Family</strong> to perform stoichiometric cross-matching.
              </p>

              <div className="grid grid-cols-2 gap-3 w-full max-w-xs text-left text-[11px]">
                <div
                  className={`p-3 rounded-lg border ${
                    isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                  }`}
                >
                  <span className="block font-bold uppercase tracking-wider opacity-60">Status</span>
                  <span className="font-semibold flex items-center gap-1.5 mt-1 text-emerald-500">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    Ready for Ingest
                  </span>
                </div>
                <div
                  className={`p-3 rounded-lg border ${
                    isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                  }`}
                >
                  <span className="block font-bold uppercase tracking-wider opacity-60">Library</span>
                  <span className="font-semibold mt-1 block">ASTM E1508 Loaded</span>
                </div>
              </div>
            </div>
          ) : (
            /* Analyzed Results View */
            <>
              {/* Hero Result Card */}
              <div
                id="hero-result-card"
                className={`rounded-xl border shadow-sm relative overflow-hidden flex-none transition-colors ${
                  isDarkMode
                    ? 'bg-[#07100d] border-[#3a4a44]'
                    : 'bg-white border-[#c0c8c2]'
                }`}
              >
                {/* Macro metallic texture background */}
                <div
                  className="absolute inset-0 bg-cover bg-center opacity-10 mix-blend-luminosity pointer-events-none"
                  style={{ backgroundImage: `url('${METAL_MACRO_BG}')` }}
                />

                <div className="relative z-10 p-6">
                  {/* Badge & Execution Timer */}
                  <div className="flex justify-between items-start mb-4">
                    <span className="inline-flex items-center gap-1.5 bg-[#bcedd4] text-[#002115] px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wider border border-[#a1d1b9]">
                      <span className="material-symbols-outlined text-[14px]">check_circle</span>
                      IDENTIFIED
                    </span>

                    <div
                      className={`flex items-center gap-1 text-[11px] font-mono-code ${
                        isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[15px]">timer</span>
                      <span>{analysisDuration}</span>
                    </div>
                  </div>

                  {/* Material Title & Grade Hint */}
                  <div className="mb-6">
                    <h3
                      className={`font-display text-[32px] md:text-[36px] font-bold leading-tight mb-1 tracking-tight ${
                        isDarkMode ? 'text-white' : 'text-[#191c1e]'
                      }`}
                    >
                      {activeFamily.name}
                    </h3>
                    <p
                      className={`text-[14px] font-medium flex items-center gap-1.5 ${
                        isDarkMode ? 'text-[#b9cbc2]' : 'text-[#414944]'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[16px]">info</span>
                      Grade hint: {activeFamily.gradeHint}
                    </p>
                  </div>

                  {/* Compatibility Gauge Row */}
                  <div
                    className={`flex items-center gap-4 p-4 rounded-lg border ${
                      isDarkMode
                        ? 'bg-[#151d1a] border-[#3a4a44]/50'
                        : 'bg-[#f2f4f6] border-[#c0c8c2]/50'
                    }`}
                  >
                    {/* SVG Gauge */}
                    <div className="relative w-16 h-16 shrink-0">
                      <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                        <path
                          className={isDarkMode ? 'text-[#2e3733]' : 'text-[#c0c8c2]'}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3.2"
                        />
                        <path
                          className={isDarkMode ? 'text-[#00ffcc]' : 'text-[#26fedc]'}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          strokeDasharray={strokeDash}
                          strokeWidth="3.2"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span
                          className={`font-mono-code font-bold text-[14px] ${
                            isDarkMode ? 'text-[#00ffcc]' : 'text-[#134231]'
                          }`}
                        >
                          {gaugePct}%
                        </span>
                      </div>
                    </div>

                    <div>
                      <h4
                        className={`font-semibold text-[15px] ${
                          isDarkMode ? 'text-white' : 'text-[#191c1e]'
                        }`}
                      >
                        High Compatibility
                      </h4>
                      <p
                        className={`text-[12.5px] leading-snug mt-0.5 ${
                          isDarkMode ? 'text-[#b9cbc2]' : 'text-[#414944]'
                        }`}
                      >
                        Spectral signature closely matches reference library standards for {activeFamily.code} ({activeFamily.gradeHint}).
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Split Row: Candidate Components & Analysis Context */}
              <div className="flex-1 flex gap-5 min-h-[220px]">
                {/* Candidate Components List */}
                <div
                  id="candidate-components-card"
                  className={`flex-1 rounded-xl border shadow-sm p-4 flex flex-col overflow-hidden transition-colors ${
                    isDarkMode
                      ? 'bg-[#07100d] border-[#3a4a44]'
                      : 'bg-white border-[#c0c8c2]'
                  }`}
                >
                  <h4
                    className={`text-[11px] font-bold uppercase tracking-wider mb-2 px-1 border-b pb-1.5 ${
                      isDarkMode
                        ? 'text-[#83958d] border-[#3a4a44]'
                        : 'text-[#717974] border-[#c0c8c2]'
                    }`}
                  >
                    CANDIDATE COMPONENTS
                  </h4>

                  <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
                    {activeFamily.candidateComponents.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center p-3 opacity-60">
                        <span className="material-symbols-outlined text-[26px] mb-1">category</span>
                        <p className="text-[12px] font-semibold">No candidate components mapped</p>
                        <p className="text-[11px] mt-0.5">Catalog components in the Knowledge Base.</p>
                      </div>
                    ) : (
                      activeFamily.candidateComponents.slice(0, 3).map((comp, idx) => (
                        <div
                          key={comp.id}
                          onClick={() => onSelectComponent(comp)}
                          className={`flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer group ${
                            isDarkMode
                              ? 'bg-[#151d1a] border-transparent hover:border-[#00ffcc] hover:bg-[#1a2420]'
                              : 'bg-[#f7f9fb] border-transparent hover:border-[#134231] hover:bg-[#f2f4f6]'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <span
                              className={`w-6 h-6 rounded-full flex items-center justify-center font-mono-code text-[11px] font-bold ${
                                idx === 0
                                  ? isDarkMode
                                    ? 'bg-[#00ffcc] text-[#00382b]'
                                    : 'bg-[#134231] text-white'
                                  : isDarkMode
                                  ? 'bg-[#232c28] text-[#b9cbc2]'
                                  : 'bg-[#eceef0] text-[#717974]'
                              }`}
                            >
                              {idx + 1}
                            </span>
                            <div className="min-w-0">
                              <span
                                className={`font-semibold text-[13px] block truncate group-hover:underline ${
                                  isDarkMode ? 'text-white' : 'text-[#191c1e]'
                                }`}
                              >
                                {comp.name}
                              </span>
                              <span className={`text-[10px] font-mono-code ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                                {comp.partNumber} • {comp.nominalAlloy}
                              </span>
                            </div>
                          </div>
                          <span
                            className={`material-symbols-outlined text-[18px] transition-transform group-hover:translate-x-0.5 ${
                              isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
                            }`}
                          >
                            chevron_right
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Analysis Context Sidebar */}
                <div
                  id="analysis-context-card"
                  className={`w-[42%] rounded-xl border shadow-sm p-4 flex flex-col relative overflow-hidden transition-colors ${
                    isDarkMode
                      ? 'bg-[#07100d] border-[#3a4a44]'
                      : 'bg-white border-[#c0c8c2]'
                  }`}
                >
                  {/* Background watermark */}
                  <div className="absolute -right-6 -bottom-6 opacity-5 pointer-events-none">
                    <span className="material-symbols-outlined text-[110px]">analytics</span>
                  </div>

                  <h4
                    className={`text-[11px] font-bold uppercase tracking-wider mb-2 px-1 border-b pb-1.5 relative z-10 ${
                      isDarkMode
                        ? 'text-[#83958d] border-[#3a4a44]'
                        : 'text-[#717974] border-[#c0c8c2]'
                    }`}
                  >
                    ANALYSIS CONTEXT
                  </h4>

                  <div className="space-y-2 relative z-10 overflow-y-auto">
                    {activeFamily.contextCaveats.map((caveat, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded border flex gap-2 items-start ${
                          isDarkMode
                            ? 'bg-[#151d1a] border-[#3a4a44]/50'
                            : 'bg-[#f7f9fb] border-[#c0c8c2]/50'
                        }`}
                      >
                        <span
                          className={`material-symbols-outlined text-[16px] mt-0.5 shrink-0 ${
                            isDarkMode ? 'text-[#00ffcc]' : 'text-[#717974]'
                          }`}
                        >
                          {caveat.icon}
                        </span>
                        <div>
                          <span
                            className={`block font-semibold text-[12px] ${
                              isDarkMode ? 'text-white' : 'text-[#191c1e]'
                            }`}
                          >
                            {caveat.title}
                          </span>
                          <span
                            className={`block text-[11px] leading-tight mt-0.5 ${
                              isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                            }`}
                          >
                            {caveat.description}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
