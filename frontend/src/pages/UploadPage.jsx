import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchDocuments, uploadDocument, analyzeSingleDocument, analyzeMultiDocuments, getDocumentStatus, getAnalysisResults, getComparisonStatus, getComparisonResults } from '../utils/api';
import UploadArea from '../components/UploadArea';
import FileItem from '../components/FileItem';
import AnalysisProgress from '../components/AnalysisProgress';
import AnalysisResults from '../components/AnalysisResults';
import { formatFileSize, isValidFile } from '../utils/helpers';
import { generatePDFReport } from '../utils/pdfReport';

/**
 * UploadPage – the main analysis page.
 *
 * Supports two modes:
 * 1. Upload new files for analysis
 * 2. Select from existing uploaded documents
 */

const ANALYSIS_STEPS = [
    { id: 'upload', text: 'Uploading documents...', duration: 1000 },
    { id: 'extract', text: 'Extracting text content...', duration: 1500 },
    { id: 'process', text: 'Running AI analysis...', duration: 3000 },
    { id: 'analyze', text: 'Detecting contradictions...', duration: 2000 },
    { id: 'report', text: 'Generating detailed report...', duration: 1500 },
];

/**
 * Maps backend processing_stage values to step index + user-facing text.
 * Used by the polling loop to reflect real pipeline progress.
 */
const STAGE_MAP = {
    // Single-doc stages (step indices match AnalysisProgress STEPS: 0=Upload, 1=Extract, 2=AI, 3=Detection, 4=Results)
    downloading:  { step: 1, text: 'Downloading document...' },
    extracting:   { step: 1, text: 'Extracting text content...' },
    segmenting:   { step: 1, text: 'Segmenting clauses...' },
    embedding:    { step: 2, text: 'Generating AI embeddings...' },
    ner:          { step: 2, text: 'Extracting named entities (NER)...' },
    similarity:   { step: 3, text: 'Finding similar clause pairs...' },
    rules:        { step: 3, text: 'Running rule-based checks...' },
    nli:          { step: 3, text: 'Verifying contradictions with NLI model...' },
    storing:      { step: 4, text: 'Storing results...' },
    completed:    { step: 4, text: 'Analysis complete!' },
    // Multi-doc stages
    preparing:    { step: 0, text: 'Preparing comparison session...' },
};

