import React, { useState, useEffect, useContext } from 'react';
import { useParams, Link } from 'react-router-dom';
import { API, BACKEND_URL, AuthContext } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import Navbar from '../components/Navbar';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { ArrowUp, ArrowDown, MapPin, Calendar, MessageCircle, TrendingUp, Image as ImageIcon, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { TextWithURLPreviews } from '../components/URLPreview';

const IdeaDetail = () => {
  const { id } = useParams();
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [mainIdea, setMainIdea] = useState(null);
  const [allIdeas, setAllIdeas] = useState([]); // Flat list of all ideas sorted by upvotes
  const [userVotes, setUserVotes] = useState({}); // Track user's votes: { ideaId: 1 or -1 }
  const [loading, setLoading] = useState(true);
  const [replyToId, setReplyToId] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [replyImages, setReplyImages] = useState([]);
  const [replyImagePreviews, setReplyImagePreviews] = useState([]);
  const [replying, setReplying] = useState(false);

  useEffect(() => {
    fetchIdea();
    if (user && token) {
      fetchUserVotes();
    }
  }, [id, user, token]);

  const fetchUserVotes = async () => {
    if (!user || !token) return;
    
    try {
      // Get all ideas in the thread
      const response = await axios.get(`${API}/ideas/${id}`);
      const data = response.data;
      
      const flattenComments = (comments) => {
        let result = [];
        comments.forEach(comment => {
          result.push(comment);
          if (comment.comments && comment.comments.length > 0) {
            result = result.concat(flattenComments(comment.comments));
          }
        });
        return result;
      };

      const allComments = flattenComments(data.comments || []);
      const allIdeaIds = [data.id, ...allComments.map(c => c.id)];
      
      // Fetch user's votes for all these ideas
      const votesResponse = await axios.get(`${API}/my-votes?idea_ids=${allIdeaIds.join(',')}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Convert to { ideaId: voteValue } format
      const votesMap = {};
      votesResponse.data.forEach(vote => {
        votesMap[vote.idea_id] = vote.vote_value;
      });
      
      setUserVotes(votesMap);
    } catch (error) {
      console.error('Failed to fetch user votes', error);
    }
  };

  const fetchIdea = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/ideas/${id}`);
      const data = response.data;
      
      // Flatten all comments into a single array
      const flattenComments = (comments) => {
        let result = [];
        comments.forEach(comment => {
          result.push(comment);
          if (comment.comments && comment.comments.length > 0) {
            result = result.concat(flattenComments(comment.comments));
          }
        });
        return result;
      };

      const allComments = flattenComments(data.comments || []);
      
      // Create a flat list with main idea and all comments
      const allIdeasList = [data, ...allComments];
      
      // Sort by upvotes descending
      allIdeasList.sort((a, b) => b.upvotes - a.upvotes);
      
      setMainIdea(data);
      setAllIdeas(allIdeasList);
    } catch (error) {
      console.error('Failed to fetch idea', error);
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (ideaId, voteValue) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    if (!user.is_verified_email) {
      toast.error('Verify your email to vote');
      return;
    }

    // Optimistic update
    const currentVote = userVotes[ideaId];
    const newVote = currentVote === voteValue ? 0 : voteValue; // Toggle off if same
    
    setUserVotes(prev => {
      const updated = { ...prev };
      if (newVote === 0) {
        delete updated[ideaId];
      } else {
        updated[ideaId] = newVote;
      }
      return updated;
    });

    try {
      await axios.post(
        `${API}/ideas/${ideaId}/vote`,
        { vote: voteValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Refresh to get updated votes and potentially new order
      fetchIdea();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to vote');
      // Revert optimistic update
      fetchUserVotes();
    }
  };

  const handleReply = async (parentId) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    // Require either body text or images
    if (!replyBody.trim() && replyImages.length === 0) {
      toast.error('Please add some text or an image');
      return;
    }

    setReplying(true);
    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append('body', replyBody || ' '); // Send space if empty but has images
      
      // Add images
      replyImages.forEach(image => {
        formData.append('images', image);
      });

      await axios.post(
        `${API}/ideas/${parentId}/comments`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success('Idea posted!');
      setReplyBody('');
      setReplyImages([]);
      setReplyImagePreviews([]);
      setReplyToId(null);
      fetchIdea();
    } catch (error) {
      console.error('Reply submission error:', error);
      console.error('Error response:', error.response);
      console.error('Error detail:', error.response?.data);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to post idea';
      toast.error(errorMessage);
    } finally {
      setReplying(false);
    }
  };

  const handleReplyImageSelect = (e) => {
    const files = Array.from(e.target.files);
    const validImages = files.filter(file => file.type.startsWith('image/'));
    
    if (validImages.length !== files.length) {
      toast.error('Only image files are allowed');
    }
    
    setReplyImages(prev => [...prev, ...validImages]);
    
    // Create previews
    validImages.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setReplyImagePreviews(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removeReplyImage = (index) => {
    setReplyImages(prev => prev.filter((_, i) => i !== index));
    setReplyImagePreviews(prev => prev.filter((_, i) => i !== index));
  };

  // Calculate indentation level based on position in sorted list
  const getIndentLevel = (index) => {
    if (index === 0) return 0; // Top idea has no indent
    
    const currentUpvotes = allIdeas[index].upvotes;
    const previousUpvotes = allIdeas[index - 1].upvotes;
    
    // Same upvotes = same indent level
    if (currentUpvotes === previousUpvotes) {
      return getIndentLevel(index - 1);
    }
    
    // Less upvotes = more indent
    return getIndentLevel(index - 1) + 1;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        <Navbar />
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
        </div>
      </div>
    );
  }

  if (!mainIdea) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-gray-500">Idea not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Info */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <div className="flex items-center space-x-2 text-sm text-gray-600 mb-4">
            <TrendingUp size={16} />
            <span className="font-medium">Ideas ranked by upvotes - highest at top, indented by vote hierarchy</span>
          </div>
          
          {mainIdea.category && (
            <div className="flex items-center flex-wrap gap-2">
              <Badge className="bg-emerald-50 text-emerald-700">{mainIdea.category}</Badge>
              {mainIdea.city && (
                <Badge variant="outline" className="flex items-center space-x-1">
                  <MapPin size={12} />
                  <span>{mainIdea.city}</span>
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Outline - All Ideas Sorted by Upvotes */}
        <div className="bg-white rounded-2xl p-8 shadow-lg mb-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center space-x-2">
            <MessageCircle size={24} />
            <span>All Ideas ({allIdeas.length})</span>
          </h2>

          <div className="space-y-4">
            {allIdeas.map((idea, index) => {
              const indentLevel = getIndentLevel(index);
              const marginLeft = indentLevel * 40; // 40px per level
              const isMainIdea = idea.id === mainIdea.id;
              const userVote = userVotes[idea.id]; // 1, -1, or undefined
              const hasUpvoted = userVote === 1;
              const hasDownvoted = userVote === -1;

              return (
                <div
                  key={idea.id}
                  className="group relative"
                  style={{ marginLeft: `${marginLeft}px` }}
                  data-testid="idea-item"
                >
                  {/* Indent indicator line */}
                  {indentLevel > 0 && (
                    <div 
                      className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-emerald-200 to-transparent"
                      style={{ left: `-20px` }}
                    />
                  )}

                  <div className="bg-gray-50 rounded-xl p-5 hover:bg-gray-100 transition-all border-2 border-transparent hover:border-emerald-200">
                    <div className="flex items-start space-x-4">
                      {/* Voting */}
                      <div className="flex flex-col items-center space-y-1 flex-shrink-0">
                        <button
                          onClick={() => handleVote(idea.id, 1)}
                          className={`p-2 rounded-lg transition-colors ${
                            hasUpvoted 
                              ? 'bg-emerald-100 text-emerald-600' 
                              : 'hover:bg-emerald-50 text-gray-400 hover:text-emerald-600'
                          }`}
                          data-testid="upvote-button"
                          title={hasUpvoted ? 'Remove upvote' : 'Upvote this idea'}
                        >
                          <ArrowUp size={18} className={hasUpvoted ? 'fill-current' : ''} />
                        </button>
                        <span className="font-bold text-lg text-emerald-600" data-testid="upvote-count">
                          {idea.upvotes}
                        </span>
                        <button
                          onClick={() => handleVote(idea.id, -1)}
                          className={`p-2 rounded-lg transition-colors ${
                            hasDownvoted 
                              ? 'bg-red-100 text-red-600' 
                              : 'hover:bg-red-50 text-gray-400 hover:text-red-600'
                          }`}
                          data-testid="downvote-button"
                          title={hasDownvoted ? 'Remove downvote' : 'Downvote this idea'}
                        >
                          <ArrowDown size={18} className={hasDownvoted ? 'fill-current' : ''} />
                        </button>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Title (only for main ideas with titles) */}
                        {idea.title && (
                          <h3 className="text-xl font-bold text-gray-900 mb-2" data-testid="idea-title">
                            {idea.title}
                            {isMainIdea && (
                              <Badge className="ml-2 bg-blue-100 text-blue-700">Original</Badge>
                            )}
                          </h3>
                        )}

                        {/* Body */}
                        <div className="mb-3">
                          <TextWithURLPreviews text={idea.body} />
                        </div>

                        {/* Attached Images */}
                        {idea.attachments && idea.attachments.length > 0 && (
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                            {idea.attachments.map((attachment, idx) => {
                              const imageUrl = attachment.startsWith('http') ? attachment : `${BACKEND_URL}${attachment}`;
                              return (
                                <img
                                  key={idx}
                                  src={imageUrl}
                                  alt={`Image ${idx + 1}`}
                                  className="w-full h-48 object-cover rounded-lg border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => window.open(imageUrl, '_blank')}
                                  onError={(e) => {
                                    console.error('Failed to load image:', imageUrl);
                                  }}
                                />
                              );
                            })}
                          </div>
                        )}

                        {/* Author and timestamp */}
                        <div className="flex items-center justify-between">
                          <Link
                            to={`/leaders/${idea.author?.username}`}
                            className="flex items-center space-x-2 text-sm text-gray-500 hover:text-emerald-600 transition-colors"
                          >
                            <Avatar className="w-6 h-6">
                              <AvatarFallback className="text-xs bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
                                {idea.author?.name?.charAt(0).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <span className="font-medium">{idea.author?.name}</span>
                            <span className="text-gray-400">·</span>
                            <span className="flex items-center space-x-1">
                              <Calendar size={12} />
                              <span>{formatDistanceToNow(new Date(idea.created_at), { addSuffix: true })}</span>
                            </span>
                          </Link>

                          {/* Reply button */}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setReplyToId(replyToId === idea.id ? null : idea.id)}
                            className="text-sm"
                            data-testid="reply-button"
                          >
                            <MessageCircle size={14} className="mr-1" />
                            Reply
                          </Button>
                        </div>

                        {/* Reply form */}
                        {replyToId === idea.id && (
                          <div className="mt-4 space-y-3 bg-white p-4 rounded-lg border border-gray-200">
                            <Textarea
                              placeholder="Share your idea..."
                              value={replyBody}
                              onChange={(e) => setReplyBody(e.target.value)}
                              className="text-sm"
                              rows={3}
                              data-testid="reply-textarea"
                            />
                            
                            {/* Image Upload */}
                            <div>
                              <label
                                htmlFor={`reply-images-${idea.id}`}
                                className="flex items-center justify-center px-3 py-2 border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-emerald-500 transition-colors text-sm"
                              >
                                <ImageIcon size={16} className="mr-2 text-gray-400" />
                                <span className="text-gray-600">Add images</span>
                                <input
                                  id={`reply-images-${idea.id}`}
                                  type="file"
                                  accept="image/*"
                                  multiple
                                  onChange={handleReplyImageSelect}
                                  className="hidden"
                                />
                              </label>
                            </div>

                            {/* Image Previews */}
                            {replyImagePreviews.length > 0 && (
                              <div className="grid grid-cols-3 gap-2">
                                {replyImagePreviews.map((preview, index) => (
                                  <div key={index} className="relative group">
                                    <img
                                      src={preview}
                                      alt={`Preview ${index + 1}`}
                                      className="w-full h-24 object-cover rounded-lg border border-gray-200"
                                    />
                                    <button
                                      type="button"
                                      onClick={() => removeReplyImage(index)}
                                      className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                      <X size={12} />
                                    </button>
                                  </div>
                                ))}
                              </div>
                            )}

                            <div className="flex space-x-2">
                              <Button
                                size="sm"
                                onClick={() => handleReply(idea.id)}
                                disabled={replying}
                                data-testid="submit-reply"
                              >
                                {replying ? 'Posting...' : 'Post Idea'}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setReplyToId(null);
                                  setReplyBody('');
                                  setReplyImages([]);
                                  setReplyImagePreviews([]);
                                }}
                              >
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IdeaDetail;
