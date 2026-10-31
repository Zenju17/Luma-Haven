"""Admin CMS (company) and Developer Console endpoints (P3).

Everything lives under /api/v1/admin/ so the portal middleware selects the admin session cookie.
Role matrix: ADMIN = all CMS + read-only developer views; CONTENT_EDITOR = CMS drafts only;
DEVELOPER = developer console (read/write) and nothing that exposes guest PII.
"""
import platform
import re
import time
from datetime import timedelta

import django
from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import path
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from . import flags
from .models import (Audit, CmsBlock, CmsPage, CmsRevision, ErrorEvent, FeatureFlag, JobRun, Outbox,
                     PaymentAttempt, User)
from .views import staff

SLUG = re.compile(r'^[a-z0-9]+(?:[-.][a-z0-9]+)*$')  # block keys may contain dots
PAGE_SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
LANGS = ('en', 'km')
CMS_EDIT = ('ADMIN', 'CONTENT_EDITOR')
CMS_PUBLISH = ('ADMIN',)
DEV_READ = ('DEVELOPER', 'ADMIN')
DEV_WRITE = ('DEVELOPER',)


def _actor(request):
    return request.user.username


def _lang(value):
    if value not in LANGS:
        raise ValidationError({'language': 'Language must be en or km.'})
    return value


# ---------------------------------------------------------------- public CMS

def _fallback(model, lang, **lookup):
    qs = model.objects.filter(is_published=True, **lookup)
    return qs.filter(language=lang).first() or qs.filter(language='en').first()


@api_view(['GET'])
def cms_public_page(request, slug):
    lang = request.query_params.get('lang', 'en')
    page = _fallback(CmsPage, lang if lang in LANGS else 'en', slug=slug)
    if not page:
        raise NotFound('Page not found')
    return Response({'slug': page.slug, 'language': page.language, 'title': page.published_title,
                     'body_markdown': page.published_body, 'seo_description': page.published_seo_description,
                     'published_at': page.published_at})


@api_view(['GET'])
def cms_public_blocks(request):
    lang = request.query_params.get('lang', 'en')
    lang = lang if lang in LANGS else 'en'
    now = timezone.now()
    result = {}
    for block in CmsBlock.objects.filter(is_published=True).order_by('key'):
        if (block.starts_at and block.starts_at > now) or (block.ends_at and block.ends_at <= now):
            continue
        if block.key not in result or block.language == lang:
            result[block.key] = {'key': block.key, 'language': block.language, 'content': block.published_content}
    return Response(list(result.values()))


# ---------------------------------------------------------------- admin CMS: pages

def _page_row(p, detail=False):
    pending = (not p.is_published or (p.title, p.body_markdown, p.seo_description) !=
               (p.published_title, p.published_body, p.published_seo_description))
    row = {'id': p.pk, 'slug': p.slug, 'language': p.language, 'title': p.title, 'is_published': p.is_published,
           'has_unpublished_changes': pending, 'published_at': p.published_at, 'updated_by': p.updated_by,
           'updated_at': p.updated_at}
    if detail:
        row.update(body_markdown=p.body_markdown, seo_description=p.seo_description,
                   revisions=list(p.revisions.order_by('-saved_at', '-pk').values('id', 'action', 'title', 'saved_by', 'saved_at')[:20]))
    return row


def _revision(page, action, actor):
    CmsRevision.objects.create(page=page, title=page.title, body_markdown=page.body_markdown,
                               seo_description=page.seo_description, action=action, saved_by=actor)


def _clean_page_fields(data, page=None):
    title = str(data.get('title', page.title if page else '')).strip()
    body = str(data.get('body_markdown', page.body_markdown if page else ''))
    seo = str(data.get('seo_description', page.seo_description if page else '')).strip()
    if not title or len(title) > 160:
        raise ValidationError({'title': 'Title is required (max 160 characters).'})
    if len(body) > 50000:
        raise ValidationError({'body_markdown': 'Body is too long (max 50,000 characters).'})
    if len(seo) > 300:
        raise ValidationError({'seo_description': 'Max 300 characters.'})
    return title, body, seo


