import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import IdeaCard from '../components/IdeaCard';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Search, TrendingUp, Clock, Users, Filter, X } from 'lucide-react';
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
import { Link, useSearchParams } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

const Home = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [ideas, setIdeas] = useState([]);
  const [leaders, setLeaders] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedCity, setSelectedCity] = useState(searchParams.get('city') || 'all');
  const [sortBy, setSortBy] = useState('hot');
  const [showType, setShowType] = useState('ideas'); // 'ideas' or 'leaders'
  const [trendingTags, setTrendingTags] = useState([]);

  useEffect(() => {
    fetchCategories();
    fetchCities();
    fetchTrendingTags();
  }, []);

  useEffect(() => {
    if (sortBy === 'leaders') {
      setShowType('leaders');
      fetchLeaders();
    } else {
      setShowType('ideas');
      fetchIdeas();
    }
  }, [searchQuery, selectedCategories, selectedCity, sortBy]);

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

  const fetchTrendingTags = async () => {
    try {
      const response = await axios.get(`${API}/tags/trending?limit=10`);
      setTrendingTags(response.data);
    } catch (error) {
      console.error('Failed to fetch trending tags', error);
    }
  };

  const fetchIdeas = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      
      // Add multiple categories
      if (selectedCategories.length > 0) {
        selectedCategories.forEach(catId => {
          params.append('category', catId);
        });
      }
      
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

  const fetchLeaders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCity && selectedCity !== 'all') params.append('city', selectedCity);
      params.append('sort', 'score');

      const response = await axios.get(`${API}/leaders?${params.toString()}`);
      setLeaders(response.data.data);
    } catch (error) {
      console.error('Failed to fetch leaders', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (categoryId) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
  };

  const clearCategory = (categoryId) => {
    setSelectedCategories(prev => prev.filter(id => id !== categoryId));
  };

  const getSelectedCategoryNames = () => {
    return categories
      .filter(cat => selectedCategories.includes(cat.id))
      .map(cat => cat.name);
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

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-3">
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

            {/* Multi-select Categories */}
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-between" data-testid="category-filter">
                  <div className="flex items-center space-x-2">
                    <Filter size={16} />
                    <span>
                      {selectedCategories.length === 0
                        ? 'All Categories'
                        : `${selectedCategories.length} selected`}
                    </span>
                  </div>
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80 p-4" align="start">
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  <p className="font-semibold text-sm mb-3">Select Categories</p>
                  {categories.map((cat) => (
                    <div key={cat.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={cat.id}
                        checked={selectedCategories.includes(cat.id)}
                        onCheckedChange={() => toggleCategory(cat.id)}
                      />
                      <label
                        htmlFor={cat.id}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {cat.name}
                      </label>
                    </div>
                  ))}
                </div>
                {selectedCategories.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full mt-3"
                    onClick={() => setSelectedCategories([])}
                  >
                    Clear All
                  </Button>
                )}
              </PopoverContent>
            </Popover>

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
                <SelectItem value="hot">
                  <div className="flex items-center space-x-2">
                    <TrendingUp size={16} />
                    <span>Hot</span>
                  </div>
                </SelectItem>
                <SelectItem value="top">
                  <div className="flex items-center space-x-2">
                    <TrendingUp size={16} />
                    <span>Top</span>
                  </div>
                </SelectItem>
                <SelectItem value="new">
                  <div className="flex items-center space-x-2">
                    <Clock size={16} />
                    <span>New</span>
                  </div>
                </SelectItem>
                <SelectItem value="rising">
                  <div className="flex items-center space-x-2">
                    <TrendingUp size={16} className="text-orange-500" />
                    <span>Rising</span>
                  </div>
                </SelectItem>
                <SelectItem value="leaders">
                  <div className="flex items-center space-x-2">
                    <Users size={16} />
                    <span>Top Leaders</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Selected Categories Badges */}
          {selectedCategories.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
              {getSelectedCategoryNames().map((name, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="bg-emerald-50 text-emerald-700 flex items-center space-x-1"
                >
                  <span>{name}</span>
                  <button
                    onClick={() => clearCategory(selectedCategories[index])}
                    className="ml-1 hover:bg-emerald-100 rounded-full p-0.5"
                  >
                    <X size={12} />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        ) : showType === 'leaders' ? (
          // Leaders Grid
          leaders.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl">
              <p className="text-gray-500 text-lg" data-testid="empty-state">No leaders found</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="leaders-list">
              {leaders.map((leader) => (
                <Link
                  key={leader.id}
                  to={`/leaders/${leader.username}`}
                  className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all border border-gray-100 group"
                  data-testid="leader-card"
                >
                  <div className="flex flex-col items-center text-center">
                    <Avatar className="w-20 h-20 mb-4 ring-4 ring-emerald-500/20 group-hover:ring-emerald-500/40 transition-all">
                      <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white text-2xl font-bold">
                        {leader.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>

                    <h3 className="text-xl font-bold text-gray-900 mb-1 group-hover:text-emerald-600 transition-colors" data-testid="leader-name">
                      {leader.name}
                    </h3>
                    <p className="text-sm text-gray-500 mb-3" data-testid="leader-username">@{leader.username}</p>

                    {leader.bio && (
                      <p className="text-sm text-gray-600 mb-4 line-clamp-2">{leader.bio}</p>
                    )}

                    <div className="flex items-center space-x-4 text-sm">
                      <Badge className="bg-emerald-50 text-emerald-700 flex items-center space-x-1">
                        <TrendingUp size={14} />
                        <span>{leader.leader_score} score</span>
                      </Badge>
                      <span className="text-xs text-gray-400">
                        Joined {formatDistanceToNow(new Date(leader.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )
        ) : (
          // Ideas List
          ideas.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl">
              <p className="text-gray-500 text-lg" data-testid="empty-state">No ideas yet — be the first Leader to post!</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="ideas-list">
              {ideas.map((idea) => (
                <IdeaCard key={idea.id} idea={idea} onUpdate={fetchIdeas} />
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* Sidebar */}
      <div className="lg:col-span-1">
        {/* Trending Tags */}
        {trendingTags.length > 0 && (
          <div className="bg-white rounded-2xl p-6 shadow-sm mb-6 sticky top-20">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center space-x-2">
              <TrendingUp size={18} className="text-emerald-600" />
              <span>Trending Tags</span>
            </h3>
            <div className="flex flex-wrap gap-2">
              {trendingTags.map((tagData) => (
                <Badge
                  key={tagData.tag}
                  variant="outline"
                  className="cursor-pointer hover:bg-emerald-50 border-emerald-300 text-emerald-700"
                  onClick={() => {
                    // TODO: Filter by tag
                    setSearchQuery(`#${tagData.tag}`);
                  }}
                >
                  #{tagData.tag} <span className="ml-1 text-xs text-gray-500">({tagData.count})</span>
                </Badge>
              ))}
            </div>
          </div>
        )}
        
        {/* Quick Stats */}
        <div className="bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl p-6 text-white shadow-lg">
          <h3 className="font-bold mb-4">Ideas grow here</h3>
          <p className="text-sm text-emerald-50">
            Every idea competes equally. The best thinking rises to the top through transparent voting.
          </p>
        </div>
      </div>
    </div>
      </div>
    </div>
  );
};

export default Home;
