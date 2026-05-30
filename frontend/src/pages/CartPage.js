import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { FaShoppingCart, FaTrash, FaPlus, FaMinus, FaArrowRight } from 'react-icons/fa';

function CartPage() {
    const { cart, refreshCart, isLoading } = useCart();
    const [checkingOut, setCheckingOut] = useState(false);
    const [notification, setNotification] = useState('');
    const navigate = useNavigate();

    useEffect(() => { refreshCart(); }, [refreshCart]);

    const showNote = msg => { setNotification(msg); setTimeout(() => setNotification(''), 3500); };

    const removeItem = async name => {
        try {
            await axios.post('/api/cart/remove', { item_name: name });
            refreshCart();
        } catch { showNote('Failed to remove item.'); }
    };

    const handleCheckout = async () => {
        setCheckingOut(true);
        try {
            const res = await axios.post('/api/checkout');
            showNote(res.data.message || 'Order placed!');
            refreshCart();
            setTimeout(() => navigate('/order-history'), 2000);
        } catch (e) {
            showNote(e.response?.data?.message || 'Checkout failed.');
        } finally { setCheckingOut(false); }
    };

    const total = cart.reduce((s, i) => s + i.qty * i.unit_price, 0);

    if (isLoading) return (
        <div className="page-content" style={{ textAlign: 'center', paddingTop: '8rem', color: 'var(--neon-cyan)' }}>
            Loading cart...
        </div>
    );

    return (
        <div className="cart-page page-content">
            {notification && (
                <div className="notification-banner">
                    {notification}
                    <button onClick={() => setNotification('')} className="notification-close">&times;</button>
                </div>
            )}

            <div className="menu-header">
                <h1 className="menu-title"><FaShoppingCart style={{ marginRight: '0.5rem' }} />Your Cart</h1>
                <p className="menu-subtitle">Review your selection before checkout</p>
            </div>

            {cart.length === 0 ? (
                <div className="empty-cart-view glass-panel animate-in">
                    <div className="no-results-icon"><FaShoppingCart style={{ opacity: 0.15 }} /></div>
                    <h3>Your cart is empty</h3>
                    <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Discover something extraordinary from our menu.</p>
                    <Link to="/menu" className="btn btn-primary" style={{ textDecoration: 'none' }}>Explore Menu</Link>
                </div>
            ) : (
                <div className="cart-container">
                    {/* Items */}
                    <div className="cart-items-section">
                        <div className="cart-items-list">
                            {cart.map((item, i) => (
                                <div key={i} className="cart-item-card glass-panel animate-in"
                                    style={{ animationDelay: `${i * 0.06}s` }}>
                                    <div className="item-info">
                                        <h3>{item.name}</h3>
                                        <p className="item-price-detail">₹{item.unit_price.toFixed(2)} × {item.qty}</p>
                                    </div>
                                    <div className="item-actions">
                                        <div className="item-subtotal">₹{(item.qty * item.unit_price).toFixed(2)}</div>
                                        <button onClick={() => removeItem(item.name)} className="btn-remove" title="Remove">
                                            <FaTrash />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Summary */}
                    <div className="cart-summary-section">
                        <div className="cart-summary-card glass-panel">
                            <h2>Order Summary</h2>
                            <div className="summary-details">
                                <div className="summary-row">
                                    <span>Subtotal ({cart.length} item{cart.length !== 1 ? 's' : ''})</span>
                                    <span>₹{total.toFixed(2)}</span>
                                </div>
                                <div className="summary-row">
                                    <span>Service Fee</span>
                                    <span style={{ color: 'var(--neon-green)' }}>Free</span>
                                </div>
                                <div className="summary-divider"></div>
                                <div className="summary-row total-row">
                                    <span>Total</span>
                                    <span className="total-amount">₹{total.toFixed(2)}</span>
                                </div>
                            </div>
                            <button
                                className="btn btn-primary checkout-btn"
                                onClick={handleCheckout}
                                disabled={checkingOut}
                            >
                                {checkingOut ? 'Placing Order...' : (
                                    <><FaArrowRight style={{ marginRight: 8 }} />Place Order</>
                                )}
                            </button>
                            <Link to="/menu" style={{ display: 'block', textAlign: 'center', marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.9rem', textDecoration: 'none' }}>
                                ← Continue Shopping
                            </Link>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CartPage;
