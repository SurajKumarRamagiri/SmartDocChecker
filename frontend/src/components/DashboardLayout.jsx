import React, { useState, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './Navbar';
import Notification from './Notification';
import ErrorBoundary from './ErrorBoundary';
import UploadPage from '../pages/UploadPage';
import DashboardPage from '../pages/DashboardPage';
import DocumentsPage from '../pages/DocumentsPage';


/**
 * DashboardLayout – wraps the authenticated area with Navbar + notifications.
 */
function DashboardLayout() {
    const [notifications, setNotifications] = useState([]);

    const showNotification = useCallback((message, type = 'info') => {
        const id = Date.now() + Math.random();
        setNotifications((prev) => [...prev, { id, message, type }]);
    }, []);

    const removeNotification = useCallback((id) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, []);

    return (
        <>
            <Navbar />
            <main className="main-content">
                <ErrorBoundary>
                    <Routes>
                        <Route index element={<DashboardPage />} />
                        <Route path="analyze" element={<UploadPage onNotification={showNotification} />} />
                        <Route path="documents" element={<DocumentsPage onNotification={showNotification} />} />
                    </Routes>
                </ErrorBoundary>
            </main>

            {notifications.map((n, index) => (
                <Notification
                    key={n.id}
                    message={n.message}
                    type={n.type}
                    index={index}
                    onClose={() => removeNotification(n.id)}
                />
            ))}
        </>
    );
}

export default DashboardLayout;
