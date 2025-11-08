import React, { useState, useEffect, useContext } from 'react';
import { API, AuthContext } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import IdeaCard from '../components/IdeaCard';
import { Bookmark, Folder } from 'lucide-react';
import { Link } from 'react-router-dom';

const Collections = () => {
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [bookmarkedIdeas, setBookmarkedIdeas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }
    fetchBookmarks();
  }, [user]);

  const fetchBookmarks = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/bookmarks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBookmarkedIdeas(response.data);
    } catch (error) {
      console.error('Failed to fetch bookmarks', error);
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 py-12 text-center">
          <p className="text-gray-500">Please sign in to view your collections</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-2 mb-2">
            <Link 
              to="/" 
              className="text-sm text-emerald-600 hover:text-emerald-700 font-medium"
            >
              ← Back to Feed
            </Link>
          </div>
          <div className="flex items-center space-x-3">
            <Bookmark size={32} className="text-emerald-600" />
            <h1 className="text-3xl font-bold text-gray-900">My Collections</h1>
          </div>
          <p className="text-gray-600 mt-2">Ideas you've bookmarked for later</p>
        </div>

        {/* Collections */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        ) : bookmarkedIdeas.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center shadow-sm">
            <Bookmark size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 text-lg mb-2">No bookmarks yet</p>
            <p className="text-gray-400 text-sm">
              Start bookmarking ideas you want to save for later
            </p>
            <Link 
              to="/" 
              className="inline-block mt-6 px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              Explore Ideas
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {bookmarkedIdeas.map((idea) => (
              <IdeaCard key={idea.id} idea={idea} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Collections;
