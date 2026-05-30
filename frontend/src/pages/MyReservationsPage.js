import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { FaCalendarAlt, FaClock, FaUsers, FaCheckCircle, FaTimesCircle, FaPlus } from 'react-icons/fa';

const STATUS_COLORS = {
    confirmed: { color: '#39ff14', bg: 'rgba(57,255,20,0.1)', icon: <FaCheckCircle /> },
    cancelled: { color: '#ff3b7f', bg: 'rgba(255,59,127,0.1)', icon: <FaTimesCircle /> },
    completed: { color: '#00f3ff', bg: 'rgba(0,243,255,0.1)', icon: <FaCheckCircle /> },
};

const OCCASION_ICONS = {
    birthday: '🎂', anniversary: '💍', corporate: '💼', none: '🍴'
};

function MyReservationsPage() {
    const [reservations, setReservations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [cancelling, setCancelling] = useState(null);

    useEffect(() => {
        fetchReservations();
    }, []);

    const fetchReservations = async () => {
        try {
            const res = await axios.get('/api/reservations/my-bookings');
            const data = res.data;
            const reservationsList = Array.isArray(data)
                ? data
                : data?.reservations || [];
            setReservations(reservationsList);
        } catch (err) {
            setError('Failed to load reservations.');
        } finally {
            setLoading(false);
        }
    };

    const cancelReservation = async (id) => {
        if (!window.confirm('Are you sure you want to cancel this reservation?')) return;
        setCancelling(id);
        try {
            await axios.post(`/api/reservations/${id}/cancel`);
            setReservations(prev => prev.map(r => r.id === id ? { ...r, status: 'cancelled' } : r));
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to cancel reservation.');
        } finally {
            setCancelling(null);
        }
    };

    if (loading) return <div className="page-content" style={{ textAlign: 'center', paddingTop: '8rem', color: 'var(--neon-cyan)' }}>Loading reservations...</div>;

    return (
        <div className="my-reservations-page page-content">
            <div className="menu-header">
                <h1 className="menu-title"><FaCalendarAlt style={{ marginRight: '0.5rem' }} />My Reservations</h1>
                <p className="menu-subtitle">Manage your upcoming and past table bookings</p>
            </div>

            {error && <div style={{ background: 'rgba(255,59,127,0.1)', border: '1px solid #ff3b7f', color: '#ff3b7f', padding: '1rem 1.5rem', borderRadius: '12px', marginBottom: '2rem' }}>{error}</div>}

            <div style={{ textAlign: 'right', marginBottom: '2rem' }}>
                <Link to="/book-table" className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}>
                    <FaPlus /> New Reservation
                </Link>
            </div>

            {reservations.length === 0 ? (
                <div className="empty-orders-view glass-panel animate-in" style={{ textAlign: 'center', padding: '4rem 2rem', borderRadius: '20px' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📅</div>
                    <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No reservations yet</h3>
                    <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Book a table for your next dining experience.</p>
                    <Link to="/book-table" className="btn btn-primary" style={{ textDecoration: 'none' }}>Book a Table</Link>
                </div>
            ) : (
                <div className="reservations-grid">
                    {reservations.map((res, index) => {
                        const statusStyle = STATUS_COLORS[res.status] || STATUS_COLORS.confirmed;
                        const isPast = new Date(`${res.reservation_date}T${res.reservation_time}`) < new Date();
                        return (
                            <div key={res.id} className="reservation-card glass-panel animate-in" style={{ animationDelay: `${index * 0.08}s` }}>
                                <div className="res-card-header">
                                    <div className="res-code">
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Confirmation</span>
                                        <strong style={{ fontFamily: 'Orbitron, sans-serif', color: 'var(--neon-cyan)', letterSpacing: '2px' }}>{res.confirmation_code}</strong>
                                    </div>
                                    <div className="res-status" style={{ background: statusStyle.bg, color: statusStyle.color, padding: '0.4rem 1rem', borderRadius: '50px', fontSize: '0.85rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                        {statusStyle.icon} {res.status?.charAt(0).toUpperCase() + res.status?.slice(1)}
                                    </div>
                                </div>

                                <div className="res-card-body">
                                    <div className="res-detail-row">
                                        <FaCalendarAlt style={{ color: 'var(--neon-cyan)' }} />
                                        <span>{res.reservation_date}</span>
                                        <FaClock style={{ color: 'var(--neon-cyan)', marginLeft: '1rem' }} />
                                        <span>{res.reservation_time}</span>
                                    </div>
                                    <div className="res-detail-row">
                                        <FaUsers style={{ color: 'var(--neon-cyan)' }} />
                                        <span>{res.party_size} guests · {res.table_type?.charAt(0).toUpperCase() + res.table_type?.slice(1)} Table × {res.table_quantity}</span>
                                    </div>
                                    <div className="res-detail-row">
                                        <span>{OCCASION_ICONS[res.occasion_type] || '🍴'}</span>
                                        <span>{res.occasion_type === 'none' ? 'Regular Dining' : res.occasion_type?.charAt(0).toUpperCase() + res.occasion_type?.slice(1)}</span>
                                        <span style={{ marginLeft: 'auto', color: 'var(--neon-cyan)', fontWeight: '700' }}>₹{res.total_cost}</span>
                                    </div>
                                    {res.seating_preference && res.seating_preference !== 'indoor' && (
                                        <div className="res-detail-row">
                                            <span>🪑</span>
                                            <span style={{ color: 'var(--text-muted)' }}>{res.seating_preference?.charAt(0).toUpperCase() + res.seating_preference?.slice(1)} seating</span>
                                        </div>
                                    )}
                                    {res.special_requests && (
                                        <div className="res-special-req">
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>📝 {res.special_requests}</span>
                                        </div>
                                    )}
                                </div>

                                {res.status === 'confirmed' && !isPast && (
                                    <div className="res-card-footer">
                                        <button
                                            className="btn-cancel-res"
                                            onClick={() => cancelReservation(res.id)}
                                            disabled={cancelling === res.id}
                                        >
                                            {cancelling === res.id ? 'Cancelling...' : '✕ Cancel Reservation'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <style>{`
                .my-reservations-page { max-width: 900px; margin: 0 auto; padding: 2rem; }
                .reservations-grid { display: flex; flex-direction: column; gap: 1.5rem; }
                .reservation-card { border-radius: 16px; overflow: hidden; opacity: 0; transform: translateY(20px); }
                .reservation-card.animate-in { animation: cardReveal 0.5s cubic-bezier(0.23,1,0.32,1) forwards; }
                .res-card-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 1.5rem; border-bottom: 1px solid rgba(0,243,255,0.1); }
                .res-code { display: flex; flex-direction: column; gap: 0.25rem; }
                .res-card-body { padding: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }
                .res-detail-row { display: flex; align-items: center; gap: 0.75rem; color: var(--text-secondary); font-size: 0.95rem; }
                .res-special-req { background: rgba(255,255,255,0.03); border-radius: 8px; padding: 0.75rem; margin-top: 0.5rem; }
                .res-card-footer { padding: 1rem 1.5rem; border-top: 1px solid rgba(255,59,127,0.1); }
                .btn-cancel-res { background: rgba(255,59,127,0.1); border: 1px solid rgba(255,59,127,0.4); color: #ff3b7f; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
                .btn-cancel-res:hover { background: rgba(255,59,127,0.2); }
                .glass-panel { background: rgba(10,10,15,0.85); backdrop-filter: blur(20px); border: 1px solid rgba(0,243,255,0.1); }
            `}</style>
        </div>
    );
}

export default MyReservationsPage;
