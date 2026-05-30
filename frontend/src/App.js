import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import './App.css';

// Components
import Navbar from './components/Navbar';
import ChatWidget from './components/ChatWidget';

// Pages
import HomePage from './pages/HomePage';
import MenuPage from './pages/MenuPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProfilePage from './pages/ProfilePage';
import OrderHistoryPage from './pages/OrderHistoryPage';
import AdminDashboard from './pages/AdminDashboard';
import AdminInbox from './pages/AdminInbox';
import UserInboxPage from './pages/UserInboxPage';
import AdminPage from './pages/AdminPage';
import CartPage from './pages/CartPage';
import AllergiesPage from './pages/AllergiesPage';
import BookingPage from './pages/BookingPage';
import MyReservationsPage from './pages/MyReservationsPage';
import MyFavoritesPage from './pages/MyFavoritesPage';

function ProtectedRoute({ children }) {
  const { currentUser } = useAuth();
  return currentUser ? children : <Navigate to="/login" />;
}

function AdminRoute({ children }) {
  const { currentUser } = useAuth();
  if (!currentUser) return <Navigate to="/login" />;
  return currentUser.role === 'admin' ? children : <Navigate to="/" />;
}

function App() {
  const { currentUser, logout } = useAuth();

  return (
    <CartProvider>
      <div className="App">
        <Navbar currentUser={currentUser} onLogout={logout} />

        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/register" element={<Navigate to="/signup" />} />

          {/* Table Booking */}
          <Route
            path="/book-table"
            element={
              <ProtectedRoute>
                <BookingPage />
              </ProtectedRoute>
            }
          />

          {/* Protected User Routes */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/order-history"
            element={
              <ProtectedRoute>
                <OrderHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/user-inbox"
            element={
              <ProtectedRoute>
                <UserInboxPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cart"
            element={
              <ProtectedRoute>
                <CartPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-reservations"
            element={
              <ProtectedRoute>
                <MyReservationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-favorites"
            element={
              <ProtectedRoute>
                <MyFavoritesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/allergies"
            element={
              <ProtectedRoute>
                <AllergiesPage />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes */}
          <Route
            path="/admin-dashboard"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />
          <Route
            path="/admin-inbox"
            element={
              <AdminRoute>
                <AdminInbox />
              </AdminRoute>
            }
          />
          <Route
            path="/admin-menu"
            element={
              <AdminRoute>
                <AdminPage />
              </AdminRoute>
            }
          />
        </Routes>

        <ChatWidget />
      </div>
    </CartProvider>
  );
}

export default App;
