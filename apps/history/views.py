import json
import time
from datetime import datetime
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.history.models import AuditLog, AnalysisHistory
from apps.feedback.models import PredictionFeedback
from apps.analyzer.views import _reconstruct_full_result_from_history_record
from services.eds.extractor import get_dataset_supported_elements
from services.audit.logger import log_event, get_audit_logs


def history_view(request: HttpRequest) -> HttpResponse:
    try:
        from database import init_db, get_connection
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(analysis_history)")
            cols = {row[1] for row in cur.fetchall()}
            if "full_result_json" not in cols:
                cur.execute("ALTER TABLE analysis_history ADD COLUMN full_result_json TEXT")
                conn.commit()
            conn.close()
        except Exception:
            init_db()

        logs = [l.to_frontend_dict() for l in AuditLog.objects.all()[:200]]
        history_records = list(AnalysisHistory.objects.all()[:100])
        feedback_records = list(PredictionFeedback.objects.all()[:100])
    except Exception:
        try:
            from database import init_db
            init_db()
            logs = [l.to_frontend_dict() for l in AuditLog.objects.all()[:200]]
            history_records = list(AnalysisHistory.objects.all()[:100])
            feedback_records = list(PredictionFeedback.objects.all()[:100])
        except Exception:
            logs, history_records, feedback_records = [], [], []

    history_payloads = []
    for rec in history_records:
        try:
            payload = _reconstruct_full_result_from_history_record(rec)
            payload['analysisId'] = rec.id
            payload['timestamp'] = rec.timestamp
            payload['sourceFilename'] = rec.filename or rec.source_type or 'Saved Analysis Run'
            history_payloads.append(payload)
        except Exception:
            pass

    selected_id = request.GET.get('id') or (history_payloads[0]['analysisId'] if history_payloads else None)
    selected_payload = None
    for p in history_payloads:
        if p.get('analysisId') == selected_id:
            selected_payload = p
            break
    if not selected_payload and history_payloads:
        selected_payload = history_payloads[0]

    dataset_elements = get_dataset_supported_elements()
    users = sorted(list(set(l['user'] for l in logs)))
    action_types = sorted(list(set(l['actionType'] for l in logs)))
    families = sorted(list(set(l['familyCode'] for l in logs if l['familyCode'] != 'All')))

    context = {
        'logs': logs,
        'history_records': history_records,
        'history_payloads_json': json.dumps(history_payloads),
        'selected_prediction_json': json.dumps(selected_payload) if selected_payload else 'null',
        'selected_history_id': selected_id or '',
        'dataset_elements': dataset_elements,
        'dataset_elements_json': json.dumps(dataset_elements),
        'feedback_records': feedback_records,
        'users': users,
        'action_types': action_types,
        'families': families,
        'current_section': 'history',
        'top_tab': 'archive',
    }
    return render(request, 'history/index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class AuditLogsAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        action_type = request.GET.get('action_type')
        limit = int(request.GET.get('limit', 200))
        logs = get_audit_logs(action_type=action_type, limit=limit)
        return JsonResponse(logs, safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            entry = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        new_id = entry.get('id') or f"audit-{int(time.time()*1000)}"
        user = entry.get('user', 'Lab Operator')
        user_role = entry.get('userRole', 'Metallurgist')
        action = entry.get('action', 'General System Event')
        action_type = entry.get('actionType', 'Calibration')
        family_code = entry.get('familyCode', 'All')
        change_details = entry.get('changeDetails', {})
        impact_type = entry.get('impactType', 'neutral')

        log_id = log_event(
            user_name=user,
            user_role=user_role,
            action=action,
            action_type=action_type,
            entity_id=family_code,
            details=change_details,
            impact_type=impact_type,
        )
        return JsonResponse({'status': 'created', 'id': log_id})


class AnalysisHistoryAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        history_id = request.GET.get('id')
        if history_id:
            rec = AnalysisHistory.objects.filter(id=history_id).first()
            if not rec:
                return JsonResponse({'error': 'Analysis history record not found'}, status=404)
            return JsonResponse(_reconstruct_full_result_from_history_record(rec))

        records = AnalysisHistory.objects.all()[:100]
        data = []
        for r in records:
            full_res = _reconstruct_full_result_from_history_record(r)
            data.append({
                'id': r.id,
                'timestamp': r.timestamp,
                'source_type': r.source_type,
                'filename': r.filename,
                'composition': r.get_composition(),
                'decision': r.decision,
                'material_family': r.material_family,
                'grade_hint': r.grade_hint,
                'compatibility': r.compatibility_pct,
                'candidates': r.get_candidates(),
                'top_component': r.top_component_name,
                'top_indirect_source': r.top_indirect_source_name,
                'spectra_count': r.spectra_count,
                'processing_time_s': r.processing_time_s,
                'full_result': full_res,
            })
        return JsonResponse(data, safe=False)

