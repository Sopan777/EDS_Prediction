
# WSA (Within Shift Analysis)

## Project Overview
WSA (Within Shift Analysis) is a quality inspection and audit management system developed to manage production audit records, Non-OK (NOK) cases, analytics, observations, and reporting within manufacturing or industrial environments.

The system is designed for:
- Auditors
- Supervisors / Admins
- Quality Management Teams

The application helps organizations:
- Maintain production audit records
- Track NOK parts and rejection cases
- Upload inspection images
- Analyze production quality trends
- Generate reports and downloadable CSV data
- Maintain role-based access control

---

# Key Features

## Authentication & Authorization
- Secure login system
- Separate Admin and User roles
- User registration for supervisors/admins
- Password validation and security constraints
- Session-based authentication

## Admin / Supervisor Features
Admins can:
- Register and login
- Add new audit records
- Edit any record
- Delete records
- Manage NOK cases
- Edit cases created by any user
- View dashboards and analytics
- Download filtered CSV reports

## Auditor / User Features
Users can:
- Login and create records
- Add NOK case details
- Upload images for cases
- View analytics and dashboards
- Edit only their own records and cases
- Cannot delete records
- Cannot edit records created by other users

---

# Record Management

The system allows creation of inspection records containing:
- Date
- Auditor Name
- Type Number
- Parts Checked
- NOK Count
- Shift
- Line Information

Based on the NOK count, the system automatically generates the required number of NOK cases.

---

# NOK Case Management

Each NOK case can contain:
- Rejection Status
- Bin Number
- Particle Location
- Body Details
- Valve Details
- Nozzle Details
- Magnet Details
- Remarks
- Up to 3 Images per Case

This helps in proper defect tracking and root cause analysis.

---

# Dashboard & Analytics

## Dashboard Features
The dashboard provides:
- Daily record statistics
- Weekly statistics
- Monthly statistics
- Auditor-wise statistics
- Shift-wise analysis

## Analytics Features
Advanced filtering available for:
- Shift
- Line
- Auditor
- Type
- Date Range

Visualized charts and graphs are used to analyze:
- Production quality
- Rejection trends
- Auditor performance
- Shift performance

---

# Observations Module
The observations section allows users to:
- View NOK case details
- Apply filters
- Analyze defect observations
- Review rejection information

---

# Download & Reporting

The system supports CSV export functionality:
- Record data only
- Combined Record + NOK case data
- Filtered data export

This helps management in:
- Reporting
- Documentation
- External analysis
- Audit review

---

# Technology Stack

## Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap

## Backend
- Python
- FastAPI

## Database
- SQLite
- Future migration planned to PostgreSQL

## ORM & Security
- SQLAlchemy
- Passlib

## Template Engine
- Jinja2 Templates

## APIs & Validation
- Pydantic

---

# Python Libraries & Frameworks Used

## FastAPI & Backend
```python
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
```

## Database & ORM
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session
```

## Models
```python
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
```

## Authentication
```python
from passlib.context import CryptContext
```

## Validation
```python
from pydantic import BaseModel
```

---

# Project Structure

WSA/
│
├── backend/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
│
├── static/
│   ├── style.css
│   ├── script.js
│   ├── analytics.js
│   ├── dashboard.js
│   ├── records.js
│   └── uploads/
│
├── templates/
│
├── requirements.txt
│
└── README.md

---

# How to Run the Project

## Step 1: Clone the Repository
```bash
git clone <repository-url>
cd WSA
```

## Step 2: Create Virtual Environment
```bash
python -m venv venv
```

## Step 3: Activate Environment

### Windows
```bash
venv\Scripts\activate
```

### Linux / Mac
```bash
source venv/bin/activate
```

## Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 5: Run the Application
```bash
uvicorn backend.main:app --reload
```

## Step 6: Open in Browser
```text
http://127.0.0.1:8000
```

---

# Future Scope

## Planned Improvements
- Migration from SQLite to PostgreSQL
- Cloud deployment support
- Email notification system
- Role-based advanced permissions
- Real-time analytics dashboard
- PDF report generation
- AI-based defect analysis
- Mobile responsive enhancements
- API integration with ERP/MES systems
- Multi-plant support
- Data backup & recovery
- Audit history tracking

---

# Benefits of the Project

- Centralized quality monitoring
- Better production tracking
- Improved defect analysis
- Faster report generation
- Enhanced audit management
- Easy data visualization
- Better accountability through role management

---

# Conclusion

WSA (Within Shift Analysis) is a complete audit and production quality management system developed using FastAPI, Python, SQLAlchemy, HTML, CSS, JavaScript, and Bootstrap.

The project provides a scalable foundation for manufacturing quality inspection systems and can be further expanded using PostgreSQL, advanced analytics, and enterprise integrations.

