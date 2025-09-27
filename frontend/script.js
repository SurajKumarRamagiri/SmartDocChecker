class SmartDocChecker {
    constructor() {
        this.currentPage = 'upload';
        this.uploadedFiles = [];
        this.analysisResults = null;
        this.totalCost = 0;
        this.accumulatedDocCost = 0;
        this.accumulatedReportCost = 0;
        this.isAnalyzing = false;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateCostEstimate();
        this.showPage('upload');
    }
    
    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = e.currentTarget.dataset.page;
                this.showPage(page);
            });
        });
        
        // File upload
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const browseLink = document.querySelector('.browse-link');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        browseLink.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
        
        // Analysis button
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.startAnalysis();
        });
        
        // Results actions
        document.getElementById('new-analysis-btn')?.addEventListener('click', () => {
            this.resetAnalysis();
        });
        
        document.getElementById('download-report-btn')?.addEventListener('click', () => {
            this.downloadReport();
        });
        
        // Monitor form
        document.querySelector('.add-monitor-btn')?.addEventListener('click', () => {
            this.addMonitor();
        });
    }
    
    showPage(pageId) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-page="${pageId}"]`).classList.add('active');
        
        // Show page
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        document.getElementById(`${pageId}-page`).classList.add('active');
        
        // Sync billing info when switching to billing page
        if (pageId === 'billing') {
            // Update billing amount and breakdown
            const docCount = this.uploadedFiles.length;
            const docCost = this.accumulatedDocCost;
            const reportCount = this.accumulatedReportCost / 2.0;
            const reportCost = this.accumulatedReportCost;
            const totalCost = docCost + reportCost;
            // Current month amount
            const billingAmount = document.querySelector('#billing-page .billing-amount .amount');
            if (billingAmount) billingAmount.textContent = totalCost.toFixed(2);
            // Breakdown
            const docBreakdown = document.querySelector('#billing-page .billing-breakdown .breakdown-item:nth-child(1) span:last-child');
            if (docBreakdown) docBreakdown.textContent = `$${docCost.toFixed(2)}`;
            const reportBreakdown = document.querySelector('#billing-page .billing-breakdown .breakdown-item:nth-child(2) span:last-child');
            if (reportBreakdown) reportBreakdown.textContent = `$${reportCost.toFixed(2)}`;
            // Usage stats
            const docStat = document.querySelector('#billing-page .usage-stats .stat-card:nth-child(1) h4');
            if (docStat) docStat.textContent = docCount;
            const reportStat = document.querySelector('#billing-page .usage-stats .stat-card:nth-child(2) h4');
            if (reportStat) reportStat.textContent = reportCount;
        }
        this.currentPage = pageId;
    }
    
    handleFiles(files) {
        Array.from(files).forEach(file => {
            if (this.uploadedFiles.length >= 3) {
                this.showNotification('Maximum 3 documents allowed', 'warning');
                return;
            }
            
            if (!this.isValidFile(file)) {
                this.showNotification(`Invalid file type: ${file.name}`, 'error');
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                this.showNotification(`File too large: ${file.name}`, 'error');
                return;
            }
            
            const fileObj = {
                id: Date.now() + Math.random(),
                file: file,
                name: file.name,
                size: this.formatFileSize(file.size),
                type: file.type
            };
            
            this.uploadedFiles.push(fileObj);
            this.renderUploadedFiles();
            this.updateCostEstimate();
            this.checkAnalyzeButton();
        });
    }
    
    isValidFile(file) {
        const validTypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ];
        return validTypes.includes(file.type) || 
               file.name.toLowerCase().endsWith('.pdf') ||
               file.name.toLowerCase().endsWith('.docx') ||
               file.name.toLowerCase().endsWith('.txt');
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    renderUploadedFiles() {
        const container = document.getElementById('uploaded-files');
        container.innerHTML = '';
        
        this.uploadedFiles.forEach(fileObj => {
            const fileElement = document.createElement('div');
            fileElement.className = 'file-item';
            fileElement.innerHTML = `
                <div class="file-info">
                    <div class="file-icon">
                        <i class="fas ${this.getFileIcon(fileObj.file)}"></i>
                    </div>
                    <div class="file-details">
                        <h4>${fileObj.name}</h4>
                        <p>${fileObj.size}</p>
                    </div>
                </div>
                <button class="remove-file" onclick="smartDocChecker.removeFile('${fileObj.id}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(fileElement);
        });
    }
    
    getFileIcon(file) {
        if (file.type.includes('pdf')) return 'fa-file-pdf';
        if (file.type.includes('word')) return 'fa-file-word';
        if (file.type.includes('text')) return 'fa-file-alt';
        return 'fa-file';
    }
    
    removeFile(fileId) {
        this.uploadedFiles = this.uploadedFiles.filter(f => f.id != fileId);
        this.renderUploadedFiles();
        this.updateCostEstimate();
        this.checkAnalyzeButton();
    }
    
    updateCostEstimate() {
    const docCount = this.uploadedFiles.length;
    const docCost = this.accumulatedDocCost;
    const reportCost = this.accumulatedReportCost;
    const totalCost = docCost + reportCost;

    document.getElementById('doc-count').textContent = docCount;
    document.getElementById('doc-cost').textContent = `$${docCost.toFixed(2)}`;
    document.getElementById('report-cost').textContent = `$${reportCost.toFixed(2)}`;
    document.getElementById('total-cost').textContent = `$${totalCost.toFixed(2)}`;

    this.totalCost = totalCost;
    }
    
    checkAnalyzeButton() {
        const analyzeBtn = document.getElementById('analyze-btn');
        analyzeBtn.disabled = this.uploadedFiles.length < 2 || this.isAnalyzing;
    }
    
    async startAnalysis() {
        if (this.uploadedFiles.length < 2) {
            this.showNotification('Please upload at least 2 documents', 'warning');
            return;
        }
        
        this.isAnalyzing = true;
        this.checkAnalyzeButton();
        
        // Show progress section
        document.getElementById('analysis-progress').style.display = 'block';
        document.getElementById('analysis-results').style.display = 'none';
        
        await Promise.all([
            this.runAnalysisSteps(),
            this.generateAnalysisResults()
        ]);
        // On successful analysis, accumulate doc cost
        const docCount = this.uploadedFiles.length;
        this.accumulatedDocCost += docCount * 0.10;
        this.updateCostEstimate();
        
        // Show results
        document.getElementById('analysis-progress').style.display = 'none';
        document.getElementById('analysis-results').style.display = 'block';
        this.renderAnalysisResults();
        
        this.isAnalyzing = false;
        this.checkAnalyzeButton();
    }
    
    async runAnalysisSteps() {
        const steps = [
            { id: 'upload', text: 'Uploading documents...', duration: 1000 },
            { id: 'extract', text: 'Extracting text content...', duration: 1500 },
            { id: 'process', text: 'Running AI analysis...', duration: 3000 },
            { id: 'analyze', text: 'Detecting contradictions...', duration: 2000 },
            { id: 'report', text: 'Generating detailed report...', duration: 1500 }
        ];
        
        let progress = 0;
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            
            // Update active step
            document.querySelectorAll('.progress-step').forEach(s => {
                s.classList.remove('active', 'completed');
            });
            
            // Mark previous steps as completed
            for (let j = 0; j < i; j++) {
                document.querySelector(`[data-step="${steps[j].id}"]`).classList.add('completed');
            }
            
            // Mark current step as active
            document.querySelector(`[data-step="${step.id}"]`).classList.add('active');
            
            // Update progress text
            progressText.textContent = step.text;
            
            // Animate progress bar
            const targetProgress = ((i + 1) / steps.length) * 100;
            await this.animateProgress(progress, targetProgress, step.duration);
            progress = targetProgress;
        }
        
        // Mark all steps as completed
        document.querySelectorAll('.progress-step').forEach(s => {
            s.classList.remove('active');
            s.classList.add('completed');
        });
        
        progressText.textContent = 'Analysis complete!';
    }
    
    animateProgress(from, to, duration) {
        return new Promise(resolve => {
            const startTime = Date.now();
            const progressFill = document.getElementById('progress-fill');
            
            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const currentValue = from + (to - from) * progress;
                
                progressFill.style.width = `${currentValue}%`;
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    resolve();
                }
            };
            
            animate();
        });
    }
    
    async generateAnalysisResults() {
        // Prepare form data for backend
        const formData = new FormData();
        this.uploadedFiles.forEach((fileObj, idx) => {
            formData.append('files', fileObj.file, fileObj.name);
        });

        try {
            const startTime = performance.now();
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                throw new Error('Analysis failed.');
            }
            const result = await response.json();
            const summary = result[result.length - 1];
            const contradictions = result.slice(0, -1);

            const endTime = performance.now();

            
            this.analysisResults = {
                contradictions: contradictions || [],
                totalContradictions: summary.totalContradictions || 0,
                averageConfidence: summary.averageConfidence || 0,
                analysisTime: ((endTime - startTime) / 1000).toFixed(2) + 's',
                timestamp: new Date().toISOString()
            };
            // console.log(this.analysisResults);
        } catch (err) {
            this.showNotification('Failed to analyze documents: ' + err.message, 'error');
            this.analysisResults = {
                contradictions: [],
                totalContradictions: 0,
                averageConfidence: 0,
                analysisTime: '0s',
                timestamp: new Date().toISOString()
            };
        }
        // this.renderAnalysisResults();
    }
    
    renderAnalysisResults() {
        // Update summary
        document.getElementById('contradictions-found').textContent = this.analysisResults.totalContradictions || 0;
    // Convert average confidence to -1 to 1 scale if needed, clamp, then map to 50%-100%
    let avgConf = this.analysisResults.averageConfidence;
    if (Math.abs(avgConf) > 1) avgConf = avgConf / 100;
    avgConf = Math.max(-1, Math.min(1, avgConf));
    // Map -1 to 1 to 50% to 100%
    let avgConfPercent = 50 + ((avgConf + 1) / 2) * 50;
    document.getElementById('confidence-score').textContent = `${avgConfPercent.toFixed(2)}%`;
        document.getElementById('analysis-time').textContent = this.analysisResults.analysisTime || '';

        // Render contradictions list
        const container = document.getElementById('contradictions-list');
        container.innerHTML = '';

        // Flatten all contradiction pairs from the nested structure
        let allPairs = [];
        this.analysisResults.contradictions.forEach((docPair) => {
            if (docPair.contradiction_pairs) {
                allPairs = allPairs.concat(docPair.contradiction_pairs.map(pair => ({
                    ...pair,
                    docPair: docPair.doc_pair
                })));
            }
        });

        allPairs.forEach((contradiction, index) => {
            const contradictionElement = document.createElement('div');
            contradictionElement.className = 'contradiction-item';

            // Convert confidence to -1 to 1 scale, clamp, then map to 50%-100% for display
            let confidence = contradiction.sentence_contradiction_score;
            if (Math.abs(confidence) > 1) confidence = confidence / 100;
            confidence = Math.max(-1, Math.min(1, confidence));
            let confidencePercent = 50 + ((confidence + 1) / 2) * 50;
            contradictionElement.innerHTML = `
                <div class="contradiction-header">
                    <div class="contradiction-type">
                        <span class="type-badge">${contradiction.entity_doc1[1]}</span>
                        <span class="severity-badge low">low</span>
                    </div>
                    <div class="confidence-score">
                        <span>Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                        </div>
                        <span>${confidencePercent.toFixed(2)}%</span>
                    </div>
                </div>
                <div class="contradiction-content">
                    <div class="document-snippet">
                        <h4>Document ${contradiction.docPair[0] + 1}</h4>
                        <p><b>Contradicted Sentence:</b> "${contradiction.sentence_doc1}"</p>
                    </div>
                    <div class="document-snippet">
                        <h4>Document ${contradiction.docPair[1] + 1}</h4>
                        <p><b>Contradicted Sentence:</b> "${contradiction.sentence_doc2}"</p>
                    </div>
                </div>
                <div class="contradiction-explanation">
                    <p>${contradiction.explanation}</p>
                </div>
            `;
            container.appendChild(contradictionElement);
        });
    }

    
    resetAnalysis() {
    this.uploadedFiles = [];
    this.analysisResults = null;
    this.isAnalyzing = false;
    this.accumulatedDocCost = 0;
        
        document.getElementById('uploaded-files').innerHTML = '';
        document.getElementById('analysis-progress').style.display = 'none';
        document.getElementById('analysis-results').style.display = 'none';
        
        this.updateCostEstimate();
        this.checkAnalyzeButton();
        
        // Reset file input
        document.getElementById('file-input').value = '';
        
        this.showNotification('Analysis reset. Ready for new documents.', 'success');
    }
    
    downloadReport() {
    if (!this.analysisResults) return;

    // Add report cost only when downloading, and accumulate it
    const docCount = this.uploadedFiles.length;
    const reportCost = docCount > 0 ? 2.00 : 0;
    this.accumulatedReportCost += reportCost;
    this.updateCostEstimate();

    this.generatePDFReport();
    }
    
    async generatePDFReport() {
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');

        // Constants
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 20;
        const contentWidth = pageWidth - (margin * 2);
        let yPosition = margin;

        // Helper functions same as before
        const checkPageBreak = (requiredHeight = 20) => {
            if (yPosition + requiredHeight > pageHeight - margin) {
                pdf.addPage();
                yPosition = margin;
                return true;
            }
            return false;
        };

        const wrapText = (text, maxWidth, fontSize = 10) => {
            pdf.setFontSize(fontSize);
            return pdf.splitTextToSize(text, maxWidth);
        };

        // Header Section: same as your existing code for title, logo, metadata etc.

        // ---------------------------------------------------------------
        // Executive Summary
        checkPageBreak(40);
        pdf.setFontSize(16);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(37, 99, 235);
        pdf.text('Executive Summary', margin, yPosition);
        yPosition += 10;

        pdf.setFillColor(248, 250, 252);
        pdf.setDrawColor(226, 232, 240);
        pdf.rect(margin, yPosition, contentWidth, 35, 'FD');

        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'normal');

        const summaryY = yPosition + 8;
        pdf.text(`Documents Analyzed: ${this.uploadedFiles.length}`, margin + 5, summaryY);

        // Use analysisResults object properties for summary
        pdf.text(`Contradictions Found: ${this.analysisResults?.totalContradictions ?? 0}`, margin + 5, summaryY + 7);
        pdf.text(`Average Confidence: ${typeof this.analysisResults?.averageConfidence === 'number' ? this.analysisResults.averageConfidence.toFixed(2) : '0.00'}%`, margin + 5, summaryY + 14);
        pdf.text(`Analysis Time: ${this.analysisResults?.analysisTime ?? ''}`, margin + 5, summaryY + 21);

        yPosition += 50;

        // Documents Analyzed: same as your code...

        // ---------------------------------------------------------------
        // Contradictions Detected
        const contradictionsList = this.analysisResults?.contradictions ?? [];
        if (contradictionsList.length > 0) {
            checkPageBreak(30);
            pdf.setFontSize(14);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(37, 99, 235);
            pdf.text('Contradictions Detected', margin, yPosition);

            yPosition += 15;

            contradictionsList.forEach((docPair, pairIdx) => {
                if (!docPair.contradiction_pairs) return;

                docPair.contradiction_pairs.forEach((contradiction, index) => {
                    checkPageBreak(70);

                    // Draw contradiction header box
                    pdf.setFillColor(254, 242, 242);
                    pdf.setDrawColor(239, 68, 68);
                    pdf.rect(margin, yPosition, contentWidth, 10, 'FD');

                    pdf.setFontSize(12);
                    pdf.setFont('helvetica', 'bold');
                    pdf.setTextColor(220, 38, 38);
                    pdf.text(`Contradiction #${pairIdx + 1}.${index + 1}`, margin + 3, yPosition + 7);

                    // Entity type badge
                    pdf.setFontSize(9);
                    pdf.setFont('helvetica', 'bold');
                    pdf.setFillColor(243, 244, 246);
                    pdf.setTextColor(51, 65, 85);
                    pdf.rect(margin + 80, yPosition + 2, 40, 5, 'F');
                    pdf.text(contradiction.entity_doc1[1].toUpperCase(), margin + 82, yPosition + 6);

                    // Confidence score
                    pdf.setFillColor(255, 255, 255);
                    pdf.setTextColor(0, 0, 0);
                    pdf.text(`Confidence: ${contradiction.sentence_contradiction_score.toFixed(2)}`, margin + contentWidth - 50, yPosition + 6);

                    yPosition += 15;

                    // Document 1 snippet
                    pdf.setFontSize(10);
                    pdf.setFont('helvetica', 'bold');
                    pdf.setTextColor(0, 0, 0);
                    pdf.text(`Document ${docPair.doc_pair[0] + 1}:`, margin + 5, yPosition);
                    pdf.setFont('helvetica', 'normal');
                    pdf.setFontSize(9);
                    pdf.setTextColor(100, 116, 139);
                    pdf.text(wrapText(`"${contradiction.sentence_doc1}"`, contentWidth - 10, 9), margin + 10, yPosition + 5);

                    yPosition += 35;

                    // Document 2 snippet
                    pdf.setFont('helvetica', 'bold');
                    pdf.setTextColor(0, 0, 0);
                    pdf.text(`Document ${docPair.doc_pair[1] + 1}:`, margin + 5, yPosition);
                    pdf.setFont('helvetica', 'normal');
                    pdf.setFontSize(9);
                    pdf.setTextColor(100, 116, 139);
                    pdf.text(wrapText(`"${contradiction.sentence_doc2}"`, contentWidth - 10, 9), margin + 10, yPosition + 5);

                    yPosition += 35;

                    // Explanation box
                    checkPageBreak(20);
                    pdf.setFillColor(255, 251, 235);
                    pdf.setDrawColor(245, 158, 11);
                    const explanationText = wrapText(contradiction.explanation, contentWidth - 10, 9);
                    const explanationHeight = explanationText.length * 5;
                    pdf.rect(margin, yPosition, contentWidth, explanationHeight, 'FD');
                    pdf.setFontSize(9);
                    pdf.setFont('helvetica', 'bold');
                    pdf.setTextColor(146, 64, 14);
                    pdf.text('Analysis:', margin + 3, yPosition + 5);

                    pdf.setFont('helvetica', 'normal');
                    pdf.text(explanationText, margin + 3, yPosition + 10);

                    yPosition += explanationHeight + 15;
                });
            });
        }

        // Recommendations and footer same as your existing code...

        // Save PDF
        const fileName = `smart-doc-analysis-${Date.now()}.pdf`;
        pdf.save(fileName);

        this.showNotification('PDF report downloaded successfully', 'success');
    }

    
    getTypeColor(type) {
        const colors = {
            temporal: { bg: [254, 243, 199], text: [146, 64, 14] },
            numerical: { bg: [219, 234, 254], text: [29, 78, 216] },
            requirement: { bg: [252, 231, 243], text: [190, 24, 93] },
            semantic: { bg: [209, 250, 229], text: [6, 95, 70] }
        };
        return colors[type] || colors.semantic;
    }
    
    getSeverityColor(severity) {
        const colors = {
            high: { bg: [254, 226, 226], text: [220, 38, 38] },
            medium: { bg: [254, 243, 199], text: [217, 119, 6] },
            low: { bg: [224, 242, 254], text: [3, 105, 161] }
        };
        return colors[severity] || colors.medium;
    }
    
    addMonitor() {
        const url = document.getElementById('monitor-url').value;
        const name = document.getElementById('monitor-name').value;
        const frequency = document.getElementById('check-frequency').value;
        
        if (!url || !name) {
            this.showNotification('Please fill in all required fields', 'warning');
            return;
        }
        
        if (!this.isValidUrl(url)) {
            this.showNotification('Please enter a valid URL', 'error');
            return;
        }
        
        // Simulate adding monitor
        this.showNotification(`Monitor "${name}" added successfully`, 'success');
        
        // Reset form
        document.getElementById('monitor-url').value = '';
        document.getElementById('monitor-name').value = '';
        document.getElementById('check-frequency').value = 'daily';
    }
    
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 2rem;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
            backdrop-filter: blur(10px);
        `;
        
        // Add close functionality
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        });
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
        
        // Add animations to document if not exists
        if (!document.querySelector('#notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'notification-styles';
            styles.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                .notification-content {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }
                .notification-close {
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    padding: 0.25rem;
                    border-radius: 4px;
                    transition: background 0.2s ease;
                }
                .notification-close:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'fa-check-circle';
            case 'error': return 'fa-exclamation-circle';
            case 'warning': return 'fa-exclamation-triangle';
            default: return 'fa-info-circle';
        }
    }
    
    getNotificationColor(type) {
        switch (type) {
            case 'success': return '#10b981';
            case 'error': return '#ef4444';
            case 'warning': return '#f59e0b';
            default: return '#2563eb';
        }
    }
}

// Initialize the application
const smartDocChecker = new SmartDocChecker();