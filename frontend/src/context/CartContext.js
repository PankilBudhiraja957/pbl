import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const CartContext = createContext();

export const CartProvider = ({ children }) => {
    const { currentUser } = useAuth();
    const [cart, setCart] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const refreshCart = useCallback(async () => {
        if (!currentUser) {
            setCart([]);
            return;
        }
        setIsLoading(true);
        setError(null);
        try {
            const response = await axios.get('/api/cart');
            setCart(response.data.cart);
        } catch (err) {
            console.error('Failed to fetch cart:', err);
            setError('Failed to load cart.');
            setCart([]);
        } finally {
            setIsLoading(false);
        }
    }, [currentUser]);

    useEffect(() => {
        refreshCart();
    }, [currentUser, refreshCart]); // Refresh cart whenever the user logs in or out

    return (
        <CartContext.Provider value={{ cart, refreshCart, isLoading, error }}>
            {children}
        </CartContext.Provider>
    );
};

export const useCart = () => {
    return useContext(CartContext);
};