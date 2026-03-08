import React, { useEffect, useState, useCallback } from 'react';

/**
 * Notification – a toast-style notification that slides in from the right and auto-dismisses.
 *
 * Props:
 *   message  – string text to display
 *   type     – 'success' | 'error' | 'warning' | 'info'
 *   onClose  – callback when the notification is dismissed
 */

const ICONS = {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle',
};

const COLORS = {
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#2563eb',
};

export default function Notification({ message, type = 'info', onClose, index = 0 }) {
    const [exiting, setExiting] = useState(false);

    const dismiss = useCallback(() => {
        setExiting(true);
        setTimeout(() => onClose(), 300);
    }, [onClose]);

    useEffect(() => {
        const timer = setTimeout(dismiss, 5000);
        return () => clearTimeout(timer);
    }, [dismiss]);

    return (
        <div
            className="notification-toast"
            style={{
                position: 'fixed',
                top: `${100 + index * 80}px`,
                right: '2rem',
                background: COLORS[type] || COLORS.info,
                color: 'white',
                padding: '1rem 1.5rem',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
                zIndex: 10000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
                maxWidth: '400px',
                animation: exiting ? 'slideOutRight 0.3s ease forwards' : 'slideInRight 0.3s ease',
                backdropFilter: 'blur(10px)',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <i className={`fas ${ICONS[type] || ICONS.info}`}></i>
                <span>{message}</span>
            </div>
            <button
                onClick={dismiss}
                aria-label="Dismiss notification"
                style={{
                    background: 'none',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer',
                    padding: '0.25rem',
                    borderRadius: '4px',
                }}
            >
                <i className="fas fa-times"></i>
            </button>
        </div>
    );
}
