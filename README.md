# Algorithm Visualizer Chrome Extension

Convert Python algorithms to Algorithm Visualizer JavaScript with a beautiful Chrome extension UI.

## 🏗️ Project Structure

```
autovis/
├── analyzer.py                 # Code analysis module
├── blueprint_generator.py      # Blueprint generation
├── code_combiner.py           # Code combination
├── indentation_fixer.py       # Indentation normalization
├── translator.py              # Python to JavaScript translation
├── api_server.py              # Flask API server (NEW)
├── requirements.txt           # Python dependencies (NEW)
└── chrome-extension/          # Chrome extension files (NEW)
    ├── manifest.json
    ├── popup.html
    ├── popup.js
    ├── styles.css
    └── icons/
        ├── icon16.png
        ├── icon48.png
        └── icon128.png
```

## 🚀 Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
python api_server.py
```

You should see:
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ALGORITHM VISUALIZER API SERVER                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

🚀 Server starting on http://localhost:5000

📍 Available endpoints:
   GET  /health          - Health check
   POST /api/convert     - Convert Python to JavaScript
   POST /api/analyze     - Analyze Python code only
   GET  /api/examples    - Get example algorithms

💡 Ready to accept requests from Chrome extension
```

### 3. Install Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. The extension icon will appear in your toolbar

### 4. Create Extension Icons (Optional)

Create three icon sizes and place them in `chrome-extension/icons/`:
- `icon16.png` (16x16px)
- `icon48.png` (48x48px)
- `icon128.png` (128x128px)

Or use a simple colored square for testing.

## 📖 Usage

### Using the Chrome Extension

1. **Click the extension icon** in your Chrome toolbar
2. **Paste or type Python code** in the input area
   - Or click "Example" to load sample algorithms
3. **Click "Convert to JavaScript"**
4. **View the results**:
   - Analysis info (arrays detected, visualization type)
   - Generated JavaScript code
5. **Copy or download** the JavaScript code

### Example Workflow

```python
# Input Python code:
def bubbleSort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
```

⬇️ Click "Convert" ⬇️

```javascript
// Output: Fully instrumented JavaScript
const { Array1DTracer, ChartTracer, Layout, LogTracer, ... } = require('algorithm-visualizer');

// ... complete visualization code ready for Algorithm Visualizer
```

## 🎨 Features

### Chrome Extension UI
- ✅ Modern dark theme with smooth animations
- ✅ Real-time input statistics (lines, characters)
- ✅ Server connection status indicator
- ✅ Example algorithms (Bubble Sort, Binary Search, Two Sum, etc.)
- ✅ Code syntax highlighting in output
- ✅ One-click copy to clipboard
- ✅ Download as .js file
- ✅ Detailed analysis information
- ✅ Error handling with clear messages

### Python Pipeline
- ✅ Automatic indentation fixing
- ✅ Smart code analysis (arrays, data structures, patterns)
- ✅ Blueprint generation with proper tracers
- ✅ Python to JavaScript translation
- ✅ Automatic visualization instrumentation
- ✅ Code validation

## 🔧 API Endpoints

### `POST /api/convert`
Convert Python code to JavaScript

**Request:**
```json
{
  "code": "def bubbleSort(arr):\n    ..."
}
```

**Response:**
```json
{
  "success": true,
  "javascript": "const { Array1DTracer, ... }",
  "analysis": {
    "vars_1d": ["arr"],
    "vars_2d": [],
    "viz_type": "sorting",
    "has_sorting": true
  },
  "validation": {
    "has_imports": true,
    "has_layout": true,
    "has_logger": true,
    "has_tracer_delay": true,
    "has_functions": true,
    "no_syntax_errors": true
  }
}
```

### `POST /api/analyze`
Analyze Python code without conversion

### `GET /api/examples`
Get example algorithms

### `GET /health`
Check server status

## 🛠️ Development

### Running Tests
```bash
python test_pipeline.py
```

### Modifying the Extension

1. Make changes to files in `chrome-extension/`
2. Go to `chrome://extensions/`
3. Click the refresh icon on your extension
4. Test your changes

### Modifying the Pipeline

Edit the Python modules:
- `analyzer.py` - Add new pattern detection
- `translator.py` - Improve JavaScript generation
- `blueprint_generator.py` - Enhance tracer setup
- `code_combiner.py` - Refine code combination

## 🎯 Supported Algorithms

- ✅ Sorting (Bubble, Quick, Merge, etc.)
- ✅ Searching (Binary, Linear, etc.)
- ✅ Array manipulation (Two Sum, etc.)
- ✅ Matrix operations
- ✅ Stack/Queue operations
- ✅ Tree traversals
- ✅ Graph algorithms
- ✅ Dynamic programming

## 🐛 Troubleshooting

### "Server Offline" in Extension

**Solution:**
1. Make sure the Flask server is running: `python api_server.py`
2. Check that port 5000 is not in use
3. Verify no firewall is blocking localhost:5000

### CORS Errors

**Solution:** The server has CORS enabled. If you still see errors:
```python
# In api_server.py, modify CORS:
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Extension Not Loading

**Solution:**
1. Check Chrome console (F12) for errors
2. Verify all files are in `chrome-extension/` folder
3. Make sure `manifest.json` is valid JSON
4. Try removing and re-adding the extension

### Conversion Failures

**Solution:**
1. Check Python syntax is valid
2. Look at server console for detailed error messages
3. Try one of the example algorithms first
4. Check that all pipeline modules are in the same directory

## 📦 Distribution

### Package as CRX (Chrome Extension)

1. Go to `chrome://extensions/`
2. Click "Pack extension"
3. Select the `chrome-extension` folder
4. Save the generated `.crx` file

### Deploy API Server

For production use:
```bash
# Use gunicorn for production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- More algorithm patterns
- Better error messages
- Syntax highlighting in input
- Dark/light theme toggle
- Custom server URL configuration
- Batch conversion
- Algorithm templates

## 📝 License

MIT License - Feel free to use and modify

## 🙏 Credits

Built for [Algorithm Visualizer](https://github.com/algorithm-visualizer/algorithm-visualizer)

---

**Made with ❤️ for algorithm learners**