# LogInsight AI - Frontend UI

A modern, professional web interface for LogInsight AI - Intelligent Log Analysis powered by Groq LLM.

## 🎨 Design Features

- **Modern & Clean UI** - Professional design that's intuitive and easy to use
- **Dark Mode Support** - Toggle between light and dark themes
- **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- **Real-time Feedback** - Visual indicators for upload status and analysis progress
- **Drag & Drop Support** - Easy file upload with drag-and-drop functionality
- **History Tracking** - Quick access to past analyses
- **Export Options** - Copy results or download as JSON

## 🚀 Quick Start

### Prerequisites

- FastAPI backend running on `http://localhost:8000`
- Modern web browser

### Running the UI

The frontend is automatically served by the FastAPI backend. Simply:

1. Start the FastAPI server:
```bash
uvicorn api.main:app --reload
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## 📁 File Structure

```
frontend/
├── index.html       # Main HTML template
├── style.css        # Styling and layout
└── app.js          # JavaScript functionality
```

## 🎯 Key Features

### Upload Section
- Drag and drop or click to browse
- Supports `.log`, `.txt`, and `.json` files
- File size and name display
- Clear visual feedback

### Analysis Results
- **Summary**: AI-generated insight of the issues
- **Issues Detected**: Categorized list with severity levels and occurrence counts
- **Suggested Fixes**: Actionable remediation steps for each issue
- Sample messages from logs for context

### History
- View recent analyses
- Click to reload past analyses
- Quick status indicators

### Export
- **Copy Results**: Copy formatted text to clipboard
- **Download Report**: Export full analysis as JSON

## 🎨 Color Scheme

### Light Mode
- Background: Clean white
- Accents: Indigo gradients
- Text: Dark grays
- Highlights: Success green, Error red, Warning amber

### Dark Mode
- Background: Deep slate
- Accents: Light indigo
- Text: Light grays
- Highlights: Bright greens, reds, and ambers

## 📱 Responsive Breakpoints

- Desktop: Full layout with all features
- Tablet: Optimized grid layout
- Mobile: Single column, touch-friendly buttons

## 🔌 API Integration

The frontend communicates with the FastAPI backend using these endpoints:

- `POST /analyze` - Submit a log file for analysis
- `GET /results/{job_id}` - Retrieve past analysis
- `GET /history` - Get list of recent analyses
- `GET /health` - Health check

## 🛠️ Customization

### Modifying Styles
Edit `style.css` to customize colors, spacing, and typography:
- CSS Variables in `:root` for theme colors
- `data-theme="dark"` selector for dark mode styles

### Adding Features
Extend `app.js` to add new functionality:
- Event listeners are in `setupEventListeners()`
- API calls in dedicated functions
- Toast notifications for user feedback

## 🐛 Known Limitations

- Requires backend API to be running
- Browser must have fetch API support
- Large files (>50MB) may time out

## 📝 Tips for Users

1. **For best results**: Keep log files under 10MB
2. **Supported formats**: Syslog, Apache/Nginx logs, JSON, generic text logs
3. **History**: Analyses are saved for future reference
4. **Offline**: Frontend requires active API connection
5. **Theme**: Your theme preference is saved automatically

## 🎓 Browser Support

- Chrome/Edge: ✅ Latest versions
- Firefox: ✅ Latest versions
- Safari: ✅ Latest versions
- Mobile browsers: ✅ Safari iOS, Chrome Android

---

**Built with ❤️ for better log analysis**