export default function UploadPage({ onNotification }) {
    const { token } = useAuth();
    const [mode, setMode] = useState('upload'); // 'upload' | 'select'
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [existingDocs, setExistingDocs] = useState([]);
    const [selectedDocIds, setSelectedDocIds] = useState([]);
    const [analysisType, setAnalysisType] = useState('multi'); // 'single' | 'multi'

    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [showProgress, setShowProgress] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [progressPercent, setProgressPercent] = useState(0);
    const [progressText, setProgressText] = useState('Initializing...');
    const [analysisResults, setAnalysisResults] = useState(null);
    const [loadingDocs, setLoadingDocs] = useState(false);
    const [showReRunModal, setShowReRunModal] = useState(false);
    const [pendingDocId, setPendingDocId] = useState(null);
    const rafRef = useRef(null);

    // Cleanup requestAnimationFrame on unmount
    useEffect(() => {
        return () => {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
        };
    }, []);

    // Close re-run modal on Escape key
    useEffect(() => {
        if (!showReRunModal) return;
        const handleEscape = (e) => {
            if (e.key === 'Escape') setShowReRunModal(false);
        };
        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [showReRunModal]);

    // ── Load existing documents when in select mode ──
    useEffect(() => {
        if (mode === 'select' && existingDocs.length === 0) {
            loadExistingDocuments();
        }
    }, [mode]);

    const loadExistingDocuments = async () => {
        try {
            setLoadingDocs(true);
            const docs = await fetchDocuments(token);
            setExistingDocs(docs);
        } catch (err) {
            onNotification?.('Failed to load documents', 'error');
        } finally {
            setLoadingDocs(false);
        }
    };

    // ── File handling (upload mode) ──
    const handleFilesSelected = useCallback(
        (fileList) => {
            const newFiles = Array.from(fileList);

            newFiles.forEach((file) => {
                setUploadedFiles((prev) => {
                    const maxFiles = analysisType === 'single' ? 1 : 10;
                    if (prev.length >= maxFiles) {
                        onNotification?.(`Maximum ${maxFiles} document${maxFiles > 1 ? 's' : ''} allowed`, 'warning');
                        return prev;
                    }
                    if (!isValidFile(file)) {
                        onNotification?.(`Invalid file type: ${file.name}`, 'error');
                        return prev;
                    }
                    if (file.size > 10 * 1024 * 1024) {
                        onNotification?.(`File too large: ${file.name}`, 'error');
                        return prev;
                    }
                    return [
                        ...prev,
                        {
                            id: Date.now() + Math.random(),
                            file: file,
                            name: file.name,
                            size: formatFileSize(file.size),
                        },
                    ];
                });
            });
        },
        [onNotification, analysisType]
    );

    const removeFile = useCallback((id) => {
        setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    }, []);

    // ── Document selection (select mode) ──
    const toggleDocSelection = useCallback((docId) => {
        setSelectedDocIds((prev) => {
            const maxDocs = analysisType === 'single' ? 1 : 10;
            if (prev.includes(docId)) {
                return prev.filter((id) => id !== docId);
            } else {
                if (prev.length >= maxDocs) {
                    onNotification?.(`Maximum ${maxDocs} document${maxDocs > 1 ? 's' : ''} allowed`, 'warning');
                    return prev;
                }
                return [...prev, docId];
            }
        });
    }, [analysisType, onNotification]);

    // ── Progress animation helper ──
    const animateProgress = (from, to, duration) => {
        return new Promise((resolve) => {
            const startTime = Date.now();
            const tick = () => {
                const elapsed = Date.now() - startTime;
                const t = Math.min(elapsed / duration, 1);
                setProgressPercent(from + (to - from) * t);
                if (t < 1) {
                    requestAnimationFrame(tick);
                } else {
                    resolve();
                }
            };
            tick();
        });
    };

    // ── Analysis flow ──
    const startAnalysis = async () => {
        const minDocs = analysisType === 'single' ? 1 : 2;
        const currentCount = mode === 'upload' ? uploadedFiles.length : selectedDocIds.length;

        if (currentCount < minDocs) {
            onNotification?.(`Please ${mode === 'upload' ? 'upload' : 'select'} at least ${minDocs} document${minDocs > 1 ? 's' : ''}`, 'warning');
            return;
        }

        // Check if previously analyzed
        if (analysisType === 'single' && mode === 'select') {
            const docId = selectedDocIds[0];
            const doc = existingDocs.find(d => d.id === docId);
            if (doc && doc.status === 'completed') {
                setPendingDocId(docId);
                setShowReRunModal(true);
                return;
            }
        }

        executeAnalysis();
    };

    const handleViewExisting = async () => {
        const documentId = pendingDocId;
        setShowReRunModal(false);
        setIsAnalyzing(true);
        setShowResults(false);
        setShowProgress(true);
        setProgressPercent(0);
        setCurrentStepIndex(0);
        setProgressText('Loading existing results...');

        try {
            await animateProgress(0, 100, 500);
            const resultsData = await getAnalysisResults(documentId, token);
            finalizeAnalysis(documentId, resultsData, 0);
        } catch (err) {
            onNotification?.('Failed to fetch existing results', 'error');
            resetAnalysis();
        }
    };

    const handleReRun = () => {
        setShowReRunModal(false);
        executeAnalysis(pendingDocId);
    };

    const finalizeAnalysis = (documentId, resultsData, pollCount) => {
        const results = {
            contradictions: resultsData.contradictions_by_severity || {},
            totalContradictions: resultsData.total_contradictions || 0,
            totalClauses: resultsData.total_clauses || 0,
            averageConfidence: (() => {
                const allC = Object.values(resultsData.contradictions_by_severity || {}).flat();
                return allC.length > 0
                    ? Math.round(allC.reduce((s, c) => s + (c.confidence || 0), 0) / allC.length)
                    : 0;
            })(),
            analysisTime: resultsData.analysis_duration ? resultsData.analysis_duration + 's' : pollCount + 's',
            documentId: documentId,
            status: resultsData.status,
            timestamp: new Date().toISOString(),
        };

        setAnalysisResults(results);
        setProgressText('Analysis complete!');
        setCurrentStepIndex(ANALYSIS_STEPS.length);
        setIsAnalyzing(false);
        setShowProgress(false);
        setShowResults(true);
    };

    const executeAnalysis = async (docIdOverride = null) => {
        setIsAnalyzing(true);
        setShowProgress(true);
        setShowResults(false);
        setProgressPercent(0);

        try {
            if (analysisType === 'single') {
                let documentId = docIdOverride;

                // Step 1: Upload (if in upload mode)
                if (mode === 'upload' && !documentId) {
                    setCurrentStepIndex(0);
                    setProgressText('Uploading document...');

                    const uploadedDoc = await uploadDocument(uploadedFiles[0].file, token);
                    documentId = uploadedDoc.id;
                } else if (!documentId) {
                    documentId = selectedDocIds[0];
                    setCurrentStepIndex(0);
                    setProgressText('Preparing document...');
                }

                // Step 2: Trigger analysis
                setCurrentStepIndex(1);
                setProgressText('Starting analysis...');

                await analyzeSingleDocument(documentId, token);

                // Step 3-5: Poll for real-time status and stage
                let pollStatus = 'processing';
                let pollCount = 0;
                const maxPolls = 120;

                while ((pollStatus === 'processing' || pollStatus === 'pending') && pollCount < maxPolls) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    const statusData = await getDocumentStatus(documentId, token);
                    pollStatus = statusData.status;
                    pollCount++;

                    // Use real backend progress + stage directly
                    const stage = statusData.processing_stage;
                    const stageInfo = STAGE_MAP[stage];

                    if (stageInfo) {
                        setCurrentStepIndex(stageInfo.step);
                        setProgressText(stageInfo.text);
                    }
                    setProgressPercent(statusData.progress_percent || 0);
                }

                if (pollStatus === 'failed') {
                    throw new Error('Analysis failed');
                }

                // Fetch results
                setCurrentStepIndex(4);
                setProgressText('Fetching results...');
                setProgressPercent(100);

                const resultsData = await getAnalysisResults(documentId, token);
                finalizeAnalysis(documentId, resultsData, pollCount);

            } else {
                // ── Multi-document comparison (new background workflow) ──
                let documentIds = [];

                // Step 1: Upload files if in upload mode, or use selected IDs
                if (mode === 'upload') {
                    setCurrentStepIndex(0);
                    setProgressText('Uploading documents...');

                    for (let i = 0; i < uploadedFiles.length; i++) {
                        setProgressText(`Uploading document ${i + 1} of ${uploadedFiles.length}...`);
                        const uploadedDoc = await uploadDocument(uploadedFiles[i].file, token);
                        documentIds.push(uploadedDoc.id);
                    }
                } else {
                    documentIds = [...selectedDocIds];
                    setCurrentStepIndex(0);
                    setProgressText('Preparing documents...');
                }

                // Step 2: Trigger multi-doc comparison
                setCurrentStepIndex(1);
                setProgressText('Starting cross-document comparison...');

                const { comparison_id } = await analyzeMultiDocuments(documentIds, token);

                // Step 3–5: Poll for real-time comparison status and stage
                let status = 'processing';
                let pollCount = 0;
                const maxPolls = 180; // 3 minutes max

                while ((status === 'processing' || status === 'pending') && pollCount < maxPolls) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    const statusData = await getComparisonStatus(comparison_id, token);
                    status = statusData.status;
                    pollCount++;

                    // Use real backend progress + stage directly
                    const stage = statusData.processing_stage;
                    const stageInfo = STAGE_MAP[stage];

                    if (stageInfo) {
                        setCurrentStepIndex(stageInfo.step);
                        setProgressText(stageInfo.text);
                    }
                    setProgressPercent(statusData.progress_percent || 0);

                    if (status === 'failed') {
                        throw new Error(statusData.error_message || 'Comparison failed');
                    }
                }

                if (status !== 'completed') {
                    throw new Error('Comparison timed out');
                }

                // Fetch results
                setCurrentStepIndex(4);
                setProgressText('Fetching comparison results...');
                setProgressPercent(100);

                const resultsData = await getComparisonResults(comparison_id, token);

                const allContras = Object.values(resultsData.contradictions_by_severity || {}).flat();
                const avgConf = allContras.length > 0
                    ? Math.round(allContras.reduce((sum, c) => sum + (c.confidence || 0), 0) / allContras.length)
                    : 0;

                const results = {
                    contradictions: resultsData.contradictions_by_severity || {},
                    totalContradictions: resultsData.total_contradictions || 0,
                    totalClauses: resultsData.total_clauses || 0,
                    averageConfidence: avgConf,
                    analysisTime: resultsData.analysis_duration ? resultsData.analysis_duration + 's' : pollCount + 's',
                    comparisonId: comparison_id,
                    documents: resultsData.documents || [],
                    status: resultsData.status,
                    timestamp: new Date().toISOString(),
                    isMultiDoc: true,
                };

                setAnalysisResults(results);
                setProgressText('Comparison complete!');
                setCurrentStepIndex(ANALYSIS_STEPS.length);
            }

            setShowProgress(false);
            setShowResults(true);
            onNotification?.('Analysis completed successfully!', 'success');

        } catch (err) {
            onNotification?.('Failed to analyze: ' + err.message, 'error');
            resetAnalysis();
        } finally {
            setIsAnalyzing(false);
        }
    };

    // ── Reset ──
    const resetAnalysis = () => {
        setUploadedFiles([]);
        setSelectedDocIds([]);
        setAnalysisResults(null);
        setShowProgress(false);
        setShowResults(false);
        setIsAnalyzing(false);
        setProgressPercent(0);
        setCurrentStepIndex(0);
        setPendingDocId(null);
        setShowReRunModal(false);
        onNotification?.('Analysis reset. Ready for new documents.', 'success');
    };

    // ── PDF download ──
    const downloadReport = () => {
        if (!analysisResults) return;
        generatePDFReport({ uploadedFiles, analysisResults });
        onNotification?.('PDF report downloaded successfully', 'success');
    };

    // ── Handle analysis type change ──
    const handleAnalysisTypeChange = (newType) => {
        setAnalysisType(newType);
        // Reset selections when switching types
        if (newType === 'single') {
            setUploadedFiles((prev) => prev.slice(0, 1));
            setSelectedDocIds((prev) => prev.slice(0, 1));
        }
    };

    // ── Render ──
    return (
        <div id="upload-page" className="page active">

            <div className="page-header">
                <h1>Document Analysis</h1>
                <p>
                    {analysisType === 'single'
                        ? 'Analyze a single document for quality and consistency'
                        : 'Upload or select 2-10 documents to detect cross-document contradictions and inconsistencies'}
                </p>
            </div>

            <div className="analysis-container">
                {/* Left column */}
                <div className="upload-section">
                    {/* Mode toggle */}
                    <div className="mode-toggle">
                        <button
                            className={`mode-btn ${mode === 'upload' ? 'active' : ''}`}
                            onClick={() => setMode('upload')}
                        >
                            <i className="fas fa-cloud-upload-alt"></i>
                            Upload New
                        </button>
                        <button
                            className={`mode-btn ${mode === 'select' ? 'active' : ''}`}
                            onClick={() => setMode('select')}
                        >
                            <i className="fas fa-folder-open"></i>
                            Select Existing
                        </button>
                    </div>

                    {/* Upload mode */}
                    {mode === 'upload' && (
                        <>
                            <UploadArea onFilesSelected={handleFilesSelected} />
                            <div className="uploaded-files">
                                {uploadedFiles.map((f) => (
                                    <FileItem key={f.id} fileObj={f} onRemove={removeFile} />
                                ))}
                            </div>
                        </>
                    )}

                    {/* Select mode */}
                    {mode === 'select' && (
                        <div className="document-selector">
                            {loadingDocs ? (
                                <div className="loading-docs">
                                    <div className="spinner"></div>
                                    <p>Loading documents...</p>
                                </div>
                            ) : existingDocs.length === 0 ? (
                                <div className="no-docs">
                                    <i className="fas fa-folder-open"></i>
                                    <p>No documents uploaded yet</p>
                                    <button onClick={() => setMode('upload')} className="switch-mode-btn">
                                        Upload Documents
                                    </button>
                                </div>
                            ) : (
                                <div className="doc-list">
                                    {existingDocs.map((doc) => (
                                        <div
                                            key={doc.id}
                                            className={`doc-item ${selectedDocIds.includes(doc.id) ? 'selected' : ''}`}
                                            role="checkbox"
                                            aria-checked={selectedDocIds.includes(doc.id)}
                                            tabIndex={0}
                                            onClick={() => toggleDocSelection(doc.id)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' || e.key === ' ') {
                                                    e.preventDefault();
                                                    toggleDocSelection(doc.id);
                                                }
                                            }}
                                        >
                                            <div className="doc-checkbox">
                                                {selectedDocIds.includes(doc.id) && <i className="fas fa-check"></i>}
                                            </div>
                                            <div className="doc-info">
                                                <span className="doc-name">{doc.name}</span>
                                                <span className="doc-date">
                                                    {new Date(doc.upload_date).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Analysis options */}
                    <div className="analysis-options">
                        <div className="option-group">
                            <label>Analysis Type</label>
                            <select
                                value={analysisType}
                                onChange={(e) => handleAnalysisTypeChange(e.target.value)}
                            >
                                <option value="single">Single Document Analysis</option>
                                <option value="multi">Multi-Document Comparison</option>
                            </select>
                        </div>
                    </div>

                    <button
                        className="analyze-btn"
                        disabled={
                            (mode === 'upload' && uploadedFiles.length < (analysisType === 'single' ? 1 : 2)) ||
                            (mode === 'select' && selectedDocIds.length < (analysisType === 'single' ? 1 : 2)) ||
                            isAnalyzing
                        }
                        onClick={startAnalysis}
                    >
                        <i className="fas fa-play"></i>
                        {isAnalyzing ? 'Analyzing...' : 'Analyze Documents'}
                    </button>
                </div>


            </div>

            {/* Progress */}
            {showProgress && (
                <AnalysisProgress
                    currentStepIndex={currentStepIndex}
                    progressPercent={progressPercent}
                    progressText={progressText}
                />
            )}
            {/* Results */}
            {showResults && analysisResults && (
                <div id="results-section">
                    <AnalysisResults
                        results={analysisResults}
                        onNewAnalysis={resetAnalysis}
                        onDownload={downloadReport}
                    />
                </div>
            )}
            {/* ── Re-run / View existing choice modal ── */}
            {showReRunModal && (
                <div className="modal-overlay">
                    <div className="choice-modal">
                        <div className="modal-header">
                            <i className="fas fa-history"></i>
                            <h3>Previous Analysis Found</h3>
                        </div>
                        <p>
                            This document has already been analyzed. Would you like to view the existing results or start a fresh analysis?
                        </p>
                        <div className="modal-actions">
                            <button className="choice-btn secondary" onClick={handleViewExisting}>
                                <i className="fas fa-eye"></i>
                                View Existing Results
                            </button>
                            <button className="choice-btn primary" onClick={handleReRun}>
                                <i className="fas fa-redo"></i>
                                Re-run New Analysis
                            </button>
                        </div>
                        <button className="modal-close" onClick={() => setShowReRunModal(false)}>
                            <i className="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
