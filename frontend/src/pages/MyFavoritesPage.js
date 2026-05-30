import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { FaHeart, FaPlus, FaCheck, FaLeaf, FaDrumstickBite, FaUtensils } from 'react-icons/fa';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';

function MyFavoritesPage() {
    const { currentUser } = useAuth();
    const { refreshCart } = useCart();
    const [favorites, setFavorites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [addedItems, setAddedItems] = useState(new Set());
    const [notification, setNotification] = useState('');

    useEffect(() => {
        fetchFavorites();
    }, []);

    const fetchFavorites = async () => {
        try {
            const res = await axios.get('/api/favorites/my-favorites');
            // Backend returns a plain array of menu item objects
            const data = Array.isArray(res.data) ? res.data : (res.data.favorites || []);
            setFavorites(data);
        } catch (err) {
            setError('Failed to load favorites.');
        } finally {
            setLoading(false);
        }
    };

    const removeFavorite = async (itemId) => {
        try {
            await axios.post('/api/favorites/toggle', { item_id: itemId });
            setFavorites(prev => prev.filter(f => f.id !== itemId));
            showNotification('Removed from favorites');
        } catch (err) {
            showNotification('Failed to remove favorite.');
        }
    };

    const addToCart = async (item) => {
        if (!currentUser) return;
        if (currentUser.allergies) {
            const userAllergies = currentUser.allergies.toLowerCase().split(',').map(a => a.trim()).filter(a => a);
            const itemIngredients = (item.ingredients || '').toLowerCase();
            const detected = userAllergies.filter(a => itemIngredients.includes(a));
            if (detected.length > 0) {
                const confirmed = window.confirm(`⚠️ This item contains ${detected.join(', ')} which you are allergic to! Add anyway?`);
                if (!confirmed) return;
            }
        }
        try {
            await axios.post('/api/cart/add', { item_id: item.id, quantity: 1, force: true });
            refreshCart();
            setAddedItems(prev => new Set(prev).add(item.id));
            setTimeout(() => setAddedItems(prev => { const s = new Set(prev); s.delete(item.id); return s; }), 2000);
        } catch (err) {
            showNotification('Failed to add to cart.');
        }
    };

    const showNotification = (msg) => {
        setNotification(msg);
        setTimeout(() => setNotification(''), 3000);
    };

    const getDietIcon = (diet) => {
        switch (diet) {
            case 'Vegetarian': return <FaLeaf style={{ color: '#28a745' }} />;
            case 'Non-Vegetarian': return <FaDrumstickBite style={{ color: '#dc3545' }} />;
            case 'Vegan': return <FaLeaf style={{ color: '#17a2b8' }} />;
            default: return <FaUtensils style={{ color: '#6c757d' }} />;
        }
    };

    if (loading) return <div className="page-content" style={{ textAlign: 'center', paddingTop: '8rem', color: 'var(--neon-cyan)' }}>Loading favorites...</div>;

    return (
        <div className="favorites-page page-content">
            {notification && (
                <div className="notification-banner">
                    {notification}
                    <button onClick={() => setNotification('')} className="notification-close">&times;</button>
                </div>
            )}

            <div className="menu-header">
                <h1 className="menu-title"><FaHeart style={{ marginRight: '0.5rem', color: '#ff3b7f' }} />My Favorites</h1>
                <p className="menu-subtitle">Your curated collection of beloved dishes</p>
            </div>

            {error && <div style={{ background: 'rgba(255,59,127,0.1)', border: '1px solid #ff3b7f', color: '#ff3b7f', padding: '1rem 1.5rem', borderRadius: '12px', marginBottom: '2rem' }}>{error}</div>}

            {favorites.length === 0 ? (
                <div className="empty-orders-view glass-panel animate-in" style={{ textAlign: 'center', padding: '4rem 2rem', borderRadius: '20px', maxWidth: '500px', margin: '0 auto' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>❤️</div>
                    <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No favorites yet</h3>
                    <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Tap the ❤️ on any dish to save it here.</p>
                    <Link to="/menu" className="btn btn-primary" style={{ textDecoration: 'none' }}>Explore Menu</Link>
                </div>
            ) : (
                <div className="menu-grid">
                    {favorites.map((item, index) => (
                        <div
                            key={item.id}
                            className="menu-card animate-in"
                            style={{ animationDelay: `${index * 0.08}s` }}
                        >
                            <div className="menu-card-header">
                                <div className="menu-card-title-section">
                                    <h3 className="menu-card-title">{item.name}</h3>
                                    <div className="menu-card-diet">
                                        {getDietIcon(item.diet)}
                                        <span>{item.diet}</span>
                                    </div>
                                </div>
                                <div className="menu-card-price">₹{item.price?.toFixed(2)}</div>
                            </div>

                            <div className="menu-card-content">
                                <p className="menu-card-description">{item.description}</p>
                                <div className="menu-card-ingredients">
                                    <strong>Ingredients:</strong> {item.ingredients}
                                </div>
                                {item.calories && (
                                    <div style={{ fontSize: '0.85rem', color: 'var(--neon-green)', marginTop: '0.5rem' }}>
                                        {item.calories} cal · {item.protein}g protein · {item.carbs}g carbs · {item.fat}g fat
                                    </div>
                                )}
                            </div>

                            <div className="menu-card-actions">
                                <button
                                    className="action-icon-button liked"
                                    onClick={() => removeFavorite(item.id)}
                                    title="Remove from favorites"
                                    style={{ color: '#ff3b7f' }}
                                >
                                    ❤️
                                </button>
                                <button
                                    className={`menu-card-button ${addedItems.has(item.id) ? 'added' : ''}`}
                                    style={{ gridColumn: '2 / -1' }}
                                    onClick={() => addToCart(item)}
                                >
                                    {addedItems.has(item.id) ? <><FaCheck /> Added!</> : <><FaPlus /> Add to Cart</>}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default MyFavoritesPage;
