import React, { useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API, BACKEND_URL } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowUp, ArrowDown, MessageCircle, MapPin, Calendar, Bookmark, BookmarkCheck, Share2 } from 'lucide-react';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { formatDistanceToNow } from 'date-fns';
import { TextWithURLPreviews } from './URLPreview';

const IdeaCard = ({ idea }) => {
  const navigate = useNavigate();
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [upvotes, setUpvotes] = useState(idea.upvotes || 0);
  const [downvotes, setDownvotes] = useState(idea.downvotes || 0);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [voting, setVoting] = useState(false);
  const [bookmarking, setBookmarking] = useState(false);
  const [showReply, setShowReply] = useState(false);
  const [replyBody, setReplyBody] = useState('');
  const [replyImages, setReplyImages] = useState([]);
  const [replyImagePreviews, setReplyImagePreviews] = useState([]);
  const [replying, setReplying] = useState(false);

  const handleVote = async (e, voteValue) => {
    e.stopPropagation();
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
      
      // Don't refresh feed - local state update is sufficient
      // This keeps user at current scroll position
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to vote');
    } finally {
      setVoting(false);
    }
  };

  const handleBookmark = async (e) => {
    e.stopPropagation();
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    setBookmarking(true);
    try {
      if (isBookmarked) {
        await axios.delete(`${API}/bookmarks/${idea.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setIsBookmarked(false);
        toast.success('Removed from bookmarks');
      } else {
        await axios.post(`${API}/bookmarks?idea_id=${idea.id}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setIsBookmarked(true);
        toast.success('Bookmarked!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to bookmark');
    } finally {
      setBookmarking(false);
    }
  };

  const handleShare = (e) => {
    e.stopPropagation();
    const url = `${window.location.origin}/ideas/${idea.id}`;
    navigator.clipboard.writeText(url);
    toast.success('Link copied to clipboard!');
  };

  const handleReplyClick = (e) => {
    e.stopPropagation();
    if (!user) {
      setShowAuthModal(true);
      return;
    }
    setShowReply(!showReply);
  };

  const handleReplySubmit = async (e) => {
    e.stopPropagation();
    if (!replyBody.trim() && replyImages.length === 0) {
      toast.error('Please add some text or an image');
      return;
    }

    setReplying(true);
    try {
      const formData = new FormData();
      formData.append('body', replyBody || '');
      
      replyImages.forEach(image => {
        formData.append('images', image);
      });

      await axios.post(
        `${API}/ideas/${idea.id}/comments`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success('Reply posted!');
      setReplyBody('');
      setReplyImages([]);
      setReplyImagePreviews([]);
      setShowReply(false);
      // Don't refresh feed - keeps scroll position stable
    } catch (error) {
      console.error('Reply error:', error);
      let errorMessage = 'Failed to post reply';
      
      if (error.response?.status === 403) {
        errorMessage = 'Please verify your email to post replies';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      toast.error(errorMessage);
    } finally {
      setReplying(false);
    }
  };

  const handleReplyImageSelect = (e) => {
    e.stopPropagation();
    const files = Array.from(e.target.files);
    const validImages = files.filter(file => file.type.startsWith('image/'));
    
    if (validImages.length !== files.length) {
      toast.error('Only image files are allowed');
    }
    
    setReplyImages(prev => [...prev, ...validImages]);
    
    validImages.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setReplyImagePreviews(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removeReplyImage = (e, index) => {
    e.stopPropagation();
    setReplyImages(prev => prev.filter((_, i) => i !== index));
    setReplyImagePreviews(prev => prev.filter((_, i) => i !== index));
  };

  const handleCardClick = () => {
    navigate(`/ideas/${idea.id}`);
  };

  // Truncate body to ~300 characters
  const truncatedBody = idea.body && idea.body.length > 300 
    ? idea.body.substring(0, 300) + '...' 
    : idea.body;

  // Get first 2 images
  const displayImages = idea.attachments ? idea.attachments.slice(0, 2) : [];

  return (
    <div 
      className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all border border-gray-100 cursor-pointer" 
      data-testid="idea-card"
      onClick={handleCardClick}
    >
      <div className="flex items-start space-x-4">
        <div className="flex flex-col items-center space-y-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={(e) => handleVote(e, 1)}
            disabled={voting}
            className="p-2 rounded-lg hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 transition-colors disabled:opacity-50"
            data-testid="upvote-button"
          >
            <ArrowUp size={20} />
          </button>
          <span className="font-bold text-lg" data-testid="upvote-count">{upvotes}</span>
          <button
            onClick={(e) => handleVote(e, -1)}
            disabled={voting}
            className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
            data-testid="downvote-button"
          >
            <ArrowDown size={20} />
          </button>
        </div>

        <div className="flex-1">
          {/* Title */}
          <h3 className="text-xl font-bold text-gray-900 hover:text-emerald-600 transition-colors mb-2" data-testid="idea-title">
            {idea.title}
          </h3>

          {/* Body text preview with URL previews */}
          {truncatedBody && (
            <div className="text-gray-700 mb-3" data-testid="idea-body">
              <TextWithURLPreviews text={truncatedBody} />
            </div>
          )}

          {/* Images inline (up to 2) */}
          {displayImages.length > 0 && (
            <div className={`grid gap-2 mb-3 ${displayImages.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
              {displayImages.map((attachment, idx) => {
                const imageUrl = attachment.startsWith('http') ? attachment : `${BACKEND_URL}${attachment}`;
                return (
                  <img
                    key={idx}
                    src={imageUrl}
                    alt={`Image ${idx + 1}`}
                    className="w-full h-64 object-cover rounded-lg border border-gray-200"
                    onClick={(e) => e.stopPropagation()}
                  />
                );
              })}
            </div>
          )}

          {/* Categories and tags */}
          <div className="flex items-center flex-wrap gap-2 mb-3" onClick={(e) => e.stopPropagation()}>
            {idea.category && (
              <Badge 
                variant="secondary" 
                className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 cursor-pointer transition-colors" 
                data-testid="idea-category"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/?category=${idea.category_id}`);
                }}
              >
                {idea.category}
              </Badge>
            )}
            {idea.city && (
              <Badge 
                variant="outline" 
                className="flex items-center space-x-1 hover:bg-gray-50 cursor-pointer transition-colors" 
                data-testid="idea-city"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/?city=${idea.city_id}`);
                }}
              >
                <MapPin size={12} />
                <span>{idea.city}</span>
              </Badge>
            )}
            {idea.tags && idea.tags.map((tag, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="text-xs text-blue-600 border-blue-300 hover:bg-blue-50 cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/?tag=${tag}`);
                }}
              >
                #{tag}
              </Badge>
            ))}
          </div>

          {/* Author and actions */}
          <div className="flex items-center justify-between text-sm text-gray-500" onClick={(e) => e.stopPropagation()}>
            <div
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/leaders/${idea.author?.username}`);
              }}
              className="flex items-center space-x-2 hover:text-emerald-600 transition-colors cursor-pointer"
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
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleReplyClick}
                className="flex items-center space-x-1 text-gray-500 hover:text-emerald-600 transition-colors"
                data-testid="reply-button"
              >
                <MessageCircle size={16} />
                <span>{idea.comments_count || 0}</span>
              </button>
              
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={handleBookmark}
                disabled={bookmarking}
                data-testid="bookmark-button"
              >
                {isBookmarked ? (
                  <BookmarkCheck size={16} className="text-emerald-600" />
                ) : (
                  <Bookmark size={16} />
                )}
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={handleShare}
                data-testid="share-button"
              >
                <Share2 size={16} />
              </Button>
            </div>
          </div>

          {/* Inline reply form */}
          {showReply && (
            <div className="mt-4 pt-4 border-t border-gray-200" onClick={(e) => e.stopPropagation()}>
              <Textarea
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                placeholder="Write your reply..."
                className="mb-2"
                rows={3}
              />

              {/* Reply image previews */}
              {replyImagePreviews.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {replyImagePreviews.map((preview, idx) => (
                    <div key={idx} className="relative">
                      <img
                        src={preview}
                        alt={`Preview ${idx + 1}`}
                        className="w-20 h-20 object-cover rounded-lg border border-gray-200"
                      />
                      <button
                        onClick={(e) => removeReplyImage(e, idx)}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-center space-x-2">
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleReplyImageSelect}
                  className="hidden"
                  id={`reply-image-${idea.id}`}
                />
                <label
                  htmlFor={`reply-image-${idea.id}`}
                  className="cursor-pointer text-sm text-gray-500 hover:text-emerald-600 flex items-center space-x-1"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                  </svg>
                  <span>Add images</span>
                </label>

                <div className="flex-1"></div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowReply(false);
                    setReplyBody('');
                    setReplyImages([]);
                    setReplyImagePreviews([]);
                  }}
                >
                  Cancel
                </Button>

                <Button
                  size="sm"
                  onClick={handleReplySubmit}
                  disabled={replying}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {replying ? 'Posting...' : 'Reply'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IdeaCard;