@api_view(['GET', 'POST'])
def admin_cms_pages(request):
    staff(request, *CMS_EDIT)
    if request.method == 'POST':
        slug, lang = str(request.data.get('slug', '')).strip().lower(), _lang(request.data.get('language', 'en'))
        if not PAGE_SLUG.match(slug) or len(slug) > 60:
            raise ValidationError({'slug': 'Use lowercase letters, numbers and dashes.'})
        if CmsPage.objects.filter(slug=slug, language=lang).exists():
            raise ValidationError({'slug': 'A page with this slug and language already exists.'})
        title, body, seo = _clean_page_fields(request.data)
        page = CmsPage.objects.create(slug=slug, language=lang, title=title, body_markdown=body, seo_description=seo, updated_by=_actor(request))
        _revision(page, 'SAVE', _actor(request))
        Audit.objects.create(actor=_actor(request), action='CMS_PAGE_CREATED', target=f'{slug}/{lang}')
        return Response(_page_row(page, True), status=201)
    return Response([_page_row(p) for p in CmsPage.objects.order_by('slug', 'language')])


@api_view(['GET', 'PATCH'])
def admin_cms_page(request, pk):
    staff(request, *CMS_EDIT)
    page = CmsPage.objects.filter(pk=pk).first()
    if not page:
        raise NotFound('Page not found')
    if request.method == 'PATCH':
        page.title, page.body_markdown, page.seo_description = _clean_page_fields(request.data, page)
        page.updated_by, page.updated_at = _actor(request), timezone.now()
        page.save()
        _revision(page, 'SAVE', _actor(request))
        Audit.objects.create(actor=_actor(request), action='CMS_PAGE_SAVED', target=f'{page.slug}/{page.language}')
    return Response(_page_row(page, True))


@api_view(['POST'])
def admin_cms_page_publish(request, pk):
    staff(request, *CMS_PUBLISH)
    page = CmsPage.objects.filter(pk=pk).first()
    if not page:
        raise NotFound('Page not found')
    page.published_title, page.published_body, page.published_seo_description = page.title, page.body_markdown, page.seo_description
    page.is_published, page.published_at = True, timezone.now()
    page.save()
    _revision(page, 'PUBLISH', _actor(request))
    Audit.objects.create(actor=_actor(request), action='CMS_PAGE_PUBLISHED', target=f'{page.slug}/{page.language}')
    return Response(_page_row(page, True))


@api_view(['POST'])
def admin_cms_page_unpublish(request, pk):
    staff(request, *CMS_PUBLISH)
    page = CmsPage.objects.filter(pk=pk).first()
    if not page:
        raise NotFound('Page not found')
    page.is_published = False
    page.save(update_fields=['is_published'])
    Audit.objects.create(actor=_actor(request), action='CMS_PAGE_UNPUBLISHED', target=f'{page.slug}/{page.language}')
    return Response(_page_row(page, True))


@api_view(['POST'])
def admin_cms_page_restore(request, pk):
    staff(request, *CMS_EDIT)
    page = CmsPage.objects.filter(pk=pk).first()
    revision = CmsRevision.objects.filter(pk=request.data.get('revision_id'), page_id=pk).first() if page else None
    if not page or not revision:
        raise NotFound('Page or revision not found')
    page.title, page.body_markdown, page.seo_description = revision.title, revision.body_markdown, revision.seo_description
    page.updated_by, page.updated_at = _actor(request), timezone.now()
    page.save()
    _revision(page, 'RESTORE', _actor(request))
    Audit.objects.create(actor=_actor(request), action='CMS_PAGE_RESTORED', target=f'{page.slug}/{page.language}')
    return Response(_page_row(page, True))


# ---------------------------------------------------------------- admin CMS: blocks

