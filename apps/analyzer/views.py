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
    get_dataset_supported_elements,
    generate_excel_template_bytes,
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

    dataset_elements = get_dataset_supported_elements()
    context = {
        'families': families,
        'active_family': active_family,
        'presets': [p.to_dict() for p in presets],
        'dataset_elements': dataset_elements,
        'dataset_elements_json': json.dumps(dataset_elements),
        'current_section': 'analyzer',
    }
    return render(request, 'analyzer/index.html', context)


from services.prediction.engine import run_prediction, predict_single_spectrum_full


def prediction_results_view(request: HttpRequest) -> HttpResponse:
    """Dedicated multi-spectrum prediction & interactive spectrum editing page."""
    dataset_elements = get_dataset_supported_elements()
    latest_pred = None
    try:
        latest_pred = request.session.get('latest_prediction')
    except Exception:
        latest_pred = None

    context = {
        'dataset_elements': dataset_elements,
        'dataset_elements_json': json.dumps(dataset_elements),
        'initial_prediction_json': json.dumps(latest_pred) if latest_pred else 'null',
        'current_section': 'analyzer',
    }
    return render(request, 'analyzer/results.html', context)


def download_excel_template_api(request: HttpRequest) -> HttpResponse:
    """Serve the standard Excel (.xlsx) template with columns for the dataset's supported elements."""
    xlsx_bytes = generate_excel_template_bytes()
    response = HttpResponse(
        xlsx_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Dhatu_Bodh_EDS_Template.xlsx"'
    return response


@method_decorator(csrf_exempt, name='dispatch')
class ExtractEDSFileAPIView(View):
    """Extract elemental composition from an uploaded Excel/EDS/PDF/DOCX file without running full prediction yet."""

    def post(self, request: HttpRequest) -> JsonResponse:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        uploaded_file = request.FILES['file']
        if uploaded_file.size > 15 * 1024 * 1024:
            return JsonResponse({'error': 'File exceeds maximum size of 15 MB.'}, status=400)
        try:
            file_bytes = uploaded_file.read()
            spectra_list, analysed_elements, meta = extract_all_spectra_from_file(
                file_bytes, uploaded_file.name
            )
            return JsonResponse({
                'status': 'extracted',
                'filename': uploaded_file.name,
                'spectra': spectra_list,
                'analysed_elements': analysed_elements,
                'metadata': meta,
            })
        except Exception as err:
            return JsonResponse({'error': f'Failed to extract composition from file: {str(err)}'}, status=400)


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
        file_meta = {}

        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            source_filename = uploaded_file.name
            source_type = 'file_upload'
            try:
                file_bytes = uploaded_file.read()
                spectra_list, analysed_elements, file_meta = extract_all_spectra_from_file(
                    file_bytes, source_filename
                )
            except Exception as err:
                return JsonResponse({'error': f'Failed to process uploaded file: {str(err)}'}, status=400)
        else:
            try:
                body = json.loads(request.body.decode('utf-8')) if request.body else {}
            except Exception:
                body = {}

            source_filename = body.get('source_filename') if isinstance(body, dict) else None
            if 'spectra' in body and isinstance(body['spectra'], list) and len(body['spectra']) > 0:
                source_type = body.get('source_type') or 'multi_manual_entry'
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
                            'source_type', 'source_filename', 'sample_id', 'customer', 'timestamp',
                            'spectra_details', 'report_metadata'
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
            or file_meta.get('declared_material')
        )
        chemistry = (
            request.GET.get('chemistry')
            or request.POST.get('chemistry')
            or (body.get('chemistry') if isinstance(body, dict) else None)
            or file_meta.get('chemistry')
        )
        surface_coating = (
            request.GET.get('surface_coating')
            or request.POST.get('surface_coating')
            or (body.get('surface_coating') if isinstance(body, dict) else None)
            or file_meta.get('surface_coating')
        )
        location = (
            request.GET.get('location')
            or request.POST.get('location')
            or (body.get('location') if isinstance(body, dict) else None)
            or file_meta.get('location')
        )
        spectra_details = (
            file_meta.get('spectra_details')
            or (body.get('spectra_details') if isinstance(body, dict) else None)
        )
        report_metadata = (
            file_meta.get('report_metadata')
            or (body.get('report_metadata') if isinstance(body, dict) else None)
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
                spectra_details=spectra_details,
                report_metadata=report_metadata,
            )
            result['extracted_spectra'] = spectra_list
            result['extracted_elements'] = analysed_elements
            try:
                request.session['latest_prediction'] = result
            except Exception:
                pass
            return JsonResponse(result)
        except Exception as err:
            return JsonResponse({'error': f'Prediction execution failed: {str(err)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PredictSingleSpectrumAPIView(View):
    """Re-predict a single edited spectrum from the interactive Spectrum Results page."""

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        raw_spec = body.get('spectrum') or body.get('composition') or {}
        spec_index = int(body.get('spectrum_index') or body.get('index') or 1)
        spec_meta = body.get('spectrum_meta') or {
            k: body.get(k)
            for k in ('label', 'siteName', 'site_name', 'page', 'chemistry', 'surface_coating', 'location', 'analysed_elements')
            if body.get(k) is not None
        }
        declared_material = body.get('declared_material')

        clean_spec, analysed_els = clean_numeric_composition(raw_spec, auto_balance_fe=False)
        if not clean_spec:
            return JsonResponse({'error': 'Spectrum must contain at least one positive element wt%.'}, status=400)

        kb = get_kb()
        if not kb:
            return JsonResponse({'error': 'Knowledge base not loaded'}, status=500)

        try:
            spec_result = predict_single_spectrum_full(
                spec=clean_spec,
                spec_index=spec_index,
                spec_meta=spec_meta,
                fallback_elements=analysed_els,
                kb=kb,
                declared_material=declared_material,
                chemistry=spec_meta.get('chemistry'),
                surface_coating=spec_meta.get('surface_coating'),
                location=spec_meta.get('location'),
            )
            # Also update session if latest_prediction exists
            try:
                latest = request.session.get('latest_prediction')
                if isinstance(latest, dict) and isinstance(latest.get('perSpectrum'), list):
                    idx_0 = spec_index - 1
                    if 0 <= idx_0 < len(latest['perSpectrum']):
                        latest['perSpectrum'][idx_0] = spec_result
                        if isinstance(latest.get('allSpectra'), list) and idx_0 < len(latest['allSpectra']):
                            latest['allSpectra'][idx_0] = clean_spec
                        request.session['latest_prediction'] = latest
            except Exception:
                pass

            return JsonResponse({
                'status': 'ok',
                'spectrumResult': spec_result,
                **spec_result,
            })
        except Exception as err:
            return JsonResponse({'error': f'Failed to predict edited spectrum: {str(err)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class IndirectSourcePredictAPIView(View):
    """
    Standalone API endpoint for the Indirect Material Source Rule Engine.
    - GET: Returns all 24 Cleaning Area indirect reference parts, material families, and tolerance rules.
    - POST: Runs two-stage Indirect Material Source prediction (Composition -> Indirect Material Family -> Indirect Part).
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        from indirect_engine.reference_loader import load_indirect_reference
        from indirect_engine.engine import INDIRECT_FAMILY_LABELS

        parts = load_indirect_reference()
        return JsonResponse({
            'status': 'ok',
            'scope': 'Indirect Material Composition - Cleaning Area',
            'totalParts': len(parts),
            'materialFamilies': INDIRECT_FAMILY_LABELS,
            'toleranceRules': [
                {'range': '< 1', 'tolerance': '±25%', 'minFormula': 'Value * 0.75', 'maxFormula': 'Value * 1.25'},
                {'range': '1 to 5 (inclusive)', 'tolerance': '±20%', 'minFormula': 'Value * 0.80', 'maxFormula': 'Value * 1.20'},
                {'range': '> 5', 'tolerance': '±10%', 'minFormula': 'Value * 0.90', 'maxFormula': 'Value * 1.10'},
            ],
            'parts': [p.to_dict() for p in parts],
        })

    def post(self, request: HttpRequest) -> JsonResponse:
        from indirect_engine.engine import predict_indirect_source, predict_indirect_particle

        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        if 'spectra' in body and isinstance(body['spectra'], list) and body['spectra']:
            res = predict_indirect_particle(body['spectra'])
            return JsonResponse(res)

        raw_comp = body.get('composition') or body.get('spectrum') or body.get('elements') or body
        if not isinstance(raw_comp, dict):
            return JsonResponse({'error': 'Composition dictionary is required'}, status=400)

        res = predict_indirect_source(raw_comp)
        return JsonResponse(res)


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
