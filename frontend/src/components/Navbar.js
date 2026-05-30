import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FaSignOutAlt, FaSignInAlt, FaUserPlus, FaShoppingCart, FaInbox, FaUser, FaUtensils, FaCalendarAlt, FaHistory, FaBars, FaTimes, FaHeart } from 'react-icons/fa';

function Navbar() {
    const { currentUser, logout } = useAuth();
    const navigate = useNavigate();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [diningDropdownOpen, setDiningDropdownOpen] = useState(false);
    const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);

    const handleLogout = async () => {
        try {
            await logout();
            navigate('/');
            setMobileMenuOpen(false);
        } catch (error) {
            console.error("Failed to logout:", error);
        }
    };

    const toggleMobileMenu = () => {
        setMobileMenuOpen(!mobileMenuOpen);
    };

    const closeMobileMenu = () => {
        setMobileMenuOpen(false);
        setDiningDropdownOpen(false);
        setAccountDropdownOpen(false);
    };

    return (
        <>
            <nav className="navbar-premium">
                <div className="navbar-container">
                    {/* Logo */}
                    <Link className="navbar-logo" to="/" onClick={closeMobileMenu}>
                        <span className="logo-icon">🌶️</span>
                        <span className="logo-text">DineSmartAI</span>
                    </Link>

                    {/* Mobile Toggle */}
                    <button className="mobile-toggle" onClick={toggleMobileMenu}>
                        {mobileMenuOpen ? <FaTimes /> : <FaBars />}
                    </button>

                    {/* Nav Links */}
                    <ul className={`navbar-menu ${mobileMenuOpen ? 'active' : ''}`}>

                        {/* Dining Dropdown */}
                        <li className="nav-item dropdown">
                            <button
                                className="nav-link dropdown-toggle"
                                onClick={() => setDiningDropdownOpen(!diningDropdownOpen)}
                            >
                                <FaUtensils /> Dining
                            </button>
                            <ul className={`dropdown-menu ${diningDropdownOpen ? 'show' : ''}`}>
                                <li>
                                    <Link className="dropdown-item" to="/menu" onClick={closeMobileMenu}>
                                        <FaUtensils /> Browse Menu
                                    </Link>
                                </li>
                                <li>
                                    <Link className="dropdown-item" to="/book-table" onClick={closeMobileMenu}>
                                        <FaCalendarAlt /> Book a Table
                                    </Link>
                                </li>
                            </ul>
                        </li>

                        {/* Conditional User Links */}
                        {currentUser ? (
                            <>
                                {/* Cart Link */}
                                <li className="nav-item">
                                    <Link className="nav-link" to="/cart" onClick={closeMobileMenu}>
                                        <FaShoppingCart /> Cart
                                    </Link>
                                </li>

                                {/* My Account Dropdown */}
                                <li className="nav-item dropdown">
                                    <button
                                        className="nav-link dropdown-toggle"
                                        onClick={() => setAccountDropdownOpen(!accountDropdownOpen)}
                                    >
                                        <FaUser /> My Account
                                    </button>
                                    <ul className={`dropdown-menu ${accountDropdownOpen ? 'show' : ''}`}>
                                        <li>
                                            <Link className="dropdown-item" to="/order-history" onClick={closeMobileMenu}>
                                                <FaHistory /> My Orders
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="dropdown-item" to="/my-reservations" onClick={closeMobileMenu}>
                                                <FaCalendarAlt /> My Reservations
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="dropdown-item" to="/my-favorites" onClick={closeMobileMenu}>
                                                <FaHeart /> My Favorites
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="dropdown-item" to="/user-inbox" onClick={closeMobileMenu}>
                                                <FaInbox /> Inbox
                                            </Link>
                                        </li>
                                        <li>
                                            <Link className="dropdown-item" to="/profile" onClick={closeMobileMenu}>
                                                <FaUser /> Profile & Nutrition
                                                <span className="nutrition-labels-hint"> (Calories, Carbs, Protein, Fats)</span>
                                            </Link>
                                        </li>
                                    </ul>
                                </li>

                                {/* Admin Link */}
                                {currentUser.role === 'admin' && (
                                    <li className="nav-item">
                                        <Link className="nav-link admin-link" to="/admin-dashboard" onClick={closeMobileMenu}>
                                            🛡️ Admin
                                        </Link>
                                    </li>
                                )}

                                {/* Logout */}
                                <li className="nav-item">
                                    <button className="nav-link btn-logout" onClick={handleLogout}>
                                        <FaSignOutAlt /> Logout
                                    </button>
                                </li>
                            </>
                        ) : (
                            <>
                                {/* Login/Register */}
                                <li className="nav-item">
                                    <Link className="nav-link" to="/login" onClick={closeMobileMenu}>
                                        <FaSignInAlt /> Login
                                    </Link>
                                </li>
                                <li className="nav-item">
                                    <Link className="nav-link btn-register" to="/signup" onClick={closeMobileMenu}>
                                        <FaUserPlus /> Register
                                    </Link>
                                </li>
                            </>
                        )}
                    </ul>
                </div>
            </nav>

            <style jsx>{`
                .navbar-premium {
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    padding: 0;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                }

                .navbar-container {
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 2rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    height: 70px;
                }

                .navbar-logo {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    text-decoration: none;
                    color: #fff;
                    font-size: 1.5rem;
                    font-weight: 700;
                    transition: transform 0.3s;
                }

                .navbar-logo:hover {
                    transform: scale(1.05);
                }

                .logo-icon {
                    font-size: 2rem;
                }

                .logo-text {
                    background: linear-gradient(135deg, #00d4ff, #b026ff);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .mobile-toggle {
                    display: none;
                    background: none;
                    border: none;
                    color: #fff;
                    font-size: 1.5rem;
                    cursor: pointer;
                }

                .navbar-menu {
                    display: flex;
                    list-style: none;
                    margin: 0;
                    padding: 0;
                    gap: 0.5rem;
                    align-items: center;
                }

                .nav-item {
                    position: relative;
                }

                .nav-link, .dropdown-toggle {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 18px;
                    color: rgba(255, 255, 255, 0.9);
                    text-decoration: none;
                    border-radius: 8px;
                    transition: all 0.3s;
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 0.95rem;
                    font-weight: 500;
                }

                .nav-link:hover, .dropdown-toggle:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #00d4ff;
                }

                .btn-logout {
                    background: rgba(220, 53, 69, 0.2);
                    border: 1px solid rgba(220, 53, 69, 0.5);
                }

                .btn-logout:hover {
                    background: rgba(220, 53, 69, 0.4);
                    color: #fff;
                }

                .btn-register {
                    background: linear-gradient(135deg, #00d4ff, #b026ff);
                    color: #fff;
                    font-weight: 600;
                }

                .btn-register:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0, 212, 255, 0.4);
                }

                .admin-link {
                    background: rgba(255, 193, 7, 0.2);
                    border: 1px solid rgba(255, 193, 7, 0.5);
                }

                /* Dropdown Styles */
                .dropdown-menu {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    background: #16213e;
                    border: 1px solid rgba(0, 212, 255, 0.3);
                    border-radius: 8px;
                    padding: 8px 0;
                    min-width: 200px;
                    list-style: none;
                    margin-top: 8px;
                    opacity: 0;
                    visibility: hidden;
                    transform: translateY(-10px);
                    transition: all 0.3s;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                }

                .dropdown-menu.show {
                    opacity: 1;
                    visibility: visible;
                    transform: translateY(0);
                }

                .dropdown-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 12px 20px;
                    color: rgba(255, 255, 255, 0.9);
                    text-decoration: none;
                    transition: all 0.2s;
                    font-size: 0.9rem;
                }

                .dropdown-item:hover {
                    background: rgba(0, 212, 255, 0.1);
                    color: #00d4ff;
                }

                .nutrition-labels-hint {
                    display: block;
                    font-size: 0.75rem;
                    color: rgba(255, 255, 255, 0.5);
                    margin-top: 2px;
                    margin-left: 28px;
                }

                /* Mobile Styles */
                @media (max-width: 992px) {
                    .mobile-toggle {
                        display: block;
                    }

                    .navbar-menu {
                        position: fixed;
                        top: 70px;
                        right: -100%;
                        width: 280px;
                        height: calc(100vh - 70px);
                        background: #1a1a2e;
                        flex-direction: column;
                        align-items: flex-start;
                        padding: 2rem;
                        gap: 0;
                        transition: right 0.3s;
                        box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
                        overflow-y: auto;
                    }

                    .navbar-menu.active {
                        right: 0;
                    }

                    .nav-item {
                        width: 100%;
                        margin: 8px 0;
                    }

                    .nav-link, .dropdown-toggle {
                        width: 100%;
                        justify-content: flex-start;
                        padding: 14px 18px;
                    }

                    .dropdown-menu {
                        position: static;
                        width: 100%;
                        margin-top: 8px;
                        margin-left: 20px;
                        box-shadow: none;
                        border-left: 2px solid #00d4ff;
                    }
                }
            `}</style>
        </>
    );
}

export default Navbar;