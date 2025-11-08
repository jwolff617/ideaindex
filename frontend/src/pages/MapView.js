import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { ChevronLeft, ChevronRight, ArrowUp, ExternalLink } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const MapView = () => {
  const [ideas, setIdeas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [center] = useState([39.8283, -98.5795]); // Center of USA

  useEffect(() => {
    fetchIdeas();
  }, []);

  const fetchIdeas = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/ideas`);
      // Filter ideas that have geo coordinates
      const geoIdeas = response.data.data.filter(idea => idea.geo_lat && idea.geo_lon);
      setIdeas(geoIdeas);
    } catch (error) {
      console.error('Failed to fetch ideas', error);
    } finally {
      setLoading(false);
    }
  };

  // Group ideas by location (lat, lon)
  const groupIdeasByLocation = () => {
    const grouped = {};
    
    ideas.forEach(idea => {
      const key = `${idea.geo_lat.toFixed(2)},${idea.geo_lon.toFixed(2)}`;
      if (!grouped[key]) {
        grouped[key] = {
          lat: idea.geo_lat,
          lon: idea.geo_lon,
          city: idea.city,
          ideas: []
        };
      }
      grouped[key].ideas.push(idea);
    });

    // Sort ideas within each location by upvotes (descending)
    Object.values(grouped).forEach(location => {
      location.ideas.sort((a, b) => b.upvotes - a.upvotes);
    });

    return Object.values(grouped);
  };

  const groupedLocations = groupIdeasByLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent" data-testid="map-title">
            Ideas Map
          </h1>
          <p className="text-gray-600">
            Explore ideas from around the country
          </p>
        </div>

        <div className="bg-white rounded-2xl overflow-hidden shadow-lg" style={{ height: '600px' }} data-testid="map-container">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            </div>
          ) : (
            <MapContainer
              center={center}
              zoom={4}
              style={{ height: '100%', width: '100%' }}
              className="z-0"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {groupedLocations.map((location, idx) => (
                <Marker key={idx} position={[location.lat, location.lon]}>
                  <Popup maxWidth={320} minWidth={280} maxHeight={500} className="custom-popup">
                    <LocationPopup location={location} />
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          )}
        </div>

        {!loading && ideas.length === 0 && (
          <div className="text-center mt-8 text-gray-500">
            <p>No ideas with geographic locations yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Separate component for the popup content with pagination
const LocationPopup = ({ location }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const ideasPerPage = 10;
  const totalPages = Math.ceil(location.ideas.length / ideasPerPage);

  const startIdx = (currentPage - 1) * ideasPerPage;
  const endIdx = startIdx + ideasPerPage;
  const currentIdeas = location.ideas.slice(startIdx, endIdx);

  const getCityId = () => {
    return location.ideas[0]?.city_id;
  };

  return (
    <div className="py-2">
      {/* Header */}
      <div className="mb-3 pb-3 border-b border-gray-200">
        <h3 className="font-bold text-lg text-gray-900">{location.city || 'Ideas'}</h3>
        <p className="text-sm text-gray-500">{location.ideas.length} ideas at this location</p>
      </div>

      {/* Ideas List */}
      <div className="space-y-3 max-h-80 overflow-y-auto">
        {currentIdeas.map((idea, idx) => (
          <div key={idea.id} className="pb-3 border-b border-gray-100 last:border-0">
            <Link 
              to={`/ideas/${idea.id}`}
              className="block hover:bg-gray-50 -mx-2 px-2 py-1 rounded transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <h4 className="font-semibold text-sm text-gray-900 hover:text-emerald-600 line-clamp-2">
                  {idea.title}
                </h4>
                <div className="flex items-center space-x-1 text-emerald-600 flex-shrink-0">
                  <ArrowUp size={14} />
                  <span className="text-sm font-bold">{idea.upvotes}</span>
                </div>
              </div>
              <p className="text-xs text-gray-600 line-clamp-2 mb-2">{idea.body}</p>
              {idea.category && (
                <Badge className="bg-emerald-50 text-emerald-700 text-xs">
                  {idea.category}
                </Badge>
              )}
            </Link>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="h-8"
          >
            <ChevronLeft size={14} />
          </Button>
          
          <span className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
          
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="h-8"
          >
            <ChevronRight size={14} />
          </Button>
        </div>
      )}

      {/* View All Link */}
      {location.city && getCityId() && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <Link
            to={`/?city=${getCityId()}`}
            className="flex items-center justify-center space-x-2 text-sm text-emerald-600 hover:text-emerald-700 font-medium"
          >
            <span>View all {location.city} ideas</span>
            <ExternalLink size={14} />
          </Link>
        </div>
      )}
    </div>
  );
};

export default MapView;
