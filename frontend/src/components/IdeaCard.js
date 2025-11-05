import React, { useContext, useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext, API } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowUp, ArrowDown, MessageCircle, MapPin, Calendar, Bookmark, BookmarkCheck, Share2 } from 'lucide-react';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { formatDistanceToNow } from 'date-fns';

const IdeaCard = ({ idea, onUpdate }) => {
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [upvotes, setUpvotes] = useState(idea.upvotes || 0);
  const [downvotes, setDownvotes] = useState(idea.downvotes || 0);
  const [voting, setVoting] = useState(false);

  const handleVote = async (voteValue) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    if (!user.is_verified_email) {
      toast.error('Verify your email to vote');
      return;
    }

    setVoting(true);
    try {
      const response = await axios.post(
        `${API}/ideas/${idea.id}/vote`,
        { vote: voteValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setUpvotes(response.data.upvotes);
      setDownvotes(response.data.downvotes);
      
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to vote');
    } finally {
      setVoting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all border border-gray-100" data-testid="idea-card">
      <div className="flex items-start space-x-4">
        <div className="flex flex-col items-center space-y-2">
          <button
            onClick={() => handleVote(1)}
            disabled={voting}
            className="p-2 rounded-lg hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 transition-colors disabled:opacity-50"
            data-testid="upvote-button"
          >
            <ArrowUp size={20} />
          </button>
          <span className="font-bold text-lg" data-testid="upvote-count">{upvotes}</span>
          <button
            onClick={() => handleVote(-1)}
            disabled={voting}
            className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
            data-testid="downvote-button"
          >
            <ArrowDown size={20} />
          </button>
        </div>

        <div className="flex-1">
          <Link to={`/ideas/${idea.id}`} className="block group">
            <h3 className="text-xl font-bold text-gray-900 group-hover:text-emerald-600 transition-colors mb-2" data-testid="idea-title">
              {idea.title}
            </h3>
          </Link>

          <p className="text-gray-600 mb-4 line-clamp-2" data-testid="idea-body">{idea.body}</p>

          <div className="flex items-center flex-wrap gap-2 mb-3">
            {idea.category && (
              <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100" data-testid="idea-category">
                {idea.category}
              </Badge>
            )}
            {idea.city && (
              <Badge variant="outline" className="flex items-center space-x-1" data-testid="idea-city">
                <MapPin size={12} />
                <span>{idea.city}</span>
              </Badge>
            )}
          </div>

          <div className="flex items-center justify-between text-sm text-gray-500">
            <Link
              to={`/leaders/${idea.author?.username}`}
              className="flex items-center space-x-2 hover:text-emerald-600 transition-colors"
              data-testid="author-link"
            >
              <Avatar className="w-6 h-6">
                <AvatarFallback className="text-xs bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
                  {idea.author?.name?.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="font-medium">{idea.author?.name}</span>
              <span className="text-gray-400">·</span>
              <span className="flex items-center space-x-1">
                <Calendar size={14} />
                <span>{formatDistanceToNow(new Date(idea.created_at), { addSuffix: true })}</span>
              </span>
            </Link>

            <div className="flex items-center space-x-1 text-gray-500" data-testid="comments-count">
              <MessageCircle size={16} />
              <span>{idea.comments_count || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IdeaCard;
