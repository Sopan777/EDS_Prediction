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
        '/analyzer/results/',
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
    assert len(data['perSpectrum']) == 1
    assert data['perSpectrum'][0]['familyCode'] == 'F4'


def test_pdf_upload_analyze_api(client):
    """Verify PDF report upload, non-extraction of Mean/Std/Min/Max, and per-spectrum prediction."""
    repo_root = Path(__file__).resolve().parent.parent
    reports_dir = repo_root / "data" / "reports"
    matches_146 = list(reports_dir.glob("*26-146*.pdf"))
    if not matches_146:
        pytest.skip("Sample PDF not found")

    sample_pdf = matches_146[0]
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
    for sp in data['perSpectrum']:
        lbl_lower = (sp.get('label') or '').lower()
        assert 'mean' not in lbl_lower
        assert 'std' not in lbl_lower
        assert 'min' not in lbl_lower
        assert 'max' not in lbl_lower
        assert sp['familyCode'] == 'F6a'
        assert sp['topCandidate']['name'] == 'CRI Sealing ring'
        assert 'Cu' in sp['values']
        assert 'Sn' in sp['values']

    # Also verify multi-site report 26-130 (9 spectra across 3 sites, 0 statistics rows)
    matches_130 = list(reports_dir.glob("*26-130*.pdf"))
    if matches_130:
        with open(matches_130[0], 'rb') as fp:
            res_130 = client.post('/api/analyze', {'file': fp})
        assert res_130.status_code == 200
        d130 = res_130.json()
        assert d130['spectraCount'] == 9
        assert len(d130['perSpectrum']) == 9
        # First 7 spectra (Site 1: 4 spectra, Site 2: 3 spectra) are F1 steel; last 2 spectra (Site 4 Ball Damage) are unknown
        for idx, sp in enumerate(d130['perSpectrum']):
            lbl_lower = (sp.get('label') or '').lower()
            assert not any(stat in lbl_lower for stat in ('mean', 'std', 'min', 'max'))
            if idx < 7:
                assert sp['familyCode'].startswith('F1')
                assert sp['topCandidate'] is not None
            else:
                assert sp['decision'] == 'unknown'

    # Also verify multi-site report 26-108 (5 spectra across 2 sites, 0 statistics rows)
    matches_108 = list(reports_dir.glob("*26-108*.pdf"))
    if matches_108:
        with open(matches_108[0], 'rb') as fp:
            res_108 = client.post('/api/analyze', {'file': fp})
        assert res_108.status_code == 200
        d108 = res_108.json()
        assert d108['spectraCount'] == 5
        assert len(d108['perSpectrum']) == 5
        assert d108['perSpectrum'][0]['familyCode'] == 'F1a'
        assert d108['perSpectrum'][1]['familyCode'] == 'F1a'
        assert d108['perSpectrum'][2]['familyCode'] == 'F1a'
        assert d108['perSpectrum'][3]['familyCode'] == 'F1b'
        assert d108['perSpectrum'][4]['familyCode'] == 'F1b'


def test_predict_single_spectrum_edit_api(client):
    """Verify /api/predict-spectrum live re-prediction when user edits spectrum values."""
    payload = {
        'index': 1,
        'label': 'Site of Interest 1 — Spectrum 1 (Edited)',
        'siteName': 'Site of Interest 1',
        'page': 2,
        'composition': {
            'Cr': 1.48,
            'Mn': 0.35,
            'Si': 0.25,
            'Fe': 97.92,
        },
        'analysed_elements': ['Cr', 'Mn', 'Si', 'Fe'],
    }
    res = client.post('/api/predict-spectrum', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 200
    sp = res.json()
    assert sp['index'] == 1
    assert sp['familyCode'] == 'F2'
    assert sp['decision'] in ('identified', 'ambiguous')
    assert sp['topCandidate'] is not None
    assert len(sp['candidateComponents']) > 0
    assert len(sp['compositionBreakdown']) > 0


def test_multi_spectrum_manual_analyze_api(client):
    """Verify multi-spectrum manual payload pools and predicts component for every spectrum."""
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
    assert len(data['perSpectrum']) == 2
    for sp in data['perSpectrum']:
        assert sp['familyCode'] == 'F4'
        assert sp['topCandidate'] is not None


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
