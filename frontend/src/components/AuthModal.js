import React, { useState, useContext } from 'react';
import { AuthContext, API } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import { X, Mail, Lock, User, UserCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

const AuthModal = ({ onClose }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    email: '',
    password: ''
  });
  const [resetEmail, setResetEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? '/login' : '/signup';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      login(response.data.token, response.data.user);
      
      if (!isLogin) {
        toast.success('Account created! Check console for verification email.');
      }
      
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetEmail || !newPassword) {
      toast.error('Please enter both email and new password');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/reset-password`, null, {
        params: {
          email: resetEmail,
          new_password: newPassword
        }
      });
      
      toast.success('Password reset successfully! You can now login.');
      setShowForgotPassword(false);
      setIsLogin(true);
      setResetEmail('');
      setNewPassword('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" data-testid="auth-modal">
      <div className="bg-white rounded-2xl w-full max-w-md mx-4 shadow-2xl">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">
            {showForgotPassword ? 'Reset Password' : isLogin ? 'Welcome Back' : 'Join Idea Index'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            data-testid="close-auth-modal"
          >
            <X size={24} />
          </button>
        </div>

        {showForgotPassword ? (
          <form onSubmit={handleResetPassword} className="p-6 space-y-4">
            <p className="text-sm text-gray-600 mb-4">
              Enter your email and choose a new password
            </p>
            
            <div>
              <Label htmlFor="reset-email">Email</Label>
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <Input
                  id="reset-email"
                  type="email"
                  placeholder="you@example.com"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div>
              <Label htmlFor="new-password">New Password</Label>
              <div className="relative mt-1">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <Input
                  id="new-password"
                  type="password"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full mt-6"
              disabled={loading}
            >
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>

            <button
              type="button"
              onClick={() => {
                setShowForgotPassword(false);
                setResetEmail('');
                setNewPassword('');
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium w-full text-center"
            >
              Back to login
            </button>
          </form>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {!isLogin && (
            <>
              <div>
                <Label htmlFor="name">Full Name</Label>
                <div className="relative mt-1">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <Input
                    id="name"
                    type="text"
                    placeholder="Jane Doe"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="pl-10"
                    required
                    data-testid="name-input"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="username">Username</Label>
                <div className="relative mt-1">
                  <UserCircle className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <Input
                    id="username"
                    type="text"
                    placeholder="janedoe"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="pl-10"
                    required
                    data-testid="username-input"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <Label htmlFor="email">Email</Label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="pl-10"
                required
                data-testid="email-input"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="pl-10"
                required
                data-testid="password-input"
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full mt-6"
            disabled={loading}
            data-testid="submit-auth-button"
          >
            {loading ? 'Loading...' : isLogin ? 'Sign In' : 'Create Account'}
          </Button>
        </form>

        <div className="p-6 pt-0 space-y-2 text-center">
          {isLogin && (
            <button
              onClick={() => setShowForgotPassword(true)}
              className="text-sm text-gray-600 hover:text-gray-800 font-medium block w-full"
            >
              Forgot password?
            </button>
          )}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            data-testid="toggle-auth-mode"
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>
        </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthModal;