def _clean_content(value):
    if not isinstance(value, dict) or len(value) > 12:
        raise ValidationError({'content': 'Content must be an object with at most 12 fields.'})
    clean = {}
    for key, item in value.items():
        if not isinstance(key, str) or not SLUG.match(key.lower().replace('_', '-')) or not isinstance(item, str) or len(item) > 500:
            raise ValidationError({'content': 'Fields must be short text values (max 500 characters).'})
        clean[key] = item
    link = clean.get('link', '')
    if link and not (link.startswith('/') and not link.startswith('//')) and not link.startswith('https://'):
        raise ValidationError({'content': 'Links must start with / or https://'})
    return clean


def _when(value, name):
    if value in (None, ''):
        return None
    parsed = parse_datetime(str(value))
    if not parsed:
        raise ValidationError({name: 'Use an ISO date-time.'})
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


def _block_row(b):
    return {'id': b.pk, 'key': b.key, 'language': b.language, 'content': b.content, 'is_published': b.is_published,
            'published_content': b.published_content, 'has_unpublished_changes': (not b.is_published) or b.content != b.published_content,
            'starts_at': b.starts_at, 'ends_at': b.ends_at, 'updated_by': b.updated_by, 'updated_at': b.updated_at}


@api_view(['GET', 'POST'])
def admin_cms_blocks(request):
    staff(request, *CMS_EDIT)
    if request.method == 'POST':
        key, lang = str(request.data.get('key', '')).strip().lower(), _lang(request.data.get('language', 'en'))
        if not SLUG.match(key) or len(key) > 60:
            raise ValidationError({'key': 'Use lowercase letters, numbers, dots and dashes.'})
        starts, ends = _when(request.data.get('starts_at'), 'starts_at'), _when(request.data.get('ends_at'), 'ends_at')
        if starts and ends and ends <= starts:
            raise ValidationError({'ends_at': 'End must be after start.'})
        block, _ = CmsBlock.objects.get_or_create(key=key, language=lang)
        block.content, block.starts_at, block.ends_at = _clean_content(request.data.get('content', {})), starts, ends
        block.updated_by, block.updated_at = _actor(request), timezone.now()
        block.save()
        Audit.objects.create(actor=_actor(request), action='CMS_BLOCK_SAVED', target=f'{key}/{lang}')
        return Response(_block_row(block), status=201)
    return Response([_block_row(b) for b in CmsBlock.objects.order_by('key', 'language')])


@api_view(['POST'])
def admin_cms_block_publish(request, pk):
    staff(request, *CMS_PUBLISH)
    block = CmsBlock.objects.filter(pk=pk).first()
    if not block:
        raise NotFound('Block not found')
    block.published_content, block.is_published = block.content, True
    block.save(update_fields=['published_content', 'is_published'])
    Audit.objects.create(actor=_actor(request), action='CMS_BLOCK_PUBLISHED', target=f'{block.key}/{block.language}')
    return Response(_block_row(block))


@api_view(['POST'])
def admin_cms_block_unpublish(request, pk):
    staff(request, *CMS_PUBLISH)
    block = CmsBlock.objects.filter(pk=pk).first()
    if not block:
        raise NotFound('Block not found')
    block.is_published = False
    block.save(update_fields=['is_published'])
    Audit.objects.create(actor=_actor(request), action='CMS_BLOCK_UNPUBLISHED', target=f'{block.key}/{block.language}')
    return Response(_block_row(block))


# ---------------------------------------------------------------- developer console

def backup_status():
    """Read the markers written by scripts/backup_db.sh and restore_drill.sh (never the dump itself)."""
    import json
    from pathlib import Path
    marker = Path(settings.BACKUP_STATUS_FILE)
    try:
        data = json.loads(marker.read_text())
        finished = parse_datetime(str(data.get('finished_at', '')))
        age = int((timezone.now() - finished).total_seconds()) if finished else None
    except (OSError, ValueError):
        return {'configured': False, 'ok': False, 'finished_at': None, 'age_seconds': None, 'size_bytes': None, 'last_restore_drill': None}
    try:
        drill = json.loads((marker.parent / 'last_restore_drill.json').read_text())
    except (OSError, ValueError):
        drill = None
    return {'configured': True, 'ok': bool(data.get('ok')) and age is not None and age < 26 * 3600,
            'finished_at': data.get('finished_at'), 'age_seconds': age, 'size_bytes': data.get('size_bytes'),
            'last_restore_drill': drill}


