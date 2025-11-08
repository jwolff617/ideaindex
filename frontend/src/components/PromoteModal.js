import React, { useState, useEffect, useContext } from 'react';
import { API, AuthContext } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Sparkles, X, Loader2, TrendingUp } from 'lucide-react';

const PromoteModal = ({ idea, onClose, onSuccess }) => {
  const { token } = useContext(AuthContext);
  const [title, setTitle] = useState('');
  const [generatingTitle, setGeneratingTitle] = useState(false);
  const [promoting, setPromoting] = useState(false);

  useEffect(() => {
    // Auto-generate title on mount
    generateTitle();
  }, []);

  const generateTitle = async () => {
    setGeneratingTitle(true);
    try {
      const response = await axios.post(
        `${API}/generate-title`,
        { body: idea.body },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTitle(response.data.title);
    } catch (error) {
      console.error('Failed to generate title', error);
      // Fallback: use first sentence
      const fallback = idea.body.split('.')[0].slice(0, 50);
      setTitle(fallback);
    } finally {
      setGeneratingTitle(false);
    }
  };

  const handlePromote = async () => {
    if (!title.trim()) {
      toast.error('Please add a title');
      return;
    }

    setPromoting(true);
    try {
      await axios.post(
        `${API}/ideas/${idea.id}/promote`,
        {
          title: title,
          category_id: idea.category_id,
          city_id: idea.city_id,
          tags: idea.tags ? idea.tags.join(',') : ''
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Promoted to Outdexed! 🎉');
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Failed to promote', error);
      toast.error(error.response?.data?.detail || 'Failed to promote idea');
    } finally {
      setPromoting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-emerald-50 to-teal-50">
          <div className="flex items-center space-x-3">
            <TrendingUp size={24} className="text-emerald-600" />
            <h2 className="text-2xl font-bold text-gray-900">Create New Outdexed Idea</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Idea Title</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={generateTitle}
                disabled={generatingTitle}
                className="text-xs text-emerald-600 hover:text-emerald-700"
              >
                {generatingTitle ? (
                  <>
                    <Loader2 size={12} className="mr-1 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={12} className="mr-1" />
                    Regenerate with AI
                  </>
                )}
              </Button>
            </div>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a compelling title..."
              disabled={generatingTitle}
              className="text-lg font-semibold"
            />
            <p className="text-xs text-gray-400">
              Edit as needed
            </p>
          </div>

          {/* Body Preview */}
          <div className="space-y-2">
            <Label>Idea Content (Preview)</Label>
            <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {idea.body}
              </p>
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <Label className="text-xs text-gray-500">Category</Label>
              <p className="font-medium">{idea.category || 'None'}</p>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Location</Label>
              <p className="font-medium">{idea.city || 'None'}</p>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={promoting}
          >
            Cancel
          </Button>
          <Button
            onClick={handlePromote}
            disabled={promoting || !title.trim()}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            {promoting ? (
              <>
                <Loader2 size={16} className="mr-2 animate-spin" />
                Promoting...
              </>
            ) : (
              <>
                <TrendingUp size={16} className="mr-2" />
                Create Outdexed Idea
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default PromoteModal;
