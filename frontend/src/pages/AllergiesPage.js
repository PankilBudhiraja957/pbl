import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FaExclamationTriangle, FaCheckCircle, FaRobot, FaShieldAlt } from 'react-icons/fa';

const COMMON_ALLERGENS = ['Peanuts', 'Tree Nuts', 'Dairy', 'Eggs', 'Fish', 'Shellfish', 'Wheat/Gluten', 'Soy', 'Sesame', 'Mustard'];

function AllergiesPage() {
    const { currentUser } = useAuth();
    const [allergies, setAllergies] = useState('');
    const [preferences, setPreferences] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');

    useEffect(() => {
        if (!currentUser) return;
        axios.get('/api/profile').then(r => {
            setAllergies(r.data.allergies || '');
            setPreferences(r.data.preferences || '');
        }).catch(console.error);
    }, [currentUser]);

    const toggleAllergen = (allergen) => {
        const lower = allergen.toLowerCase().replace('/gluten', '').trim();
        const list = allergies ? allergies.split(',').map(a => a.trim()).filter(Boolean) : [];
        const exists = list.some(a => a.toLowerCase() === lower);
        const updated = exists ? list.filter(a => a.toLowerCase() !== lower) : [...list, lower];
        setAllergies(updated.join(', '));
    };

    const isActive = (allergen) => {
        const lower = allergen.toLowerCase().replace('/gluten', '').trim();
        return allergies.toLowerCase().includes(lower);
    };

    const handleSubmit = async e => {
        e.preventDefault();
        setLoading(true);
        setMessage('');
        try {
            await axios.post('/api/profile', { allergies, preferences });
            setMessage('Profile updated successfully!');
            setMessageType('success');
        } catch {
            setMessage('Failed to update. Please try again.');
            setMessageType('error');
        } finally { setLoading(false); }
    };

    const allergyList = allergies ? allergies.split(',').map(a => a.trim()).filter(Boolean) : [];

    return (
        <div className="page-content" style={{ maxWidth: 700, margin: '0 auto', padding: '2rem' }}>
            <div className="menu-header">
                <h1 className="menu-title"><FaShieldAlt style={{ marginRight: '0.5rem' }} />Allergy Safety</h1>
                <p className="menu-subtitle">Keep your dietary restrictions up to date for a safe dining experience</p>
            </div>

            {/* AI Info Banner */}
            <div style={{ background: 'rgba(0,243,255,0.06)', border: '1px solid rgba(0,243,255,0.2)', borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '2rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <FaRobot style={{ color: 'var(--neon-cyan)', fontSize: '1.2rem', marginTop: 2, flexShrink: 0 }} />
                <div>
                    <strong style={{ color: 'var(--neon-cyan)' }}>AI-Powered Safety</strong>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', margin: '0.25rem 0 0' }}>
                        Our AI automatically detects allergy mentions in chat and updates your profile. Menu items containing your allergens are filtered out automatically.
                    </p>
                </div>
            </div>

            <form onSubmit={handleSubmit}>
                {/* Quick Toggle */}
                <div className="glass-panel" style={{ padding: '1.75rem', borderRadius: 16, marginBottom: '1.5rem' }}>
                    <div style={{ fontFamily: 'Orbitron, sans-serif', fontSize: '0.9rem', color: 'var(--neon-cyan)', marginBottom: '1.25rem', fontWeight: 700 }}>
                        <FaExclamationTriangle style={{ marginRight: 8 }} />Quick Select Allergens
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1.25rem' }}>
                        {COMMON_ALLERGENS.map(a => (
                            <button key={a} type="button" onClick={() => toggleAllergen(a)}
                                style={{
                                    padding: '0.45rem 1rem', borderRadius: 50, fontSize: '0.85rem', fontWeight: 600,
                                    cursor: 'pointer', transition: 'all 0.2s', border: '1px solid',
                                    borderColor: isActive(a) ? 'rgba(255,59,127,0.6)' : 'rgba(255,255,255,0.12)',
                                    background: isActive(a) ? 'rgba(255,59,127,0.15)' : 'rgba(255,255,255,0.04)',
                                    color: isActive(a) ? '#ff3b7f' : 'rgba(255,255,255,0.6)',
                                }}>
                                {isActive(a) ? '✕ ' : '+ '}{a}
                            </button>
                        ))}
                    </div>

                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.6)', fontSize: '0.82rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem' }}>
                        Or type manually (comma-separated)
                    </label>
                    <input className="form-control" value={allergies} onChange={e => setAllergies(e.target.value)}
                        placeholder="e.g. peanuts, dairy, shellfish" disabled={loading} />

                    {allergyList.length > 0 && (
                        <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {allergyList.map((a, i) => (
                                <span key={i} style={{ background: 'rgba(255,59,127,0.12)', border: '1px solid rgba(255,59,127,0.3)', color: '#ff3b7f', padding: '0.25rem 0.75rem', borderRadius: 50, fontSize: '0.8rem', fontWeight: 600 }}>
                                    ⚠️ {a}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Preferences */}
                <div className="glass-panel" style={{ padding: '1.75rem', borderRadius: 16, marginBottom: '1.5rem' }}>
                    <div style={{ fontFamily: 'Orbitron, sans-serif', fontSize: '0.9rem', color: 'var(--neon-cyan)', marginBottom: '1.25rem', fontWeight: 700 }}>
                        Dietary Preferences
                    </div>
                    <input className="form-control" value={preferences} onChange={e => setPreferences(e.target.value)}
                        placeholder="e.g. vegetarian, spicy, low-carb, keto" disabled={loading} />
                </div>

                {message && (
                    <div style={{
                        padding: '0.875rem 1.25rem', borderRadius: 10, marginBottom: '1.25rem',
                        background: messageType === 'success' ? 'rgba(57,255,20,0.08)' : 'rgba(255,59,127,0.08)',
                        border: `1px solid ${messageType === 'success' ? 'rgba(57,255,20,0.3)' : 'rgba(255,59,127,0.3)'}`,
                        color: messageType === 'success' ? '#39ff14' : '#ff3b7f', fontWeight: 600
                    }}>
                        {messageType === 'success' ? <FaCheckCircle style={{ marginRight: 8 }} /> : <FaExclamationTriangle style={{ marginRight: 8 }} />}
                        {message}
                    </div>
                )}

                <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                    {loading ? 'Saving...' : '💾 Save Allergy Profile'}
                </button>
            </form>
        </div>
    );
}

export default AllergiesPage;
