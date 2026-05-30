import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

function SignupPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirm) {
            setError('Passwords do not match.');
            return;
        }
        if (password.length < 6) {
            setError('Password must be at least 6 characters.');
            return;
        }
        setLoading(true);
        try {
            const response = await axios.post('/api/signup', { username, password });
            setSuccess(response.data.message + ' Redirecting to login...');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setError(err.response?.data?.message || 'Signup failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page page-content">
            <div className="auth-card glass-panel">
                <div className="auth-logo">
                    <span style={{ fontSize: '2.5rem' }}>🍽️</span>
                    <h1 className="auth-brand">DineSmartAI</h1>
                    <p className="auth-tagline">Join the AI-Powered Dining Experience</p>
                </div>

                <h2 className="auth-title">Create Account</h2>

                <form onSubmit={handleSignup} className="auth-form">
                    <div className="auth-field">
                        <label>Email / Username</label>
                        <input
                            type="text"
                            className="form-control"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="Enter your email or username"
                            required
                            autoFocus
                        />
                    </div>
                    <div className="auth-field">
                        <label>Password</label>
                        <input
                            type="password"
                            className="form-control"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="Min. 6 characters"
                            required
                        />
                    </div>
                    <div className="auth-field">
                        <label>Confirm Password</label>
                        <input
                            type="password"
                            className="form-control"
                            value={confirm}
                            onChange={e => setConfirm(e.target.value)}
                            placeholder="Repeat your password"
                            required
                        />
                    </div>

                    {error && <div className="auth-error">⚠️ {error}</div>}
                    {success && <div className="auth-success">✅ {success}</div>}

                    <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>Already have an account? <Link to="/login" style={{ color: 'var(--neon-cyan)' }}>Sign in</Link></p>
                </div>
            </div>

            <style>{`
                .auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 2rem; }
                .auth-card { max-width: 440px; width: 100%; padding: 3rem 2.5rem; border-radius: 24px; }
                .auth-logo { text-align: center; margin-bottom: 2rem; }
                .auth-brand { font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900; background: linear-gradient(135deg, #00f3ff, #b026ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0.5rem 0 0.25rem; }
                .auth-tagline { color: var(--text-muted); font-size: 0.9rem; }
                .auth-title { font-family: 'Orbitron', sans-serif; font-size: 1.4rem; color: var(--text-primary); margin-bottom: 2rem; text-align: center; }
                .auth-form { display: flex; flex-direction: column; gap: 1.25rem; }
                .auth-field { display: flex; flex-direction: column; gap: 0.5rem; }
                .auth-field label { color: var(--neon-cyan); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
                .auth-error { background: rgba(255,59,127,0.1); border: 1px solid rgba(255,59,127,0.4); color: #ff3b7f; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.9rem; }
                .auth-success { background: rgba(57,255,20,0.1); border: 1px solid rgba(57,255,20,0.4); color: #39ff14; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.9rem; }
                .auth-submit { width: 100%; margin-top: 0.5rem; }
                .auth-footer { text-align: center; margin-top: 2rem; color: var(--text-muted); font-size: 0.9rem; }
                .glass-panel { background: rgba(10,10,15,0.85); backdrop-filter: blur(20px); border: 1px solid rgba(0,243,255,0.1); }
            `}</style>
        </div>
    );
}

export default SignupPage;
