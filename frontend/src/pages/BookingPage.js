import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { FaCalendarAlt, FaClock, FaUsers, FaChair, FaGift, FaTag, FaCheckCircle } from 'react-icons/fa';

const TABLE_TYPES = [
    { value: 'intimate', label: 'Intimate (2 guests)', icon: '🕯️', capacity: '1-2', price: 'From ₹400' },
    { value: 'small', label: 'Small (4 guests)', icon: '🍽️', capacity: '2-4', price: 'From ₹700' },
    { value: 'family', label: 'Family (6 guests)', icon: '👨‍👩‍👧‍👦', capacity: '4-6', price: 'From ₹1100' },
    { value: 'large', label: 'Large (10 guests)', icon: '🎉', capacity: '6-10', price: 'From ₹1800' },
    { value: 'banquet', label: 'Banquet (20+ guests)', icon: '🏛️', capacity: '10-20+', price: 'From ₹3300' },
];

const SEATING_OPTIONS = [
    { value: 'indoor', label: 'Indoor', icon: '🏠' },
    { value: 'outdoor', label: 'Outdoor', icon: '🌿', extra: '+₹50' },
    { value: 'window', label: 'Window View', icon: '🪟', extra: '+₹100' },
    { value: 'private', label: 'Private Room', icon: '🔒', extra: '+₹150' },
];

const OCCASION_OPTIONS = [
    { value: 'none', label: 'No Occasion', icon: '🍴' },
    { value: 'birthday', label: 'Birthday', icon: '🎂', extra: '+₹500' },
    { value: 'anniversary', label: 'Anniversary', icon: '💍', extra: '+₹700' },
    { value: 'corporate', label: 'Corporate', icon: '💼', extra: '+₹1000' },
];

