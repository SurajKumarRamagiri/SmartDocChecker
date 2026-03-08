import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
    { path: '/app', icon: 'fas fa-chart-line', label: 'Dashboard', end: true },
    { path: '/app/documents', icon: 'fas fa-folder-open', label: 'Documents' },
    { path: '/app/analyze', icon: 'fas fa-cloud-upload-alt', label: 'Analyze' }
    // { path: '/app/monitor', icon: 'fas fa-binoculars', label: 'Monitor' },
    // { path: '/app/billing', icon: 'fas fa-credit-card', label: 'Billing' },
];

/**
 * Navbar – top navigation bar using React Router.
 *
 * Uses useLocation() to determine the active link.
 * Shows user role badge and logout button.
 */
export default function Navbar() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const isActive = (item) => {
        if (item.end) return location.pathname === item.path;
        return location.pathname.startsWith(item.path);
    };

    return (
        <nav className="navbar">
            <div className="nav-container">
                <Link to="/" className="nav-brand">
                    <i className="fas fa-file-shield"></i>
                    Smart Doc Checker
                </Link>

                <div className="nav-links">
                    {NAV_ITEMS.map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={`nav-btn ${isActive(item) ? 'active' : ''}`}
                        >
                            <i className={item.icon}></i>
                            {item.label}
                        </Link>
                    ))}
                </div>

                <div className="user-profile">
                    {user && (
                        <>
                            <span className="role-badge">{user.name}</span>
                            <button className="logout-btn" onClick={handleLogout} title="Log out" aria-label="Log out">
                                <i className="fas fa-sign-out-alt"></i>
                            </button>
                        </>
                    )}
                    <div className="user-avatar">
                        <i className="fas fa-user"></i>
                    </div>
                </div>
            </div>
        </nav>
    );
}
