import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

// Configure axios globally for the entire app.
// The proxy in package.json will automatically direct these requests to your Flask backend.
axios.defaults.withCredentials = true;
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Create the context
const AuthContext = createContext();

// Custom hook to easily use the auth context in other components
export function useAuth() {
    return useContext(AuthContext);
}

// Create the provider component
export function AuthProvider({ children }) {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check if the user is already logged in when the app loads
        const checkLoginStatus = async () => {
            try {
                const response = await axios.get('/api/auth/status');
                if (response.data && response.data.isLoggedIn) {
                    setCurrentUser(response.data.user);
                } else {
                    setCurrentUser(null);
                }
            } catch (error) {
                console.error("Auth status check failed", error);
                setCurrentUser(null);
            } finally {
                setLoading(false);
            }
        };
        checkLoginStatus();
    }, []);

    const login = async (username, password) => {
        console.log(`--- Frontend: Attempting login for ${username} ---`);
        try {
            const response = await axios.post('/api/auth/login', { username, password });
            const user = response.data;
            if (user) {
                console.log(`--- Frontend: Login successful for ${user.username}, role: ${user.role} ---`);
                setCurrentUser(user);
                return user;
            } else {
                throw new Error("Login succeeded but no user data was returned.");
            }
        } catch (error) {
            console.error(`--- Frontend: Login error for ${username}:`, error.response ? error.response.data : error.message);
            setCurrentUser(null);
            throw error;
        }
    };

    const logout = async () => {
        try {
            await axios.post('/api/logout');
            setCurrentUser(null);
        } catch (error) {
            console.error("Logout failed", error);
        }
    };

    // Re-adding this function to fix the TypeError in other components
    const refreshAuthStatus = async () => {
        console.log('--- Frontend: Manually refreshing auth status ---');
        try {
            const response = await axios.get('/api/auth/status');
            if (response.data && response.data.isLoggedIn) {
                setCurrentUser(response.data.user);
                return response.data.user;
            } else {
                setCurrentUser(null);
                return null;
            }
        } catch (error) {
            console.error("Manual auth status check failed", error);
            setCurrentUser(null);
            return null;
        }
    };
    
    // The value provided to all children components
    const value = {
        currentUser,
        loading,
        login,
        logout,
        refreshAuthStatus, // Restored the function here
    };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}
