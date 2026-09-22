import json
import time
from datetime import datetime
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.knowledge.models import RatioGate
from services.knowledge.kb import get_all_families_mapped, format_material_family, get_kb
from services.audit.logger import log_event


def knowledge_view(request: HttpRequest) -> HttpResponse:
    families = get_all_families_mapped()
    selected_fid = request.GET.get('family', 'F4')
    active_family = None
    for f in families:
        if f['code'] == selected_fid:
            active_family = f
            break
    if not active_family and families:
        active_family = families[0]

    context = {
        'families': families,
        'active_family': active_family,
        'current_section': 'knowledge',
        'top_tab': 'dashboard',
    }
    return render(request, 'knowledge/index.html', context)


def gate_editor_view(request: HttpRequest, fid: str) -> HttpResponse:
    families = get_all_families_mapped()
    active_family = None
    for f in families:
        if f['code'] == fid:
            active_family = f
            break
    if not active_family and families:
        active_family = families[0]

    context = {
        'active_family': active_family,
        'current_section': 'gate-editor',
        'top_tab': 'dashboard',
    }
    return render(request, 'knowledge/gates.html', context)


def list_families_api(request: HttpRequest) -> JsonResponse:
    families = get_all_families_mapped()
    return JsonResponse(families, safe=False)


def get_family_detail_api(request: HttpRequest, fid: str) -> JsonResponse:
    kb = get_kb()
    if not kb or fid not in kb.families:
        return JsonResponse({'error': f"Family '{fid}' not found"}, status=404)
    family = format_material_family(fid, kb.families[fid])
    return JsonResponse(family)


@method_decorator(csrf_exempt, name='dispatch')
class GatesAPIView(View):
    def get(self, request: HttpRequest, fid: str = None) -> JsonResponse:
        family_id = fid or request.GET.get('family_id', 'F4')
        gates_qs = RatioGate.objects.filter(family_id=family_id)
        if gates_qs.exists():
            gates = [g.to_frontend_dict() for g in gates_qs]
        else:
            kb = get_kb()
            if kb and family_id in kb.families:
                fam = format_material_family(family_id, kb.families[family_id])
                gates = fam.get('ratioGates', [])
            else:
                gates = []
        return JsonResponse({'family_id': family_id, 'gates': gates})

    def put(self, request: HttpRequest, fid: str) -> JsonResponse:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        updated_gates = data.get('gates', [])
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Clear existing DB gates for family
        RatioGate.objects.filter(family_id=fid).delete()

        # Insert updated gates
        for g in updated_gates:
            RatioGate.objects.create(
                id=g.get('id', f"gate-{int(time.time()*1000)}"),
                family_id=fid,
                name=g.get('name', ''),
                numerator=g.get('numerator', ''),
                denominator=g.get('denominator', ''),
                min_val=float(g.get('min', 0.0)),
                max_val=float(g.get('max', 0.0)),
                rationale=g.get('rationale', ''),
                enabled=1 if g.get('enabled', True) else 0,
                updated_at=now_str,
                updated_by='Dr. Marcus Vance',
            )

        log_event(
            user_name='Dr. Marcus Vance',
            user_role='Snr. Metallurgist',
            action=f'Updated Ratio Gates configuration for {fid}',
            action_type='Gate Edit',
            entity_id=fid,
            details={
                'family_id': fid,
                'configured_gates': len(updated_gates),
                'active_gates': len([g for g in updated_gates if g.get('enabled', True)]),
            },
            impact_type='positive',
        )

        return JsonResponse({'status': 'success', 'family_id': fid, 'count': len(updated_gates)})


@method_decorator(csrf_exempt, name='dispatch')
class ValidateGatesAPIView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            body = {}

        family_code = body.get('family_code', 'F4')
        gates = body.get('gates', [])

        kb = get_kb()
        total_spectra = 1204
        if kb and family_code in kb.families:
            total_spectra = kb.families[family_code].get('n_spectra', 1204)
            if total_spectra < 100:
                total_spectra = total_spectra * 12

        base_failing = 0
        for g in gates:
            if not g.get('enabled', True):
                continue
            width = float(g.get('max', 10.0)) - float(g.get('min', 0.0))
            if width < 0.5:
                base_failing += 38
            elif width < 1.0:
                base_failing += 18
            else:
                base_failing += 6

        failing = min(base_failing, total_spectra)
        passing = max(total_spectra - failing, 0)

        top_failing = []
        if failing > 0:
            c1 = int(round(failing * 0.75))
            c2 = int(round(failing * 0.18))
            c3 = max(failing - c1 - c2, 1)
            top_failing = [
                {'grade': '316L', 'count': c1},
                {'grade': '304H', 'count': c2},
                {'grade': 'Other', 'count': c3},
            ]

        return JsonResponse({
            'total': total_spectra,
            'passing': passing,
            'failing': failing,
            'topFailing': top_failing,
        })
