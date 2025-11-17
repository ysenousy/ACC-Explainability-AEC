# IFC Explorer Web App - Quick Start

## 30-Second Setup

### Terminal 1: Start Backend
```bash
pip install flask flask-cors
python -m backend.app
```
✓ Backend runs on `http://localhost:5000`

### Terminal 2: Start Frontend
```bash
cd frontend
npm install
npm start
```
✓ Frontend opens on `http://localhost:3000`

## Using the App

1. Click **"Browse IFC"** button
2. Enter file path (e.g., `C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\AC20-Institute-Var-2.ifc`)
3. View **Preview** (statistics), **Elements** (spaces/doors), or **Rules** (evaluation results)

## Example File Paths

### Windows
```
C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\AC20-Institute-Var-2.ifc
C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\AC20-FZK-Haus.ifc
C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\BasicHouse.ifc
```

### Linux/Mac
```
/home/user/projects/ACC-Explainability-AEC/acc-dataset/IFC/AC20-Institute-Var-2.ifc
```

## What Each Tab Does

### Preview
- Schema type (IFC4, IFC2X3, etc.)
- Element counts (spaces, doors, walls, etc.)
- Per-storey breakdown

### Elements
- Search and filter spaces/doors
- View properties (width, area, storey, connections)
- Sort by any column

### Rules
- Check "Include Manifest Rules" (auto-extracted from IFC)
- Click "Evaluate Rules" to run compliance checks
- Filter results by status (PASS/FAIL) and severity (ERROR/WARNING)

## API Base URL

Both frontend and backend connect via:
```
http://localhost:5000
```

Change in `frontend/package.json` if backend is on different port:
```json
"proxy": "http://localhost:YOUR_PORT"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'flask'` | `pip install flask flask-cors` |
| `Cannot GET /` in browser | Start frontend with `npm start` in `frontend/` folder |
| "CORS error" | Restart both servers (backend first, then frontend) |
| IFC not loading | Check file path exists and is absolute (not relative) |
| Rules not showing | Ensure IFC loaded successfully in Preview tab |

## File Organization

```
project-root/
├── backend/
│   ├── app.py              # Flask API (port 5000)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React app
│   │   ├── components/     # Tab components
│   │   └── index.js        # Entry point
│   └── package.json
└── acc-dataset/IFC/        # Your IFC files
```

## Port Configuration

- **Backend API**: `5000`
- **Frontend App**: `3000`

To change ports:

**Backend** (in `backend/app.py`):
```python
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)  # Change 5000 to 8080
```

**Frontend** (in `frontend/package.json`):
```json
"proxy": "http://localhost:8080"
```

## Next Steps

1. ✅ Start both servers
2. ✅ Load an IFC file
3. ✅ Browse the three tabs
4. ✅ Evaluate rules to test functionality
5. Read `WEB_APP_README.md` for detailed docs and development info
