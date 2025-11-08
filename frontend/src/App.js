import React, { useState, useEffect } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster, toast } from 'sonner';
import Home from './pages/Home';
import IdeaDetail from './pages/IdeaDetail';
import LeaderProfile from './pages/LeaderProfile';
import Leaders from './pages/Leaders';
import MapView from './pages/MapView';
import SubmitIdea from './pages/SubmitIdea';
import Collections from './pages/Collections';
import Settings from './pages/Settings';
import AuthModal from './components/AuthModal';
import AIChat from './components/AIChat';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export { BACKEND_URL };

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    if (token) {
      fetchUser();
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user', error);
      logout();
    }
  };

  const login = (newToken, userData) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
    if (userData.is_verified_email) {
      toast.success('Welcome back!');
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, setShowAuthModal }}>
      <div className="App">
        <BrowserRouter>
          {user && !user.is_verified_email && (
            <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 text-center" data-testid="verification-banner">
              <p className="text-amber-800 text-sm">
                📧 <strong>Email verification needed!</strong> Check backend console logs for your verification link, or{' '}
                <button
                  onClick={async () => {
                    try {
                      await axios.post(`${API}/verify-email-auto`, {}, {
                        headers: { Authorization: `Bearer ${token}` }
                      });
                      await fetchUser();
                      toast.success('Email verified! You can now post ideas.');
                    } catch (error) {
                      toast.error('Failed to verify email');
                    }
                  }}
                  className="underline font-semibold hover:text-amber-900"
                >
                  click here to auto-verify (MVP only)
                </button>
              </p>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/ideas/:id" element={<IdeaDetail />} />
            <Route path="/leaders" element={<Leaders />} />
            <Route path="/leaders/:username" element={<LeaderProfile />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/submit" element={<SubmitIdea />} />
            <Route path="/collections" element={<Collections />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </BrowserRouter>
        {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
        <Toaster position="top-center" richColors />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