def _pending_migrations():
    executor = MigrationExecutor(connection)
    return len(executor.migration_plan(executor.loader.graph.leaf_nodes()))


@api_view(['GET'])
def dev_health(request):
    staff(request, *DEV_READ)
    started = time.monotonic()
    try:
        User.objects.exists()
        db = {'ok': True, 'latency_ms': int((time.monotonic() - started) * 1000)}
    except Exception:
        db = {'ok': False, 'latency_ms': None}
    try:
        from django.core.cache import cache
        cache.set('_dev_health', 1, 5)
        redis_ok = cache.get('_dev_health') == 1
    except Exception:
        redis_ok = False
    now = timezone.now()
    beat = JobRun.objects.filter(task='core.tasks.expire_holds').order_by('-started_at').first()
    beat_age = int((now - beat.started_at).total_seconds()) if beat else None
    try:
        pending = _pending_migrations()
    except Exception:
        pending = None
    return Response({
        'database': db, 'cache': {'ok': redis_ok},
        'celery': {'last_beat_task_seconds_ago': beat_age, 'healthy': beat_age is not None and beat_age < 300},
        'pending_migrations': pending,
        'backup': backup_status(),
        'outbox_pending': Outbox.objects.filter(delivered_at__isnull=True).count(),
        'errors_24h': ErrorEvent.objects.filter(created_at__gte=now - timedelta(hours=24)).count(),
        'versions': {'app': getattr(settings, 'APP_VERSION', 'dev'), 'django': django.get_version(), 'python': platform.python_version()},
        'environment': settings.ENV, 'debug': settings.DEBUG, 'checked_at': now,
    })


@api_view(['GET'])
def dev_jobs(request):
    staff(request, *DEV_READ)
    since = timezone.now() - timedelta(hours=24)
    recent = JobRun.objects.filter(started_at__gte=since)
    summary = {}
    for task, status in recent.values_list('task', 'status'):
        row = summary.setdefault(task, {'task': task, 'runs': 0, 'failures': 0})
        row['runs'] += 1
        row['failures'] += status == 'FAILURE'
    return Response({'summary': sorted(summary.values(), key=lambda r: r['task']),
                     'recent': list(JobRun.objects.order_by('-started_at', '-pk').values('id', 'task', 'status', 'started_at', 'duration_ms', 'error')[:50]),
                     'failures': list(JobRun.objects.filter(status='FAILURE').order_by('-started_at').values('id', 'task', 'started_at', 'error')[:20])})


@api_view(['GET'])
def dev_outbox(request):
    staff(request, *DEV_READ)
    pending = Outbox.objects.filter(delivered_at__isnull=True)
    return Response({'pending_count': pending.count(), 'delivered_count': Outbox.objects.filter(delivered_at__isnull=False).count(),
                     'note': 'No delivery adapter is configured yet, so events stay pending (see HANDOVER.md).',
                     'pending': list(pending.order_by('-created_at').values('id', 'kind', 'target', 'created_at')[:50])})


