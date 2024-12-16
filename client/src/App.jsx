import React, { useState, useCallback, useEffect } from 'react';
import { 
  Container, 
  Paper, 
  TextField, 
  Select, 
  MenuItem, 
  Button, 
  Typography, 
  Box,
  LinearProgress,
  FormControl,
  InputLabel,
  Alert,
  Snackbar,
  useTheme,
  ThemeProvider,
  createTheme,
} from '@mui/material';
import { styled, keyframes } from '@mui/system';
import axios from 'axios';
import './App.css';

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:3002',
  timeout: 300000, // 5 minutes
  withCredentials: true,
});

// Add request interceptor for debugging
api.interceptors.request.use(request => {
  console.log('Starting Request:', {
    url: request.url,
    method: request.method,
    data: request.data
  });
  return request;
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    return Promise.reject(error);
  }
);

// Platform options
const PLATFORMS = {
  YOUTUBE: 'youtube',
  TIKTOK: 'tiktok'
};

// Format options
const FORMATS = {
  MP4: 'mp4',
  MP3: 'mp3'
};

// Create custom theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    secondary: {
      main: '#f50057',
      light: '#ff4081',
      dark: '#c51162',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 30,
          textTransform: 'none',
          fontWeight: 600,
          padding: '10px 24px',
          transition: 'all 0.3s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 5px 15px rgba(0,0,0,0.2)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          transition: 'transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out',
          '&:hover': {
            transform: 'perspective(1000px) rotateX(2deg)',
            boxShadow: '0 8px 25px rgba(0,0,0,0.1)',
          },
        },
      },
    },
  },
});

// Styled components
const StyledContainer = styled(Container)(({ theme }) => ({
  marginTop: theme.spacing(4),
  marginBottom: theme.spacing(4),
  '@keyframes fadeIn': {
    from: {
      opacity: 0,
      transform: 'translateY(20px)',
    },
    to: {
      opacity: 1,
      transform: 'translateY(0)',
    },
  },
  animation: 'fadeIn 0.6s ease-out',
}));

const StyledProgress = styled(LinearProgress)(({ theme }) => ({
  height: 10,
  borderRadius: 5,
  backgroundColor: theme.palette.grey[200],
  '.MuiLinearProgress-bar': {
    borderRadius: 5,
    backgroundImage: `linear-gradient(45deg, 
      ${theme.palette.primary.main} 25%, 
      ${theme.palette.primary.light} 25%, 
      ${theme.palette.primary.light} 50%, 
      ${theme.palette.primary.main} 50%, 
      ${theme.palette.primary.main} 75%, 
      ${theme.palette.primary.light} 75%, 
      ${theme.palette.primary.light})`,
    backgroundSize: '40px 40px',
    animation: 'progress-animation 2s linear infinite',
  },
  '@keyframes progress-animation': {
    '0%': {
      backgroundPosition: '0 0',
    },
    '100%': {
      backgroundPosition: '40px 0',
    },
  },
}));

const pulse = keyframes`
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
`;

const StyledDownloadButton = styled(Button)(({ theme }) => ({
  background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
  color: 'white',
  fontWeight: 'bold',
  padding: '12px 36px',
  fontSize: '1.1rem',
  '&:hover': {
    animation: `${pulse} 1s infinite`,
    background: `linear-gradient(45deg, ${theme.palette.primary.dark}, ${theme.palette.secondary.dark})`,
  },
}));

const StyledVideoCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginTop: theme.spacing(3),
  marginBottom: theme.spacing(3),
  background: 'rgba(255, 255, 255, 0.9)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  transform: 'perspective(1000px) rotateX(0deg)',
  transition: 'all 0.3s ease-in-out',
  '&:hover': {
    transform: 'perspective(1000px) rotateX(2deg)',
    boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
  },
}));

