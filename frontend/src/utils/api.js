const API_BASE = '';

/**
 * Centralized fetch wrapper with auth, error handling, and auto-logout on 401.
 */
async function fetchWithAuth(url, options = {}, token = null) {
    const headers = { ...options.headers };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${url}`, { ...options, headers });

    if (response.status === 401) {
        // Token expired or invalid — clear storage and redirect
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Session expired. Please log in again.');
    }

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed (${response.status})`);
    }

    // Handle empty / non-JSON responses (e.g. 204 No Content)
    const contentType = response.headers.get('content-type') || '';
    if (response.status === 204 || !contentType.includes('application/json')) {
        return {};
    }

    return response.json();
}

/**
 * Send files to the backend for contradiction analysis.
 * @deprecated Use analyzeMultiDocuments() instead
 */
export async function analyzeDocuments(files) {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file, file.name);
    });

    return fetchWithAuth('/api/analyze', {
        method: 'POST',
        body: formData,
    });
}

/**
 * Start multi-document comparison (background processing).
 * @param {string[]} documentIds - Array of document IDs to compare.
 * @param {string} token - JWT token.
 * @returns {Promise<{ comparison_id: string }>}
 */
export async function analyzeMultiDocuments(documentIds, token) {
    return fetchWithAuth('/api/analyze/multi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_ids: documentIds }),
    }, token);
}

/**
 * Poll comparison status.
 * @param {string} comparisonId
 * @param {string} token
 * @returns {Promise<{ status: string, error_message: string|null }>}
 */
export async function getComparisonStatus(comparisonId, token) {
    return fetchWithAuth(`/api/comparison/${comparisonId}/status`, {}, token);
}

/**
 * Fetch comparison results.
 * @param {string} comparisonId
 * @param {string} token
 * @returns {Promise<Object>}
 */
export async function getComparisonResults(comparisonId, token) {
    return fetchWithAuth(`/api/comparison/${comparisonId}/results`, {}, token);
}

/**
 * Fetch user's documents from the backend.
 */
export async function fetchDocuments(token) {
    return fetchWithAuth('/api/documents/', {}, token);
}

/**
 * Upload a single document to the backend.
 */
export async function uploadDocument(file, token) {
    const formData = new FormData();
    formData.append('file', file, file.name);

    return fetchWithAuth('/api/documents/upload', {
        method: 'POST',
        body: formData,
    }, token);
}

/**
 * Get a signed download URL for a document.
 */
export async function downloadDocument(docId, token) {
    return fetchWithAuth(`/api/documents/${docId}/download`, {}, token);
}

/**
 * Delete a document.
 */
export async function deleteDocument(docId, token) {
    return fetchWithAuth(`/api/documents/${docId}`, {
        method: 'DELETE',
    }, token);
}

/**
 * Trigger single document analysis.
 */
export async function analyzeSingleDocument(documentId, token) {
    return fetchWithAuth(`/api/analyze/single?document_id=${documentId}`, {
        method: 'POST',
    }, token);
}

/**
 * Get document status (for polling during analysis).
 * Returns { status, processing_stage, progress_percent }
 */
export async function getDocumentStatus(documentId, token) {
    const doc = await fetchWithAuth(`/api/documents/${documentId}`, {}, token);
    return {
        status: doc.status,
        processing_stage: doc.processing_stage || null,
        progress_percent: doc.progress_percent || 0,
    };
}

/**
 * Get analysis results for a document.
 */
export async function getAnalysisResults(documentId, token) {
    return fetchWithAuth(`/api/documents/${documentId}/results`, {}, token);
}

/**
 * Fetch dashboard statistics from the backend.
 */
export async function fetchDashboardStats(token) {
    return fetchWithAuth('/api/dashboard/stats', {}, token);
}