@api_view(['GET'])
def dev_payment_provider(request):
    staff(request, *DEV_READ)
    since = timezone.now() - timedelta(hours=24)
    by_status = {}
    for status in PaymentAttempt.objects.filter(created_at__gte=since).values_list('status', flat=True):
        by_status[status] = by_status.get(status, 0) + 1
    return Response({'provider': settings.PAYMENT_PROVIDER, 'currency': settings.BAKONG_CURRENCY,
                     'configured': {'token': bool(settings.BAKONG_TOKEN), 'account_id': bool(settings.BAKONG_ACCOUNT_ID),
                                    'merchant_name': bool(settings.BAKONG_MERCHANT_NAME), 'merchant_city': bool(settings.BAKONG_MERCHANT_CITY)},
                     'attempt_window_minutes': settings.PAYMENT_ATTEMPT_MINUTES, 'late_window_hours': settings.PAYMENT_LATE_WINDOW_HOURS,
                     'attempts_24h': by_status,
                     'last_sweep': JobRun.objects.filter(task='core.tasks.sweep_payment_attempts').order_by('-started_at').values('status', 'started_at', 'duration_ms', 'error').first()})


@api_view(['POST'])
def dev_payment_provider_check(request):
    """Connectivity probe: asks Bakong about a random hash. Never creates a payment or returns secrets."""
    staff(request, *DEV_WRITE)
    if settings.PAYMENT_PROVIDER != 'bakong':
        raise ValidationError('The Bakong provider is not enabled.')
    from .payments import bakong
    from .payments.base import ProviderError
    started = time.monotonic()
    try:
        status = bakong.check_status('0' * 32)
        result = {'ok': True, 'status': status}
    except ProviderError as exc:
        result = {'ok': False, 'error': str(exc)[:200]}
    result['latency_ms'] = int((time.monotonic() - started) * 1000)
    Audit.objects.create(actor=_actor(request), action='BAKONG_CONNECTIVITY_CHECK', target='ok' if result['ok'] else 'failed')
    return Response(result)


def _flag_row(f):
    return {'key': f.key, 'enabled': f.enabled, 'description': f.description, 'updated_by': f.updated_by, 'updated_at': f.updated_at}


@api_view(['GET', 'POST'])
def dev_flags(request):
    if request.method == 'POST':
        staff(request, *DEV_WRITE)
        key = str(request.data.get('key', '')).strip().lower()
        if not re.match(r'^[a-z0-9_]{2,60}$', key):
            raise ValidationError({'key': 'Use lowercase letters, numbers and underscores.'})
        if FeatureFlag.objects.filter(key=key).exists():
            raise ValidationError({'key': 'Flag already exists.'})
        flag = FeatureFlag.objects.create(key=key, description=str(request.data.get('description', ''))[:200], updated_by=_actor(request))
        Audit.objects.create(actor=_actor(request), action='FLAG_CREATED', target=key)
        return Response(_flag_row(flag), status=201)
    staff(request, *DEV_READ)
    return Response([_flag_row(f) for f in FeatureFlag.objects.order_by('key')])


@api_view(['PATCH'])
def dev_flag(request, key):
    staff(request, *DEV_WRITE)
    if not FeatureFlag.objects.filter(key=key).exists():
        raise NotFound('Flag not found')
    flag = flags.set_flag(key, bool(request.data.get('enabled')), _actor(request))
    Audit.objects.create(actor=_actor(request), action='FLAG_CHANGED', target=f'{key}={"on" if flag.enabled else "off"}')
    return Response(_flag_row(flag))


@api_view(['GET'])
def dev_config(request):
    """Effective non-secret settings. Secrets are reported only as set/unset."""
    staff(request, *DEV_READ)
    secrets_set = {name: bool(getattr(settings, name, '')) for name in ('SECRET_KEY', 'BAKONG_TOKEN', 'BAKONG_ACCOUNT_ID')}
    secrets_set['DATABASE_URL'] = bool(settings.DATABASES['default'].get('NAME') or settings.DATABASES['default'].get('HOST'))
    return Response({
        'environment': settings.ENV, 'debug': settings.DEBUG, 'time_zone': settings.TIME_ZONE,
        'allowed_hosts': list(settings.ALLOWED_HOSTS), 'frontend_origin': settings.FRONTEND_ORIGIN,
        'payment': {'provider': settings.PAYMENT_PROVIDER, 'attempt_minutes': settings.PAYMENT_ATTEMPT_MINUTES,
                    'late_window_hours': settings.PAYMENT_LATE_WINDOW_HOURS, 'currency': settings.BAKONG_CURRENCY,
                    'merchant_name': settings.BAKONG_MERCHANT_NAME, 'merchant_city': settings.BAKONG_MERCHANT_CITY},
        'retention': {'guest_years': settings.RETENTION_GUEST_YEARS, 'short_lived_hours': settings.RETENTION_SHORT_LIVED_HOURS},
        'celery_beat': sorted(settings.CELERY_BEAT_SCHEDULE),
        'secrets_configured': secrets_set,
    })


