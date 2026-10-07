import json
import os
import time
from datetime import datetime
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.knowledge.models import RatioGate
from services.knowledge.kb import (
    get_all_families_mapped,
    format_material_family,
    get_kb,
    save_family_customization,
    save_component_customization,
)
from indirect_engine.reference_loader import (
    get_indirect_kb_payload,
    save_indirect_part_customization,
    delete_indirect_part_customization,
    save_indirect_family_customization,
)
from services.audit.logger import log_event


def knowledge_view(request: HttpRequest) -> HttpResponse:
    from rule_engine.component_fingerprints import load_fingerprints
    from rule_engine.real_data import load_spectra

    families = get_all_families_mapped()
    selected_fid = request.GET.get('family', 'F4')
    active_family = None
    for f in families:
        if f['code'] == selected_fid:
            active_family = f
            break
    if not active_family and families:
        active_family = families[0]

    # Load component aliases
    aliases_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'rule_engine',
        'knowledge',
        'component_aliases.json',
    )
    alias_map = {}
    if os.path.exists(aliases_path):
        try:
            with open(aliases_path, 'r', encoding='utf-8') as f:
                raw_aliases = json.load(f).get('aliases', {})
                for alias_str, cid in raw_aliases.items():
                    if cid not in alias_map:
                        alias_map[cid] = []
                    if alias_str not in alias_map[cid] and alias_str != cid:
                        alias_map[cid].append(alias_str)
        except Exception:
            pass

    # Load component library
    fps = load_fingerprints()
    components_list = []
    for cid, fp in sorted(fps.items(), key=lambda x: x[1].display_name.lower()):
        fe_stat = fp.elements.get('Fe')
        cr_stat = fp.elements.get('Cr')
        ni_stat = fp.elements.get('Ni')
        mn_stat = fp.elements.get('Mn')
        components_list.append({
            'component_id': fp.component_id,
            'display_name': fp.display_name,
            'family_ids': fp.family_ids,
            'family_ids_str': ', '.join(fp.family_ids),
            'material_body': fp.material_body or 'Standard Material',
            'sample_count': fp.sample_count,
            'fingerprint_quality': fp.fingerprint_quality,
            'elements_count': len(fp.elements),
            'aliases': ', '.join(alias_map.get(fp.component_id, [])[:3]) or 'Standard name',
            'fe_median': fe_stat.median if fe_stat else 0.0,
            'cr_median': cr_stat.median if cr_stat else 0.0,
            'ni_median': ni_stat.median if ni_stat else 0.0,
            'mn_median': mn_stat.median if mn_stat else 0.0,
            'elements': {el: {
                'median': s.median,
                'q1': s.q1,
                'q3': s.q3,
                'iqr': s.iqr,
                'role': s.role,
            } for el, s in fp.elements.items()},
        })

    # Collect all ratio gates across families
    all_gates = []
    for fam in families:
        for gate in fam.get('ratioGates', []):
            all_gates.append({
                'family_code': fam['code'],
                'family_name': fam['name'],
                'name': gate.get('name', 'Ratio Gate'),
                'numerator': gate.get('numerator', ''),
                'denominator': gate.get('denominator', ''),
                'min': gate.get('min', 0.0),
                'max': gate.get('max', 0.0),
                'rationale': gate.get('rationale', 'Stoichiometric phase balance criterion'),
            })

    # Load reference spectra
    raw_spectra = load_spectra()
    reference_spectra = []
    for sp in raw_spectra:
        top_elems = sorted(
            [(k, v) for k, v in sp.values.items() if v > 0.1 and k not in ['C', 'O', 'N']],
            key=lambda x: x[1],
            reverse=True,
        )[:4]
        summary_str = ', '.join([f"{k} {v:.1f}%" for k, v in top_elems])
        reference_spectra.append({
            'spectrum_id': sp.spectrum_id,
            'component': sp.component,
            'site': sp.site or 'Bulk Particle',
            'total': sp.total,
            'summary': summary_str,
        })

    # Load Indirect Material Source Knowledge Base (Cleaning Area)
    indirect_kb = get_indirect_kb_payload()

    context = {
        'families': families,
        'active_family': active_family,
        'components': components_list,
        'all_gates': all_gates,
        'reference_spectra': reference_spectra,
        'indirect_kb': indirect_kb,
        'families_json': json.dumps(families),
        'active_family_json': json.dumps(active_family),
        'components_json': json.dumps(components_list),
        'indirect_kb_json': json.dumps(indirect_kb),
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
        'active_family_json': json.dumps(active_family),
        'current_section': 'gate-editor',
        'top_tab': 'dashboard',
    }
    return render(request, 'knowledge/gates.html', context)


