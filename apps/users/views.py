import json
import time
from datetime import datetime
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from apps.users.models import UserAccount
from apps.knowledge.models import AlloyPreset
from rule_engine.component_fingerprints import load_fingerprints
from services.audit.logger import log_event


def users_view(request: HttpRequest) -> HttpResponse:
    try:
        users = [u.to_dict() for u in UserAccount.objects.all()]
        presets = [p.to_dict() for p in AlloyPreset.objects.all()]
    except Exception:
        try:
            from database import init_db
            init_db()
            users = [u.to_dict() for u in UserAccount.objects.all()]
            presets = [p.to_dict() for p in AlloyPreset.objects.all()]
        except Exception:
            users, presets = [], []
    fps = load_fingerprints()

    active_techs = len([u for u in users if u['role'] == 'Lab Tech' and u['isActive']])
    total_techs = len([u for u in users if u['role'] == 'Lab Tech'])
    metallurgists = len([u for u in users if 'Metallurgist' in u['role']])
    inactive = len([u for u in users if not u['isActive']])

    roles = [
        {'id': 'role-1', 'title': 'Chief Metallurgist', 'description': 'Full access to ASTM calibration & database', 'userCount': metallurgists},
        {'id': 'role-2', 'title': 'Lab Tech', 'description': 'Microanalysis scanning & spectrum ingestion', 'userCount': total_techs},
        {'id': 'role-3', 'title': 'Auditor', 'description': 'Traceability logs & ISO report validation', 'userCount': len([u for u in users if 'Auditor' in u['role']])},
    ]

    context = {
        'users': users,
        'roles': roles,
        'presets': presets,
        'fingerprints_count': len(fps),
        'total_spectra_count': 171,
        'active_techs': active_techs,
        'total_techs': total_techs,
        'metallurgists': metallurgists,
        'inactive': inactive,
        'current_section': 'settings',
        'top_tab': 'dashboard',
    }
    return render(request, 'users/index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class UsersAPIView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        users = [u.to_dict() for u in UserAccount.objects.all()]
        return JsonResponse(users, safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        uid = data.get('id') or f"user-{int(time.time() * 1000)}"
        name = data.get('name', 'New User')
        email = data.get('email', '')
        role = data.get('role', 'Lab Tech')
        department = data.get('department', 'Operations')
        permissions = data.get('permissions', 'Read-only')
        initials = ''.join([p[0] for p in name.split() if p])[:2].upper()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        user = UserAccount.objects.create(
            id=uid,
            name=name,
            email=email,
            role=role,
            department=department,
            permissions=permissions,
            initials=initials,
            is_active=1,
            created_at=now_str,
            last_active='Just now',
        )

        log_event(
            user_name='Lead Metallurgist',
            user_role='Admin',
            action=f'Registered new lab personnel: {name} ({role})',
            action_type='User Edit',
            entity_id=uid,
            details={'name': name, 'email': email, 'role': role},
            impact_type='positive',
        )

        return JsonResponse({'status': 'created', 'id': uid, 'user': user.to_dict()})


@method_decorator(csrf_exempt, name='dispatch')
class UserDetailAPIView(View):
    def put(self, request: HttpRequest, uid: str) -> JsonResponse:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        try:
            user = UserAccount.objects.get(id=uid)
        except UserAccount.DoesNotExist:
            return JsonResponse({'error': f"User '{uid}' not found"}, status=404)

        if 'isActive' in data:
            user.is_active = 1 if data['isActive'] else 0
        if 'role' in data:
            user.role = data['role']
        if 'department' in data:
            user.department = data['department']
        if 'permissions' in data:
            user.permissions = data['permissions']
        user.save()

        log_event(
            user_name='Lead Metallurgist',
            user_role='Admin',
            action=f'Updated permissions/status for user: {user.name}',
            action_type='User Edit',
            entity_id=uid,
            details=data,
            impact_type='neutral',
        )

        return JsonResponse({'status': 'updated', 'id': uid, 'user': user.to_dict()})
