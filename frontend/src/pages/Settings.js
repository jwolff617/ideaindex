import React, { useState, useEffect, useContext } from 'react';
import { API, AuthContext } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Settings as SettingsIcon, Save, Lock, Eye, EyeOff } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const Settings = () => {
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [settings, setSettings] = useState({
    replies_in_feed: 2,
    dark_mode: false,
    email_notifications: true,
    feed_density: 'comfortable',
    auto_spellcheck: true,
    auto_generate_title: true
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }
    fetchSettings();
  }, [user]);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings', error);
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await axios.put(`${API}/settings`, settings, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
      toast.success('Settings saved successfully!');
    } catch (error) {
      console.error('Failed to save settings', error);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setChangingPassword(true);
    try {
      await axios.post(
        `${API}/reset-password`,
        null,
        {
          params: {
            email: user.email,
            new_password: newPassword
          }
        }
      );
      toast.success('Password changed successfully!');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('Failed to change password', error);
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 py-12 text-center">
          <p className="text-gray-500">Please sign in to access settings</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link 
            to="/" 
            className="text-sm text-emerald-600 hover:text-emerald-700 font-medium mb-2 inline-block"
          >
            ← Back to Feed
          </Link>
          <div className="flex items-center space-x-3">
            <SettingsIcon size={32} className="text-emerald-600" />
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          </div>
          <p className="text-gray-600 mt-2">Customize your Idea Index experience</p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl p-8 shadow-sm space-y-8">
            {/* Feed Settings */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4">Feed Settings</h2>
              
              <div className="space-y-6">
                {/* Replies in Feed */}
                <div className="space-y-2">
                  <Label htmlFor="replies_in_feed">Replies Shown in Feed</Label>
                  <p className="text-sm text-gray-500 mb-2">
                    Number of top replies to display under each idea in your feed
                  </p>
                  <Select
                    value={settings.replies_in_feed?.toString() || "2"}
                    onValueChange={(value) => setSettings({...settings, replies_in_feed: parseInt(value)})}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">None (0)</SelectItem>
                      <SelectItem value="1">1 reply</SelectItem>
                      <SelectItem value="2">2 replies (Default)</SelectItem>
                      <SelectItem value="3">3 replies</SelectItem>
                      <SelectItem value="5">5 replies</SelectItem>
                      <SelectItem value="10">10 replies</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Feed Density */}
                <div className="space-y-2">
                  <Label htmlFor="feed_density">Feed Density</Label>
                  <p className="text-sm text-gray-500 mb-2">
                    Adjust spacing and size of feed items
                  </p>
                  <Select
                    value={settings.feed_density || "comfortable"}
                    onValueChange={(value) => setSettings({...settings, feed_density: value})}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="compact">Compact - See more at once</SelectItem>
                      <SelectItem value="comfortable">Comfortable (Default)</SelectItem>
                      <SelectItem value="spacious">Spacious - More breathing room</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Appearance */}
            <div className="border-t pt-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Appearance</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <Label>Dark Mode</Label>
                    <p className="text-sm text-gray-500">Use dark theme (Coming soon)</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.dark_mode || false}
                      onChange={(e) => setSettings({...settings, dark_mode: e.target.checked})}
                      disabled
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600 opacity-50"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* AI Assistance */}
            <div className="border-t pt-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">AI Assistance</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <Label>Auto-Spellcheck</Label>
                    <p className="text-sm text-gray-500">Automatically fix typos when posting</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.auto_spellcheck || false}
                      onChange={(e) => setSettings({...settings, auto_spellcheck: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <Label>Auto-Generate Titles</Label>
                    <p className="text-sm text-gray-500">AI suggests titles for Outdexed ideas</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.auto_generate_title || false}
                      onChange={(e) => setSettings({...settings, auto_generate_title: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div className="border-t pt-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Notifications</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <Label>Email Notifications</Label>
                    <p className="text-sm text-gray-500">Receive updates via email</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.email_notifications || false}
                      onChange={(e) => setSettings({...settings, email_notifications: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <div className="border-t pt-8">
              <Button
                onClick={handleSave}
                disabled={saving}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                <Save size={16} className="mr-2" />
                {saving ? 'Saving...' : 'Save Settings'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
