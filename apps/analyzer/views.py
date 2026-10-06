import json
import time
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.knowledge.models import AlloyPreset
from services.eds.extractor import (
    extract_all_spectra_from_file,
    clean_numeric_composition,
    HAVE_PDF,
)
from services.prediction.engine import run_prediction
from services.knowledge.kb import get_all_families_mapped, get_kb


def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Executive engineering dashboard displaying real database metrics and recent analyses."""
    from apps.history.models import AnalysisHistory
    from rule_engine.component_fingerprints import load_fingerprints
    
    kb = get_kb()
    fps = load_fingerprints()
    try:
        recent = list(AnalysisHistory.objects.all()[:10])
        total_count = AnalysisHistory.objects.count()
    except Exception:
        try:
            from database import init_db
            init_db()
            recent = list(AnalysisHistory.objects.all()[:10])
            total_count = AnalysisHistory.objects.count()
        except Exception:
            recent = []
            total_count = 0

    context = {
        'recent_analyses': recent,
        'total_analyses': total_count,
        'families_count': len(kb.families) if kb else 12,
        'components_count': len(fps),
        'total_reference_spectra': 171,
        'current_section': 'dashboard',
    }
    return render(request, 'analyzer/dashboard.html', context)


def analyzer_view(request: HttpRequest) -> HttpResponse:
    families = get_all_families_mapped()
    active_family = families[0] if families else None
    try:
        presets = list(AlloyPreset.objects.all())
    except Exception:
        try:
            from database import init_db
            init_db()
            presets = list(AlloyPreset.objects.all())
        except Exception:
            presets = []

    context = {
        'families': families,
        'active_family': active_family,
        'presets': [p.to_dict() for p in presets],
        'current_section': 'analyzer',
    }
    return render(request, 'analyzer/index.html', context)


def health_api(request: HttpRequest) -> JsonResponse:
    kb = get_kb()
    return JsonResponse({
        'status': 'ok',
        'version': '2.4.0',
        'rule_engine': 'deterministic_compatibility_scoring',
        'knowledge_base_loaded': kb is not None,
        'families_count': len(kb.families) if kb else 0,
        'pdf_ingest_available': HAVE_PDF,
        'framework': 'Django 6.1',
    })


@method_decorator(csrf_exempt, name='dispatch')
class AnalyzeAPIView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        spectra_list = []
        analysed_elements = []
        source_filename = None
        source_type = 'manual_entry'
        body = {}

        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            source_filename = uploaded_file.name
            source_type = 'file_upload'
            try:
                file_bytes = uploaded_file.read()
                spectra_list, analysed_elements, meta = extract_all_spectra_from_file(
                    file_bytes, source_filename
                )
            except Exception as err:
                return JsonResponse({'error': f'Failed to process uploaded file: {str(err)}'}, status=400)
        else:
            try:
                body = json.loads(request.body.decode('utf-8')) if request.body else {}
            except Exception:
                body = {}

            if 'spectra' in body and isinstance(body['spectra'], list) and len(body['spectra']) > 0:
                source_type = 'multi_manual_entry'
                elem_set = set()
                for s in body['spectra']:
                    clean_s, el = clean_numeric_composition(s)
                    if clean_s:
                        spectra_list.append(clean_s)
                        elem_set.update(el)
                analysed_elements = sorted(list(elem_set))
            else:
                raw_comp = body.get('composition', body.get('elements', body))
                if isinstance(raw_comp, dict):
                    raw_comp = {
                        k: v for k, v in raw_comp.items()
                        if k not in (
                            'declared_material', 'chemistry', 'surface_coating', 'location',
                            'source_type', 'source_filename', 'sample_id', 'customer', 'timestamp'
                        )
                    }
                source_type = 'manual_entry'
                clean_s, analysed_elements = clean_numeric_composition(raw_comp)
                if clean_s:
                    spectra_list = [clean_s]

        declared_material = (
            request.GET.get('declared_material')
            or request.POST.get('declared_material')
            or (body.get('declared_material') if isinstance(body, dict) else None)
        )
        chemistry = (
            request.GET.get('chemistry')
            or request.POST.get('chemistry')
            or (body.get('chemistry') if isinstance(body, dict) else None)
        )
        surface_coating = (
            request.GET.get('surface_coating')
            or request.POST.get('surface_coating')
            or (body.get('surface_coating') if isinstance(body, dict) else None)
        )
        location = (
            request.GET.get('location')
            or request.POST.get('location')
            or (body.get('location') if isinstance(body, dict) else None)
        )

        if not spectra_list:
            return JsonResponse({'error': 'No valid elemental spectra could be extracted.'}, status=400)

        try:
            result = run_prediction(
                spectra=spectra_list,
                analysed_elements=analysed_elements,
                source_type=source_type,
                source_filename=source_filename,
                declared_material=declared_material,
                chemistry=chemistry,
                surface_coating=surface_coating,
                location=location,
            )
            return JsonResponse(result)
        except Exception as err:
            return JsonResponse({'error': f'Prediction execution failed: {str(err)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class InternalSourcePredictV2APIView(View):
    """Unified v2 endpoint for EDS Internal Source Prediction (Section C & D contract)."""

    def post(self, request: HttpRequest) -> JsonResponse:
        from isp.runtime import predict_internal_source_dict
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({'error': 'Invalid JSON request body'}, status=400)

        particle = body.get('particle', body) if isinstance(body, dict) else {}
        report_info = body.get('report', {}) if isinstance(body, dict) else {}

        raw_spectra = particle.get('spectra', [])
        spectra_inputs = []
        if isinstance(raw_spectra, list) and raw_spectra:
            for item in raw_spectra:
                if isinstance(item, dict):
                    els = item.get('elements', item)
                    clean_s, _ = clean_numeric_composition(els)
                    if clean_s:
                        spectra_inputs.append(clean_s)
        elif isinstance(particle.get('composition') or particle.get('elements'), dict):
            clean_s, _ = clean_numeric_composition(particle.get('composition') or particle.get('elements'))
            if clean_s:
                spectra_inputs.append(clean_s)

        chemistry_raw = particle.get('chemistry') or particle.get('declared_material')
        coating_field = particle.get('surface_coating')
        if isinstance(coating_field, dict):
            surface_coating_raw = coating_field.get('value') or coating_field.get('type')
        else:
            surface_coating_raw = coating_field
        location_raw = particle.get('location')

        if not spectra_inputs and not chemistry_raw:
            return JsonResponse({'error': 'At least one EDS spectrum or chemistry description is required.'}, status=400)

        res = predict_internal_source_dict(
            spectra_inputs=spectra_inputs,
            chemistry_raw=chemistry_raw,
            surface_coating_raw=surface_coating_raw,
            location_raw=location_raw,
            site_uid=str(particle.get('site_uid') or f"site_{particle.get('site_index', 1)}"),
            report_id=str(report_info.get('id') or 'api_report'),
        )
        return JsonResponse(res)


class DataReconciliationAPIView(View):
    """Return the Reference-First Data Reconciliation Report and Secondary Verification summary."""

    def get(self, request: HttpRequest) -> JsonResponse:
        import csv
        from isp.runtime import load_trusted_store, RECONCILIATION_CSV
        store = load_trusted_store()
        rows = []
        if RECONCILIATION_CSV.exists():
            with open(RECONCILIATION_CSV, 'r', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
        return JsonResponse({
            'version': store.get('version'),
            'data_release': store.get('data_release'),
            'secondary_verification_summary': store.get('secondary_verification_summary'),
            'validation_metrics': store.get('validation_metrics'),
            'reconciliation_table': rows,
        })


def list_components_api(request: HttpRequest) -> JsonResponse:
    """Return all canonical components and their fingerprint quality."""
    from rule_engine.component_fingerprints import load_fingerprints
    fps = load_fingerprints()
    components_list = []
    for cid, fp in sorted(fps.items(), key=lambda x: x[1].display_name):
        components_list.append({
            'component_id': fp.component_id,
            'display_name': fp.display_name,
            'family_ids': fp.family_ids,
            'material_body': fp.material_body,
            'sample_count': fp.sample_count,
            'fingerprint_quality': fp.fingerprint_quality,
            'elements_count': len(fp.elements),
            'ratios_count': len(fp.ratios),
        })
    return JsonResponse(components_list, safe=False)


def get_component_detail_api(request: HttpRequest, cid: str) -> JsonResponse:
    """Return full statistical fingerprint for one component."""
    from rule_engine.component_fingerprints import get_fingerprint
    fp = get_fingerprint(cid)
    if not fp:
        return JsonResponse({'error': f'Component {cid} not found'}, status=404)

    elements_dict = {}
    for el, stat in fp.elements.items():
        elements_dict[el] = {
            'median': stat.median,
            'q1': stat.q1,
            'q3': stat.q3,
            'iqr': stat.iqr,
            'mean': stat.mean,
            'std': stat.std,
            'min': stat.min_val,
            'max': stat.max_val,
            'sample_count': stat.sample_count,
            'frequency': stat.frequency,
            'role': stat.role,
        }

    ratios_dict = {}
    for rname, rstat in fp.ratios.items():
        ratios_dict[rname] = {
            'median': rstat.median,
            'q1': rstat.q1,
            'q3': rstat.q3,
            'sample_count': rstat.sample_count,
        }

    return JsonResponse({
        'component_id': fp.component_id,
        'display_name': fp.display_name,
        'family_ids': fp.family_ids,
        'material_body': fp.material_body,
        'sample_count': fp.sample_count,
        'fingerprint_quality': fp.fingerprint_quality,
        'elements': elements_dict,
        'ratios': ratios_dict,
    })


def validation_results_api(request: HttpRequest) -> JsonResponse:
    """Return the leave-one-out validation results."""
    from pathlib import Path
    results_path = Path(__file__).resolve().parent.parent.parent / "validation" / "results" / "loo_results.json"
    if not results_path.exists():
        return JsonResponse({'status': 'pending', 'message': 'Validation has not been executed yet.'})
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class PresetsAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        presets = AlloyPreset.objects.all()
        return JsonResponse([p.to_dict() for p in presets], safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        preset_id = f"preset-{int(time.time() * 1000)}"
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        preset = AlloyPreset.objects.create(
            id=preset_id,
            name=data.get('name', 'Custom Alloy'),
            category=data.get('category', 'Custom'),
            description=data.get('description', ''),
            composition_json=json.dumps(data.get('composition', {})),
            created_by=data.get('created_by', 'Lead Metallurgist'),
            created_at=now_str,
        )
        return JsonResponse({'status': 'created', 'preset': preset.to_dict()})
