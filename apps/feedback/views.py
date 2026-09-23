import json
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.feedback.models import PredictionFeedback
from database import save_feedback, get_all_feedback
from services.audit.logger import log_event


@method_decorator(csrf_exempt, name='dispatch')
class FeedbackAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        items = get_all_feedback(limit=100)
        return JsonResponse(items, safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        predicted_family = body.get('predicted_family') or body.get('materialFamily', 'Unknown')
        confirmed_family = body.get('confirmed_family') or predicted_family
        confirmed_component = body.get('confirmed_component') or body.get('componentName', 'Unknown')
        spectrum = body.get('spectrum') or body.get('composition', {})
        predicted_component = body.get('predicted_component')
        analysis_id = body.get('analysis_id')
        status = body.get('status', 'confirmed')
        analyst_name = body.get('analyst_name', 'Lead Metallurgist')
        notes = body.get('notes', '')

        if not confirmed_family or not confirmed_component:
            return JsonResponse({'error': 'confirmed_family and confirmed_component are required'}, status=400)

        feedback_id = save_feedback(
            predicted_family=predicted_family,
            confirmed_family=confirmed_family,
            confirmed_component=confirmed_component,
            spectrum=spectrum,
            predicted_component=predicted_component,
            analysis_id=analysis_id,
            status=status,
            analyst_name=analyst_name,
            notes=notes,
        )

        log_event(
            user_name=analyst_name,
            user_role="Snr. Metallurgist",
            action=f"Prediction Feedback logged: {status.upper()} {confirmed_component} ({confirmed_family})",
            action_type="Feedback",
            entity_id=feedback_id,
            details={
                "predicted_family": predicted_family,
                "confirmed_family": confirmed_family,
                "confirmed_component": confirmed_component,
                "status": status,
            },
            impact_type="positive" if status == "confirmed" else "neutral",
        )

        return JsonResponse({
            'status': 'success',
            'feedback_id': feedback_id,
            'message': f'Feedback registered as {status}.',
        })
