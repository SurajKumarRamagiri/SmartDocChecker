import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import Input from '../components/Input';
import './AuthPage.css';

/**
 * AuthPage – Login / Signup page with toggle.
 *
 * On success → redirects to /app (or the page they were trying to reach).
 */
export default function AuthPage() {
    const [mode, setMode] = useState('login'); // 'login' | 'signup'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});

    const { login, signup } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from?.pathname || '/app';

    // ── Validation ──
    const validate = () => {
        const errs = {};

        if (!email.trim()) errs.email = 'Email is required';
        else if (!/\S+@\S+\.\S+/.test(email)) errs.email = 'Enter a valid email address';

        if (!password) errs.password = 'Password is required';
        else if (password.length < 8) errs.password = 'Password must be at least 8 characters';

        if (mode === 'signup') {
            if (!name.trim()) errs.name = 'Name is required';
            if (!confirmPassword) errs.confirmPassword = 'Please confirm your password';
            else if (password !== confirmPassword) errs.confirmPassword = 'Passwords do not match';
        }

        setFieldErrors(errs);
        return Object.keys(errs).length === 0;
    };

    // ── Submit ──
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (!validate()) return;

        setLoading(true);
        try {
            if (mode === 'login') {
                await login(email, password);
            } else {
                await signup(name, email, password);
            }
            navigate(from, { replace: true });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const switchMode = () => {
        setMode((prev) => (prev === 'login' ? 'signup' : 'login'));
        setError('');
        setFieldErrors({});
    };

    return (
        <div className="auth-page">
            {/* Background decoration */}
            <div className="auth-bg">
                <div className="auth-bg__circle auth-bg__circle--1"></div>
                <div className="auth-bg__circle auth-bg__circle--2"></div>
            </div>

            <div className="auth-card">
                <Link to="/" className="auth-card__logo">
                    <i className="fas fa-file-shield"></i>
                    Smart Doc Checker
                </Link>

                <h1 className="auth-card__title">
                    {mode === 'login' ? 'Welcome back' : 'Create an account'}
                </h1>
                <p className="auth-card__subtitle">
                    {mode === 'login'
                        ? 'Sign in to access your dashboard'
                        : 'Start detecting policy contradictions'}
                </p>

                {error && (
                    <div className="auth-error">
                        <i className="fas fa-exclamation-circle"></i>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form" noValidate>
                    <Input
                        label="Email"
                        type="email"
                        icon="fas fa-envelope"
                        placeholder="you@company.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        error={fieldErrors.email}
                        autoComplete="email"
                    />

                    <Input
                        label="Password"
                        type="password"
                        icon="fas fa-lock"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        error={fieldErrors.password}
                        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    />

                    {mode === 'signup' && (
                        <>
                            <Input
                                label="Full Name"
                                type="text"
                                icon="fas fa-user"
                                placeholder="John Doe"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                error={fieldErrors.name}
                                autoComplete="name"
                            />

                            <Input
                                label="Confirm Password"
                                type="password"
                                icon="fas fa-lock"
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                error={fieldErrors.confirmPassword}
                                autoComplete="new-password"
                            />
                        </>
                    )}

                    <Button
                        type="submit"
                        variant="primary"
                        size="lg"
                        loading={loading}
                        icon={mode === 'login' ? 'fas fa-sign-in-alt' : 'fas fa-user-plus'}
                        style={{ width: '100%' }}
                    >
                        {mode === 'login' ? 'Sign In' : 'Create Account'}
                    </Button>
                </form>

                <p className="auth-switch">
                    {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}
                    <button onClick={switchMode} className="auth-switch__btn">
                        {mode === 'login' ? 'Sign Up' : 'Sign In'}
                    </button>
                </p>
            </div>
        </div>
    );
}
