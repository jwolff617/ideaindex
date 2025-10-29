import React, { useState, useEffect, useContext } from 'react';
import { useParams, Link } from 'react-router-dom';
import { API, AuthContext } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import Navbar from '../components/Navbar';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { ArrowUp, ArrowDown, MapPin, Calendar, MessageCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const Comment = ({ comment, depth = 0, onUpdate }) => {
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [upvotes, setUpvotes] = useState(comment.upvotes || 0);
  const [downvotes, setDownvotes] = useState(comment.downvotes || 0);
  const [voting, setVoting] = useState(false);
  const [showReply, setShowReply] = useState(false);
  const [replyBody, setReplyBody] = useState('');
  const [replying, setReplying] = useState(false);

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
        `${API}/ideas/${comment.id}/vote`,
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

  const handleReply = async () => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    if (!replyBody.trim()) return;

    setReplying(true);
    try {
      await axios.post(
        `${API}/ideas/${comment.id}/comments`,
        { body: replyBody },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Reply posted!');
      setReplyBody('');
      setShowReply(false);
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post reply');
    } finally {
      setReplying(false);
    }
  };

  return (
    <div className={`${depth > 0 ? 'ml-8 mt-4' : 'mt-4'} border-l-2 border-gray-200 pl-4`} data-testid="comment">
      <div className="flex items-start space-x-3">
        <div className="flex flex-col items-center space-y-1">
          <button
            onClick={() => handleVote(1)}
            disabled={voting}
            className="p-1 rounded hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 transition-colors"
            data-testid="comment-upvote"
          >
            <ArrowUp size={16} />
          </button>
          <span className="text-sm font-bold" data-testid="comment-upvote-count">{upvotes}</span>
          <button
            onClick={() => handleVote(-1)}
            disabled={voting}
            className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors"
            data-testid="comment-downvote"
          >
            <ArrowDown size={16} />
          </button>
        </div>

        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <Link to={`/leaders/${comment.author?.username}`} className="flex items-center space-x-2 hover:text-emerald-600 transition-colors">
              <Avatar className="w-6 h-6">
                <AvatarFallback className="text-xs bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
                  {comment.author?.name?.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium" data-testid="comment-author">{comment.author?.name}</span>
            </Link>
            <span className="text-xs text-gray-400">
              {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
            </span>
          </div>

          <p className="text-gray-700 mb-2" data-testid="comment-body">{comment.body}</p>

          <button
            onClick={() => setShowReply(!showReply)}
            className="text-xs text-gray-500 hover:text-emerald-600 font-medium"
            data-testid="reply-button"
          >
            Reply
          </button>

          {showReply && (
            <div className="mt-3 space-y-2">
              <Textarea
                placeholder="Write a reply..."
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                className="text-sm"
                data-testid="reply-textarea"
              />
              <div className="flex space-x-2">
                <Button size="sm" onClick={handleReply} disabled={replying} data-testid="submit-reply">
                  {replying ? 'Posting...' : 'Post Reply'}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowReply(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {comment.comments && comment.comments.length > 0 && (
            <div className="mt-2">
              {comment.comments.map((childComment) => (
                <Comment key={childComment.id} comment={childComment} depth={depth + 1} onUpdate={onUpdate} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const IdeaDetail = () => {
  const { id } = useParams();
  const { user, token, setShowAuthModal } = useContext(AuthContext);
  const [idea, setIdea] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upvotes, setUpvotes] = useState(0);
  const [downvotes, setDownvotes] = useState(0);
  const [voting, setVoting] = useState(false);
  const [commentBody, setCommentBody] = useState('');
  const [commenting, setCommenting] = useState(false);

  useEffect(() => {
    fetchIdea();
  }, [id]);

  const fetchIdea = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/ideas/${id}`);
      setIdea(response.data);
      setUpvotes(response.data.upvotes || 0);
      setDownvotes(response.data.downvotes || 0);
    } catch (error) {
      console.error('Failed to fetch idea', error);
    } finally {
      setLoading(false);
    }
  };

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
        `${API}/ideas/${id}/vote`,
        { vote: voteValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setUpvotes(response.data.upvotes);
      setDownvotes(response.data.downvotes);
      fetchIdea();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to vote');
    } finally {
      setVoting(false);
    }
  };

  const handleComment = async () => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    if (!commentBody.trim()) return;

    setCommenting(true);
    try {
      await axios.post(
        `${API}/ideas/${id}/comments?body=${encodeURIComponent(commentBody)}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Comment posted!');
      setCommentBody('');
      fetchIdea();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post comment');
    } finally {
      setCommenting(false);
    }
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

  if (!idea) {
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

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-2xl p-8 shadow-lg mb-6">
          <div className="flex items-start space-x-6">
            <div className="flex flex-col items-center space-y-3">
              <button
                onClick={() => handleVote(1)}
                disabled={voting}
                className="p-3 rounded-xl hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 transition-colors disabled:opacity-50"
                data-testid="main-upvote-button"
              >
                <ArrowUp size={24} />
              </button>
              <span className="font-bold text-2xl" data-testid="main-upvote-count">{upvotes}</span>
              <button
                onClick={() => handleVote(-1)}
                disabled={voting}
                className="p-3 rounded-xl hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                data-testid="main-downvote-button"
              >
                <ArrowDown size={24} />
              </button>
            </div>

            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-4" data-testid="idea-detail-title">{idea.title}</h1>
              
              <div className="flex items-center flex-wrap gap-2 mb-4">
                {idea.category && (
                  <Badge className="bg-emerald-50 text-emerald-700">{idea.category}</Badge>
                )}
                {idea.city && (
                  <Badge variant="outline" className="flex items-center space-x-1">
                    <MapPin size={12} />
                    <span>{idea.city}</span>
                  </Badge>
                )}
              </div>

              <p className="text-gray-700 text-lg leading-relaxed mb-6 whitespace-pre-wrap" data-testid="idea-detail-body">{idea.body}</p>

              <Link
                to={`/leaders/${idea.author?.username}`}
                className="flex items-center space-x-3 text-sm text-gray-500 hover:text-emerald-600 transition-colors mb-4"
              >
                <Avatar className="w-8 h-8">
                  <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
                    {idea.author?.name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-medium">{idea.author?.name}</p>
                  <p className="text-xs flex items-center space-x-1">
                    <Calendar size={12} />
                    <span>{formatDistanceToNow(new Date(idea.created_at), { addSuffix: true })}</span>
                  </p>
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Comments Section */}
        <div className="bg-white rounded-2xl p-8 shadow-lg">
          <h2 className="text-2xl font-bold mb-6 flex items-center space-x-2">
            <MessageCircle size={24} />
            <span>Discussion</span>
          </h2>

          {/* Add Comment */}
          <div className="mb-8">
            <Textarea
              placeholder="Share your thoughts..."
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              className="mb-3"
              rows={3}
              data-testid="comment-textarea"
            />
            <Button onClick={handleComment} disabled={commenting} data-testid="submit-comment-button">
              {commenting ? 'Posting...' : 'Post Comment'}
            </Button>
          </div>

          {/* Comments List */}
          <div data-testid="comments-list">
            {idea.comments && idea.comments.length > 0 ? (
              idea.comments.map((comment) => (
                <Comment key={comment.id} comment={comment} onUpdate={fetchIdea} />
              ))
            ) : (
              <p className="text-center text-gray-500 py-8">No comments yet. Be the first to share your thoughts!</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IdeaDetail;