function BookingPage() {
    const { currentUser } = useAuth();
    const navigate = useNavigate();

    const [form, setForm] = useState({
        table_type: 'small',
        party_size: 2,
        date: '',
        time: '19:00',
        seating_preference: 'indoor',
        occasion_type: 'none',
        special_requests: '',
        table_quantity: 1,
        discount_code: '',
    });

    const [availability, setAvailability] = useState(null);
    const [quote, setQuote] = useState(null);
    const [loading, setLoading] = useState(false);
    const [checkingAvail, setCheckingAvail] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState('');

    const today = new Date().toISOString().split('T')[0];

    useEffect(() => {
        if (success) {
            const timer = setTimeout(() => {
                navigate('/my-reservations');
            }, 1800);
            return () => clearTimeout(timer);
        }
    }, [success, navigate]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm(prev => ({ ...prev, [name]: value }));
        setAvailability(null);
        setQuote(null);
    };

    const checkAvailability = async () => {
        if (!form.date || !form.time) {
            setError('Please select a date and time first.');
            return;
        }
        setCheckingAvail(true);
        setError('');
        try {
            const res = await axios.get('/api/reservations/availability', {
                params: { date: form.date, time: form.time, table_type: form.table_type }
            });
            setAvailability(res.data);
        } catch (err) {
            setError('Could not check availability. Please try again.');
        } finally {
            setCheckingAvail(false);
        }
    };

    const getQuote = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await axios.post('/api/reservations/quote', {
                table_type: form.table_type,
                party_size: parseInt(form.party_size),
                table_quantity: parseInt(form.table_quantity),
                seating_preference: form.seating_preference,
                occasion_type: form.occasion_type,
                discount_code: form.discount_code || null,
            });
            setQuote(res.data);
        } catch (err) {
            setError(err.response?.data?.error || 'Could not get quote.');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!currentUser) { navigate('/login'); return; }
        setLoading(true);
        setError('');
        try {
            const res = await axios.post('/api/reservations/book', {
                ...form,
                party_size: parseInt(form.party_size),
                table_quantity: parseInt(form.table_quantity),
            });
            setSuccess(res.data);
        } catch (err) {
            setError(err.response?.data?.error || 'Booking failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="booking-page page-content">
                <div className="booking-success glass-panel animate-in">
                    <FaCheckCircle className="success-icon" />
                    <h2>Reservation Confirmed!</h2>
                    <div className="confirmation-code">
                        <span>Confirmation Code</span>
                        <strong>{success.confirmation_code}</strong>
                    </div>
                    <div className="success-details">
                        <p>📅 {success.reservation_date} at {success.reservation_time}</p>
                        <p>🪑 {success.table_type?.charAt(0).toUpperCase() + success.table_type?.slice(1)} Table × {success.table_quantity}</p>
                        <p>👥 {success.party_size} guests</p>
                        <p>💰 Total: ₹{success.total_cost}</p>
                    </div>
                    <p className="success-note">A confirmation has been sent to your inbox.</p>
                    <div className="success-actions">
                        <button className="btn btn-primary" onClick={() => navigate('/my-reservations')}>
                            View My Reservations
                        </button>
                        <button className="btn btn-secondary" onClick={() => { setSuccess(null); setForm({ table_type: 'small', party_size: 2, date: '', time: '19:00', seating_preference: 'indoor', occasion_type: 'none', special_requests: '', table_quantity: 1, discount_code: '' }); }}>
                            Book Another
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="booking-page page-content">
            <div className="menu-header">
                <h1 className="menu-title"><FaCalendarAlt style={{ marginRight: '0.5rem' }} />Reserve a Table</h1>
                <p className="menu-subtitle">Secure your perfect dining experience at DineSmartAI</p>
            </div>

            {error && <div className="booking-error">{error}</div>}

            <form onSubmit={handleSubmit} className="booking-form">
                {/* Table Type */}
                <div className="booking-section glass-panel">
                    <h3 className="booking-section-title">Choose Your Table</h3>
                    <div className="table-type-grid">
                        {TABLE_TYPES.map(t => (
                            <div
                                key={t.value}
                                className={`table-type-card ${form.table_type === t.value ? 'selected' : ''}`}
                                onClick={() => setForm(prev => ({ ...prev, table_type: t.value }))}
                            >
                                <div className="table-icon">{t.icon}</div>
                                <div className="table-label">{t.label}</div>
                                <div className="table-capacity">👥 {t.capacity}</div>
                                <div className="table-price">{t.price}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Date, Time, Party Size */}
                <div className="booking-section glass-panel">
                    <h3 className="booking-section-title">When & How Many</h3>
                    <div className="booking-fields-row">
                        <div className="booking-field">
                            <label><FaCalendarAlt /> Date</label>
                            <input
                                type="date"
                                name="date"
                                value={form.date}
                                min={today}
                                onChange={handleChange}
                                className="form-control"
                                required
                            />
                        </div>
                        <div className="booking-field">
                            <label><FaClock /> Time</label>
                            <select name="time" value={form.time} onChange={handleChange} className="form-control">
                                {['12:00','12:30','13:00','13:30','14:00','14:30','18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30'].map(t => (
                                    <option key={t} value={t}>{t}</option>
                                ))}
                            </select>
                        </div>
                        <div className="booking-field">
                            <label><FaUsers /> Party Size</label>
                            <input
                                type="number"
                                name="party_size"
                                value={form.party_size}
                                min="1"
                                max="50"
                                onChange={handleChange}
                                className="form-control"
                                required
                            />
                        </div>
                        <div className="booking-field">
                            <label><FaChair /> No. of Tables</label>
                            <input
                                type="number"
                                name="table_quantity"
                                value={form.table_quantity}
                                min="1"
                                max="10"
                                onChange={handleChange}
                                className="form-control"
                            />
                        </div>
                    </div>
                    <button type="button" className="btn-check-avail" onClick={checkAvailability} disabled={checkingAvail}>
                        {checkingAvail ? 'Checking...' : '🔍 Check Availability'}
                    </button>
                    {availability && (
                        <div className={`availability-result ${availability.available ? 'avail-yes' : 'avail-no'}`}>
                            {availability.available
                                ? `✅ ${availability.available_count} table(s) available for your selection`
                                : `❌ No tables available at this time. Try a different slot.`}
                        </div>
                    )}
                </div>

                {/* Seating & Occasion */}
                <div className="booking-section glass-panel">
                    <h3 className="booking-section-title">Preferences</h3>
                    <div className="booking-fields-row">
                        <div className="booking-field full-width">
                            <label>Seating Preference</label>
                            <div className="option-chips">
                                {SEATING_OPTIONS.map(s => (
                                    <div
                                        key={s.value}
                                        className={`option-chip ${form.seating_preference === s.value ? 'selected' : ''}`}
                                        onClick={() => setForm(prev => ({ ...prev, seating_preference: s.value }))}
                                    >
                                        {s.icon} {s.label} {s.extra && <span className="chip-extra">{s.extra}</span>}
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="booking-field full-width">
                            <label><FaGift /> Occasion</label>
                            <div className="option-chips">
                                {OCCASION_OPTIONS.map(o => (
                                    <div
                                        key={o.value}
                                        className={`option-chip ${form.occasion_type === o.value ? 'selected' : ''}`}
                                        onClick={() => setForm(prev => ({ ...prev, occasion_type: o.value }))}
                                    >
                                        {o.icon} {o.label} {o.extra && <span className="chip-extra">{o.extra}</span>}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Special Requests & Discount */}
                <div className="booking-section glass-panel">
                    <h3 className="booking-section-title">Special Requests & Discount</h3>
                    <div className="booking-fields-row">
                        <div className="booking-field full-width">
                            <label>Special Requests</label>
                            <textarea
                                name="special_requests"
                                value={form.special_requests}
                                onChange={handleChange}
                                className="form-control"
                                rows="3"
                                placeholder="Dietary requirements, decorations, accessibility needs..."
                            />
                        </div>
                        <div className="booking-field">
                            <label><FaTag /> Discount Code</label>
                            <input
                                type="text"
                                name="discount_code"
                                value={form.discount_code}
                                onChange={handleChange}
                                className="form-control"
                                placeholder="e.g. FIRST10, BULK20, VIP25"
                            />
                        </div>
                    </div>
                </div>

                {/* Quote & Submit */}
                <div className="booking-actions">
                    <button type="button" className="btn btn-secondary" onClick={getQuote} disabled={loading}>
                        {loading ? 'Calculating...' : '💰 Get Price Quote'}
                    </button>
                    {quote && (
                        <div className="quote-panel glass-panel">
                            <h4>Price Breakdown</h4>
                            <div className="quote-row"><span>Table Cost</span><span>₹{quote.base_cost}</span></div>
                            <div className="quote-row"><span>Extras (Seating + Occasion)</span><span>₹{quote.extras_cost}</span></div>
                            {quote.bulk_discount > 0 && <div className="quote-row discount"><span>Bulk Discount</span><span>-₹{quote.bulk_discount}</span></div>}
                            {quote.promo_discount > 0 && <div className="quote-row discount"><span>Promo Discount</span><span>-₹{quote.promo_discount}</span></div>}
                            <div className="quote-row total"><span>Total</span><span>₹{quote.total_quote}</span></div>
                        </div>
                    )}
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? 'Booking...' : '✅ Confirm Reservation'}
                    </button>
                </div>
            </form>

            <style>{`
                .booking-page { max-width: 900px; margin: 0 auto; padding: 2rem; }
                .booking-form { display: flex; flex-direction: column; gap: 2rem; }
                .booking-section { padding: 2rem; border-radius: 16px; }
                .booking-section-title { font-family: 'Orbitron', sans-serif; font-size: 1.1rem; color: var(--neon-cyan); margin-bottom: 1.5rem; }
                .table-type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem; }
                .table-type-card { background: rgba(255,255,255,0.03); border: 2px solid rgba(0,243,255,0.1); border-radius: 12px; padding: 1.25rem; text-align: center; cursor: pointer; transition: all 0.3s; }
                .table-type-card:hover { border-color: var(--neon-cyan); background: rgba(0,243,255,0.05); }
                .table-type-card.selected { border-color: var(--neon-cyan); background: rgba(0,243,255,0.1); box-shadow: 0 0 20px rgba(0,243,255,0.2); }
                .table-icon { font-size: 2rem; margin-bottom: 0.5rem; }
                .table-label { font-weight: 700; font-size: 0.9rem; color: var(--text-primary); margin-bottom: 0.25rem; }
                .table-capacity { font-size: 0.8rem; color: var(--text-muted); }
                .table-price { font-size: 0.8rem; color: var(--neon-cyan); margin-top: 0.25rem; }
                .booking-fields-row { display: flex; flex-wrap: wrap; gap: 1.5rem; }
                .booking-field { flex: 1; min-width: 180px; display: flex; flex-direction: column; gap: 0.5rem; }
                .booking-field.full-width { flex: 100%; }
                .booking-field label { color: var(--neon-cyan); font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
                .btn-check-avail { margin-top: 1.5rem; background: rgba(0,243,255,0.1); border: 1px solid var(--neon-cyan); color: var(--neon-cyan); padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
                .btn-check-avail:hover { background: rgba(0,243,255,0.2); }
                .availability-result { margin-top: 1rem; padding: 0.75rem 1.25rem; border-radius: 8px; font-weight: 600; }
                .avail-yes { background: rgba(57,255,20,0.1); border: 1px solid var(--neon-green); color: var(--neon-green); }
                .avail-no { background: rgba(255,59,127,0.1); border: 1px solid var(--neon-pink); color: var(--neon-pink); }
                .option-chips { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.5rem; }
                .option-chip { background: rgba(255,255,255,0.03); border: 2px solid rgba(0,243,255,0.1); border-radius: 50px; padding: 0.5rem 1.25rem; cursor: pointer; font-size: 0.9rem; transition: all 0.3s; display: flex; align-items: center; gap: 0.5rem; }
                .option-chip:hover { border-color: var(--neon-cyan); }
                .option-chip.selected { border-color: var(--neon-cyan); background: rgba(0,243,255,0.1); color: var(--neon-cyan); }
                .chip-extra { font-size: 0.75rem; color: var(--neon-yellow); }
                .booking-actions { display: flex; flex-direction: column; gap: 1.5rem; align-items: center; }
                .booking-actions .btn { min-width: 250px; }
                .quote-panel { padding: 1.5rem; border-radius: 12px; width: 100%; max-width: 400px; }
                .quote-panel h4 { color: var(--neon-cyan); margin-bottom: 1rem; font-family: 'Orbitron', sans-serif; }
                .quote-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-secondary); }
                .quote-row.discount span:last-child { color: var(--neon-green); }
                .quote-row.total { font-weight: 700; font-size: 1.1rem; color: var(--text-primary); border-bottom: none; margin-top: 0.5rem; }
                .booking-error { background: rgba(255,59,127,0.1); border: 1px solid var(--neon-pink); color: var(--neon-pink); padding: 1rem 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; }
                .booking-success { max-width: 500px; margin: 4rem auto; padding: 3rem; text-align: center; border-radius: 20px; }
                .success-icon { font-size: 4rem; color: var(--neon-green); margin-bottom: 1.5rem; filter: drop-shadow(0 0 20px var(--neon-green)); }
                .booking-success h2 { font-family: 'Orbitron', sans-serif; color: var(--neon-green); margin-bottom: 2rem; }
                .confirmation-code { background: rgba(0,243,255,0.05); border: 1px solid var(--neon-cyan); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
                .confirmation-code span { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; }
                .confirmation-code strong { font-family: 'Orbitron', sans-serif; font-size: 1.5rem; color: var(--neon-cyan); letter-spacing: 3px; }
                .success-details { text-align: left; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
                .success-details p { padding: 0.4rem 0; color: var(--text-secondary); }
                .success-note { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 2rem; }
                .success-actions { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
                .btn-secondary { background: rgba(255,255,255,0.05); border: 2px solid rgba(255,255,255,0.2); color: var(--text-primary); padding: 0.875rem 2rem; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
                .btn-secondary:hover { border-color: var(--neon-cyan); color: var(--neon-cyan); }
                .glass-panel { background: rgba(10,10,15,0.85); backdrop-filter: blur(20px); border: 1px solid rgba(0,243,255,0.1); }
            `}</style>
        </div>
    );
}

export default BookingPage;
