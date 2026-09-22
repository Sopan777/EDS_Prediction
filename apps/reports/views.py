import json
import time
from datetime import datetime
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.reports.models import Report
from services.audit.logger import log_event


def reports_view(request: HttpRequest) -> HttpResponse:
    reports = [r.to_dict() for r in Report.objects.all()[:100]]
    context = {
        'reports': reports,
        'current_section': 'reports',
        'top_tab': 'reports',
    }
    return render(request, 'reports/index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class ReportsAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        reports = [r.to_dict() for r in Report.objects.all()[:100]]
        return JsonResponse(reports, safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        report_id = f"RPT-{datetime.now().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = Report.objects.create(
            id=report_id,
            title=data.get('title', f"Microanalysis of {data.get('sample_id', 'Sample')}"),
            sample_id=data.get('sample_id', 'SMP-001'),
            lot_number=data.get('lot_number', 'N/A'),
            customer=data.get('customer', 'Internal Lab'),
            analyst_id=data.get('analyst_id', 'usr-admin'),
            analyst_name=data.get('analyst_name', 'Lead Metallurgist'),
            created_at=now_str,
            source_type=data.get('source_type', 'Manual Entry'),
            source_filename=data.get('source_filename'),
            raw_composition_json=json.dumps(data.get('raw_composition', {})),
            normalized_composition_json=json.dumps(data.get('normalized_composition', [])),
            decision=data.get('decision', 'identified'),
            family_id=data.get('family_id'),
            family_label=data.get('family_label'),
            grade_hint=data.get('grade_hint'),
            compatibility_pct=float(data.get('compatibility_pct', 95.0)),
            candidates_json=json.dumps(data.get('candidates', [])),
            caveats_json=json.dumps(data.get('caveats', [])),
            analyst_notes=data.get('analyst_notes', ''),
            status=data.get('status', 'Completed'),
        )

        log_event(
            user_name=report.analyst_name,
            user_role='Analyst',
            action=f"Created official analysis report '{report_id}' for sample {report.sample_id}",
            action_type='Report Creation',
            entity_id=report_id,
            details={'sample_id': report.sample_id, 'family': report.family_label},
            impact_type='positive',
        )

        return JsonResponse({'status': 'created', 'report_id': report_id, 'report': report.to_dict()})
