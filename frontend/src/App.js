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
import AuthModal from './components/AuthModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

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
    toast.success('Welcome back!');
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
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/ideas/:id" element={<IdeaDetail />} />
            <Route path="/leaders" element={<Leaders />} />
            <Route path="/leaders/:username" element={<LeaderProfile />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/submit" element={<SubmitIdea />} />
          </Routes>
        </BrowserRouter>
        {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
        <Toaster position="top-center" richColors />
      </div>
    </AuthContext.Provider>
  );
}

import React from 'react';
export default App;
