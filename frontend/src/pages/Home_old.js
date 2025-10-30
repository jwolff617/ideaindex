import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import IdeaCard from '../components/IdeaCard';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Search, TrendingUp, Clock, Users, Filter } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Link } from 'react-router-dom';

const Home = () => {
  const [ideas, setIdeas] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedCity, setSelectedCity] = useState('all');
  const [sortBy, setSortBy] = useState('top');

  useEffect(() => {
    fetchCategories();
    fetchCities();
  }, []);

  useEffect(() => {
    fetchIdeas();
  }, [searchQuery, selectedCategory, selectedCity, sortBy]);

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

  const fetchIdeas = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (selectedCategory && selectedCategory !== 'all') params.append('category', selectedCategory);
      if (selectedCity && selectedCity !== 'all') params.append('city', selectedCity);
      params.append('sort', sortBy);

      const response = await axios.get(`${API}/ideas?${params.toString()}`);
      setIdeas(response.data.data);
    } catch (error) {
      console.error('Failed to fetch ideas', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent" data-testid="page-title">
            Great Ideas, Great Leaders
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto" data-testid="page-subtitle">
            A modern index of brilliant ideas. Upvote the best, and watch comments rise to become main ideas.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <Input
                placeholder="Search ideas..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="search-input"
              />
            </div>

            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger data-testid="category-filter">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedCity} onValueChange={setSelectedCity}>
              <SelectTrigger data-testid="city-filter">
                <SelectValue placeholder="All Cities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Cities</SelectItem>
                {cities.map((city) => (
                  <SelectItem key={city.id} value={city.id}>
                    {city.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger data-testid="sort-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="top">
                  <div className="flex items-center space-x-2">
                    <TrendingUp size={16} />
                    <span>Top Ideas</span>
                  </div>
                </SelectItem>
                <SelectItem value="new">
                  <div className="flex items-center space-x-2">
                    <Clock size={16} />
                    <span>Latest</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Ideas Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        ) : ideas.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl">
            <p className="text-gray-500 text-lg" data-testid="empty-state">No ideas yet — be the first Leader to post!</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="ideas-list">
            {ideas.map((idea) => (
              <IdeaCard key={idea.id} idea={idea} onUpdate={fetchIdeas} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
