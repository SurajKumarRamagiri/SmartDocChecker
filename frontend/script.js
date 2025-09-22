class SmartDocChecker {
    constructor() {
        this.currentPage = 'upload';
        this.uploadedFiles = [];
        this.analysisResults = null;
        this.totalCost = 0;
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
        const docCost = docCount * 0.10;
        const reportCost = docCount > 0 ? 2.00 : 0;
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
        
        // Simulate analysis steps
        await this.runAnalysisSteps();
        
        // Generate results
        this.generateAnalysisResults();
        
        // Show results
        document.getElementById('analysis-progress').style.display = 'none';
        document.getElementById('analysis-results').style.display = 'block';
        
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
            const endTime = performance.now();

            // Expecting result: { contradictions: [...], ... }
            this.analysisResults = {
                contradictions: result.contradictions || [],
                totalContradictions: result.contradictions ? result.contradictions.length : 0,
                averageConfidence: result.averageConfidence || 0,
                analysisTime: ((endTime - startTime) / 1000).toFixed(2) + 's',
                timestamp: new Date().toISOString()
            };
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
        this.renderAnalysisResults();
    }
    
    renderAnalysisResults() {
        // Update summary
        document.getElementById('contradictions-found').textContent = this.analysisResults.totalContradictions;
        document.getElementById('confidence-score').textContent = `${this.analysisResults.averageConfidence}%`;
        document.getElementById('analysis-time').textContent = this.analysisResults.analysisTime;
        
        // Render contradictions list
        const container = document.getElementById('contradictions-list');
        container.innerHTML = '';
        
        this.analysisResults.contradictions.forEach((contradiction, index) => {
            const contradictionElement = document.createElement('div');
            contradictionElement.className = 'contradiction-item';
            contradictionElement.innerHTML = `
                <div class="contradiction-header">
                    <div class="contradiction-type">
                        <span class="type-badge ${contradiction.type}">${contradiction.type}</span>
                        <span class="severity-badge ${contradiction.severity}">${contradiction.severity}</span>
                    </div>
                    <div class="confidence-score">
                        <span>Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${contradiction.confidence}%"></div>
                        </div>
                        <span>${contradiction.confidence}%</span>
                    </div>
                </div>
                
                <div class="contradiction-content">
                    <div class="document-snippet">
                        <h4>${contradiction.document1.name}</h4>
                        <p>"${contradiction.document1.text}"</p>
                    </div>
                    <div class="document-snippet">
                        <h4>${contradiction.document2.name}</h4>
                        <p>"${contradiction.document2.text}"</p>
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
        
        this.generatePDFReport();
    }
    
    async generatePDFReport() {
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        
        // PDF styling constants
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 20;
        const contentWidth = pageWidth - (margin * 2);
        let yPosition = margin;
        
        // Helper function to add new page if needed
        const checkPageBreak = (requiredHeight = 20) => {
            if (yPosition + requiredHeight > pageHeight - margin) {
                pdf.addPage();
                yPosition = margin;
                return true;
            }
            return false;
        };
        
        // Helper function to wrap text
        const wrapText = (text, maxWidth, fontSize = 10) => {
            pdf.setFontSize(fontSize);
            return pdf.splitTextToSize(text, maxWidth);
        };
        
        // Header
        pdf.setFillColor(37, 99, 235); // Primary blue
        pdf.rect(0, 0, pageWidth, 40, 'F');
        
        pdf.setTextColor(255, 255, 255);
        pdf.setFontSize(24);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Smart Doc Checker', margin, 25);
        
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'normal');
        pdf.text('Document Contradiction Analysis Report', margin, 32);
        
        yPosition = 55;
        
        // Report metadata
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        
        const reportDate = new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        pdf.text(`Generated: ${reportDate}`, margin, yPosition);
        pdf.text(`Analysis Engine: Smart Doc Checker AI v2.1`, margin, yPosition + 5);
        pdf.text(`Total Cost: $${this.totalCost.toFixed(2)}`, margin, yPosition + 10);
        
        yPosition += 25;
        
        // Executive Summary
        checkPageBreak(40);
        pdf.setFontSize(16);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(37, 99, 235);
        pdf.text('Executive Summary', margin, yPosition);
        
        yPosition += 10;
        
        // Summary box
        pdf.setFillColor(248, 250, 252);
        pdf.setDrawColor(226, 232, 240);
        pdf.rect(margin, yPosition, contentWidth, 35, 'FD');
        
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'normal');
        
        const summaryY = yPosition + 8;
        pdf.text(`Documents Analyzed: ${this.uploadedFiles.length}`, margin + 5, summaryY);
        pdf.text(`Contradictions Found: ${this.analysisResults.totalContradictions}`, margin + 5, summaryY + 7);
        pdf.text(`Average Confidence: ${this.analysisResults.averageConfidence}%`, margin + 5, summaryY + 14);
        pdf.text(`Analysis Time: ${this.analysisResults.analysisTime}`, margin + 5, summaryY + 21);
        
        yPosition += 50;
        
        // Documents Analyzed
        checkPageBreak(30);
        pdf.setFontSize(14);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(37, 99, 235);
        pdf.text('Documents Analyzed', margin, yPosition);
        
        yPosition += 10;
        
        this.uploadedFiles.forEach((file, index) => {
            checkPageBreak(15);
            pdf.setFontSize(11);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(0, 0, 0);
            pdf.text(`${index + 1}. ${file.name}`, margin + 5, yPosition);
            
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(10);
            pdf.setTextColor(100, 116, 139);
            pdf.text(`Size: ${file.size} | Type: ${file.file.type}`, margin + 10, yPosition + 5);
            
            yPosition += 15;
        });
        
        yPosition += 10;
        
        // Contradictions Found
        if (this.analysisResults.contradictions.length > 0) {
            checkPageBreak(30);
            pdf.setFontSize(14);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(37, 99, 235);
            pdf.text('Contradictions Detected', margin, yPosition);
            
            yPosition += 15;
            
            this.analysisResults.contradictions.forEach((contradiction, index) => {
                checkPageBreak(60);
                
                // Contradiction header
                pdf.setFillColor(254, 242, 242);
                pdf.setDrawColor(239, 68, 68);
                pdf.rect(margin, yPosition, contentWidth, 8, 'FD');
                
                pdf.setFontSize(12);
                pdf.setFont('helvetica', 'bold');
                pdf.setTextColor(220, 38, 38);
                pdf.text(`Contradiction #${index + 1}`, margin + 3, yPosition + 5);
                
                // Type and severity badges
                const typeColor = this.getTypeColor(contradiction.type);
                const severityColor = this.getSeverityColor(contradiction.severity);
                
                pdf.setFontSize(9);
                pdf.setFont('helvetica', 'bold');
                
                // Type badge
                pdf.setFillColor(...typeColor.bg);
                pdf.setTextColor(...typeColor.text);
                pdf.rect(margin + 80, yPosition + 1, 25, 6, 'F');
                pdf.text(contradiction.type.toUpperCase(), margin + 82, yPosition + 4.5);
                
                // Severity badge
                pdf.setFillColor(...severityColor.bg);
                pdf.setTextColor(...severityColor.text);
                pdf.rect(margin + 110, yPosition + 1, 25, 6, 'F');
                pdf.text(contradiction.severity.toUpperCase(), margin + 112, yPosition + 4.5);
                
                // Confidence score
                pdf.setTextColor(0, 0, 0);
                pdf.text(`Confidence: ${contradiction.confidence}%`, margin + 140, yPosition + 4.5);
                
                yPosition += 15;
                
                // Document snippets
                pdf.setFontSize(10);
                pdf.setFont('helvetica', 'bold');
                pdf.setTextColor(0, 0, 0);
                pdf.text('Document 1:', margin + 5, yPosition);
                
                pdf.setFont('helvetica', 'normal');
                pdf.setFontSize(9);
                pdf.setTextColor(100, 116, 139);
                pdf.text(contradiction.document1.name, margin + 25, yPosition);
                
                yPosition += 5;
                
                pdf.setFontSize(9);
                pdf.setTextColor(0, 0, 0);
                const doc1Text = wrapText(`"${contradiction.document1.text}"`, contentWidth - 10, 9);
                pdf.text(doc1Text, margin + 5, yPosition);
                yPosition += doc1Text.length * 4 + 5;
                
                checkPageBreak(20);
                
                pdf.setFont('helvetica', 'bold');
                pdf.text('Document 2:', margin + 5, yPosition);
                
                pdf.setFont('helvetica', 'normal');
                pdf.setFontSize(9);
                pdf.setTextColor(100, 116, 139);
                pdf.text(contradiction.document2.name, margin + 25, yPosition);
                
                yPosition += 5;
                
                pdf.setFontSize(9);
                pdf.setTextColor(0, 0, 0);
                const doc2Text = wrapText(`"${contradiction.document2.text}"`, contentWidth - 10, 9);
                pdf.text(doc2Text, margin + 5, yPosition);
                yPosition += doc2Text.length * 4 + 5;
                
                // Explanation
                checkPageBreak(15);
                pdf.setFillColor(255, 251, 235);
                pdf.setDrawColor(245, 158, 11);
                
                const explanationText = wrapText(contradiction.explanation, contentWidth - 10, 9);
                const explanationHeight = explanationText.length * 4 + 6;
                
                pdf.rect(margin, yPosition, contentWidth, explanationHeight, 'FD');
                
                pdf.setFontSize(9);
                pdf.setFont('helvetica', 'bold');
                pdf.setTextColor(146, 64, 14);
                pdf.text('Analysis:', margin + 3, yPosition + 4);
                
                pdf.setFont('helvetica', 'normal');
                pdf.text(explanationText, margin + 3, yPosition + 8);
                
                yPosition += explanationHeight + 15;
            });
        }
        
        // Recommendations
        checkPageBreak(40);
        pdf.setFontSize(14);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(37, 99, 235);
        pdf.text('Recommendations', margin, yPosition);
        
        yPosition += 15;
        
        const recommendations = [
            'Review and align deadline specifications across all documents',
            'Establish consistent attendance policies',
            'Standardize penalty rates for late submissions',
            'Create a master policy document to prevent future contradictions',
            'Implement regular document review cycles',
            'Consider using document version control systems'
        ];
        
        recommendations.forEach((recommendation, index) => {
            checkPageBreak(10);
            pdf.setFontSize(10);
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(0, 0, 0);
            
            const recText = wrapText(`${index + 1}. ${recommendation}`, contentWidth - 10, 10);
            pdf.text(recText, margin + 5, yPosition);
            yPosition += recText.length * 4 + 3;
        });
        
        // Footer on last page
        yPosition = pageHeight - 30;
        pdf.setFillColor(248, 250, 252);
        pdf.rect(0, yPosition, pageWidth, 30, 'F');
        
        pdf.setFontSize(8);
        pdf.setTextColor(100, 116, 139);
        pdf.setFont('helvetica', 'normal');
        pdf.text('Generated by Smart Doc Checker AI v2.1', margin, yPosition + 10);
        pdf.text(`Report ID: SDC-${Date.now()}`, margin, yPosition + 15);
        pdf.text('For questions or support, contact: support@smartdocchecker.com', margin, yPosition + 20);
        
        // Save the PDF
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