import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { FaHistory, FaShoppingBag } from 'react-icons/fa';

function OrderHistoryPage() {
    const [orders, setOrders] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        axios.get('/api/orders')
            .then(r => setOrders(r.data))
            .catch(() => setError('Failed to load order history.'))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="page-content" style={{ textAlign: 'center', paddingTop: '8rem', color: 'var(--neon-cyan)' }}>
            Loading your orders...
        </div>
    );

    return (
        <div className="order-history-page page-content">
            <div className="menu-header">
                <h1 className="menu-title"><FaHistory style={{ marginRight: '0.5rem' }} />Order History</h1>
                <p className="menu-subtitle">A chronicle of your culinary adventures</p>
            </div>

            {error && (
                <div style={{ background: 'rgba(255,59,127,0.1)', border: '1px solid #ff3b7f', color: '#ff3b7f', padding: '1rem 1.5rem', borderRadius: 12, marginBottom: '2rem' }}>
                    ⚠️ {error}
                </div>
            )}

            {orders.length === 0 ? (
                <div style={{ maxWidth: 480, margin: '4rem auto', textAlign: 'center', background: 'rgba(10,10,15,0.85)', border: '1px solid rgba(0,243,255,0.1)', borderRadius: 20, padding: '4rem 2rem' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📜</div>
                    <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No orders yet</h3>
                    <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Start your culinary journey today.</p>
                    <Link to="/menu" className="btn btn-primary" style={{ textDecoration: 'none' }}>Explore Menu</Link>
                </div>
            ) : (
                <div className="orders-grid">
                    {orders.map((order, index) => (
                        <div key={order.id} className="order-card glass-panel animate-in"
                            style={{ animationDelay: `${index * 0.07}s` }}>
                            <div className="order-card-header">
                                <div className="order-info">
                                    <h3 className="order-number">Order #{order.id}</h3>
                                    <span className="order-date">{new Date(order.timestamp).toLocaleString()}</span>
                                </div>
                                <div className="order-status-badge">
                                    <span className={`status-dot ${order.status || 'completed'}`}></span>
                                    {order.status ? order.status.charAt(0).toUpperCase() + order.status.slice(1) : 'Completed'}
                                </div>
                            </div>
                            <div className="order-card-content">
                                <ul className="order-items-list">
                                    {order.items.map((item, idx) => (
                                        <li key={idx} className="order-item-row">
                                            <span className="item-qty">{item.quantity}×</span>
                                            <span className="item-name">{item.item_name}</span>
                                            <span className="item-price">₹{(item.unit_price * item.quantity).toFixed(2)}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="order-card-footer">
                                <div className="order-total-label">Total</div>
                                <div className="order-total-value">₹{order.total_price.toFixed(2)}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default OrderHistoryPage;
