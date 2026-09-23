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
    recent = list(AnalysisHistory.objects.all()[:10])
    total_count = AnalysisHistory.objects.count()

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
    presets = list(AlloyPreset.objects.all())

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
                        if k not in ('declared_material', 'source_type', 'source_filename', 'sample_id', 'customer', 'timestamp')
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

        if not spectra_list:
            return JsonResponse({'error': 'No valid elemental spectra could be extracted.'}, status=400)

        try:
            result = run_prediction(
                spectra=spectra_list,
                analysed_elements=analysed_elements,
                source_type=source_type,
                source_filename=source_filename,
                declared_material=declared_material,
            )
            return JsonResponse(result)
        except Exception as err:
            return JsonResponse({'error': f'Prediction execution failed: {str(err)}'}, status=500)


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
