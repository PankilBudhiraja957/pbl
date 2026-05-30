import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FaUser, FaAllergies, FaHeartbeat, FaSave } from 'react-icons/fa';

function ProfilePage() {
    const { currentUser } = useAuth();
    const [profile, setProfile] = useState({
        allergies: '', preferences: '',
        calorie_goal: '', protein_goal: '', carb_goal: '', fat_goal: ''
    });
    const [message, setMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (!currentUser) return;
        axios.get('/api/profile').then(r => setProfile({
            allergies: r.data.allergies || '',
            preferences: r.data.preferences || '',
            calorie_goal: r.data.calorie_goal || '',
            protein_goal: r.data.protein_goal || '',
            carb_goal: r.data.carb_goal || '',
            fat_goal: r.data.fat_goal || '',
        })).catch(console.error);
    }, [currentUser]);

    const handleChange = e => setProfile({ ...profile, [e.target.name]: e.target.value });

    const handleSubmit = async e => {
        e.preventDefault();
        setIsSaving(true);
        setMessage('');
        try {
            const res = await axios.post('/api/profile', {
                allergies: profile.allergies,
                preferences: profile.preferences,
                calorie_goal: profile.calorie_goal ? parseFloat(profile.calorie_goal) : null,
                protein_goal: profile.protein_goal ? parseFloat(profile.protein_goal) : null,
                carb_goal: profile.carb_goal ? parseFloat(profile.carb_goal) : null,
                fat_goal: profile.fat_goal ? parseFloat(profile.fat_goal) : null,
            });
            setMessage(res.data.message);
        } catch { setMessage('Failed to update profile.'); }
        finally { setIsSaving(false); }
    };

    const isSuccess = message.toLowerCase().includes('success');

    return (
        <div className="page-content" style={{ maxWidth: 700, margin: '0 auto', padding: '2rem' }}>
            <div className="menu-header">
                <h1 className="menu-title">My Profile</h1>
                <p className="menu-subtitle">Manage your dietary preferences and nutrition goals</p>
            </div>

            {message && (
                <div style={{
                    padding: '1rem 1.5rem', borderRadius: 12, marginBottom: '1.5rem',
                    background: isSuccess ? 'rgba(57,255,20,0.08)' : 'rgba(255,59,127,0.08)',
                    border: `1px solid ${isSuccess ? 'rgba(57,255,20,0.3)' : 'rgba(255,59,127,0.3)'}`,
                    color: isSuccess ? '#39ff14' : '#ff3b7f', fontWeight: 600
                }}>
                    {isSuccess ? '✅' : '⚠️'} {message}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                {/* Account Info */}
                <div className="profile-section glass-panel">
                    <div className="profile-section-title"><FaUser /> Account</div>
                    <div className="profile-field">
                        <label>Username</label>
                        <input className="form-control" value={currentUser?.username || ''} disabled
                            style={{ opacity: 0.5, cursor: 'not-allowed' }} />
                    </div>
                </div>

                {/* Allergies & Preferences */}
                <div className="profile-section glass-panel">
                    <div className="profile-section-title"><FaAllergies /> Dietary Info</div>
                    <div className="profile-field">
                        <label>Known Allergies <span className="field-hint">(comma-separated)</span></label>
                        <input name="allergies" className="form-control" value={profile.allergies}
                            onChange={handleChange} placeholder="e.g. peanuts, dairy, gluten" disabled={isSaving} />
                        {profile.allergies && (
                            <div className="allergy-tags">
                                {profile.allergies.split(',').map(a => a.trim()).filter(Boolean).map((a, i) => (
                                    <span key={i} className="allergy-tag">{a}</span>
                                ))}
                            </div>
                        )}
                    </div>
                    <div className="profile-field">
                        <label>Dietary Preferences <span className="field-hint">(comma-separated)</span></label>
                        <input name="preferences" className="form-control" value={profile.preferences}
                            onChange={handleChange} placeholder="e.g. vegetarian, spicy, low-carb" disabled={isSaving} />
                    </div>
                </div>

                {/* Nutrition Goals */}
                <div className="profile-section glass-panel">
                    <div className="profile-section-title"><FaHeartbeat /> Daily Nutrition Goals</div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
                        Set your daily targets. The AI will recommend meals that fit within 1/3 of these values per meal.
                    </p>
                    <div className="nutrition-grid-4">
                        {[
                            { name: 'calorie_goal', label: 'Calories', unit: 'kcal', placeholder: '2000', color: '#00f3ff' },
                            { name: 'protein_goal', label: 'Protein', unit: 'g', placeholder: '50', color: '#39ff14' },
                            { name: 'carb_goal', label: 'Carbs', unit: 'g', placeholder: '250', color: '#ffe600' },
                            { name: 'fat_goal', label: 'Fat', unit: 'g', placeholder: '70', color: '#ff6b00' },
                        ].map(f => (
                            <div key={f.name} className="nutrition-goal-card" style={{ borderColor: `${f.color}30` }}>
                                <div className="nutrition-goal-label" style={{ color: f.color }}>{f.label}</div>
                                <input
                                    type="number" name={f.name} className="form-control nutrition-input"
                                    value={profile[f.name]} onChange={handleChange}
                                    placeholder={f.placeholder} disabled={isSaving}
                                    style={{ borderColor: `${f.color}30` }}
                                />
                                <div className="nutrition-goal-unit">{f.unit}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={isSaving}>
                    <FaSave style={{ marginRight: 8 }} />
                    {isSaving ? 'Saving...' : 'Save Profile'}
                </button>
            </form>

            <style>{`
                .profile-section { padding: 1.75rem; border-radius: 16px; margin-bottom: 1.5rem; }
                .profile-section-title { display: flex; align-items: center; gap: 0.6rem; font-family: 'Orbitron', sans-serif; font-size: 0.95rem; color: var(--neon-cyan); margin-bottom: 1.25rem; font-weight: 700; }
                .profile-field { margin-bottom: 1.25rem; }
                .profile-field:last-child { margin-bottom: 0; }
                .profile-field label { display: block; color: rgba(255,255,255,0.7); font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px; }
                .field-hint { color: var(--text-muted); font-weight: 400; text-transform: none; letter-spacing: 0; }
                .allergy-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
                .allergy-tag { background: rgba(255,59,127,0.12); border: 1px solid rgba(255,59,127,0.3); color: #ff3b7f; padding: 0.25rem 0.75rem; border-radius: 50px; font-size: 0.8rem; font-weight: 600; }
                .nutrition-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
                @media (max-width: 600px) { .nutrition-grid-4 { grid-template-columns: repeat(2, 1fr); } }
                .nutrition-goal-card { background: rgba(255,255,255,0.03); border: 1px solid; border-radius: 12px; padding: 1rem; text-align: center; }
                .nutrition-goal-label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.6rem; }
                .nutrition-input { text-align: center; font-family: 'Orbitron', sans-serif; font-size: 1.1rem; padding: 0.6rem; }
                .nutrition-goal-unit { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem; }
                .glass-panel { background: rgba(10,10,15,0.85); backdrop-filter: blur(20px); border: 1px solid rgba(0,243,255,0.1); }
            `}</style>
        </div>
    );
}

export default ProfilePage;
