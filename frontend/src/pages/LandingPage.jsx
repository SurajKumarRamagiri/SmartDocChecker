import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/Button';
import './LandingPage.css';

/**
 * LandingPage – public marketing page with 6 sections:
 * Hero, How It Works, Features, Security, Demo, Footer.
 */

const STEPS = [
    {
        icon: 'fas fa-cloud-upload-alt',
        title: 'Upload Documents',
        desc: 'Upload up to 3 policy documents in PDF, DOCX, or TXT format. Your files are processed securely.',
    },
    {
        icon: 'fas fa-brain',
        title: 'AI Analyzes Clauses',
        desc: 'Our engine extracts rules, dates, and requirements from every clause using NLP and entity recognition.',
    },
    {
        icon: 'fas fa-exclamation-triangle',
        title: 'View Contradictions',
        desc: 'Contradictions are highlighted with severity levels, confidence scores, and side-by-side comparisons.',
    },
];

const FEATURES = [
    {
        icon: 'fas fa-search-plus',
        title: 'Clause-Level Detection',
        desc: 'Pinpoints the exact clauses that conflict, not just the document — so you know precisely what to fix.',
    },
    {
        icon: 'fas fa-copy',
        title: 'Cross-Document Comparison',
        desc: 'Compare policies, handbooks, and contracts against each other to catch hidden inconsistencies.',
    },
    {
        icon: 'fas fa-percentage',
        title: 'Confidence Scoring',
        desc: 'Every contradiction includes a 0–100 confidence score so you can prioritize what matters most.',
    },
    {
        icon: 'fas fa-layer-group',
        title: 'Severity Classification',
        desc: 'Issues are rated from Low to Critical, helping your team triage and resolve conflicts efficiently.',
    },
    {
        icon: 'fas fa-file-pdf',
        title: 'PDF & CSV Reports',
        desc: 'Export analysis results as professional reports for audits, compliance, or stakeholder reviews.',
    },
    {
        icon: 'fas fa-binoculars',
        title: 'External Monitoring',
        desc: 'Track changes in external policy pages and get alerted when documents are updated silently.',
    },
];

const SECURITY_ITEMS = [
    { icon: 'fas fa-lock', text: 'End-to-end secure document processing' },
    { icon: 'fas fa-eye-slash', text: 'No public file URLs — files are never exposed' },
    { icon: 'fas fa-user-shield', text: 'Role-based access: Admin, Reviewer, Viewer' },
    { icon: 'fas fa-trash-alt', text: 'Automatic file deletion policy option' },
];