@api_view(['GET'])
def dev_errors(request):
    staff(request, *DEV_READ)
    return Response(list(ErrorEvent.objects.order_by('-created_at', '-pk').values('id', 'created_at', 'request_id', 'method', 'path', 'exc_type', 'message')[:100]))


def _session_user_id(session):
    try:
        return int(session.get_decoded().get('_auth_user_id'))
    except (TypeError, ValueError):
        return None


@api_view(['GET'])
def dev_security(request):
    staff(request, *DEV_READ)
    now = timezone.now()
    failed = {}
    for actor, portal in Audit.objects.filter(action='LOGIN_FAILED', timestamp__gte=now - timedelta(hours=24)).values_list('actor', 'target'):
        row = failed.setdefault((actor, portal), {'username': actor, 'portal': portal, 'count': 0})
        row['count'] += 1
    per_user = {}
    for session in Session.objects.filter(expire_date__gt=now):
        uid = _session_user_id(session)
        if uid:
            per_user[uid] = per_user.get(uid, 0) + 1
    users = {u.pk: u for u in User.objects.filter(pk__in=per_user)}
    return Response({'failed_logins_24h': sorted(failed.values(), key=lambda r: -r['count'])[:30],
                     'active_sessions': [{'user_id': uid, 'username': users[uid].username, 'role': users[uid].role, 'sessions': n}
                                         for uid, n in sorted(per_user.items()) if uid in users]})


@api_view(['POST'])
def dev_revoke_sessions(request, user_id):
    staff(request, *DEV_WRITE)
    target = User.objects.filter(pk=user_id).first()
    if not target:
        raise NotFound('User not found')
    if target.pk == request.user.pk:
        raise ValidationError('You cannot revoke your own sessions here; sign out instead.')
    removed = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        if _session_user_id(session) == target.pk:
            session.delete()
            removed += 1
    Audit.objects.create(actor=_actor(request), action='SESSIONS_REVOKED', target=f'{target.username}:{removed}')
    return Response({'revoked': removed})


urlpatterns = [
    path('cms/pages/<slug:slug>', cms_public_page), path('cms/blocks', cms_public_blocks),
    path('admin/cms/pages', admin_cms_pages), path('admin/cms/pages/<int:pk>', admin_cms_page),
    path('admin/cms/pages/<int:pk>/publish', admin_cms_page_publish), path('admin/cms/pages/<int:pk>/unpublish', admin_cms_page_unpublish),
    path('admin/cms/pages/<int:pk>/restore', admin_cms_page_restore),
    path('admin/cms/blocks', admin_cms_blocks),
    path('admin/cms/blocks/<int:pk>/publish', admin_cms_block_publish), path('admin/cms/blocks/<int:pk>/unpublish', admin_cms_block_unpublish),
    path('admin/dev/health', dev_health), path('admin/dev/jobs', dev_jobs), path('admin/dev/outbox', dev_outbox),
    path('admin/dev/payment-provider', dev_payment_provider), path('admin/dev/payment-provider/check', dev_payment_provider_check),
    path('admin/dev/flags', dev_flags), path('admin/dev/flags/<slug:key>', dev_flag),
    path('admin/dev/config', dev_config), path('admin/dev/errors', dev_errors),
    path('admin/dev/security', dev_security), path('admin/dev/security/revoke/<int:user_id>', dev_revoke_sessions),
]
