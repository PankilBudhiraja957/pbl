import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

axios.defaults.withCredentials = true;

const TABS = ['Add Dish', 'Manage Menu', 'Reservations'];

function AdminDashboard() {
    const { currentUser, refreshAuthStatus } = useAuth();
    const [activeTab, setActiveTab] = useState('Add Dish');
    const [menuItems, setMenuItems] = useState([]);
    const [reservations, setReservations] = useState([]);
    const [resFilter, setResFilter] = useState('all');
    const [loadingRes, setLoadingRes] = useState(false);
    const [newItem, setNewItem] = useState({
        name: '', description: '', price: '', category: '',
        ingredients: '', diet: 'Vegetarian', cooking_tips: '',
        calories: '', protein: '', carbs: '', fat: ''
    });
    const [notification, setNotification] = useState('');

    useEffect(() => {
        refreshAuthStatus();
    }, [refreshAuthStatus]);

    const fetchMenu = useCallback(async () => {
        try {
            const res = await axios.get('/api/menu');
            setMenuItems(res.data);
        } catch (e) { console.error('Failed to fetch menu', e); }
    }, []);

    const fetchReservations = useCallback(async () => {
        setLoadingRes(true);
        try {
            const params = resFilter !== 'all' ? { status: resFilter } : {};
            const res = await axios.get('/api/admin/reservations', { params });
            setReservations(res.data.reservations || []);
        } catch (e) { console.error('Failed to fetch reservations', e); }
        finally { setLoadingRes(false); }
    }, [resFilter]);

    useEffect(() => { fetchMenu(); }, [fetchMenu]);
    useEffect(() => { if (activeTab === 'Reservations') fetchReservations(); }, [activeTab, fetchReservations]);

    const showNotification = (msg) => {
        setNotification(msg);
        setTimeout(() => setNotification(''), 3000);
    };

    const handleInputChange = (e) => setNewItem({ ...newItem, [e.target.name]: e.target.value });

    const handleAddDish = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/admin/menu', newItem);
            fetchMenu();
            setNewItem({ name: '', description: '', price: '', category: '', ingredients: '', diet: 'Vegetarian', cooking_tips: '', calories: '', protein: '', carbs: '', fat: '' });
            showNotification('Dish added successfully!');
        } catch { showNotification('Failed to add dish.'); }
    };

    const handleDeleteDish = async (dishId) => {
        if (!window.confirm('Delete this dish?')) return;
        try {
            await axios.delete(`/api/admin/menu/${dishId}`);
            fetchMenu();
            showNotification('Dish deleted.');
        } catch { showNotification('Failed to delete dish.'); }
    };

    const handleCancelReservation = async (id) => {
        if (!window.confirm('Cancel this reservation?')) return;
        try {
            await axios.post(`/api/reservations/${id}/cancel`);
            fetchReservations();
            showNotification('Reservation cancelled.');
        } catch (e) { showNotification(e.response?.data?.error || 'Failed to cancel.'); }
    };

    const STATUS_COLORS = {
        confirmed: '#39ff14', cancelled: '#ff3b7f', completed: '#00f3ff'
    };

    return (
        <div className="container mt-4 page-content">
            {notification && (
                <div className="notification-banner">
                    {notification}
                    <button onClick={() => setNotification('')} className="notification-close">&times;</button>
                </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
                <h2 style={{ fontFamily: 'Orbitron, sans-serif', background: 'linear-gradient(135deg, #00f3ff, #b026ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    🛡️ Admin Dashboard
                </h2>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <Link to="/admin-inbox" className="btn btn-primary" style={{ textDecoration: 'none', padding: '0.6rem 1.2rem', fontSize: '0.9rem' }}>
                        📬 Real-time Orders
                    </Link>
                </div>
            </div>

            {/* Tabs */}
            <div className="admin-tabs">
                {TABS.map(tab => (
                    <button
                        key={tab}
                        className={`admin-tab ${activeTab === tab ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab === 'Add Dish' && '➕ '}
                        {tab === 'Manage Menu' && '🍽️ '}
                        {tab === 'Reservations' && '📅 '}
                        {tab}
                    </button>
                ))}
            </div>

            {/* ── ADD DISH TAB ── */}
            {activeTab === 'Add Dish' && (
                <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
                    <h4 style={{ color: 'var(--neon-cyan)', marginBottom: '1.5rem', fontFamily: 'Orbitron, sans-serif' }}>Add New Dish</h4>
                    <form onSubmit={handleAddDish}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <input name="name" value={newItem.name} onChange={handleInputChange} placeholder="Dish Name *" className="form-control" required />
                            <input name="price" value={newItem.price} onChange={handleInputChange} placeholder="Price (₹) *" type="number" step="0.01" className="form-control" required />
                            <input name="category" value={newItem.category} onChange={handleInputChange} placeholder="Category (e.g. Main Course) *" className="form-control" required />
                            <select name="diet" value={newItem.diet} onChange={handleInputChange} className="form-control">
                                <option value="Vegetarian">Vegetarian</option>
                                <option value="Non-Vegetarian">Non-Vegetarian</option>
                                <option value="Vegan">Vegan</option>
                            </select>
                        </div>
                        <textarea name="description" value={newItem.description} onChange={handleInputChange} placeholder="Description *" className="form-control" rows="2" style={{ marginTop: '1rem', width: '100%' }} required />
                        <input name="ingredients" value={newItem.ingredients} onChange={handleInputChange} placeholder="Ingredients (comma separated)" className="form-control" style={{ marginTop: '1rem', width: '100%' }} />
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginTop: '1rem' }}>
                            <input name="calories" value={newItem.calories} onChange={handleInputChange} placeholder="Calories (kcal)" type="number" className="form-control" />
                            <input name="protein" value={newItem.protein} onChange={handleInputChange} placeholder="Protein (g)" type="number" className="form-control" />
                            <input name="carbs" value={newItem.carbs} onChange={handleInputChange} placeholder="Carbs (g)" type="number" className="form-control" />
                            <input name="fat" value={newItem.fat} onChange={handleInputChange} placeholder="Fat (g)" type="number" className="form-control" />
                        </div>
                        <textarea name="cooking_tips" value={newItem.cooking_tips} onChange={handleInputChange} placeholder="Chef's Cooking Tips (optional)" className="form-control" rows="2" style={{ marginTop: '1rem', width: '100%' }} />
                        <button type="submit" className="btn btn-primary" style={{ marginTop: '1.5rem' }}>➕ Add Dish</button>
                    </form>
                </div>
            )}

            {/* ── MANAGE MENU TAB ── */}
            {activeTab === 'Manage Menu' && (
                <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
                    <h4 style={{ color: 'var(--neon-cyan)', marginBottom: '1.5rem', fontFamily: 'Orbitron, sans-serif' }}>
                        Menu Items ({menuItems.length})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {menuItems.map(item => (
                            <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.25rem', background: 'rgba(255,255,255,0.03)', borderRadius: '10px', border: '1px solid rgba(0,243,255,0.08)' }}>
                                <div>
                                    <strong style={{ color: 'var(--text-primary)' }}>{item.name}</strong>
                                    <span style={{ color: 'var(--text-muted)', marginLeft: '1rem', fontSize: '0.85rem' }}>{item.category} · {item.diet}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontFamily: 'Orbitron, sans-serif', color: 'var(--neon-cyan)', fontSize: '0.95rem' }}>₹{item.price}</span>
                                    <button onClick={() => handleDeleteDish(item.id)} style={{ background: 'rgba(255,59,127,0.1)', border: '1px solid rgba(255,59,127,0.3)', color: '#ff3b7f', padding: '0.4rem 0.9rem', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '0.85rem' }}>
                                        Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── RESERVATIONS TAB ── */}
            {activeTab === 'Reservations' && (
                <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                        <h4 style={{ color: 'var(--neon-cyan)', fontFamily: 'Orbitron, sans-serif' }}>
                            Reservations ({reservations.length})
                        </h4>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            {['all', 'confirmed', 'cancelled', 'completed'].map(f => (
                                <button
                                    key={f}
                                    onClick={() => setResFilter(f)}
                                    style={{
                                        padding: '0.4rem 1rem', borderRadius: '50px', border: '1px solid',
                                        borderColor: resFilter === f ? 'var(--neon-cyan)' : 'rgba(255,255,255,0.15)',
                                        background: resFilter === f ? 'rgba(0,243,255,0.1)' : 'transparent',
                                        color: resFilter === f ? 'var(--neon-cyan)' : 'var(--text-muted)',
                                        cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', textTransform: 'capitalize'
                                    }}
                                >
                                    {f}
                                </button>
                            ))}
                            <button onClick={fetchReservations} style={{ padding: '0.4rem 1rem', borderRadius: '50px', border: '1px solid rgba(0,243,255,0.3)', background: 'rgba(0,243,255,0.05)', color: 'var(--neon-cyan)', cursor: 'pointer', fontSize: '0.85rem' }}>
                                🔄 Refresh
                            </button>
                        </div>
                    </div>

                    {loadingRes ? (
                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>Loading reservations...</p>
                    ) : reservations.length === 0 ? (
                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>No reservations found.</p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {reservations.map(res => (
                                <div key={res.id} style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(0,243,255,0.08)' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                                        <div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                                                <strong style={{ fontFamily: 'Orbitron, sans-serif', color: 'var(--neon-cyan)', fontSize: '0.9rem', letterSpacing: '1px' }}>{res.confirmation_code}</strong>
                                                <span style={{ background: `${STATUS_COLORS[res.status]}20`, border: `1px solid ${STATUS_COLORS[res.status]}50`, color: STATUS_COLORS[res.status], padding: '0.2rem 0.75rem', borderRadius: '50px', fontSize: '0.8rem', fontWeight: '700', textTransform: 'capitalize' }}>
                                                    {res.status}
                                                </span>
                                            </div>
                                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                                                <span>👤 {res.username}</span>
                                                <span>📅 {res.reservation_date} {res.reservation_time}</span>
                                                <span>🪑 {res.table_type} × {res.table_quantity}</span>
                                                <span>👥 {res.party_size} guests</span>
                                                {res.occasion_type && res.occasion_type !== 'none' && <span>🎉 {res.occasion_type}</span>}
                                            </div>
                                            {res.special_requests && (
                                                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.4rem' }}>📝 {res.special_requests}</div>
                                            )}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                            <span style={{ fontFamily: 'Orbitron, sans-serif', color: 'var(--neon-cyan)', fontWeight: '700' }}>₹{res.total_cost}</span>
                                            {res.status === 'confirmed' && (
                                                <button onClick={() => handleCancelReservation(res.id)} style={{ background: 'rgba(255,59,127,0.1)', border: '1px solid rgba(255,59,127,0.3)', color: '#ff3b7f', padding: '0.4rem 0.9rem', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '0.85rem' }}>
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default AdminDashboard;