function App() {
  const [url, setUrl] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [platform, setPlatform] = useState(PLATFORMS.YOUTUBE);
  const [format, setFormat] = useState(FORMATS.MP4);
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [videoInfo, setVideoInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // URL validation
  const validateUrl = useCallback((url) => {
    try {
      const urlObj = new URL(url);
      const hostname = urlObj.hostname.toLowerCase();
      
      if (platform === PLATFORMS.YOUTUBE) {
        if (!hostname.includes('youtube.com') && !hostname.includes('youtu.be')) {
          return 'Please enter a valid YouTube URL';
        }
      } else if (platform === PLATFORMS.TIKTOK) {
        if (!hostname.includes('tiktok.com')) {
          return 'Please enter a valid TikTok URL';
        }
      }
      return null;
    } catch (err) {
      return 'Please enter a valid URL';
    }
  }, [platform]);

  // Fetch video information when URL or platform changes
  useEffect(() => {
    const fetchVideoInfo = async () => {
      if (!url) {
        setVideoInfo(null);
        return;
      }

      const urlError = validateUrl(url);
      if (urlError) {
        setError(urlError);
        setVideoInfo(null);
        return;
      }

      setLoading(true);
      setError('');
      try {
        const response = await api.post('/api/video-info', {
          url: url.trim(),
          platform: platform.toLowerCase()
        });

        if (response.data.status === 'success') {
          setVideoInfo(response.data.data);
          setError('');
        }
      } catch (err) {
        const errorMessage = err.response?.data?.message || 'Failed to fetch video information';
        setError(errorMessage);
        setVideoInfo(null);
      } finally {
        setLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchVideoInfo, 500);
    return () => clearTimeout(debounceTimer);
  }, [url, platform]);

  // Clear error when URL, platform, or format changes
  useEffect(() => {
    setError('');
  }, [url, platform, format]);

  // Video info component
  const VideoInfoCard = ({ info }) => {
    if (!info) return null;

    const formatDuration = (seconds) => {
      if (!seconds) return 'Unknown duration';
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = seconds % 60;
      return `${hours ? `${hours}:` : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    };

    const formatDate = (dateStr) => {
      if (!dateStr) return 'Unknown date';
      return new Date(
        dateStr.slice(0, 4) + '-' + 
        dateStr.slice(4, 6) + '-' + 
        dateStr.slice(6, 8)
      ).toLocaleDateString();
    };

    const formatNumber = (num) => {
      if (num === undefined || num === null) return 'Unknown';
      return num.toLocaleString();
    };

    return (
      <StyledVideoCard elevation={8}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {info.thumbnail && (
            <Box sx={{ width: 200, height: 'auto' }}>
              <img 
                src={info.thumbnail} 
                alt={info.title} 
                style={{ 
                  width: '100%', 
                  height: 'auto', 
                  borderRadius: 4,
                  objectFit: 'cover'
                }}
              />
            </Box>
          )}
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" gutterBottom>
              {info.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {info.platform === 'tiktok' ? '@' : 'Channel: '}{info.channel}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Duration: {formatDuration(info.duration)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Views: {formatNumber(info.view_count)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload Date: {formatDate(info.upload_date)}
            </Typography>
            
            {info.platform === 'tiktok' && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Likes: {formatNumber(info.like_count)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Reposts: {formatNumber(info.repost_count)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Comments: {formatNumber(info.comment_count)}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
        {info.description && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ 
              whiteSpace: 'pre-wrap',
              maxHeight: '100px',
              overflow: 'auto'
            }}>
              {info.description}
            </Typography>
          </Box>
        )}
      </StyledVideoCard>
    );
  };

  // Handle download
  const handleDownload = async () => {
    // Input validation
    if (!url) {
      setError('Please enter a URL');
      return;
    }

    const urlError = validateUrl(url);
    if (urlError) {
      setError(urlError);
      return;
    }

    if (!Object.values(PLATFORMS).includes(platform)) {
      setError('Invalid platform selected');
      return;
    }

    if (!Object.values(FORMATS).includes(format)) {
      setError('Invalid format selected');
      return;
    }

    setDownloading(true);
    setError('');
    const response = await api.post('/api/download', {
      url: url.trim(),
      platform: platform.toLowerCase(),
      format: format.toLowerCase()
    });

    const downloadId = response.data.download_id;
    let retryCount = 0;
    const MAX_RETRIES = 3;

    // Set appropriate message based on status
    if (response.data.status === 'in_progress') {
      setMessage('Download already in progress...');
    } else {
      setMessage('Starting download...');
    }
    
    // Poll for progress
    const progressInterval = setInterval(async () => {
      try {
        const progressResponse = await api.get(`/api/progress/${downloadId}`);
        const { status, progress: downloadProgress, message: statusMessage } = progressResponse.data;

        setProgress(downloadProgress || 0);
        setMessage(statusMessage || '');

        if (status === 'completed') {
          clearInterval(progressInterval);
          setDownloading(false);
          setSnackbar({
            open: true,
            message: 'Download completed successfully!',
            severity: 'success'
          });
          // Update the file download URL to match the backend endpoint
          window.location.href = `${api.defaults.baseURL}/api/download/${downloadId}/file`;
        } else if (status === 'error') {
          clearInterval(progressInterval);
          setDownloading(false);
          setError(statusMessage || 'Download failed');
          setSnackbar({
            open: true,
            message: statusMessage || 'Download failed',
            severity: 'error'
          });
        }
      } catch (err) {
        retryCount++;
        console.error('Progress check error:', err);
        
        if (retryCount >= MAX_RETRIES) {
          clearInterval(progressInterval);
          setDownloading(false);
          const errorMessage = err.response?.data?.message || 'Failed to get download progress';
          setError(errorMessage);
          setSnackbar({
            open: true,
            message: errorMessage,
            severity: 'error'
          });
        }
      }
    }, 1000);
  };

  // Handle snackbar close
  const handleSnackbarClose = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleImageChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <StyledContainer maxWidth="md">
        <Typography 
          variant="h3" 
          component="h1" 
          gutterBottom 
          align="center"
          sx={{
            background: 'linear-gradient(45deg, #2196f3, #f50057)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 'bold',
            mb: 4
          }}
        >
          Video Downloader
        </Typography>
        
        <StyledVideoCard elevation={8}>
          <Box component="form" onSubmit={(e) => e.preventDefault()} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Video URL"
              variant="outlined"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              error={!!error}
              helperText={error}
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&:hover fieldset': {
                    borderColor: 'primary.main',
                  },
                },
              }}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Platform</InputLabel>
                <Select
                  value={platform}
                  label="Platform"
                  onChange={(e) => setPlatform(e.target.value)}
                >
                  <MenuItem value={PLATFORMS.YOUTUBE}>YouTube</MenuItem>
                  <MenuItem value={PLATFORMS.TIKTOK}>TikTok</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Format</InputLabel>
                <Select
                  value={format}
                  label="Format"
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <MenuItem value={FORMATS.MP4}>MP4</MenuItem>
                  <MenuItem value={FORMATS.MP3}>MP3</MenuItem>
                </Select>
              </FormControl>
            </Box>

            {loading && (
              <Box sx={{ width: '100%' }}>
                <StyledProgress />
              </Box>
            )}

            {videoInfo && <VideoInfoCard info={videoInfo} />}

            {error && (
              <Alert 
                severity="error" 
                sx={{ 
                  borderRadius: 2,
                  animation: 'shake 0.5s ease-in-out',
                  '@keyframes shake': {
                    '0%, 100%': { transform: 'translateX(0)' },
                    '25%': { transform: 'translateX(-10px)' },
                    '75%': { transform: 'translateX(10px)' },
                  },
                }}
              >
                {error}
              </Alert>
            )}

            <StyledDownloadButton
              variant="contained"
              onClick={handleDownload}
              disabled={downloading || !url || !!error}
              fullWidth
            >
              {downloading ? 'Downloading...' : 'Download'}
            </StyledDownloadButton>

            {downloading && (
              <Box sx={{ width: '100%' }}>
                <StyledProgress variant="determinate" value={progress} />
                <Typography 
                  variant="body2" 
                  color="text.secondary" 
                  align="center" 
                  sx={{ mt: 1, fontWeight: 'medium' }}
                >
                  {message || `Downloading... ${progress}%`}
                </Typography>
              </Box>
            )}
          </Box>
        </StyledVideoCard>

        <Box sx={{ mt: 4 }}>
          <Typography variant="h4" component="h2" gutterBottom sx={{ 
            color: '#fff',
            textAlign: 'center',
            fontWeight: 'bold',
            textShadow: '2px 2px 4px rgba(0,0,0,0.3)'
          }}>
            About Us
          </Typography>
          <Box sx={{ 
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '16px',
            padding: '2rem',
            color: '#fff',
            textAlign: 'center',
            boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
          }}>
            <Typography variant="body1" paragraph sx={{ 
              fontSize: '1.1rem',
              lineHeight: 1.8,
              marginBottom: '1.5rem'
            }}>
              Welcome to our Video Downloader! We provide a simple and efficient way to download your favorite videos from YouTube and TikTok. Our service is designed to be user-friendly and reliable, ensuring you can easily save the content you love.
            </Typography>
            <Typography variant="body1" paragraph sx={{ 
              fontSize: '1.1rem',
              lineHeight: 1.8,
              marginBottom: '1.5rem'
            }}>
              Simply paste the video URL, choose your preferred format, and click download. We support high-quality downloads and various formats to suit your needs. Whether you're looking to save educational content, music videos, or memorable moments, we've got you covered.
            </Typography>
            <Typography variant="body1" sx={{ 
              fontSize: '1.1rem',
              lineHeight: 1.8
            }}>
              Our tool is completely free to use and regularly updated to ensure compatibility with the latest platform changes. Enjoy downloading your favorite content hassle-free!
            </Typography>
          </Box>
        </Box>
      </StyledContainer>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
      >
        <Alert 
          onClose={handleSnackbarClose} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

export default App;
