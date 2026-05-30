import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import io from 'socket.io-client';
import axios from 'axios';
import { FaCheck, FaClock, FaRedo, FaUser, FaInfoCircle } from 'react-icons/fa';

const socket = io('http://localhost:5000');

function AdminInbox() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchOrders = async () => {
        try {
            const response = await axios.get('/api/admin/orders');
            setOrders(response.data);
            setLoading(false);
        } catch (err) {
            console.error('Error fetching admin orders:', err);
            setError('Failed to load orders. Please login again.');
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrders();

        socket.emit('join', { role: 'admin' });

        socket.on('new_order', (newOrder) => {
            setOrders(prevOrders => [newOrder, ...prevOrders]);
            // Optional: Play a sound or show a desktop notification
            if (Notification.permission === 'granted') {
                new Notification('New Order Received!', {
                    body: `Order #${newOrder.id} - ₹${newOrder.total_price}`,
                });
            }
        });

        return () => {
            socket.off('new_order');
        };
    }, []);

    const updateOrderStatus = async (orderId, newStatus) => {
        try {
            await axios.patch(`/api/admin/orders/${orderId}/status`, { status: newStatus });
            setOrders(orders.map(o => o.id === orderId ? { ...o, status: newStatus } : o));
        } catch (err) {
            alert('Failed to update status');
        }
    };

    const getStatusBadgeClass = (status) => {
        switch (status) {
            case 'completed': return 'status-badge completed';
            case 'cancelled': return 'status-badge cancelled';
            case 'preparing': return 'status-badge preparing';
            default: return 'status-badge pending';
        }
    };

    if (loading) return <div className="admin-loading">Loading live orders...</div>;

    return (
        <div className="container mt-4 page-content admin-inbox-page">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <div className="title-group">
                    <h2 className="admin-title">Live Seller Inbox</h2>
                    <p className="admin-subtitle">Real-time order tracking and status management</p>
                </div>
                <div className="admin-nav-pills">
                    <Link to="/admin-dashboard" className="btn btn-outline-secondary me-2">Add Dish</Link>
                    <Link to="/admin-menu" className="btn btn-outline-secondary me-2">Manage All</Link>
                    <Link to="/admin-inbox" className="btn btn-outline-primary active">Real-time Orders</Link>
                </div>
            </div>

            {error ? (
                <div className="alert alert-danger">{error}</div>
            ) : orders.length === 0 ? (
                <div className="empty-orders-card">
                    <div className="pulse-icon"><FaClock /></div>
                    <p>Waiting for new orders...</p>
                    <button className="btn btn-sm btn-outline-info mt-3" onClick={fetchOrders}><FaRedo /> Refresh Now</button>
                </div>
            ) : (
                <div className="orders-timeline">
                    {orders.map((order) => (
                        <div key={order.id} className={`order-card-premium ${order.status}`}>
                            <div className="order-header">
                                <div className="order-info">
                                    <span className="order-id">#{order.id}</span>
                                    <span className="order-time">{new Date(order.timestamp).toLocaleString()}</span>
                                </div>
                                <div className={getStatusBadgeClass(order.status)}>
                                    {order.status.toUpperCase()}
                                </div>
                            </div>

                            <div className="order-body">
                                <div className="customer-info mb-3">
                                    <FaUser className="me-2" /> <strong>{order.username}</strong>
                                </div>
                                <ul className="order-items-list">
                                    {order.items.map((item, idx) => (
                                        <li key={idx} className="order-item-row">
                                            <span className="item-qty">{item.quantity}x</span>
                                            <span className="item-name">{item.item_name}</span>
                                            <span className="item-price">₹{item.unit_price}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div className="order-total-row">
                                    <span>Total Amount</span>
                                    <span className="total-amount">₹{order.total_price.toFixed(2)}</span>
                                </div>
                            </div>

                            <div className="order-actions">
                                {order.status === 'pending' && (
                                    <button
                                        className="btn btn-preparing"
                                        onClick={() => updateOrderStatus(order.id, 'preparing')}
                                    >
                                        <FaClock /> Start Preparing
                                    </button>
                                )}
                                {(order.status === 'pending' || order.status === 'preparing') && (
                                    <button
                                        className="btn btn-complete"
                                        onClick={() => updateOrderStatus(order.id, 'completed')}
                                    >
                                        <FaCheck /> Mark Complete
                                    </button>
                                )}
                                {order.status === 'completed' && (
                                    <div className="completed-label text-success">
                                        <FaCheck /> Successfully Delivered
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <style jsx>{`
                .admin-inbox-page {
                    max-width: 900px !important;
                    margin: 0 auto;
                }

                .admin-title {
                    font-size: 2rem;
                    font-weight: 700;
                    margin: 0;
                    background: linear-gradient(135deg, #00d4ff, #b026ff);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .admin-subtitle {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.9rem;
                    margin-top: 4px;
                }

                .empty-orders-card {
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    padding: 3rem;
                    text-align: center;
                    color: rgba(255, 255, 255, 0.7);
                    margin-top: 2rem;
                }

                .pulse-icon {
                    font-size: 3rem;
                    margin-bottom: 1rem;
                    animation: pulse 2s infinite;
                    color: #00d4ff;
                }

                @keyframes pulse {
                    0% { opacity: 0.4; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.1); }
                    100% { opacity: 0.4; transform: scale(1); }
                }

                .orders-timeline {
                    display: flex;
                    flex-direction: column;
                    gap: 1.5rem;
                    margin-top: 2rem;
                }

                .order-card-premium {
                    background: rgba(15, 15, 25, 0.8);
                    backdrop-filter: blur(20px);
                    border-radius: 20px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    overflow: hidden;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                }

                .order-card-premium:hover {
                    transform: translateY(-5px);
                    border-color: rgba(0, 212, 255, 0.3);
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                }

                .order-card-premium.completed {
                    opacity: 0.8;
                    border-color: rgba(40, 167, 69, 0.3);
                }

                .order-header {
                    padding: 1.2rem 1.5rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: rgba(255, 255, 255, 0.03);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                }

                .order-id {
                    color: #00d4ff;
                    font-weight: 700;
                    font-size: 1.2rem;
                    margin-right: 12px;
                }

                .order-time {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.85rem;
                }

                .status-badge {
                    padding: 6px 14px;
                    border-radius: 50px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }

                .status-badge.pending { background: rgba(255, 193, 7, 0.15); color: #ffc107; border: 1px solid #ffc107; }
                .status-badge.preparing { background: rgba(23, 162, 184, 0.15); color: #17a2b8; border: 1px solid #17a2b8; }
                .status-badge.completed { background: rgba(40, 167, 69, 0.15); color: #28a745; border: 1px solid #28a745; }
                .status-badge.cancelled { background: rgba(220, 53, 69, 0.15); color: #dc3545; border: 1px solid #dc3545; }

                .order-body {
                    padding: 1.5rem;
                }

                .order-items-list {
                    list-style: none;
                    padding: 0;
                    margin: 0 0 1.5rem 0;
                }

                .order-item-row {
                    display: flex;
                    padding: 8px 0;
                    border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
                    font-size: 1rem;
                }

                .item-qty {
                    color: #00d4ff;
                    font-weight: 700;
                    width: 40px;
                }

                .item-name {
                    flex: 1;
                    color: rgba(255, 255, 255, 0.9);
                }

                .item-price {
                    color: rgba(255, 255, 255, 0.6);
                    font-variant-numeric: tabular-nums;
                }

                .order-total-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 1rem;
                }

                .total-amount {
                    color: #fff;
                    font-size: 1.5rem;
                    font-weight: 700;
                }

                .order-actions {
                    padding: 1.2rem 1.5rem;
                    background: rgba(0, 0, 0, 0.2);
                    display: flex;
                    gap: 1rem;
                }

                .btn-preparing {
                    background: rgba(23, 162, 184, 0.2);
                    border: 1px solid #17a2b8;
                    color: #17a2b8;
                    padding: 10px 20px;
                    border-radius: 12px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: 600;
                    transition: all 0.2s;
                }

                .btn-preparing:hover {
                    background: #17a2b8;
                    color: #fff;
                }

                .btn-complete {
                    background: linear-gradient(135deg, #00d4ff, #b026ff);
                    border: none;
                    color: #fff;
                    padding: 10px 20px;
                    border-radius: 12px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: 600;
                    transition: all 0.2s;
                    box-shadow: 0 4px 15px rgba(176, 38, 255, 0.3);
                }

                .btn-complete:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(176, 38, 255, 0.5);
                }

                .completed-label {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: 700;
                    font-size: 1.1rem;
                }
            `}</style>
        </div>
    );
}

export default AdminInbox;