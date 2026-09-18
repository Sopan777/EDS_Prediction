import React, { useState, useRef } from 'react';
import { MaterialFamily, CandidateComponent, ElementalComposition } from '../types';

interface AnalyzerViewProps {
  isDarkMode: boolean;
  activeFamily: MaterialFamily | null;
  onSelectFamily: (family: MaterialFamily) => void;
  onSelectComponent: (comp: CandidateComponent) => void;
  allFamilies: MaterialFamily[];
  onAnalysisComplete?: () => void;
}

export const AnalyzerView: React.FC<AnalyzerViewProps> = ({
  isDarkMode,
  activeFamily,
  onSelectFamily,
  onSelectComponent,
  allFamilies,
  onAnalysisComplete,
}) => {
  const [ingestionTab, setIngestionTab] = useState<'upload' | 'manual'>('upload');
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);
  const [analysisDuration, setAnalysisDuration] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [lastDecision, setLastDecision] = useState<'identified' | 'ambiguous' | 'unknown'>('identified');
  const [lastReason, setLastReason] = useState<string>('');
  const [extraElements, setExtraElements] = useState<{ [elem: string]: number }>({});
  const [showAddElement, setShowAddElement] = useState(false);
  const [selectedNewElement, setSelectedNewElement] = useState('Mo');
  const [newElementVal, setNewElementVal] = useState('');

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
    setLastDecision('identified');
    setLastReason('');
    setExtraElements({});
    setComposition({
      cr: 0,
      ni: 0,
      mn: 0,
      si: 0,
      c: null,
      fe: 'Bal.',
    });
  };

  // Predict family based on elemental inputs using Python rule engine
  const handlePredictFamily = async () => {
    const totalExtra = Object.values(extraElements).reduce((a, b) => a + b, 0);
    const total = composition.cr + composition.ni + composition.mn + composition.si + totalExtra;
    if (total === 0 && !uploadedFileName) {
      alert('Please enter elemental concentrations (wt%) or upload an EDS report to perform microanalysis.');
      return;
    }

    setIsAnalyzing(true);
    const start = performance.now();

    const payload: Record<string, any> = {
      Cr: composition.cr,
      Ni: composition.ni,
      Mn: composition.mn,
      Si: composition.si,
      Fe: composition.fe || 'Bal.',
      ...extraElements,
    };

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composition: payload }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Prediction failed');
        setIsAnalyzing(false);
        return;
      }

      if (data.topFamily) {
        const updatedFam: MaterialFamily = {
          ...data.topFamily,
          compatibilityScore: data.compatibilityPct ?? data.topFamily.compatibilityScore,
          candidateComponents: data.candidateComponents?.length ? data.candidateComponents : data.topFamily.candidateComponents,
        };
        onSelectFamily(updatedFam);
      }
      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      setAnalysisDuration(data.processingTime || `${elapsed}s`);
      setLastDecision(data.decision || 'identified');
      setLastReason(data.reason || '');
      setHasAnalyzed(true);
      onAnalysisComplete?.();
    } catch (err) {
      console.error('Analysis error:', err);
      alert('Connection error communicating with rule engine API.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploadedFileName(file.name);
    setIsAnalyzing(true);
    const start = performance.now();

    const fd = new FormData();
    fd.append('file', file);

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'File extraction failed');
        setIsAnalyzing(false);
        return;
      }

      // Populate composition inputs with extracted values from report
      if (data.extractedComposition) {
        const ext = data.extractedComposition;
        setComposition({
          cr: ext.Cr || 0,
          ni: ext.Ni || 0,
          mn: ext.Mn || 0,
          si: ext.Si || 0,
          c: ext.C !== undefined ? ext.C : null,
          fe: ext.Fe !== undefined ? `${ext.Fe}%` : 'Bal.',
        });

        const extras: Record<string, number> = {};
        for (const [k, v] of Object.entries(ext)) {
          if (!['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k) && typeof v === 'number') {
            extras[k] = v;
          }
        }
        setExtraElements(extras);
      }

      if (data.topFamily) {
        const updatedFam: MaterialFamily = {
          ...data.topFamily,
          compatibilityScore: data.compatibilityPct ?? data.topFamily.compatibilityScore,
          candidateComponents: data.candidateComponents?.length ? data.candidateComponents : data.topFamily.candidateComponents,
        };
        onSelectFamily(updatedFam);
      }
      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      setAnalysisDuration(data.processingTime || `${elapsed}s`);
      setLastDecision(data.decision || 'identified');
      setLastReason(data.reason || '');
      setHasAnalyzed(true);
      onAnalysisComplete?.();
    } catch (err) {
      console.error('File analysis error:', err);
      alert('Error uploading and analyzing spectral report.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAddExtraElement = (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(newElementVal);
    if (!isNaN(val) && selectedNewElement) {
      setExtraElements((prev) => ({
        ...prev,
        [selectedNewElement]: val,
      }));
      setNewElementVal('');
      setShowAddElement(false);
    }
  };

  const handleRemoveExtraElement = (el: string) => {
    setExtraElements((prev) => {
      const copy = { ...prev };
      delete copy[el];
      return copy;
    });
  };

  const gaugePct = activeFamily?.compatibilityScore ?? (lastDecision === 'unknown' ? 0 : 95);
  const strokeDash = `${gaugePct}, 100`;

  return (
    <div id="analyzer-screen" className="flex flex-col gap-5 h-full">
      {/* Page Title */}
      <header className="flex items-center justify-between">
        <div>
          <h2
            className="type-display font-bold tracking-tight"
            style={{ color: 'var(--color-text-primary)', fontSize: '28px' }}
          >
            Analyze New Particle
          </h2>
          <p className="type-body" style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>
            EDS Microanalysis &amp; Automated Reference Library Cross-Correlation
          </p>
        </div>

        {hasAnalyzed && (
          <button
            onClick={handleClearAnalysis}
            className="press-target px-3 py-1.5 rounded-lg text-[12px] font-semibold border flex items-center gap-1.5 transition-all"
            style={{
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)',
              background: 'transparent',
            }}
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
            className="rounded-xl border shadow-sm p-6 flex-1 flex flex-col relative overflow-hidden transition-colors"
            style={{
              background: 'var(--color-bg-card)',
              borderColor: 'var(--color-border)',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <div className="relative z-10 flex-1 flex flex-col">
              {/* Card Header with tabs */}
              <div
                className="flex justify-between items-center mb-4 pb-3 border-b"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <h3
                  className="font-semibold text-[16px] flex items-center gap-2"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  <span className="material-symbols-outlined text-[20px]">upload_file</span>
                  Data Ingestion
                </h3>

                {/* Tabs */}
                <div
                  className="flex p-1 rounded-lg"
                  style={{ background: 'var(--color-bg-elevated)' }}
                >
                  <button
                    id="tab-file-upload"
                    onClick={() => setIngestionTab('upload')}
                    className="press-target px-3 py-1 text-[11px] font-bold uppercase tracking-wider transition-all"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      ...(ingestionTab === 'upload'
                        ? {
                            background: 'var(--color-accent)',
                            color: 'var(--color-accent-on)',
                            boxShadow: 'var(--shadow-sm)',
                          }
                        : {
                            background: 'transparent',
                            color: 'var(--color-text-secondary)',
                          }),
                    }}
                  >
                    File Upload
                  </button>
                  <button
                    id="tab-manual-entry"
                    onClick={() => setIngestionTab('manual')}
                    className="press-target px-3 py-1 text-[11px] font-bold uppercase tracking-wider transition-all"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      ...(ingestionTab === 'manual'
                        ? {
                            background: 'var(--color-accent)',
                            color: 'var(--color-accent-on)',
                            boxShadow: 'var(--shadow-sm)',
                          }
                        : {
                            background: 'transparent',
                            color: 'var(--color-text-secondary)',
                          }),
                    }}
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
                className="flex-1 border-2 border-dashed rounded-lg flex flex-col items-center justify-center p-8 cursor-pointer group"
                style={{
                  borderColor: isDragging ? 'var(--color-accent)' : 'var(--color-border-strong)',
                  background: isDragging ? 'var(--color-accent-subtle)' : 'var(--color-bg-base)',
                  transform: isDragging ? 'scale(1.01)' : 'scale(1)',
                  transition: 'all 200ms var(--ease-out-expo)',
                }}
              >
                <span
                  className="material-symbols-outlined text-[48px] mb-3 transition-colors"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  cloud_upload
                </span>
                <p
                  className="font-semibold text-[15px] mb-1 text-center"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {uploadedFileName ? `Loaded: ${uploadedFileName}` : 'Drag and drop EDS report here'}
                </p>
                <p
                  className="text-[13px] text-center mb-4 max-w-sm"
                  style={{ color: 'var(--color-text-secondary)' }}
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
                  className="press-target border py-2 px-6 rounded-lg text-[13px] font-semibold transition-all shadow-sm"
                  style={{
                    background: 'var(--color-bg-elevated)',
                    color: 'var(--color-accent)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  Browse Files
                </button>
              </div>
            </div>
          </div>

          {/* Manual EDS Entry (wt%) Card */}
          <div
            className="border p-6 flex-none transition-colors"
            style={{
              background: 'var(--color-bg-card)',
              borderColor: 'var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <div className="flex justify-between items-center mb-3">
              <h3 className="type-headline flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                <span className="material-symbols-outlined text-[18px]" style={{ color: 'var(--color-accent)' }}>dialpad</span>
                Manual EDS Entry (wt%)
              </h3>
              <span className="type-caption type-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                Stoichiometric Normalization Active
              </span>
            </div>

            {/* Inputs Grid */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
              {/* Cr */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
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
                  className="w-full border p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>

              {/* Ni */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
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
                  className="w-full border p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>

              {/* Mn */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
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
                  className="w-full border p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>

              {/* Si */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
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
                  className="w-full border p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>

              {/* C */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  C
                </label>
                <input
                  disabled
                  placeholder="--"
                  className="w-full border p-2 text-right font-mono-code text-[13px] cursor-not-allowed opacity-60"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-tertiary)',
                  }}
                />
              </div>

              {/* Fe */}
              <div>
                <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Fe
                </label>
                <input
                  disabled
                  value={composition.fe || 'Bal.'}
                  className="w-full border p-2 text-right font-mono-code text-[13px] cursor-not-allowed opacity-60"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-tertiary)',
                  }}
                />
              </div>
            </div>


            {/* Extra Dynamic Elements (e.g. Mo, Cu, Sn, Zn, etc.) */}
            {Object.keys(extraElements).length > 0 && (
              <div className="mt-3 pt-3 border-t border-inherit">
                <span className={`block text-[11px] font-bold uppercase tracking-wider mb-2 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                  Additional Elements Measured (wt%)
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                  {Object.entries(extraElements).map(([elem, val]) => (
                    <div key={elem} className="relative group">
                      <div className="flex justify-between items-center mb-1">
                        <label className={`text-[11px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-[#00ffcc]' : 'text-[#134231]'}`}>
                          {elem}
                        </label>
                        <button
                          type="button"
                          onClick={() => handleRemoveExtraElement(elem)}
                          className="text-[11px] text-rose-500 hover:text-rose-700 opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Remove element"
                        >
                          ✕
                        </button>
                      </div>
                      <input
                        type="number"
                        step="0.01"
                        value={val}
                        onChange={(e) =>
                          setExtraElements({
                            ...extraElements,
                            [elem]: parseFloat(e.target.value) || 0,
                          })
                        }
                        className={`w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium focus:outline-none transition-colors ${
                          isDarkMode
                            ? 'bg-[#151d1a] border-[#00ffcc]/40 text-[#dbe5df] focus:border-[#00ffcc]'
                            : 'bg-[#f7f9fb] border-[#134231]/40 text-[#191c1e] focus:border-[#134231]'
                        }`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Add Element Inline Form & Predict Button Row */}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                {!showAddElement ? (
                  <button
                    type="button"
                    onClick={() => setShowAddElement(true)}
                    className="press-target text-[12px] font-semibold flex items-center gap-1 transition-colors"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    <span className="material-symbols-outlined text-[16px]">add_circle</span>
                    Add Element (Mo, Cu, Sn, Al, Zn...)
                  </button>
                ) : (
                  <form onSubmit={handleAddExtraElement} className="flex items-center gap-2">
                    <select
                      value={selectedNewElement}
                      onChange={(e) => setSelectedNewElement(e.target.value)}
                      className="text-[12px] border px-2 py-1 focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      {['Mo', 'Cu', 'Sn', 'Al', 'Zn', 'W', 'V', 'Ti', 'Nb', 'Co', 'P', 'S', 'Pb', 'Au'].map((el) => (
                        <option key={el} value={el}>
                          {el}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="wt%"
                      value={newElementVal}
                      onChange={(e) => setNewElementVal(e.target.value)}
                      className="w-20 text-[12px] border px-2 py-1 text-right focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                    <button
                      type="submit"
                      className="press-target px-2.5 py-1 text-[12px] font-semibold"
                      style={{
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-accent)',
                        color: 'var(--color-accent-on)',
                      }}
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowAddElement(false)}
                      className="press-target px-2 py-1 text-[12px] opacity-60 hover:opacity-100"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      Cancel
                    </button>
                  </form>
                )}
              </div>

              <button
                id="btn-predict-family"
                onClick={handlePredictFamily}
                disabled={isAnalyzing}
                className="press-target py-2 px-8 text-[14px] font-semibold transition-all shadow flex items-center gap-2"
                style={{
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-accent)',
                  color: 'var(--color-accent-on)',
                  opacity: isAnalyzing ? 0.7 : 1,
                  cursor: isAnalyzing ? 'not-allowed' : 'pointer',
                }}
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
              className="border p-8 flex-1 flex flex-col items-center justify-center text-center relative overflow-hidden transition-colors"
              style={{
                borderRadius: 'var(--radius-xl)',
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-colors border"
                style={{
                  background: 'var(--color-bg-base)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-accent)',
                }}
              >
                <span className="material-symbols-outlined text-[34px]">biotech</span>
              </div>

              <span
                className="type-caption px-3 py-1 rounded-full uppercase tracking-wider mb-3 border font-bold"
                style={{
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--color-bg-base)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                Awaiting Microanalysis
              </span>

              <h3 className="type-title mb-2" style={{ color: 'var(--color-text-primary)' }}>
                No Particle Analyzed Yet
              </h3>

              <p className="type-body max-w-sm leading-relaxed mb-6" style={{ color: 'var(--color-text-secondary)' }}>
                Upload an EDS microanalysis report (PDF, DOCX, CSV) or manually input elemental concentrations (wt%) on the left and select <strong style={{ color: 'var(--color-text-primary)' }}>Predict Family</strong> to perform stoichiometric cross-matching.
              </p>

              <div className="grid grid-cols-2 gap-3 w-full max-w-xs text-left text-[11px]">
                <div
                  className="p-3 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <span className="type-caption block uppercase tracking-wider opacity-60">Status</span>
                  <span className="font-semibold flex items-center gap-1.5 mt-1" style={{ color: 'var(--color-pass)' }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-pass)' }}></span>
                    Ready for Ingest
                  </span>
                </div>
                <div
                  className="p-3 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <span className="type-caption block uppercase tracking-wider opacity-60">Library</span>
                  <span className="font-semibold mt-1 block" style={{ color: 'var(--color-text-primary)' }}>
                    ASTM E1508 Loaded
                  </span>
                </div>
              </div>
            </div>
          ) : (

            /* Analyzed Results View */
            <>
              {/* Hero Result Card */}
              <div
                id="hero-result-card"
                className="border relative overflow-hidden flex-none transition-colors"
                style={{
                  borderRadius: 'var(--radius-xl)',
                  background: 'var(--color-bg-card)',
                  borderColor: 'var(--color-border)',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div className="relative z-10 p-6">
                  {/* Badge & Execution Timer */}
                  <div className="flex justify-between items-start mb-4">
                    {lastDecision === 'identified' ? (
                      <span
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold tracking-wider"
                        style={{
                          borderRadius: 'var(--radius-full)',
                          background: 'var(--color-pass-subtle)',
                          color: 'var(--color-pass)',
                          border: '1px solid var(--color-pass)',
                        }}
                      >
                        <span className="material-symbols-outlined text-[14px]">check_circle</span>
                        IDENTIFIED
                      </span>
                    ) : lastDecision === 'ambiguous' ? (
                      <span
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold tracking-wider"
                        style={{
                          borderRadius: 'var(--radius-full)',
                          background: 'var(--color-warn-subtle)',
                          color: 'var(--color-warn)',
                          border: '1px solid var(--color-warn)',
                        }}
                      >
                        <span className="material-symbols-outlined text-[14px]">help</span>
                        AMBIGUOUS SET
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold tracking-wider"
                        style={{
                          borderRadius: 'var(--radius-full)',
                          background: 'var(--color-fail-subtle)',
                          color: 'var(--color-fail)',
                          border: '1px solid var(--color-fail)',
                        }}
                      >
                        <span className="material-symbols-outlined text-[14px]">cancel</span>
                        UNKNOWN / ABSTAINED
                      </span>
                    )}

                    <div
                      className="flex items-center gap-1 text-[11px] font-mono-code"
                      style={{ color: 'var(--color-text-tertiary)' }}
                    >
                      <span className="material-symbols-outlined text-[15px]">timer</span>
                      <span>{analysisDuration}</span>
                    </div>
                  </div>

                  {/* Material Title & Grade Hint */}
                  <div className="mb-6">
                    <h3
                      className="type-display leading-tight mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      {lastDecision === 'unknown' ? 'Unclassified Material' : (activeFamily?.name || 'Identified Material')}
                    </h3>
                    <p
                      className="type-body flex items-center gap-1.5"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      <span className="material-symbols-outlined text-[16px]">info</span>
                      {lastDecision === 'unknown'
                        ? (lastReason || 'Abstained: insufficient alloy signal for reliable specification check')
                        : `Grade hint: ${activeFamily?.gradeHint || 'Alloy Grade'}${lastDecision === 'ambiguous' ? ' (Tied candidate families)' : ''}`}
                    </p>
                  </div>

                  {/* Compatibility Gauge Row */}
                  <div
                    className="flex items-center gap-4 p-4 border"
                    style={{
                      borderRadius: 'var(--radius-lg)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                    }}
                  >
                    {/* SVG Gauge */}
                    <div className="relative w-16 h-16 shrink-0">
                      <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                        <path
                          style={{ stroke: 'var(--color-border)' }}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          strokeWidth="3.2"
                        />
                        <path
                          style={{
                            stroke:
                              lastDecision === 'unknown'
                                ? 'var(--color-fail)'
                                : gaugePct >= 80
                                ? 'var(--color-pass)'
                                : 'var(--color-warn)',
                            transition: 'stroke-dasharray 600ms var(--ease-out-expo)',
                          }}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          strokeDasharray={strokeDash}
                          strokeWidth="3.2"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span
                          className="font-mono-code font-bold text-[14px]"
                          style={{
                            color:
                              lastDecision === 'unknown'
                                ? 'var(--color-fail)'
                                : gaugePct >= 80
                                ? 'var(--color-pass)'
                                : 'var(--color-warn)',
                          }}
                        >
                          {gaugePct}%
                        </span>
                      </div>
                    </div>

                    <div>
                      <h4 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                        {lastDecision === 'unknown'
                          ? 'Abstained by Rule Engine'
                          : lastDecision === 'ambiguous'
                          ? 'Ambiguous Spectral Fit'
                          : 'High Compatibility'}
                      </h4>
                      <p className="type-body text-[12.5px] leading-snug mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                        {lastDecision === 'unknown'
                          ? (lastReason || 'Measurement did not exhibit required decisive alloy markers. Safe abstention prevents misclassification.')
                          : lastDecision === 'ambiguous'
                          ? 'Observed stoichiometry is consistent with multiple material families within measurement error.'
                          : `Spectral signature closely matches reference library standards for ${activeFamily?.code || 'family'} (${activeFamily?.gradeHint || 'standard'}).`}
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
                  className="flex-1 border p-4 flex flex-col overflow-hidden transition-colors"
                  style={{
                    borderRadius: 'var(--radius-lg)',
                    background: 'var(--color-bg-card)',
                    borderColor: 'var(--color-border)',
                    boxShadow: 'var(--shadow-card)',
                  }}
                >
                  <h4
                    className="type-caption font-bold uppercase tracking-wider mb-2 px-1 border-b pb-1.5"
                    style={{
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-tertiary)',
                    }}
                  >
                    CANDIDATE COMPONENTS
                  </h4>

                  <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
                    {!activeFamily || activeFamily.candidateComponents.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center p-3 opacity-60">
                        <span className="material-symbols-outlined text-[26px] mb-1" style={{ color: 'var(--color-text-tertiary)' }}>category</span>
                        <p className="text-[12px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>No candidate components mapped</p>
                        <p className="type-caption mt-0.5" style={{ color: 'var(--color-text-tertiary)' }}>Catalog components in the Knowledge Base.</p>
                      </div>
                    ) : (
                      activeFamily.candidateComponents.slice(0, 3).map((comp, idx) => (
                        <div
                          key={comp.id}
                          onClick={() => onSelectComponent(comp)}
                          className="press-target flex items-center justify-between p-2.5 border transition-all cursor-pointer group"
                          style={{
                            borderRadius: 'var(--radius-md)',
                            background: 'var(--color-bg-base)',
                            borderColor: 'var(--color-border)',
                          }}
                        >
                          <div className="flex items-center gap-2.5">
                            <span
                              className="w-6 h-6 rounded-full flex items-center justify-center font-mono-code text-[11px] font-bold"
                              style={{
                                background: idx === 0 ? 'var(--color-accent)' : 'var(--color-bg-card)',
                                color: idx === 0 ? 'var(--color-accent-on)' : 'var(--color-text-secondary)',
                                border: '1px solid var(--color-border)',
                              }}
                            >
                              {idx + 1}
                            </span>
                            <div className="min-w-0">
                              <span
                                className="font-semibold text-[13px] block truncate group-hover:underline"
                                style={{ color: 'var(--color-text-primary)' }}
                              >
                                {comp.name}
                              </span>
                              <span className="type-caption font-mono-code" style={{ color: 'var(--color-text-tertiary)' }}>
                                {comp.partNumber} • {comp.nominalAlloy}
                              </span>
                            </div>
                          </div>
                          <span
                            className="material-symbols-outlined text-[18px] transition-transform group-hover:translate-x-0.5"
                            style={{ color: 'var(--color-text-tertiary)' }}
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
                  className="w-[42%] border p-4 flex flex-col relative overflow-hidden transition-colors"
                  style={{
                    borderRadius: 'var(--radius-lg)',
                    background: 'var(--color-bg-card)',
                    borderColor: 'var(--color-border)',
                    boxShadow: 'var(--shadow-card)',
                  }}
                >
                  {/* Background watermark */}
                  <div className="absolute -right-6 -bottom-6 opacity-5 pointer-events-none">
                    <span className="material-symbols-outlined text-[110px]">analytics</span>
                  </div>

                  <h4
                    className="type-caption font-bold uppercase tracking-wider mb-2 px-1 border-b pb-1.5 relative z-10"
                    style={{
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-tertiary)',
                    }}
                  >
                    ANALYSIS CONTEXT
                  </h4>

                  <div className="space-y-2 relative z-10 overflow-y-auto">
                    {(activeFamily?.contextCaveats || []).map((caveat, idx) => (
                      <div
                        key={idx}
                        className="p-2 border flex gap-2 items-start"
                        style={{
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--color-bg-base)',
                          borderColor: 'var(--color-border)',
                        }}
                      >
                        <span
                          className="material-symbols-outlined text-[16px] mt-0.5 shrink-0"
                          style={{ color: 'var(--color-accent)' }}
                        >
                          {caveat.icon}
                        </span>
                        <div>
                          <span
                            className="block font-semibold text-[12px]"
                            style={{ color: 'var(--color-text-primary)' }}
                          >
                            {caveat.title}
                          </span>
                          <span
                            className="type-caption block leading-tight mt-0.5"
                            style={{ color: 'var(--color-text-secondary)' }}
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
