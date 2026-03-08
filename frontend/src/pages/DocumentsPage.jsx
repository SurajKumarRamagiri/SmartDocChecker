import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchDocuments, uploadDocument, downloadDocument, deleteDocument } from '../utils/api';
import './DocumentsPage.css';

/**
 * DocumentsPage – manage uploaded documents.
 *
 * Lists all user documents, supports upload, download, and delete.
 */
export default function DocumentsPage({ onNotification }) {
    const { token } = useAuth();
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState('newest');
    const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
    const fileInputRef = useRef(null);

    // ── Load documents on mount ──
    const loadDocuments = useCallback(async () => {
        try {
            setLoading(true);
            const docs = await fetchDocuments(token);
            setDocuments(docs);
        } catch (err) {
            onNotification?.('Failed to load documents', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, onNotification]);

    useEffect(() => {
        loadDocuments();
    }, [loadDocuments]);

    // ── Upload handler ──
    const handleUpload = useCallback(async (files) => {
        if (!files || files.length === 0) return;

        // Validate file types before uploading
        const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
        const validFiles = Array.from(files).filter((f) => {
            const ext = f.name.split('.').pop()?.toLowerCase();
            if (!ext || !ALLOWED_EXTENSIONS.includes('.' + ext)) {
                onNotification?.(`Unsupported file type: ${f.name}`, 'error');
                return false;
            }
            return true;
        });
        if (validFiles.length === 0) return;

        setUploading(true);
        let successCount = 0;

        for (const file of validFiles) {
            try {
                const doc = await uploadDocument(file, token);
                setDocuments((prev) => [doc, ...prev]);
                successCount++;
            } catch (err) {
                onNotification?.(`Failed to upload ${file.name}`, 'error');
            }
        }

        if (successCount > 0) {
            onNotification?.(`${successCount} file${successCount > 1 ? 's' : ''} uploaded successfully`, 'success');
        }
        setUploading(false);
    }, [token, onNotification]);

    // ── Download handler ──
    const handleDownload = useCallback(async (doc) => {
        try {
            const result = await downloadDocument(doc.id, token);
            const url = result.download_url;
            // Validate URL scheme to prevent open redirect
            if (url && /^https?:\/\//i.test(url)) {
                window.open(url, '_blank', 'noopener,noreferrer');
            } else {
                onNotification?.('Invalid download URL', 'error');
            }
        } catch (err) {
            onNotification?.('Failed to generate download link', 'error');
        }
    }, [token, onNotification]);

    // ── Delete handler ──
    const handleDelete = useCallback(async (docId) => {
        if (!window.confirm('Are you sure you want to delete this document?')) return;
        try {
            await deleteDocument(docId, token);
            setDocuments((prev) => prev.filter((d) => d.id !== docId));
            onNotification?.('Document deleted', 'success');
        } catch (err) {
            onNotification?.('Failed to delete document', 'error');
        }
    }, [token, onNotification]);

    // ── Drag & Drop ──
    const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
    const handleDragLeave = () => setDragOver(false);
    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleUpload(Array.from(e.dataTransfer.files));
    };

    // ── Filter & Sort (memoized) ──
    const filteredDocs = useMemo(() => documents
        .filter((d) => d.name.toLowerCase().includes(searchQuery.toLowerCase()))
        .sort((a, b) => {
            if (sortBy === 'newest') return new Date(b.upload_date) - new Date(a.upload_date);
            if (sortBy === 'oldest') return new Date(a.upload_date) - new Date(b.upload_date);
            if (sortBy === 'name') return a.name.localeCompare(b.name);
            return 0;
        }), [documents, searchQuery, sortBy]);

    // ── File icon based on extension ──
    const getFileIcon = (name) => {
        const ext = name?.split('.').pop()?.toLowerCase();
        switch (ext) {
            case 'pdf': return 'fas fa-file-pdf';
            case 'doc': case 'docx': return 'fas fa-file-word';
            case 'txt': return 'fas fa-file-alt';
            case 'xls': case 'xlsx': return 'fas fa-file-excel';
            case 'ppt': case 'pptx': return 'fas fa-file-powerpoint';
            default: return 'fas fa-file';
        }
    };

    const getFileColor = (name) => {
        const ext = name?.split('.').pop()?.toLowerCase();
        switch (ext) {
            case 'pdf': return '#ef4444';
            case 'doc': case 'docx': return '#3b82f6';
            case 'txt': return '#64748b';
            case 'xls': case 'xlsx': return '#22c55e';
            case 'ppt': case 'pptx': return '#f97316';
            default: return '#8b5cf6';
        }
    };

    const getStatusBadge = (status) => {
        const config = {
            pending: { label: 'Pending', className: 'status-pending' },
            processing: { label: 'Processing', className: 'status-processing' },
            completed: { label: 'Completed', className: 'status-completed' },
            failed: { label: 'Failed', className: 'status-failed' },
        };
        const s = config[status] || config.pending;
        return <span className={`doc-status ${s.className}`}>{s.label}</span>;
    };

    const formatDate = (dateStr) => {
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch {
            return dateStr;
        }
    };

    return (
        <div id="documents-page" className="page active">
            {/* Header */}
            <div className="docs-header">
                <div className="docs-header__left">
                    <h1>
                        <i className="fas fa-folder-open"></i>
                        My Documents
                    </h1>
                    <p className="docs-subtitle">
                        {documents.length} document{documents.length !== 1 ? 's' : ''} uploaded
                    </p>
                </div>
                <button
                    className="docs-upload-btn"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                >
                    {uploading ? (
                        <><div className="btn-spinner"></div> Uploading...</>
                    ) : (
                        <><i className="fas fa-cloud-upload-alt"></i> Upload Files</>
                    )}
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.txt"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(Array.from(e.target.files))}
                />
            </div>

            {/* Toolbar */}
            <div className="docs-toolbar">
                <div className="docs-search">
                    <i className="fas fa-search"></i>
                    <input
                        type="text"
                        placeholder="Search documents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <div className="docs-toolbar__right">
                    <select
                        className="docs-sort"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                    >
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="name">Name A-Z</option>
                    </select>
                    <div className="docs-view-toggle">
                        <button
                            className={viewMode === 'grid' ? 'active' : ''}
                            onClick={() => setViewMode('grid')}
                            title="Grid view"
                            aria-label="Grid view"
                        >
                            <i className="fas fa-th-large"></i>
                        </button>
                        <button
                            className={viewMode === 'list' ? 'active' : ''}
                            onClick={() => setViewMode('list')}
                            title="List view"
                            aria-label="List view"
                        >
                            <i className="fas fa-list"></i>
                        </button>
                    </div>
                </div>
            </div>

            {/* Drop zone overlay */}
            <div
                className={`docs-drop-zone ${dragOver ? 'drag-over' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                {/* Loading */}
                {loading ? (
                    <div className="docs-loading">
                        <div className="docs-loading__spinner"></div>
                        <p>Loading your documents...</p>
                    </div>
                ) : filteredDocs.length === 0 ? (
                    /* Empty state */
                    <div className="docs-empty">
                        <div className="docs-empty__icon">
                            <i className="fas fa-cloud-upload-alt"></i>
                        </div>
                        <h3>
                            {searchQuery ? 'No documents match your search' : 'No documents yet'}
                        </h3>
                        <p>
                            {searchQuery
                                ? 'Try a different search term'
                                : 'Upload your first document to get started'}
                        </p>
                        {!searchQuery && (
                            <button
                                className="docs-empty__btn"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <i className="fas fa-plus"></i> Upload Document
                            </button>
                        )}
                    </div>
                ) : viewMode === 'grid' ? (
                    /* Grid view */
                    <div className="docs-grid">
                        {filteredDocs.map((doc) => (
                            <div key={doc.id} className="doc-card">
                                <div className="doc-card__icon" style={{ color: getFileColor(doc.name) }}>
                                    <i className={getFileIcon(doc.name)}></i>
                                </div>
                                <div className="doc-card__info">
                                    <h4 className="doc-card__name" title={doc.name}>{doc.name}</h4>
                                    <span className="doc-card__date">
                                        <i className="far fa-calendar"></i> {formatDate(doc.upload_date)}
                                    </span>
                                    {getStatusBadge(doc.status)}
                                </div>
                                <div className="doc-card__actions">
                                    <button
                                        className="doc-action doc-action--download"
                                        onClick={() => handleDownload(doc)}
                                        title="Download"
                                        aria-label={`Download ${doc.name}`}
                                    >
                                        <i className="fas fa-download"></i>
                                    </button>
                                    <button
                                        className="doc-action doc-action--delete"
                                        onClick={() => handleDelete(doc.id)}
                                        title="Delete"
                                        aria-label={`Delete ${doc.name}`}
                                    >
                                        <i className="fas fa-trash-alt"></i>
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    /* List view */
                    <div className="docs-list">
                        <div className="docs-list__header">
                            <span className="docs-list__col docs-list__col--name">Name</span>
                            <span className="docs-list__col docs-list__col--date">Date</span>
                            <span className="docs-list__col docs-list__col--status">Status</span>
                            <span className="docs-list__col docs-list__col--actions">Actions</span>
                        </div>
                        {filteredDocs.map((doc) => (
                            <div key={doc.id} className="docs-list__row">
                                <span className="docs-list__col docs-list__col--name">
                                    <i className={getFileIcon(doc.name)} style={{ color: getFileColor(doc.name) }}></i>
                                    <span className="docs-list__filename" title={doc.name}>{doc.name}</span>
                                </span>
                                <span className="docs-list__col docs-list__col--date">{formatDate(doc.upload_date)}</span>
                                <span className="docs-list__col docs-list__col--status">{getStatusBadge(doc.status)}</span>
                                <span className="docs-list__col docs-list__col--actions">
                                    <button
                                        className="doc-action doc-action--download"
                                        onClick={() => handleDownload(doc)}
                                        title="Download"
                                        aria-label={`Download ${doc.name}`}
                                    >
                                        <i className="fas fa-download"></i>
                                    </button>
                                    <button
                                        className="doc-action doc-action--delete"
                                        onClick={() => handleDelete(doc.id)}
                                        title="Delete"
                                        aria-label={`Delete ${doc.name}`}
                                    >
                                        <i className="fas fa-trash-alt"></i>
                                    </button>
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Drag overlay */}
                {dragOver && (
                    <div className="docs-drag-overlay">
                        <i className="fas fa-cloud-upload-alt"></i>
                        <p>Drop files here to upload</p>
                    </div>
                )}
            </div>
        </div>
    );
}
