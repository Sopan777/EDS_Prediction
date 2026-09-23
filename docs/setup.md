# DHATU BODH — Installation & Setup Guide

This guide details the procedure for setting up **DHATU BODH** in both development and production environments.

---

## 1. Prerequisites

- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS 12+
- **Python Runtime**: Python 3.10, 3.11, or 3.12 (64-bit recommended)
- **C Compiler / Build Tools**: Optional (all core dependencies have pre-built wheels)

---

## 2. Environment Setup

### Step 1: Clone or Navigate to the Repository
```bash
git clone <repository-url>
cd EDS_Prediction
```

### Step 2: Create and Activate a Python Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
Install the pinned dependencies:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Verify that key scientific packages are installed:
```bash
python -c "import django, pymupdf, openpyxl, pytest; print('Environment dependencies ready.')"
```

---

## 3. Database Initialization

DHATU BODH uses SQLite (`spectral_lab.db`) by default. Initialize the schema:

```bash
python manage.py migrate
```

Verify that the empirical component fingerprints and reference database are ready:
```bash
python manage.py shell -c "from rule_engine.component_fingerprints import load_fingerprints; fps = load_fingerprints(); print(f'Loaded {len(fps)} empirical fingerprints successfully.')"
```

---

## 4. Running the Development Server

Start the local Django server:
```bash
python manage.py runserver 127.0.0.1:8000
```

Access the application in your browser:
- **Executive Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **EDS Analyzer**: [http://localhost:8000/analyzer/](http://localhost:8000/analyzer/)
- **Knowledge Base**: [http://localhost:8000/knowledge/](http://localhost:8000/knowledge/)
- **Analysis History**: [http://localhost:8000/history/](http://localhost:8000/history/)
- **System Settings**: [http://localhost:8000/settings/](http://localhost:8000/settings/)

---

## 5. Running the Test Suite

Run the full automated test suite using `pytest`:
```bash
pytest tests/ -v
```

To run only the deterministic invariant tests:
```bash
pytest tests/test_scoring_invariance.py -v
```

To run component matching and validation tests:
```bash
pytest tests/test_real_particles.py tests/test_database_persistence.py -v
```

---

## 6. Production Deployment

For enterprise production deployments behind reverse proxies (Nginx / IIS):
1. **WSGI / ASGI Server**: Use `gunicorn` (Linux) or `waitress` (Windows):
   ```bash
   pip install waitress
   waitress-serve --port=8000 config.wsgi:application
   ```
2. **Static Files**: Collect static assets:
   ```bash
   python manage.py collectstatic --noinput
   ```
3. **Environment Variables**:
   - `DEBUG=False`
   - `SECRET_KEY=<strong-random-key>`
   - `ALLOWED_HOSTS=localhost,127.0.0.1,dhatubodh.local`
