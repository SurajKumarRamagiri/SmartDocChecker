import React, { useState } from 'react';

/**
 * Input – reusable controlled input with label, validation, and icons.
 *
 * Props:
 *   label     – field label text
 *   error     – error message string (shown in red below the input)
 *   icon      – optional Font Awesome class for left icon
 *   type      – input type (default: 'text')
 *   ...rest   – forwarded to <input>
 */
export default function Input({
    label,
    error,
    icon,
    type = 'text',
    className = '',
    ...rest
}) {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === 'password';
    const inputType = isPassword && showPassword ? 'text' : type;

    return (
        <div className={`input-group ${error ? 'input-group--error' : ''} ${className}`}>
            {label && <label className="input-label">{label}</label>}
            <div className="input-wrapper">
                {icon && <i className={`input-icon ${icon}`}></i>}
                <input
                    type={inputType}
                    className={`input-field ${icon ? 'input-field--with-icon' : ''}`}
                    {...rest}
                />
                {isPassword && (
                    <button
                        type="button"
                        className="input-toggle-password"
                        onClick={() => setShowPassword((prev) => !prev)}
                        tabIndex={-1}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                        <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                    </button>
                )}
            </div>
            {error && <span className="input-error">{error}</span>}
        </div>
    );
}
