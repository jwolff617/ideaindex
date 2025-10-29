import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { MapPin, Lightbulb } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const SubmitIdea = () => {
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [cities, setCities] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    body: '',
    category_id: '',
    city_id: '',
    geo_lat: null,
    geo_lon: null
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user) {
      setShowAuthModal(true);
      navigate('/');
      return;
    }

    if (!user.is_verified_email) {
      toast.error('Please verify your email to post ideas');
      navigate('/');
      return;
    }

    fetchCategories();
    fetchCities();
  }, [user]);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Failed to fetch categories', error);
    }
  };

  const fetchCities = async () => {
    try {
      const response = await axios.get(`${API}/cities`);
      setCities(response.data);
    } catch (error) {
      console.error('Failed to fetch cities', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.title.trim() || !formData.body.trim()) {
      toast.error('Title and body are required');
      return;
    }

    if (formData.body.length < 10) {
      toast.error('Body must be at least 10 characters');
      return;
    }

    setSubmitting(true);
    try {
      const response = await axios.post(
        `${API}/ideas`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Idea posted successfully!');
      navigate(`/ideas/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post idea');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-2xl p-8 shadow-lg">
          <div className="flex items-center space-x-3 mb-6">
            <div className="bg-gradient-to-br from-emerald-500 to-teal-600 p-3 rounded-xl">
              <Lightbulb className="text-white" size={28} />
            </div>
            <h1 className="text-3xl font-bold text-gray-900" data-testid="submit-title">Post an Idea</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                placeholder="A great idea starts with a great title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                data-testid="title-input"
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="body">Description *</Label>
              <Textarea
                id="body"
                placeholder="Describe your idea in detail... (minimum 10 characters)"
                value={formData.body}
                onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                required
                rows={8}
                data-testid="body-textarea"
                className="mt-1"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category_id}
                  onValueChange={(value) => setFormData({ ...formData, category_id: value })}
                >
                  <SelectTrigger className="mt-1" data-testid="category-select">
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="city">City</Label>
                <Select
                  value={formData.city_id}
                  onValueChange={(value) => setFormData({ ...formData, city_id: value })}
                >
                  <SelectTrigger className="mt-1" data-testid="city-select">
                    <SelectValue placeholder="Select a city" />
                  </SelectTrigger>
                  <SelectContent>
                    {cities.map((city) => (
                      <SelectItem key={city.id} value={city.id}>
                        <div className="flex items-center space-x-2">
                          <MapPin size={14} />
                          <span>{city.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="pt-4 border-t">
              <Button
                type="submit"
                disabled={submitting}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700"
                data-testid="submit-idea-button"
              >
                {submitting ? 'Publishing...' : 'Publish Idea'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SubmitIdea;
