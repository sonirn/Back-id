import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_BACKEND_URL + '/api';

const VideoGeneration = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [userId, setUserId] = useState(null);
  const [email, setEmail] = useState('');
  const [files, setFiles] = useState({
    video: null,
    character: null,
    audio: null
  });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [plan, setPlan] = useState('');
  const [planModification, setPlanModification] = useState('');
  const [generationStatus, setGenerationStatus] = useState(null);
  const [userVideos, setUserVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState(null);
  
  const fileInputRef = useRef(null);
  const characterInputRef = useRef(null);
  const audioInputRef = useRef(null);
  
  // Polls for generation status
  const statusInterval = useRef(null);

  useEffect(() => {
    // Load user from localStorage
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      setUserId(savedUserId);
      setCurrentStep(2);
      loadUserVideos(savedUserId);
    }
  }, []);

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('email', email);
      
      const response = await axios.post(`${API_BASE}/create-user`, formData);
      
      setUserId(response.data.user_id);
      localStorage.setItem('userId', response.data.user_id);
      setCurrentStep(2);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const loadUserVideos = async (uid) => {
    try {
      const response = await axios.get(`${API_BASE}/user-videos/${uid}`);
      setUserVideos(response.data.videos);
    } catch (err) {
      console.error('Failed to load user videos:', err);
    }
  };

  const handleFileSelect = (type, event) => {
    const file = event.target.files[0];
    if (file) {
      setFiles(prev => ({ ...prev, [type]: file }));
    }
  };

  const handleUpload = async () => {
    if (!files.video) {
      setError('Please select a video file');
      return;
    }

    setLoading(true);
    setError('');
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('video_file', files.video);
      formData.append('user_id', userId);
      
      if (files.character) {
        formData.append('character_image', files.character);
      }
      
      if (files.audio) {
        formData.append('audio_file', files.audio);
      }

      const response = await axios.post(`${API_BASE}/upload-video`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      setAnalysis(response.data);
      setPlan(response.data.plan);
      setSessionId(response.data.session_id);
      setCurrentStep(3);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePlanModification = async () => {
    if (!planModification.trim()) {
      setError('Please enter your modification request');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/modify-plan`, {
        session_id: sessionId,
        modification_request: planModification
      });

      setPlan(response.data.modified_plan);
      setPlanModification('');
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Plan modification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVideo = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/generate-video`, {
        session_id: sessionId,
        approved_plan: plan
      });

      setCurrentStep(4);
      startStatusPolling(sessionId);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Video generation failed');
    } finally {
      setLoading(false);
    }
  };

  const startStatusPolling = (sid) => {
    if (statusInterval.current) {
      clearInterval(statusInterval.current);
    }

    const pollStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE}/generation-status/${sid}`);
        setGenerationStatus(response.data);
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(statusInterval.current);
          if (response.data.status === 'completed') {
            loadUserVideos(userId);
            setCurrentStep(5);
          }
        }
      } catch (err) {
        console.error('Status poll failed:', err);
      }
    };

    statusInterval.current = setInterval(pollStatus, 3000);
    pollStatus(); // Initial call
  };

  const resetProcess = () => {
    setCurrentStep(2);
    setFiles({ video: null, character: null, audio: null });
    setAnalysis(null);
    setPlan('');
    setPlanModification('');
    setGenerationStatus(null);
    setSessionId(null);
    setError('');
    setUploadProgress(0);
    
    if (statusInterval.current) {
      clearInterval(statusInterval.current);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">🎬 AI Video Generator</h1>
          <p className="text-gray-300">Create stunning videos with AI in minutes</p>
        </header>

        {error && (
          <div className="bg-red-500 text-white p-4 rounded-lg mb-6 max-w-2xl mx-auto">
            {error}
          </div>
        )}

        {/* Step 1: Signup */}
        {currentStep === 1 && (
          <div className="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Get Started</h2>
            <form onSubmit={handleSignup} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Creating Account...' : 'Start Creating'}
              </button>
            </form>
          </div>
        )}

        {/* Step 2: File Upload */}
        {currentStep === 2 && (
          <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Upload Your Files</h2>
            
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              {/* Video Upload */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <div className="text-4xl mb-4">🎥</div>
                <h3 className="font-semibold text-gray-700 mb-2">Sample Video</h3>
                <p className="text-sm text-gray-500 mb-4">Required • Max 60 seconds</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={(e) => handleFileSelect('video', e)}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current.click()}
                  className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
                >
                  Choose Video
                </button>
                {files.video && (
                  <p className="text-sm text-green-600 mt-2">✓ {files.video.name}</p>
                )}
              </div>

              {/* Character Image */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <div className="text-4xl mb-4">👤</div>
                <h3 className="font-semibold text-gray-700 mb-2">Character Image</h3>
                <p className="text-sm text-gray-500 mb-4">Optional</p>
                <input
                  ref={characterInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileSelect('character', e)}
                  className="hidden"
                />
                <button
                  onClick={() => characterInputRef.current.click()}
                  className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600"
                >
                  Choose Image
                </button>
                {files.character && (
                  <p className="text-sm text-green-600 mt-2">✓ {files.character.name}</p>
                )}
              </div>

              {/* Audio Upload */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <div className="text-4xl mb-4">🎵</div>
                <h3 className="font-semibold text-gray-700 mb-2">Audio File</h3>
                <p className="text-sm text-gray-500 mb-4">Optional</p>
                <input
                  ref={audioInputRef}
                  type="file"
                  accept="audio/*"
                  onChange={(e) => handleFileSelect('audio', e)}
                  className="hidden"
                />
                <button
                  onClick={() => audioInputRef.current.click()}
                  className="bg-orange-500 text-white px-4 py-2 rounded-md hover:bg-orange-600"
                >
                  Choose Audio
                </button>
                {files.audio && (
                  <p className="text-sm text-green-600 mt-2">✓ {files.audio.name}</p>
                )}
              </div>
            </div>

            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="mb-6">
                <div className="bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p className="text-sm text-gray-600 mt-2">Uploading... {uploadProgress}%</p>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={resetProcess}
                className="bg-gray-500 text-white px-6 py-3 rounded-md hover:bg-gray-600"
              >
                Reset
              </button>
              <button
                onClick={handleUpload}
                disabled={!files.video || loading}
                className="bg-purple-600 text-white px-6 py-3 rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Analyzing...' : 'Analyze Video'}
              </button>
            </div>

            {/* User Videos */}
            {userVideos.length > 0 && (
              <div className="mt-8 border-t pt-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">Your Videos</h3>
                <div className="space-y-3">
                  {userVideos.map((video) => (
                    <div key={video.session_id} className="bg-gray-50 p-4 rounded-lg">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="text-sm text-gray-600 mb-2">{video.analysis}</p>
                          <p className="text-xs text-gray-500">
                            Created: {new Date(video.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="ml-4 text-right">
                          <span className={`inline-block px-2 py-1 text-xs rounded-full ${
                            video.status === 'completed' ? 'bg-green-100 text-green-800' :
                            video.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                            video.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {video.status}
                          </span>
                          {video.video_url && (
                            <a
                              href={video.video_url}
                              className="block mt-2 text-blue-600 hover:text-blue-800 text-sm"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Download
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Review Plan */}
        {currentStep === 3 && (
          <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Generated Plan</h2>
            
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <h3 className="font-semibold text-gray-700 mb-3">Video Analysis</h3>
              <p className="text-gray-600 mb-4">{analysis?.analysis}</p>
              
              <h3 className="font-semibold text-gray-700 mb-3">Generation Plan</h3>
              <pre className="text-gray-600 whitespace-pre-wrap">{plan}</pre>
            </div>

            <div className="border-t pt-6">
              <h3 className="font-semibold text-gray-700 mb-3">Make Changes (Optional)</h3>
              <div className="flex gap-4">
                <textarea
                  value={planModification}
                  onChange={(e) => setPlanModification(e.target.value)}
                  placeholder="Describe any changes you'd like to make to the plan..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  rows="3"
                />
                <button
                  onClick={handlePlanModification}
                  disabled={loading || !planModification.trim()}
                  className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  {loading ? 'Updating...' : 'Update Plan'}
                </button>
              </div>
            </div>

            <div className="flex justify-between mt-8">
              <button
                onClick={() => setCurrentStep(2)}
                className="bg-gray-500 text-white px-6 py-3 rounded-md hover:bg-gray-600"
              >
                Back
              </button>
              <button
                onClick={handleGenerateVideo}
                disabled={loading}
                className="bg-purple-600 text-white px-6 py-3 rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Starting Generation...' : 'Generate Video'}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Generation Progress */}
        {currentStep === 4 && (
          <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Generating Your Video</h2>
            
            <div className="text-center mb-8">
              <div className="text-6xl mb-4">🎬</div>
              <p className="text-gray-600 mb-6">
                AI is creating your video. This process continues even if you close this page.
              </p>
              
              {generationStatus && (
                <div className="space-y-4">
                  <div className="bg-gray-200 rounded-full h-4">
                    <div 
                      className="bg-purple-600 h-4 rounded-full transition-all duration-300"
                      style={{ width: `${generationStatus.progress}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Progress: {generationStatus.progress}%</span>
                    <span>
                      Time remaining: {formatTime(generationStatus.estimated_time_remaining)}
                    </span>
                  </div>
                  <p className="text-lg font-semibold text-gray-800">
                    Status: {generationStatus.status}
                  </p>
                </div>
              )}
            </div>

            <div className="text-center">
              <button
                onClick={() => setCurrentStep(2)}
                className="bg-gray-500 text-white px-6 py-3 rounded-md hover:bg-gray-600"
              >
                Start New Video
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Completed */}
        {currentStep === 5 && (
          <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Video Ready!</h2>
            
            <div className="text-center mb-8">
              <div className="text-6xl mb-4">🎉</div>
              <p className="text-gray-600 mb-6">
                Your video has been generated successfully! You can access it for the next 7 days.
              </p>
              
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="bg-purple-600 text-white px-6 py-3 rounded-md hover:bg-purple-700"
                >
                  Create Another Video
                </button>
                <button
                  onClick={() => loadUserVideos(userId)}
                  className="bg-blue-500 text-white px-6 py-3 rounded-md hover:bg-blue-600"
                >
                  View My Videos
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const App = () => {
  return (
    <div className="App">
      <VideoGeneration />
    </div>
  );
};

export default App;