"""
tests/test_django_app.py
========================
Automated test suite for Spectral Lab - MaterialID Django full-stack application.
Verifies views, templates, APIs, and microanalysis ingestion.
"""

import json
import os
import pytest
from pathlib import Path

# Ensure DJANGO_SETTINGS_MODULE is set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client

@pytest.fixture
def client():
    return Client()


def test_django_views_render(client):
    """Verify all Django views render HTTP 200."""
    views = [
        '/',
        '/analyzer/',
        '/knowledge/',
        '/gates/F4/',
        '/history/',
        '/users/',
        '/settings/',
        '/reports/',
    ]
    for url in views:
        res = client.get(url)
        assert res.status_code == 200, f"Failed rendering view: {url}"


def test_health_api(client):
    """Verify /api/health endpoint returns expected status."""
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    assert data['knowledge_base_loaded'] is True
    assert data['families_count'] >= 12


def test_families_api(client):
    """Verify /api/families and /api/families/<fid>."""
    res = client.get('/api/families')
    assert res.status_code == 200
    families = res.json()
    assert len(families) >= 12

    # Single family
    res_f4 = client.get('/api/families/F4')
    assert res_f4.status_code == 200
    f4 = res_f4.json()
    assert f4['code'] == 'F4'
    assert len(f4['elementBands']) > 0


def test_manual_analyze_api(client):
    """Verify manual elemental wt% analysis."""
    payload = {
        'composition': {
            'Cr': 18.2,
            'Ni': 8.4,
            'Mn': 1.6,
            'Si': 0.5,
            'Fe': 'Bal.',
        }
    }
    res = client.post('/api/analyze', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'identified'
    assert data['familyCode'] == 'F4'
    assert data['compatibilityPct'] >= 70
    assert len(data['candidateComponents']) > 0


def test_pdf_upload_analyze_api(client):
    """Verify PDF report upload and microanalysis extraction."""
    repo_root = Path(__file__).resolve().parent.parent
    sample_pdf = repo_root / "data" / "reports" / "Field  CRI.I. 26-146 Particle In Z Hole Sr.No-2702 (M&M) ……22.pdf"
    if not sample_pdf.exists():
        pytest.skip("Sample PDF not found")

    with open(sample_pdf, 'rb') as fp:
        res = client.post('/api/analyze', {'file': fp})

    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'identified'
    assert 'Cu' in data['extractedComposition']
    assert data['familyCode'] == 'F6a'
    assert data['isPooled'] is True
    assert data['spectraCount'] == 2
    assert data['topCandidate'] is not None
    assert data['topCandidate']['name'] == 'CRI Sealing ring'
    assert len(data['perSpectrum']) == 2


def test_multi_spectrum_manual_analyze_api(client):
    """Verify multi-spectrum manual payload pools and predicts component."""
    payload = {
        'spectra': [
            {'Cr': 18.5, 'Ni': 8.2, 'Mn': 1.5, 'Si': 0.6, 'Fe': 'Bal.'},
            {'Cr': 18.0, 'Ni': 8.6, 'Mn': 1.6, 'Si': 0.5, 'Fe': 'Bal.'},
        ]
    }
    res = client.post('/api/analyze', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'identified'
    assert data['familyCode'] == 'F4'
    assert data['isPooled'] is True
    assert data['spectraCount'] == 2
    assert data['topCandidate'] is not None
    assert len(data['candidateComponents']) > 0


def test_gates_api_and_validation(client):
    """Verify ratio gates GET, validate, and PUT."""
    # Validate
    val_res = client.post(
        '/api/gates/validate',
        data=json.dumps({'family_code': 'F4', 'gates': [{'min': 1.85, 'max': 2.30, 'enabled': True}]}),
        content_type='application/json',
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert 'passing' in val_data
    assert 'failing' in val_data

    # PUT
    put_res = client.put(
        '/api/gates/F4',
        data=json.dumps({
            'gates': [
                {
                    'id': 'gate-f4-test',
                    'name': 'Cr / Ni',
                    'numerator': 'Cr',
                    'denominator': 'Ni',
                    'min': 1.85,
                    'max': 2.30,
                    'rationale': 'Test gate',
                    'enabled': True,
                }
            ]
        }),
        content_type='application/json',
    )
    assert put_res.status_code == 200
    assert put_res.json()['status'] == 'success'

    # GET
    get_res = client.get('/api/gates?family_id=F4')
    assert get_res.status_code == 200
    gates = get_res.json()['gates']
    assert len(gates) == 1
    assert gates[0]['name'] == 'Cr / Ni'


def test_audit_logs_and_users(client):
    """Verify audit logs and user management APIs."""
    # Audit log
    audit_res = client.post(
        '/api/audit-logs',
        data=json.dumps({
            'user': 'QA Automated Bot',
            'userRole': 'Tester',
            'action': 'Automated regression test event',
            'actionType': 'Calibration',
            'familyCode': 'All',
        }),
        content_type='application/json',
    )
    assert audit_res.status_code == 200

    # User add
    user_res = client.post(
        '/api/users',
        data=json.dumps({
            'name': 'Dr. Alan Grant',
            'email': 'a.grant@spectrallab.io',
            'role': 'Chief Metallurgist',
            'department': 'Failure Analysis',
            'permissions': 'Full Admin',
        }),
        content_type='application/json',
    )
    assert user_res.status_code == 200
    uid = user_res.json()['id']

    # User update
    up_res = client.put(f'/api/users/{uid}', data=json.dumps({'isActive': False}), content_type='application/json')
    assert up_res.status_code == 200
    assert up_res.json()['user']['isActive'] is False
