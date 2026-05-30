import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { FaPlus, FaCheck, FaFilter, FaSearch, FaLeaf, FaDrumstickBite, FaUtensils, FaFire, FaStar, FaWineGlass, FaHeart } from 'react-icons/fa';
import CookingTipsModal from '../components/modals/CookingTipsModal';
import RatingModal from '../components/modals/RatingModal';
import DrinkPairingModal from '../components/modals/DrinkPairingModal';

function MenuPage() {
    const { currentUser } = useAuth();
    const { refreshCart } = useCart();
    const [menu, setMenu] = useState([]);
    const [filteredMenu, setFilteredMenu] = useState([]);
    const [error, setError] = useState('');
    const [notification, setNotification] = useState('');
    const [addedItems, setAddedItems] = useState(new Set());
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [searchTerm, setSearchTerm] = useState('');
    const [dietFilter, setDietFilter] = useState('All');
    const [maxPrice, setMaxPrice] = useState(1000);
    const [isLoaded, setIsLoaded] = useState(false);
    const [nutritionRecs, setNutritionRecs] = useState([]);
    const [showNutritionRecs, setShowNutritionRecs] = useState(false);
    const [loadingNutrition, setLoadingNutrition] = useState(false);
    const [debouncedSearch, setDebouncedSearch] = useState(searchTerm);
    const [debouncedMaxPrice, setDebouncedMaxPrice] = useState(maxPrice);
    const [favorites, setFavorites] = useState(new Set());

    // Modal states
    const [showCookingTips, setShowCookingTips] = useState(false);
    const [showRating, setShowRating] = useState(false);
    const [showPairing, setShowPairing] = useState(false);
    const [selectedItem, setSelectedItem] = useState(null);

    // Debounce effects
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedSearch(searchTerm), 500);
        return () => clearTimeout(timer);
    }, [searchTerm]);

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedMaxPrice(maxPrice), 400);
        return () => clearTimeout(timer);
    }, [maxPrice]);

    useEffect(() => {
        const fetchMenu = async () => {
            const params = new URLSearchParams();
            if (dietFilter !== 'All') {
                params.append('diet', dietFilter);
            }
            if (selectedCategory !== 'All') {
                params.append('category', selectedCategory);
            }
            if (debouncedSearch) {
                params.append('search', debouncedSearch);
            }
            params.append('max_price', debouncedMaxPrice);

            const endpoint = currentUser ? '/api/menu/filtered' : '/api/menu';

            try {
                const response = await axios.get(endpoint, { params });
                setMenu(response.data);
                setFilteredMenu(response.data);
                setIsLoaded(true);
            } catch (error) {
                console.error('Error fetching menu:', error);
                setError('Could not load the menu. Please ensure the backend server is running.');
            }
        };

        const fetchFavorites = async () => {
            if (!currentUser) return;
            try {
                const response = await axios.get('/api/favorites/my-favorites');
                // Backend returns a plain array of menu item objects
                const data = Array.isArray(response.data) ? response.data : (response.data.favorites || []);
                setFavorites(new Set(data.map(f => String(f.id))));
            } catch (error) {
                console.error('Error fetching favorites:', error);
            }
        };

        fetchMenu();
        fetchFavorites();
    }, [currentUser, dietFilter, selectedCategory, debouncedSearch, debouncedMaxPrice]);

    const showNotification = (message) => {
        setNotification(message);
        setTimeout(() => {
            setNotification('');
        }, 3000);
    };

    const addToCart = async (item) => {
        if (!currentUser) {
            showNotification('Please log in to add items to your cart.');
            return;
        }

        // Proactive Frontend Allergen Check
        if (currentUser.allergies) {
            const userAllergies = currentUser.allergies.toLowerCase().split(',').map(a => a.trim()).filter(a => a);
            const itemIngredients = (item.ingredients || '').toLowerCase();
            const detected = userAllergies.filter(allergy => itemIngredients.includes(allergy));

            if (detected.length > 0) {
                const confirmed = window.confirm(`⚠️ WARNING: This item contains ${detected.join(', ')} which you are allergic to! Are you sure you want to add it?`);
                if (!confirmed) return;
            }
        }

        try {
            await axios.post('/api/cart/add', { item_id: item.id, quantity: 1, force: true });

            // Call the refreshCart function from context to update cart UI
            refreshCart();

            // Temporary visual feedback on the button
            setAddedItems(prev => new Set(prev).add(item.id));
            setTimeout(() => {
                setAddedItems(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(item.id);
                    return newSet;
                });
            }, 2000);

        } catch (error) {
            console.error('Error adding to cart:', error);
            showNotification('Failed to add item to cart.');
        }
    };

    const toggleFavorite = async (itemId) => {
        if (!currentUser) {
            showNotification('Please log in to favorite items.');
            return;
        }

        try {
            const response = await axios.post('/api/favorites/toggle', { item_id: String(itemId) });
            setFavorites(prev => {
                const newSet = new Set(prev);
                if (response.data.is_favorite) {
                    newSet.add(String(itemId));
                } else {
                    newSet.delete(String(itemId));
                }
                return newSet;
            });
        } catch (error) {
            console.error('Error toggling favorite:', error);
        }
    };

    const fetchNutritionRecommendations = async () => {
        if (!currentUser) {
            showNotification('Please log in to view nutrition recommendations.');
            return;
        }
        setLoadingNutrition(true);

        const params = new URLSearchParams();
        if (dietFilter !== 'All') params.append('diet', dietFilter);
        if (selectedCategory !== 'All') params.append('category', selectedCategory);
        if (searchTerm) params.append('search', searchTerm);
        params.append('max_price', maxPrice);

        try {
            const response = await axios.get('/api/recommendations/nutrition', { params });
            console.log("Nutrition recommendations API response:", response.data);
            if (response.data.status === 'missing_goals') {
                showNotification(response.data.message);
                setNutritionRecs([]);
                setShowNutritionRecs(false);
            } else {
                setNutritionRecs(response.data);
                setShowNutritionRecs(true);
            }
        } catch (error) {
            console.error('Error fetching nutrition recommendations:', error);
            if (error.response && error.response.status === 400) {
                showNotification('Please set your nutrition goals in your profile first.');
            } else {
                showNotification('Failed to load nutrition recommendations.');
            }
        } finally {
            setLoadingNutrition(false);
        }
    };

    const categories = ['All', ...new Set(menu.map(item => item.category).filter(Boolean))];
    const diets = ['All', 'Vegetarian', 'Non-Vegetarian', 'Vegan'];

    const getDietIcon = (diet) => {
        switch (diet) {
            case 'Vegetarian': return <FaLeaf style={{ color: '#28a745' }} />;
            case 'Non-Vegetarian': return <FaDrumstickBite style={{ color: '#dc3545' }} />;
            case 'Vegan': return <FaLeaf style={{ color: '#17a2b8' }} />;
            default: return <FaUtensils style={{ color: '#6c757d' }} />;
        }
    };

    return (
        <div className="menu-page">
            <div className="menu-header">
                <h1 className="menu-title">Our Culinary Journey</h1>
                <p className="menu-subtitle">Discover authentic flavors crafted with tradition and innovation</p>
            </div>

            {notification && (
                <div className="notification-banner">
                    {notification}
                    <button onClick={() => setNotification('')} className="notification-close">&times;</button>
                </div>
            )}

            <div className="filters-section">
                <div className="search-bar">
                    <FaSearch className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search dishes, ingredients..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="search-input"
                    />
                </div>

                <div className="filter-controls">
                    <div className="filter-group">
                        <label className="filter-label">
                            <FaFilter /> Category
                        </label>
                        <select
                            value={selectedCategory}
                            onChange={(e) => setSelectedCategory(e.target.value)}
                            className="filter-select"
                        >
                            {categories.map(category => (
                                <option key={category} value={category}>{category}</option>
                            ))}
                        </select>
                    </div>

                    <div className="filter-group">
                        <label className="filter-label">
                            <FaLeaf /> Diet
                        </label>
                        <select
                            value={dietFilter}
                            onChange={(e) => setDietFilter(e.target.value)}
                            className="filter-select"
                        >
                            {diets.map(diet => (
                                <option key={diet} value={diet}>{diet}</option>
                            ))}
                        </select>
                    </div>

                    <div className="filter-group price-filter">
                        <label className="filter-label">
                            Price Range: ₹0 - ₹{maxPrice}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="1000"
                            step="50"
                            value={maxPrice}
                            onChange={(e) => setMaxPrice(parseInt(e.target.value))}
                            className="price-slider"
                        />
                    </div>
                </div>
            </div>

            {error && (
                <div className="error-message">
                    <span>⚠️</span> {error}
                </div>
            )}

            {currentUser && (
                <div className="nutrition-section">
                    <button
                        onClick={fetchNutritionRecommendations}
                        disabled={loadingNutrition}
                        className="nutrition-button"
                    >
                        {loadingNutrition ? 'Loading...' : 'Get Nutrition-Based Recommendations'}
                    </button>
                    {showNutritionRecs && nutritionRecs.length > 0 && (
                        <div className="nutrition-recs">
                            <h2>Personalized Nutrition Recommendations</h2>
                            <p>These dishes fit your daily nutrition goals.</p>
                            <div className="nutrition-grid">
                                {nutritionRecs.map((item, index) => (
                                    <div
                                        className="menu-card animate-in"
                                        key={`rec-${item.id}`}
                                        style={{ animationDelay: `${index * 0.1}s` }}
                                        onClick={() => {
                                            if (currentUser.allergies) {
                                                const userAllergies = currentUser.allergies.toLowerCase().split(',').map(a => a.trim()).filter(a => a);
                                                const itemIngredients = (item.ingredients || '').toLowerCase();
                                                const detected = userAllergies.filter(allergy => itemIngredients.includes(allergy));
                                                if (detected.length > 0) {
                                                    alert(`⚠️ WARNING: This item contains ${detected.join(', ')} which you are allergic to!`);
                                                }
                                            }
                                        }}
                                    >
                                        <div className="menu-card-header">
                                            <div className="menu-card-title-section">
                                                <h3 className="menu-card-title">{item.rec_name || item.name}</h3>
                                                <div className="menu-card-diet">
                                                    {getDietIcon(item.diet)}
                                                    <span>{item.diet}</span>
                                                </div>
                                            </div>
                                            <div className="menu-card-price">₹{item.price.toFixed(2)}</div>
                                        </div>
                                        <div className="menu-card-content">
                                            <p className="menu-card-description">{item.description}</p>
                                            <div className="menu-card-ingredients">
                                                <strong>Ingredients:</strong> {item.ingredients}
                                            </div>
                                            <div className="nutrition-info">
                                                <strong>Nutrition:</strong> {item.calories} cal, {item.protein}g protein, {item.carbs}g carbs, {item.fat}g fat
                                            </div>
                                        </div>
                                        <div className="menu-card-actions">
                                            <button
                                                className={`action-icon-button like-btn ${favorites.has(String(item.id)) ? 'liked' : ''}`}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleFavorite(item.id);
                                                }}
                                                title={favorites.has(String(item.id)) ? "Remove from favorites" : "Add to favorites"}
                                            >
                                                ❤️
                                            </button>
                                            <button
                                                className="action-icon-button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedItem(item);
                                                    setShowCookingTips(true);
                                                }}
                                                title="Get Cooking Tips"
                                            >
                                                👨‍🍳
                                            </button>
                                            <button
                                                className="action-icon-button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedItem(item);
                                                    setShowRating(true);
                                                }}
                                                title="Rate This Dish"
                                            >
                                                ⭐
                                            </button>
                                            <button
                                                className="action-icon-button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedItem(item);
                                                    setShowPairing(true);
                                                }}
                                                title="Find Drink Pairing"
                                            >
                                                🥂
                                            </button>
                                            <button
                                                className={`menu-card-button ${addedItems.has(item.id) ? 'added' : ''}`}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    addToCart(item);
                                                }}
                                            >
                                                {addedItems.has(item.id) ? (
                                                    <>
                                                        <FaCheck /> Added!
                                                    </>
                                                ) : (
                                                    <>
                                                        <FaPlus /> Add
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    {showNutritionRecs && nutritionRecs.length === 0 && (
                        <div className="no-recs">
                            <p>No recommendations found that match your goals. Try adjusting your nutrition goals or menu filters.</p>
                        </div>
                    )}
                </div>
            )}

            <div className="menu-grid">
                {filteredMenu.map((item, index) => (
                    <div
                        className={`menu-card ${isLoaded ? 'animate-in' : ''}`}
                        key={item.id}
                        style={{ animationDelay: `${index * 0.1}s` }}
                        onClick={() => {
                            if (currentUser?.allergies) {
                                const userAllergies = currentUser.allergies.toLowerCase().split(',').map(a => a.trim()).filter(a => a);
                                const itemIngredients = (item.ingredients || '').toLowerCase();
                                const detected = userAllergies.filter(allergy => itemIngredients.includes(allergy));
                                if (detected.length > 0) {
                                    alert(`⚠️ WARNING: This item (${item.name}) contains ${detected.join(', ')} which you are allergic to!`);
                                }
                            }
                        }}
                    >
                        <div className="menu-card-header">
                            <div className="menu-card-title-section">
                                <h3 className="menu-card-title">{item.name}</h3>
                                <div className="menu-card-diet">
                                    {getDietIcon(item.diet)}
                                    <span>{item.diet}</span>
                                </div>
                            </div>
                            <div className="menu-card-price">₹{item.price.toFixed(2)}</div>
                        </div>

                        <div className="menu-card-content">
                            <p className="menu-card-description">{item.description}</p>
                            <div className="menu-card-ingredients">
                                <strong>Ingredients:</strong> {item.ingredients}
                            </div>
                        </div>

                        {currentUser && (
                            <div className="menu-card-actions">
                                <button
                                    className={`action-icon-button like-btn ${favorites.has(String(item.id)) ? 'liked' : ''}`}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        toggleFavorite(item.id);
                                    }}
                                    title={favorites.has(String(item.id)) ? "Remove from favorites" : "Add to favorites"}
                                >
                                    ❤️
                                </button>
                                <button
                                    className="action-icon-button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedItem(item);
                                        setShowCookingTips(true);
                                    }}
                                    title="Get Cooking Tips"
                                >
                                    👨‍🍳
                                </button>
                                <button
                                    className="action-icon-button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedItem(item);
                                        setShowRating(true);
                                    }}
                                    title="Rate This Dish"
                                >
                                    ⭐
                                </button>
                                <button
                                    className="action-icon-button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedItem(item);
                                        setShowPairing(true);
                                    }}
                                    title="Find Drink Pairing"
                                >
                                    🥂
                                </button>
                                <button
                                    className={`menu-card-button ${addedItems.has(item.id) ? 'added' : ''}`}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        addToCart(item);
                                    }}
                                >
                                    {addedItems.has(item.id) ? (
                                        <>
                                            <FaCheck /> Added!
                                        </>
                                    ) : (
                                        <>
                                            <FaPlus /> Add
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {filteredMenu.length === 0 && !error && isLoaded && (
                <div className="no-results">
                    <div className="no-results-icon">🔍</div>
                    <h3>No dishes found</h3>
                    <p>Try adjusting your filters or search terms</p>
                </div>
            )}

            {/* Agent Modals */}
            <CookingTipsModal
                isOpen={showCookingTips}
                onClose={() => setShowCookingTips(false)}
                itemName={selectedItem?.name || selectedItem?.rec_name}
                itemTips={selectedItem?.cooking_tips}
            />
            <RatingModal
                isOpen={showRating}
                onClose={() => setShowRating(false)}
                itemName={selectedItem?.name || selectedItem?.rec_name}
                itemId={selectedItem?.id}
            />
            <DrinkPairingModal
                isOpen={showPairing}
                onClose={() => setShowPairing(false)}
                itemName={selectedItem?.name || selectedItem?.rec_name}
            />
        </div>
    );
}

export default MenuPage;