export default function LandingPage() {
    return (
        <div className="landing">
            {/* ── Sticky Header ── */}
            <header className="landing-header">
                <div className="landing-header__inner">
                    <Link to="/" className="landing-logo">
                        <i className="fas fa-file-shield"></i>
                        Smart Doc Checker
                    </Link>
                    <div className="landing-header__actions">
                        <Link to="/login" className="landing-link">Sign In</Link>
                        <Link to="/login">
                            <Button variant="primary" size="sm">Get Started</Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* ── Hero Section ── */}
            <section className="hero">
                <div className="hero__content">
                    <div className="hero__badge">
                        <i className="fas fa-bolt"></i> AI-Powered Document Intelligence
                    </div>
                    <h1 className="hero__title">
                        Detect Policy Contradictions<br />
                        <span className="hero__accent">with Precision</span>
                    </h1>
                    <p className="hero__subtitle">
                        Upload documents. Analyze clauses. Identify conflicts instantly.<br />
                        Built for compliance teams, legal reviewers, and policy managers.
                    </p>
                    <div className="hero__cta">
                        <Link to="/login">
                            <Button variant="primary" size="lg" icon="fas fa-rocket">Get Started</Button>
                        </Link>
                        <Link to="/login">
                            <Button variant="secondary" size="lg" icon="fas fa-sign-in-alt">Sign In</Button>
                        </Link>
                    </div>
                </div>

                {/* Illustration / mock */}
                <div className="hero__visual">
                    <div className="hero-card">
                        <div className="hero-card__header">
                            <div className="hero-card__dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span className="hero-card__title">Analysis Results</span>
                        </div>
                        <div className="hero-card__body">
                            <div className="hero-card__row">
                                <span className="badge badge--red">High</span>
                                <span>Date conflict in Section 4.2 vs 7.1</span>
                                <span className="hero-card__score">94%</span>
                            </div>
                            <div className="hero-card__row">
                                <span className="badge badge--yellow">Medium</span>
                                <span>Requirement mismatch in eligibility clause</span>
                                <span className="hero-card__score">78%</span>
                            </div>
                            <div className="hero-card__row">
                                <span className="badge badge--blue">Low</span>
                                <span>Terminology inconsistency across documents</span>
                                <span className="hero-card__score">62%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── How It Works ── */}
            <section className="section how-it-works" id="how-it-works">
                <h2 className="section__title">How It Works</h2>
                <p className="section__subtitle">Three steps to conflict-free policies</p>
                <div className="steps">
                    {STEPS.map((step, i) => (
                        <div className="step-card" key={i}>
                            <div className="step-card__number">{i + 1}</div>
                            <div className="step-card__icon"><i className={step.icon}></i></div>
                            <h3>{step.title}</h3>
                            <p>{step.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── Features ── */}
            <section className="section features" id="features">
                <h2 className="section__title">Powerful Features</h2>
                <p className="section__subtitle">Everything you need for rigorous policy analysis</p>
                <div className="features-grid">
                    {FEATURES.map((feat, i) => (
                        <div className="feature-card" key={i}>
                            <div className="feature-card__icon"><i className={feat.icon}></i></div>
                            <h3>{feat.title}</h3>
                            <p>{feat.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── Security ── */}
            <section className="section security" id="security">
                <div className="security__inner">
                    <div className="security__text">
                        <h2 className="section__title section__title--left">Enterprise-Grade Security</h2>
                        <p className="section__subtitle section__subtitle--left">
                            Your documents are handled with the same rigor you apply to your policies.
                        </p>
                    </div>
                    <div className="security__items">
                        {SECURITY_ITEMS.map((item, i) => (
                            <div className="security-item" key={i}>
                                <div className="security-item__icon"><i className={item.icon}></i></div>
                                <span>{item.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Demo Preview ── */}
            <section className="section demo" id="demo">
                <h2 className="section__title">See It in Action</h2>
                <p className="section__subtitle">Upload a sample document and watch the analysis unfold</p>
                <div className="demo__preview">
                    <div className="demo-window">
                        <div className="demo-window__header">
                            <div className="hero-card__dots"><span></span><span></span><span></span></div>
                            <span>Smart Doc Checker — Live Demo</span>
                        </div>
                        <div className="demo-window__body">
                            <div className="demo-stat">
                                <span className="demo-stat__value">3</span>
                                <span className="demo-stat__label">Contradictions Found</span>
                            </div>
                            <div className="demo-stat">
                                <span className="demo-stat__value">87%</span>
                                <span className="demo-stat__label">Avg Confidence</span>
                            </div>
                            <div className="demo-stat">
                                <span className="demo-stat__value">2.4s</span>
                                <span className="demo-stat__label">Analysis Time</span>
                            </div>
                        </div>
                    </div>
                    <Link to="/login">
                        <Button variant="primary" size="lg" icon="fas fa-rocket">Get Started Free</Button>
                    </Link>
                </div>
            </section>

            {/* ── Footer ── */}
            <footer className="landing-footer">
                <div className="landing-footer__inner">
                    <div className="landing-footer__brand">
                        <i className="fas fa-file-shield"></i>
                        Smart Doc Checker
                    </div>
                    <div className="landing-footer__links">
                        <a href="#how-it-works">About</a>
                        <a href="https://github.com" target="_blank" rel="noopener noreferrer">GitHub</a>
                        <a href="#security">Privacy Policy</a>
                    </div>
                    <p className="landing-footer__copy">&copy; 2025 SmartDocChecker. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}
