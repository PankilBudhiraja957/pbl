import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { FaPlus, FaTrash, FaEdit, FaSave, FaTimes } from 'react-icons/fa';

function AdminPage() {
    const [menuItems, setMenuItems] = useState([]);
    const [newItem, setNewItem] = useState({
        name: '',
        description: '',
        ingredients: '',
        price: '',
        category: 'Starter', // Default to first option
        diet: 'Vegetarian',
        cooking_tips: '',
        calories: '',
        protein: '',
        carbs: '',
        fat: ''
    });
    const [editingItem, setEditingItem] = useState(null);
    const [editForm, setEditForm] = useState({});
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showAddForm, setShowAddForm] = useState(false);

    useEffect(() => {
        fetchMenuItems();
    }, []);

    const fetchMenuItems = async () => {
        try {
            const response = await axios.get('/api/menu');
            setMenuItems(response.data);
        } catch (error) {
            console.error('Error fetching menu items:', error);
            setError('Failed to load menu items');
        }
    };

    const handleAddItem = async (e) => {
        e.preventDefault();
        try {
            const response = await axios.post('/api/admin/menu', newItem);
            setMenuItems([...menuItems, response.data]);
            setNewItem({
                name: '',
                description: '',
                ingredients: '',
                price: '',
                category: 'Starter',
                diet: 'Vegetarian',
                cooking_tips: '',
                calories: '',
                protein: '',
                carbs: '',
                fat: ''
            });
            setShowAddForm(false);
            setSuccess('Item added successfully!');
            setTimeout(() => setSuccess(''), 3000);
        } catch (error) {
            console.error('Error adding item:', error);
            setError('Failed to add item');
        }
    };

    const handleDeleteItem = async (itemId) => {
        if (!window.confirm('Are you sure you want to delete this item?')) return;

        try {
            await axios.delete(`/api/admin/menu/${itemId}`);
            setMenuItems(menuItems.filter(item => item.id !== itemId));
            setSuccess('Item deleted successfully!');
            setTimeout(() => setSuccess(''), 3000);
        } catch (error) {
            console.error('Error deleting item:', error);
            if (error.response?.status === 403) {
                setError('Admin access required. Please login as admin.');
            } else if (error.response?.status === 401) {
                setError('Authentication required. Please login again.');
            } else {
                setError('Failed to delete item. Please try again.');
            }
        }
    };

    const startEditing = (item) => {
        setEditingItem(item.id);
        setEditForm({
            name: item.name,
            description: item.description,
            ingredients: item.ingredients,
            price: item.price,
            category: item.category,
            diet: item.diet,
            cooking_tips: item.cooking_tips || '',
            calories: item.calories || '',
            protein: item.protein || '',
            carbs: item.carbs || '',
            fat: item.fat || ''
        });
    };

    const cancelEditing = () => {
        setEditingItem(null);
        setEditForm({});
    };

    const handleUpdateItem = async (itemId) => {
        try {
            await axios.put(`/api/admin/menu/${itemId}`, editForm);
            setMenuItems(menuItems.map(item =>
                item.id === itemId ? { ...item, ...editForm } : item
            ));
            setEditingItem(null);
            setEditForm({});
            setSuccess('Item updated successfully!');
            setTimeout(() => setSuccess(''), 3000);
        } catch (error) {
            console.error('Error updating item:', error);
            setError('Failed to update item');
        }
    };

    return (
        <div className="admin-page page-content">
            <div className="admin-header mb-4">
                <div className="d-flex justify-content-between align-items-center w-100 mb-3">
                    <h1>Admin Panel - All Menu Items</h1>
                    <div className="admin-nav-pills">
                        <Link to="/admin-dashboard" className="btn btn-outline-secondary me-2">Add Dish</Link>
                        <Link to="/admin-menu" className="btn btn-outline-primary active me-2">Manage All</Link>
                        <Link to="/admin-inbox" className="btn btn-outline-secondary">Real-time Orders</Link>
                    </div>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={() => setShowAddForm(!showAddForm)}
                >
                    <FaPlus /> Add New Item
                </button>
            </div>

            {error && (
                <div className="alert alert-danger">
                    {error}
                </div>
            )}

            {success && (
                <div className="alert alert-success">
                    {success}
                </div>
            )}

            {/* Add Item Form */}
            {showAddForm && (
                <div className="admin-form-container">
                    <form onSubmit={handleAddItem} className="admin-form">
                        <h3>Add New Menu Item</h3>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Name:</label>
                                <input
                                    type="text"
                                    value={newItem.name}
                                    onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Price:</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={newItem.price}
                                    onChange={(e) => setNewItem({ ...newItem, price: parseFloat(e.target.value) })}
                                    required
                                />
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Category:</label>
                                <select
                                    value={newItem.category}
                                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                                    required
                                >
                                    <option value="Starter">Starter</option>
                                    <option value="Main Course">Main Course</option>
                                    <option value="Breads">Breads</option>
                                    <option value="Rice">Rice</option>
                                    <option value="Sides">Sides</option>
                                    <option value="Dessert">Dessert</option>
                                    <option value="Beverages">Beverages</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Diet:</label>
                                <select
                                    value={newItem.diet}
                                    onChange={(e) => setNewItem({ ...newItem, diet: e.target.value })}
                                >
                                    <option value="Vegetarian">Vegetarian</option>
                                    <option value="Non-Vegetarian">Non-Vegetarian</option>
                                    <option value="Vegan">Vegan</option>
                                </select>
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Calories (kcal):</label>
                                <input
                                    type="number"
                                    value={newItem.calories}
                                    onChange={(e) => setNewItem({ ...newItem, calories: e.target.value })}
                                    placeholder="e.g. 250"
                                />
                            </div>
                            <div className="form-group">
                                <label>Protein (g):</label>
                                <input
                                    type="number"
                                    value={newItem.protein}
                                    onChange={(e) => setNewItem({ ...newItem, protein: e.target.value })}
                                    placeholder="e.g. 15"
                                />
                            </div>
                            <div className="form-group">
                                <label>Carbs (g):</label>
                                <input
                                    type="number"
                                    value={newItem.carbs}
                                    onChange={(e) => setNewItem({ ...newItem, carbs: e.target.value })}
                                    placeholder="e.g. 30"
                                />
                            </div>
                            <div className="form-group">
                                <label>Fat (g):</label>
                                <input
                                    type="number"
                                    value={newItem.fat}
                                    onChange={(e) => setNewItem({ ...newItem, fat: e.target.value })}
                                    placeholder="e.g. 10"
                                />
                            </div>
                        </div>
                        <div className="form-group">
                            <label>Description:</label>
                            <textarea
                                value={newItem.description}
                                onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                                rows="3"
                            />
                        </div>
                        <div className="form-group">
                            <label>Ingredients:</label>
                            <textarea
                                value={newItem.ingredients}
                                onChange={(e) => setNewItem({ ...newItem, ingredients: e.target.value })}
                                rows="2"
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label>Chef's Cooking Tips (Required):</label>
                            <textarea
                                value={newItem.cooking_tips}
                                onChange={(e) => setNewItem({ ...newItem, cooking_tips: e.target.value })}
                                rows="3"
                                placeholder="Enter specific cooking tips, secrets, or preparation advice..."
                                required
                            />
                        </div>
                        <div className="form-actions">
                            <button type="submit" className="btn btn-primary">
                                <FaSave /> Add Item
                            </button>
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => setShowAddForm(false)}
                            >
                                <FaTimes /> Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Menu Items Table */}
            <div className="admin-table-container">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Category</th>
                            <th>Diet</th>
                            <th>Tips</th>
                            <th>Price</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {menuItems.map(item => (
                            <tr key={item.id}>
                                <td>
                                    {editingItem === item.id ? (
                                        <input
                                            type="text"
                                            value={editForm.name}
                                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                        />
                                    ) : (
                                        item.name
                                    )}
                                </td>
                                <td>
                                    {editingItem === item.id ? (
                                        <input
                                            type="text"
                                            value={editForm.category}
                                            onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                                        />
                                    ) : (
                                        item.category
                                    )}
                                </td>
                                <td>
                                    {editingItem === item.id ? (
                                        <select
                                            value={editForm.diet}
                                            onChange={(e) => setEditForm({ ...editForm, diet: e.target.value })}
                                        >
                                            <option value="Vegetarian">Vegetarian</option>
                                            <option value="Non-Vegetarian">Non-Vegetarian</option>
                                            <option value="Vegan">Vegan</option>
                                        </select>
                                    ) : (
                                        item.diet
                                    )}
                                </td>
                                <td>
                                    {editingItem === item.id ? (
                                        <textarea
                                            value={editForm.cooking_tips || ''}
                                            onChange={(e) => setEditForm({ ...editForm, cooking_tips: e.target.value })}
                                            rows="2"
                                            className="form-control"
                                        />
                                    ) : (
                                        <span title={item.cooking_tips} className="truncate-text">
                                            {item.cooking_tips ? item.cooking_tips.substring(0, 30) + (item.cooking_tips.length > 30 ? '...' : '') : '-'}
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {editingItem === item.id ? (
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={editForm.price}
                                            onChange={(e) => setEditForm({ ...editForm, price: parseFloat(e.target.value) })}
                                        />
                                    ) : (
                                        `₹${item.price.toFixed(2)}`
                                    )}
                                </td>
                                <td>
                                    {editingItem === item.id ? (
                                        <div className="action-buttons">
                                            <button
                                                className="btn btn-success btn-sm"
                                                onClick={() => handleUpdateItem(item.id)}
                                            >
                                                <FaSave />
                                            </button>
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                onClick={cancelEditing}
                                            >
                                                <FaTimes />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="action-buttons">
                                            <button
                                                className="btn btn-warning btn-sm"
                                                onClick={() => startEditing(item)}
                                            >
                                                <FaEdit />
                                            </button>
                                            <button
                                                className="btn btn-danger btn-sm"
                                                onClick={() => handleDeleteItem(item.id)}
                                            >
                                                <FaTrash />
                                            </button>
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default AdminPage;
