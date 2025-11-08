import React, { useState, useEffect, useContext } from 'react';
import { useParams, Link } from 'react-router-dom';
import { API, BACKEND_URL, AuthContext } from '../App';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Award, Calendar, Lightbulb, MessageCircle, Camera, Upload } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';

const LeaderProfile = () => {
  const { username } = useParams();
  const { user, token } = useContext(AuthContext);
  const [leader, setLeader] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    fetchLeader();
  }, [username]);

  const fetchLeader = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/leaders/${username}`);
      setLeader(response.data);
    } catch (error) {
      console.error('Failed to fetch leader', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast.error('Image must be less than 10MB');
        return;
      }
      setSelectedFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !token) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
      const response = await axios.post(`${API}/upload-profile-picture`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success('Profile picture updated successfully!');
      
      // Update leader state with new avatar
      setLeader({ ...leader, avatar_url: response.data.avatar_url });
      
      // Clear selection
      setSelectedFile(null);
      setPreviewUrl(null);
      
      // Reset file input
      const fileInput = document.getElementById('avatar-upload');
      if (fileInput) fileInput.value = '';
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to upload profile picture');
    } finally {
      setUploading(false);
    }
  };

  const handleCancelUpload = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    const fileInput = document.getElementById('avatar-upload');
    if (fileInput) fileInput.value = '';
  };

  const isOwnProfile = user && leader && user.username === leader.username;

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

  if (!leader) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-gray-500">Leader not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Profile Header */}
        <div className="bg-white rounded-2xl p-8 shadow-lg mb-6">
          <div className="flex flex-col md:flex-row items-center md:items-start space-y-4 md:space-y-0 md:space-x-6">
            {/* Avatar with Upload */}
            <div className="relative">
              <Avatar className="w-24 h-24 ring-4 ring-emerald-500/20">
                {leader.avatar_url ? (
                  <AvatarImage 
                    src={`${BACKEND_URL}${leader.avatar_url}`} 
                    alt={leader.name}
                  />
                ) : null}
                <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white text-4xl font-bold">
                  {leader.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              
              {/* Upload button - only visible on own profile */}
              {isOwnProfile && (
                <label
                  htmlFor="avatar-upload"
                  className="absolute bottom-0 right-0 bg-emerald-600 text-white p-2 rounded-full cursor-pointer hover:bg-emerald-700 transition-colors shadow-lg"
                  title="Upload profile picture"
                >
                  <Camera size={16} />
                  <input
                    id="avatar-upload"
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              )}
            </div>

            <div className="flex-1 text-center md:text-left">
              <h1 className="text-3xl font-bold text-gray-900 mb-2" data-testid="profile-name">{leader.name}</h1>
              <p className="text-lg text-gray-500 mb-3" data-testid="profile-username">@{leader.username}</p>

              {leader.bio && (
                <p className="text-gray-700 mb-4">{leader.bio}</p>
              )}

              <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                <Badge className="bg-emerald-50 text-emerald-700 flex items-center space-x-1">
                  <Award size={14} />
                  <span>{leader.leader_score} Leader Score</span>
                </Badge>
                <Badge variant="outline" className="flex items-center space-x-1">
                  <Calendar size={14} />
                  <span>Joined {formatDistanceToNow(new Date(leader.created_at), { addSuffix: true })}</span>
                </Badge>
              </div>
            </div>
          </div>

          {/* Upload Preview and Actions */}
          {isOwnProfile && selectedFile && (
            <div className="mt-6 p-4 bg-emerald-50 rounded-xl border border-emerald-200">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <div className="relative">
                  <Avatar className="w-20 h-20 ring-2 ring-emerald-500">
                    <AvatarImage src={previewUrl} alt="Preview" />
                  </Avatar>
                  <div className="absolute -top-1 -right-1 bg-emerald-600 text-white rounded-full p-1">
                    <Upload size={12} />
                  </div>
                </div>
                <div className="flex-1 text-center sm:text-left">
                  <p className="font-semibold text-gray-900 mb-1">Ready to upload</p>
                  <p className="text-sm text-gray-600">{selectedFile.name}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleUpload}
                    disabled={uploading}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {uploading ? 'Uploading...' : 'Upload'}
                  </Button>
                  <Button
                    onClick={handleCancelUpload}
                    variant="outline"
                    disabled={uploading}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Ideas and Comments */}
        <Tabs defaultValue="ideas" className="bg-white rounded-2xl shadow-lg overflow-hidden">
          <TabsList className="w-full justify-start border-b rounded-none h-auto p-0">
            <TabsTrigger
              value="ideas"
              className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 px-6 py-4"
              data-testid="ideas-tab"
            >
              <Lightbulb size={16} className="mr-2" />
              Ideas ({leader.ideas?.length || 0})
            </TabsTrigger>
            <TabsTrigger
              value="comments"
              className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 px-6 py-4"
              data-testid="comments-tab"
            >
              <MessageCircle size={16} className="mr-2" />
              Comments ({leader.comments?.length || 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="ideas" className="p-6">
            {leader.ideas && leader.ideas.length > 0 ? (
              <div className="space-y-4" data-testid="ideas-list">
                {leader.ideas.map((idea) => (
                  <Link
                    key={idea.id}
                    to={`/ideas/${idea.id}`}
                    className="block p-4 rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 transition-all"
                  >
                    <h3 className="font-bold text-gray-900 mb-2">{idea.title}</h3>
                    <p className="text-gray-600 text-sm line-clamp-2 mb-2">{idea.body}</p>
                    <div className="flex items-center space-x-3 text-xs text-gray-500">
                      <span>{idea.upvotes} upvotes</span>
                      <span>·</span>
                      <span>{idea.comments_count || 0} comments</span>
                      <span>·</span>
                      <span>{formatDistanceToNow(new Date(idea.created_at), { addSuffix: true })}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">No ideas yet</p>
            )}
          </TabsContent>

          <TabsContent value="comments" className="p-6">
            {leader.comments && leader.comments.length > 0 ? (
              <div className="space-y-4" data-testid="comments-list">
                {leader.comments.map((comment) => (
                  <div
                    key={comment.id}
                    className="p-4 rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 transition-all"
                  >
                    <p className="text-gray-700 mb-2">{comment.body}</p>
                    <div className="flex items-center space-x-3 text-xs text-gray-500">
                      <span>{comment.upvotes} upvotes</span>
                      <span>·</span>
                      <span>{formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">No comments yet</p>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default LeaderProfile;
