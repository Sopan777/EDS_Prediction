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
from services.audit.logger import log_event, get_audit_logs


def history_view(request: HttpRequest) -> HttpResponse:
    logs = [l.to_frontend_dict() for l in AuditLog.objects.all()[:200]]
    history_records = list(AnalysisHistory.objects.all()[:100])
    feedback_records = list(PredictionFeedback.objects.all()[:100])

    users = sorted(list(set(l['user'] for l in logs)))
    action_types = sorted(list(set(l['actionType'] for l in logs)))
    families = sorted(list(set(l['familyCode'] for l in logs if l['familyCode'] != 'All')))

    context = {
        'logs': logs,
        'history_records': history_records,
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
        records = AnalysisHistory.objects.all()[:100]
        data = []
        for r in records:
            data.append({
                'id': r.id,
                'timestamp': r.timestamp,
                'source_type': r.source_type,
                'filename': r.filename,
                'composition': r.get_composition(),
                'decision': r.decision,
                'material_family': r.material_family,
                'grade_hint': r.grade_hint,
                'compatibility': r.compatibility,
                'candidates': r.get_candidates(),
                'processing_time_s': r.processing_time_s,
            })
        return JsonResponse(data, safe=False)
