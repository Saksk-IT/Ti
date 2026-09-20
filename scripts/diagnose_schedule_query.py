"""Read-only schedule diagnostics using a locally bound account; never print secrets."""

import argparse
import hashlib
import json
import logging
from urllib.parse import urlparse

import requests

from app import create_app
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.edu_schedule.services.client import JWXTClient
from app.modules.edu_schedule.services.schedule_service import EduScheduleService
from app.modules.edu_schedule.services.parser import normalize_schedule_payload


def summarize(payload):
    student = payload.get('xsxx') or {}
    courses = payload.get('kbList') or []
    practice = payload.get('sjkList') or []
    content = json.dumps([courses, practice], sort_keys=True, ensure_ascii=False)
    return {
        'reported_term': {key: student.get(key) for key in ['XNM', 'XQM', 'XNMC', 'XQMMC']},
        'course_rows': len(courses), 'practice_rows': len(practice),
        'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16],
        'course_names': sorted({row.get('kcmc', '') for row in courses + practice}),
        'course_term_fields': [{key: row[key] for key in ['xnm', 'xqm', 'xnmc', 'xqmmc'] if key in row} for row in courses[:2]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--frontend-payload', action='store_true', help='Output only de-identified snapshots for frontend verification')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    app = create_app()
    with app.app_context():
        cfg = SystemConfigService.get_edu_schedule_config()
        account, secret = EduScheduleService._load_credentials(args.user_id)
        client = JWXTClient(cfg)
        with requests.Session() as session:
            if client.config.use_webvpn:
                client._prepare_webvpn(session)
            client._login_jwxt(session, account, secret)
            request = session.request

            def trace(method, url, **kwargs):
                response = request(method, url, **kwargs)
                form = kwargs.get('data') or {}
                print(json.dumps({'request': method, 'path': urlparse(url).path,
                    'term': {key: form.get(key) for key in ['xnm', 'xqm']},
                    'status': response.status_code,
                    'redirect_path': urlparse(response.headers.get('Location', '')).path}, ensure_ascii=False), flush=True)
                return response

            if not args.frontend_payload:
                session.request = trace
            snapshots = []
            for xnm, xqm in [('2025', '12'), ('2026', '3'), ('2024', '3')]:
                result = client._query_schedule(session, xnm, xqm)
                if not args.frontend_payload:
                    print(json.dumps({'requested': [xnm, xqm], **summarize(result)}, ensure_ascii=False), flush=True)
                normalized = normalize_schedule_payload(result)
                def course(row):
                    return {key: row.get(key, '') for key in ['course_name', 'weeks', 'section']}
                snapshots.append({'payload': {
                    'term': normalized['term'],
                    'week_table': {day: {section: [course(row) for row in rows] for section, rows in sections.items()}
                        for day, sections in normalized['week_table'].items()},
                    'practice_courses': [course(row) for row in normalized['practice_courses']],
                }})
            if args.frontend_payload:
                print(json.dumps(snapshots, ensure_ascii=False))


if __name__ == '__main__':
    main()
