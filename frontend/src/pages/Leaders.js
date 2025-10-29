import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { Link } from 'react-router-dom';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Users, Award, Calendar } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const Leaders = () => {
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaders();
  }, []);

  const fetchLeaders = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/leaders?sort=score`);
      setLeaders(response.data.data);
    } catch (error) {
      console.error('Failed to fetch leaders', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl mb-4">
            <Users className="text-white" size={32} />
          </div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent" data-testid="leaders-title">
            Leaders Directory
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Meet the brilliant minds behind the best ideas
          </p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="leaders-grid">
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
                      <Award size={14} />
                      <span>{leader.leader_score} score</span>
                    </Badge>
                    <span className="text-xs text-gray-400 flex items-center space-x-1">
                      <Calendar size={12} />
                      <span>Joined {formatDistanceToNow(new Date(leader.created_at), { addSuffix: true })}</span>
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Leaders;
