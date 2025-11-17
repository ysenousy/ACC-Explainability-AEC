# IFC Explorer - Modern Web Application

A modern React web application for browsing IFC files and evaluating compliance rules, with a Flask REST API backend.

## Architecture

```
Frontend (React)
    ↓ HTTP
Backend (Flask REST API)
    ↓
Data Layer + Rule Layer (Python)
    ↓
IFC Model
```

## Features

- **Browse IFC Files**: Load any `.ifc` file from your filesystem
- **Preview Statistics**: View schema, element counts, per-storey breakdown
- **Element Inspector**: Search and filter spaces and doors with their properties
- **Rule Evaluation**: Run compliance rules (built-in + extracted manifest rules)
- **Results Viewer**: Filter and analyze rule evaluation results
- **Modern UI**: Responsive React interface with Tailwind CSS

## Prerequisites

- **Python 3.8+**
- **Node.js 14+** and **npm**
- **ifcopenshell** and other existing dependencies

## Installation

### 1. Backend Setup

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Verify existing data/rule layer dependencies
pip install ifcopenshell jsonschema
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Step 1: Start the Backend API

```bash
# From project root
python -m backend.app
```

The Flask server will start on `http://localhost:5000` and serve API endpoints.

### Step 2: Start the React Frontend

In a new terminal:

```bash
cd frontend
npm start
```

The React app will open on `http://localhost:3000`.

## Usage

1. **Open the App**: Navigate to `http://localhost:3000`
2. **Load IFC File**: Click "Browse IFC" button
3. **Enter File Path**: Provide the absolute path to your `.ifc` file (e.g., `C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\AC20-Institute-Var-2.ifc`)
4. **View Preview**: See model statistics in the "Preview" tab
5. **Inspect Elements**: Browse spaces and doors in the "Elements" tab
6. **Evaluate Rules**: Click "Evaluate Rules" in the "Rules" tab to run compliance checks

## File Structure

```
.
├── backend/
│   ├── app.py                 # Flask REST API
│   └── requirements.txt        # Backend dependencies
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js             # Main React component
│   │   ├── App.css            # Styles
│   │   ├── index.js           # React entry point
│   │   ├── index.css
│   │   └── components/
│   │       ├── PreviewTab.js
│   │       ├── ElementsTab.js
│   │       ├── RulesTab.js
│   │       └── FileUploadModal.js
│   ├── package.json
│   └── package-lock.json
│
├── data_layer/                # Existing
├── rule_layer/                # Existing
└── acc-dataset/               # Existing
```

## API Endpoints

### IFC Loading

- `POST /api/ifc/preview` — Load and preview IFC file
- `POST /api/ifc/graph` — Build canonical data-layer graph

### Elements

- `POST /api/elements/spaces` — Get all spaces from graph
- `POST /api/elements/doors` — Get all doors from graph

### Rules

- `POST /api/rules/evaluate` — Evaluate rules against graph
- `POST /api/rules/manifest` — Get rules manifest from graph

### Health

- `GET /api/health` — API health check

See `backend/app.py` for detailed request/response schemas.

## Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim as backend
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "-m", "backend.app"]
```

Create `docker-compose.yml`:

```yaml
version: '3'
services:
  backend:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./acc-dataset:/app/acc-dataset
    environment:
      - FLASK_ENV=production

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

Run:

```bash
docker-compose up
```

### Production Deployment

For production, use a production WSGI server:

```bash
pip install gunicorn

# Run backend with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

For frontend:

```bash
cd frontend
npm run build
# Serve build/ folder with nginx or static server
```

## Troubleshooting

### "Cannot find module" errors

```bash
# Ensure all dependencies installed
pip install -r backend/requirements.txt
cd frontend && npm install
```

### CORS errors

Backend includes `flask-cors` for cross-origin requests. If issues persist, check:
- Backend is running on port 5000
- Frontend is trying to reach `http://localhost:5000`
- Browser console for specific error messages

### "IFC file not found"

Ensure the path you enter is absolute and the file exists on the server machine.

Examples (Windows):
```
C:\Research Work\ACC-Explainability-AEC\acc-dataset\IFC\AC20-Institute-Var-2.ifc
```

Examples (Linux/Mac):
```
/home/user/projects/ifc/AC20-Institute-Var-2.ifc
```

### Large IFC Files

For very large IFCs (>500 MB), extraction may take time. The UI will show a loading spinner. Server logs (`console output`) will show progress.

## Performance Tips

- **Batch Processing**: Load multiple IFCs via batch scripts (`scripts/extract_manifests.py`) for faster offline analysis
- **Caching**: Results are cached in the browser — refresh if you re-run rules
- **Filters**: Use search and filter controls to focus on specific elements

## Development

### Adding a New Tab

1. Create a new component in `frontend/src/components/MyTab.js`
2. Import it in `App.js`
3. Add a tab button in the navigation
4. Create a corresponding API endpoint in `backend/app.py`

### Adding a New API Endpoint

1. Define the endpoint in `backend/app.py` (e.g., `@app.route("/api/my-endpoint", methods=["POST"])`)
2. Call it from React with `fetch()`:
   ```javascript
   const res = await fetch('/api/my-endpoint', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ data: ... }),
   });
   ```
3. Test via browser or curl:
   ```bash
   curl -X POST http://localhost:5000/api/my-endpoint \
     -H "Content-Type: application/json" \
     -d '{"data": "..."}'
   ```

## Future Enhancements

- [ ] Multi-file batch processing in UI
- [ ] Export results to Excel/PDF
- [ ] 3D IFC viewer integration
- [ ] Authentication and user management
- [ ] Rule creation UI (no-code rule builder)
- [ ] Diff viewer (compare two IFC evaluations)
- [ ] Real-time rule profiling

## License

Same as parent project.
