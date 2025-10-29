import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { Badge } from '../components/ui/badge';
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
              {ideas.map((idea) => (
                <Marker key={idea.id} position={[idea.geo_lat, idea.geo_lon]}>
                  <Popup>
                    <div className="p-2">
                      <Link to={`/ideas/${idea.id}`} className="font-bold text-emerald-600 hover:text-emerald-700">
                        {idea.title}
                      </Link>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{idea.body}</p>
                      {idea.category && (
                        <Badge className="mt-2 bg-emerald-50 text-emerald-700 text-xs">
                          {idea.category}
                        </Badge>
                      )}
                      <div className="text-xs text-gray-500 mt-2">
                        {idea.upvotes} upvotes
                      </div>
                    </div>
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

export default MapView;