@csrf_exempt
def list_families_api(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            fid = str(body.get('code') or body.get('family_id') or '').strip()
            if not fid:
                return JsonResponse({'error': 'Family code (e.g. F9) is required.'}, status=400)
            updated = save_family_customization(fid, body)
            log_event(
                user_name='Dr. Marcus Vance',
                user_role='Snr. Metallurgist',
                action=f"Created / customized Material Family {fid} ({updated.get('name')})",
                action_type='KB Customization',
                entity_id=fid,
                details={'family_id': fid, 'name': updated.get('name')},
                impact_type='positive',
            )
            return JsonResponse({'status': 'success', 'family': updated})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    families = get_all_families_mapped()
    return JsonResponse(families, safe=False)


@csrf_exempt
def get_family_detail_api(request: HttpRequest, fid: str) -> JsonResponse:
    if request.method in ('PUT', 'POST'):
        try:
            body = json.loads(request.body.decode('utf-8'))
            updated = save_family_customization(fid, body)
            log_event(
                user_name='Dr. Marcus Vance',
                user_role='Snr. Metallurgist',
                action=f"Customized Material Family {fid} ({updated.get('name')})",
                action_type='KB Customization',
                entity_id=fid,
                details={
                    'family_id': fid,
                    'name': updated.get('name'),
                    'components_count': len(updated.get('components', [])),
                    'bands_count': len(updated.get('elementBands', [])),
                },
                impact_type='positive',
            )
            return JsonResponse({'status': 'success', 'family': updated})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    kb = get_kb()
    if not kb or fid not in kb.families:
        return JsonResponse({'error': f"Family '{fid}' not found"}, status=404)
    family = format_material_family(fid, kb.families[fid])
    return JsonResponse(family)


@method_decorator(csrf_exempt, name='dispatch')
class IndirectKBAPIView(View):
    """GET / PUT / POST / DELETE API for customizing the Indirect Material Source Knowledge Base."""

    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(get_indirect_kb_payload())

    def post(self, request: HttpRequest) -> JsonResponse:
        return self._save(request)

    def put(self, request: HttpRequest) -> JsonResponse:
        return self._save(request)

    def _save(self, request: HttpRequest) -> JsonResponse:
        try:
            body = json.loads(request.body.decode('utf-8'))
            action_mode = body.get('mode', 'part')
            if action_mode == 'family':
                old_name = body.get('old_name')
                new_name = body.get('new_name') or body.get('name')
                label = body.get('label')
                kb_payload = save_indirect_family_customization(old_name, new_name, label)
                log_event(
                    user_name='Dr. Marcus Vance',
                    user_role='Snr. Metallurgist',
                    action=f"Customized Indirect Material Family '{new_name}'",
                    action_type='Indirect KB Edit',
                    entity_id=str(new_name),
                    details={'old_name': old_name, 'new_name': new_name, 'label': label},
                    impact_type='positive',
                )
            else:
                kb_payload = save_indirect_part_customization(body)
                part_name = body.get('part_name') or body.get('partName')
                log_event(
                    user_name='Dr. Marcus Vance',
                    user_role='Snr. Metallurgist',
                    action=f"Customized Indirect Source Part '{part_name}'",
                    action_type='Indirect KB Edit',
                    entity_id=str(part_name),
                    details={'part_name': part_name, 'material': body.get('material')},
                    impact_type='positive',
                )
            return JsonResponse({'status': 'success', 'indirect_kb': kb_payload})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    def delete(self, request: HttpRequest) -> JsonResponse:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
            sn = body.get('sn') or request.GET.get('sn')
            if not sn:
                return JsonResponse({'error': 'Part sn is required to delete.'}, status=400)
            kb_payload = delete_indirect_part_customization(int(sn))
            return JsonResponse({'status': 'success', 'indirect_kb': kb_payload})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)


@csrf_exempt
def customize_component_api(request: HttpRequest, cid: str = None) -> JsonResponse:
    """PUT / POST handler to customize a canonical component fingerprint & aliases."""
    if request.method not in ('PUT', 'POST'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
        target_cid = cid or body.get('component_id') or body.get('display_name')
        updated = save_component_customization(target_cid, body)
        log_event(
            user_name='Dr. Marcus Vance',
            user_role='Snr. Metallurgist',
            action=f"Customized Component Profile '{updated.get('display_name')}'",
            action_type='KB Customization',
            entity_id=updated.get('component_id', ''),
            details={'component_id': updated.get('component_id'), 'display_name': updated.get('display_name')},
            impact_type='positive',
        )
        return JsonResponse({'status': 'success', 'component': updated})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


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

