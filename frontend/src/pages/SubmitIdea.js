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
import { MapPin, Lightbulb, Image as ImageIcon, X } from 'lucide-react';
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
  const [selectedImages, setSelectedImages] = useState([]);
  const [imagePreviews, setImagePreviews] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [locationType, setLocationType] = useState('none'); // 'none', 'city', 'specific'

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

  const handleLocationTypeChange = (type) => {
    setLocationType(type);
    if (type === 'none') {
      setFormData({ ...formData, city_id: '', geo_lat: null, geo_lon: null });
    } else if (type === 'specific') {
      setFormData({ ...formData, city_id: '' });
    }
  };

  const handleCitySelect = (cityId) => {
    const city = cities.find(c => c.id === cityId);
    if (city) {
      setFormData({
        ...formData,
        city_id: cityId,
        geo_lat: city.lat,
        geo_lon: city.lon
      });
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
      // Create FormData for multipart upload
      const submitData = new FormData();
      submitData.append('title', formData.title);
      submitData.append('body', formData.body);
      if (formData.category_id) submitData.append('category_id', formData.category_id);
      if (formData.city_id) submitData.append('city_id', formData.city_id);
      if (formData.geo_lat) submitData.append('geo_lat', formData.geo_lat);
      if (formData.geo_lon) submitData.append('geo_lon', formData.geo_lon);
      
      // Add images
      selectedImages.forEach(image => {
        submitData.append('images', image);
      });

      const response = await axios.post(
        `${API}/ideas`,
        submitData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success('Idea posted successfully!');
      navigate(`/ideas/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post idea');
    } finally {
      setSubmitting(false);
    }
  };

  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files);
    const validImages = files.filter(file => file.type.startsWith('image/'));
    
    if (validImages.length !== files.length) {
      toast.error('Only image files are allowed');
    }
    
    setSelectedImages(prev => [...prev, ...validImages]);
    
    // Create previews
    validImages.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreviews(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (index) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
    setImagePreviews(prev => prev.filter((_, i) => i !== index));
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
            </div>

            <div>
              <Label className="mb-3 block">Location (optional)</Label>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="location-none"
                    name="location"
                    value="none"
                    checked={locationType === 'none'}
                    onChange={(e) => handleLocationTypeChange(e.target.value)}
                    className="w-4 h-4 text-emerald-600 cursor-pointer"
                  />
                  <label htmlFor="location-none" className="text-sm cursor-pointer">
                    No specific location
                  </label>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="location-city"
                    name="location"
                    value="city"
                    checked={locationType === 'city'}
                    onChange={(e) => handleLocationTypeChange(e.target.value)}
                    className="w-4 h-4 text-emerald-600 cursor-pointer"
                  />
                  <label htmlFor="location-city" className="text-sm cursor-pointer">
                    Select a city
                  </label>
                </div>

                {locationType === 'city' && (
                  <div className="ml-6">
                    <Select
                      value={formData.city_id}
                      onValueChange={handleCitySelect}
                    >
                      <SelectTrigger data-testid="city-select">
                        <SelectValue placeholder="Choose a city" />
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
                )}

                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="location-specific"
                    name="location"
                    value="specific"
                    checked={locationType === 'specific'}
                    onChange={(e) => handleLocationTypeChange(e.target.value)}
                    className="w-4 h-4 text-emerald-600 cursor-pointer"
                  />
                  <label htmlFor="location-specific" className="text-sm cursor-pointer">
                    Specific address (enter coordinates)
                  </label>
                </div>

                {locationType === 'specific' && (
                  <div className="ml-6 grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="lat" className="text-xs">Latitude</Label>
                      <Input
                        id="lat"
                        type="number"
                        step="any"
                        placeholder="e.g. 41.8781"
                        value={formData.geo_lat || ''}
                        onChange={(e) => setFormData({ ...formData, geo_lat: parseFloat(e.target.value) || null })}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="lon" className="text-xs">Longitude</Label>
                      <Input
                        id="lon"
                        type="number"
                        step="any"
                        placeholder="e.g. -87.6298"
                        value={formData.geo_lon || ''}
                        onChange={(e) => setFormData({ ...formData, geo_lon: parseFloat(e.target.value) || null })}
                        className="mt-1"
                      />
                    </div>
                    <p className="text-xs text-gray-500 col-span-2">
                      Tip: Get coordinates from <a href="https://www.google.com/maps" target="_blank" rel="noopener noreferrer" className="text-emerald-600 underline">Google Maps</a>
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Image Upload */}
            <div>
              <Label htmlFor="images">Images (optional)</Label>
              <div className="mt-2">
                <label
                  htmlFor="images"
                  className="flex items-center justify-center w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-emerald-500 transition-colors"
                >
                  <ImageIcon size={20} className="mr-2 text-gray-400" />
                  <span className="text-sm text-gray-600">Click to upload images</span>
                  <input
                    id="images"
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handleImageSelect}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Image Previews */}
              {imagePreviews.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                  {imagePreviews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={preview}
                        alt={`Preview ${index + 1}`}
                        className="w-full h-32 object-cover rounded-lg border border-gray-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
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
