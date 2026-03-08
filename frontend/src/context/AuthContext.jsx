import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);
const API_BASE = import.meta.env.VITE_API_BASE || '';

/**
 * AuthProvider – wraps the app and provides authentication state.
 *
 * Exposes: { user, token, loading, login, signup, logout }
 *
 * On mount it checks localStorage for a saved token and validates it
 * by calling GET /api/auth/me.
 */
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(() => localStorage.getItem('token'));
    const [loading, setLoading] = useState(true);

    // Listen for forced logout from API layer (e.g. 401 responses)
    useEffect(() => {
        const handleForceLogout = () => {
            localStorage.removeItem('token');
            setToken(null);
            setUser(null);
        };
        window.addEventListener('auth:logout', handleForceLogout);
        return () => window.removeEventListener('auth:logout', handleForceLogout);
    }, []);

    // Validate token on mount
    useEffect(() => {
        if (!token) {
            setLoading(false);
            return;
        }

        fetch(`${API_BASE}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error('Invalid token');
                return res.json();
            })
            .then((data) => {
                setUser(data);
            })
            .catch(() => {
                // Token expired or invalid — clear it
                localStorage.removeItem('token');
                setToken(null);
                setUser(null);
            })
            .finally(() => setLoading(false));
    }, [token]);

    const login = useCallback(async (email, password) => {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        const data = await res.json().catch(() => null);

        if (!res.ok) {
            throw new Error(data?.detail || 'Login failed');
        }
        if (!data || !data.access_token) {
            throw new Error('Invalid response from server');
        }

        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser(data.user);
        return data;
    }, []);

    const signup = useCallback(async (name, email, password) => {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password }),
        });

        const data = await res.json().catch(() => null);

        if (!res.ok) {
            throw new Error(data?.detail || 'Registration failed');
        }
        if (!data || !data.access_token) {
            throw new Error('Invalid response from server');
        }

        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser(data.user);
        return data;
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

/**
 * useAuth – convenience hook to consume auth context.
 */
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
    return ctx;
}
