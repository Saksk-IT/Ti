# -*- coding: utf-8 -*-
import json

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.email_service import EmailService
from app.models.system import SystemConfig
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.quiz.services.ai_client import AIClient
from app.tasks.ai_explain_tasks import ai_explain_task


MAIL_KEYS = [
    'mail_server',
    'mail_port',
    'mail_use_tls',
    'mail_use_ssl',
    'mail_username',
    'mail_password',
    'mail_default_sender',
    'mail_default_sender_name',
    'mail_enabled',
    'mail_console_output',
]

SMS_KEYS = [
    'sms_access_key_id',
    'sms_access_key_secret',
    'sms_sign_name',
    'sms_template_code',
    'sms_template_code_bind',
    'sms_template_code_reset',
    'sms_code_length',
    'sms_valid_time',
    'sms_interval',
    'sms_enabled',
    'sms_console_output',
]

AI_KEYS = [
    'ai_provider',
    'ai_api_key',
    'ai_base_url',
    'ai_api_type',
    'ai_model',
    'ai_model_source',
    'ai_timeout',
    'dashscope_api_key',
    'dashscope_base_url',
    'dashscope_model',
    'dashscope_timeout',
]

def _clear_system_configs(keys):
    SystemConfig.query.filter(SystemConfig.config_key.in_(keys)).delete(synchronize_session=False)
    db.session.commit()


def test_mail_config_prefers_system_settings(app):
    with app.app_context():
        _clear_system_configs(MAIL_KEYS)
        try:
            SystemConfigService.update_config('mail_server', 'smtp.db.example.com', admin_id=1)
            SystemConfigService.update_config('mail_port', '2525', admin_id=1)
            SystemConfigService.update_config('mail_use_tls', 'false', admin_id=1)
            SystemConfigService.update_config('mail_username', 'db-user@example.com', admin_id=1)
            SystemConfigService.update_config('mail_password', 'db-password', admin_id=1)
            SystemConfigService.update_config('mail_default_sender', 'noreply@example.com', admin_id=1)
            SystemConfigService.update_config('mail_enabled', 'true', admin_id=1)

            cfg = SystemConfigService.get_mail_config()

            assert cfg['server'] == 'smtp.db.example.com'
            assert cfg['port'] == 2525
            assert cfg['use_tls'] is False
            assert cfg['username'] == 'db-user@example.com'
            assert cfg['password'] == 'db-password'
            assert cfg['sender'] == 'noreply@example.com'
            assert cfg['enabled'] is True
        finally:
            _clear_system_configs(MAIL_KEYS)


def test_verification_email_uses_default_rq_queue(app, monkeypatch):
    queue_calls = []
    enqueued_jobs = []

    class FakeQueue:
        def enqueue(self, *args, **kwargs):
            enqueued_jobs.append((args, kwargs))
            return object()

    def fake_get_queue(*args, **kwargs):
        queue_calls.append((args, kwargs))
        return FakeQueue()

    monkeypatch.setattr('app.core.utils.rq_utils.get_queue', fake_get_queue)
    monkeypatch.setattr(
        EmailService,
        '_get_smtp_config',
        staticmethod(lambda: {
            'server': 'smtp.example.com',
            'port': 587,
            'use_tls': True,
            'use_ssl': False,
            'username': 'mailer@example.com',
            'password': 'secret-password',
            'sender': 'mailer@example.com',
            'sender_name': '系统通知',
        }),
    )

    with app.app_context():
        _clear_system_configs(MAIL_KEYS)
        try:
            SystemConfigService.update_config('mail_enabled', 'true', admin_id=1)
            SystemConfigService.update_config('mail_console_output', 'false', admin_id=1)

            ok, code = EmailService.send_verification_code(
                'user@example.com',
                'login',
                code='123456',
            )

            assert ok is True
            assert code == '123456'
            assert queue_calls == [((), {})]
            assert enqueued_jobs
            assert enqueued_jobs[0][1]['to_email'] == 'user@example.com'
        finally:
            _clear_system_configs(MAIL_KEYS)


def test_admin_sms_settings_roundtrip(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = 1 WHERE id = :uid"),
            {'uid': seed_user['id']},
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = seed_user['id']
        sess['username'] = seed_user['username']
        sess['is_admin'] = True

    with app.app_context():
        _clear_system_configs(SMS_KEYS)

    payload = {
        'sms_access_key_id': 'LTAI123456789',
        'sms_access_key_secret': 'secret987654321',
        'sms_sign_name': '速通互联验证码',
        'sms_template_code': '100001',
        'sms_template_code_bind': '100004',
        'sms_template_code_reset': '100003',
        'sms_code_length': 6,
        'sms_valid_time': 300,
        'sms_interval': 60,
        'sms_enabled': True,
        'sms_console_output': True,
    }

    try:
        response = client.post('/admin/api/settings/sms', json=payload)
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'

        response = client.get('/admin/api/settings/sms')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['sms_sign_name'] == '速通互联验证码'
        assert '****' in data['sms_access_key_id']
        assert '****' in data['sms_access_key_secret']

        with app.app_context():
            cfg = SystemConfigService.get_sms_config()
            assert cfg['access_key_id'] == 'LTAI123456789'
            assert cfg['access_key_secret'] == 'secret987654321'
            assert cfg['template_code_bind'] == '100004'
            assert cfg['enabled'] is True
            assert cfg['console_output'] is True
    finally:
        with app.app_context():
            _clear_system_configs(SMS_KEYS)
            db.session.execute(
                text("UPDATE users SET is_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_ai_config_prefers_new_system_settings(app):
    with app.app_context():
        _clear_system_configs(AI_KEYS)
        try:
            SystemConfigService.update_config('dashscope_api_key', 'legacy-key', admin_id=1)
            SystemConfigService.update_config('dashscope_base_url', 'https://dashscope.example.com/v1', admin_id=1)
            SystemConfigService.update_config('dashscope_model', 'qwen-plus', admin_id=1)
            SystemConfigService.update_config('ai_provider', 'openai', admin_id=1)
            SystemConfigService.update_config('ai_api_key', 'new-key', admin_id=1)
            SystemConfigService.update_config('ai_base_url', 'https://api.example.com/v1', admin_id=1)
            SystemConfigService.update_config('ai_api_type', 'responses', admin_id=1)
            SystemConfigService.update_config('ai_model', 'gpt-test-model', admin_id=1)
            SystemConfigService.update_config('ai_model_source', 'upstream', admin_id=1)
            SystemConfigService.update_config('ai_timeout', '33', admin_id=1)

            cfg = SystemConfigService.get_ai_config()

            assert cfg == {
                'provider': 'openai',
                'api_key': 'new-key',
                'base_url': 'https://api.example.com/v1',
                'api_type': 'responses',
                'model': 'gpt-test-model',
                'model_source': 'upstream',
                'timeout': 33,
            }
        finally:
            _clear_system_configs(AI_KEYS)


def test_ai_config_falls_back_to_legacy_dashscope(app):
    with app.app_context():
        _clear_system_configs(AI_KEYS)
        try:
            SystemConfigService.update_config('dashscope_api_key', 'legacy-key', admin_id=1)
            SystemConfigService.update_config('dashscope_base_url', 'https://dashscope.example.com/v1/', admin_id=1)
            SystemConfigService.update_config('dashscope_model', 'qwen-max', admin_id=1)
            SystemConfigService.update_config('dashscope_timeout', '19', admin_id=1)

            cfg = SystemConfigService.get_ai_config()

            assert cfg['provider'] == 'dashscope'
            assert cfg['api_key'] == 'legacy-key'
            assert cfg['base_url'] == 'https://dashscope.example.com/v1'
            assert cfg['api_type'] == 'chat_completions'
            assert cfg['model'] == 'qwen-max'
            assert cfg['timeout'] == 19
        finally:
            _clear_system_configs(AI_KEYS)


def test_ai_explain_task_prefers_explicit_dashscope_config(monkeypatch):
    captured = {}

    def fake_generate_ai_explain(*, api_key, base_url, model, payload, timeout, provider, api_type):
        captured['api_key'] = api_key
        captured['base_url'] = base_url
        captured['model'] = model
        captured['payload'] = payload
        captured['timeout'] = timeout
        captured['provider'] = provider
        captured['api_type'] = api_type
        return 'AI 解析结果'

    monkeypatch.setattr('app.tasks.ai_explain_tasks.generate_ai_explain', fake_generate_ai_explain)

    result = ai_explain_task(
        payload={'content': '示例题目'},
        model='qwen-max',
        timeout=18,
        dashscope_config={
            'api_key': 'db-runtime-key',
            'base_url': 'https://dashscope.example.com/v1',
            'model': 'qwen-plus',
            'timeout': 25,
        },
    )

    assert result['provider'] == 'dashscope'
    assert result['model'] == 'qwen-max'
    assert result['explain'] == 'AI 解析结果'
    assert captured == {
        'api_key': 'db-runtime-key',
        'base_url': 'https://dashscope.example.com/v1',
        'model': 'qwen-max',
        'payload': {'content': '示例题目'},
        'timeout': 18,
        'provider': 'dashscope',
        'api_type': 'chat_completions',
    }


def test_ai_explain_task_accepts_openai_responses_config(monkeypatch):
    captured = {}

    def fake_generate_ai_explain(*, api_key, base_url, model, payload, timeout, provider, api_type):
        captured.update({
            'api_key': api_key,
            'base_url': base_url,
            'model': model,
            'payload': payload,
            'timeout': timeout,
            'provider': provider,
            'api_type': api_type,
        })
        return 'Responses 解析结果'

    monkeypatch.setattr('app.tasks.ai_explain_tasks.generate_ai_explain', fake_generate_ai_explain)

    result = ai_explain_task(
        payload={'content': '示例题目'},
        timeout=21,
        ai_config={
            'provider': 'openai',
            'api_key': 'openai-runtime-key',
            'base_url': 'https://api.openai.com/v1',
            'api_type': 'responses',
            'model': 'gpt-4.1-mini',
            'timeout': 25,
        },
    )

    assert result == {
        'provider': 'openai',
        'api_type': 'responses',
        'model': 'gpt-4.1-mini',
        'explain': 'Responses 解析结果',
    }
    assert captured == {
        'api_key': 'openai-runtime-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4.1-mini',
        'payload': {'content': '示例题目'},
        'timeout': 21,
        'provider': 'openai',
        'api_type': 'responses',
    }


def test_ai_client_extracts_responses_text(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                'output': [
                    {
                        'content': [
                            {'type': 'output_text', 'text': '解析正文'}
                        ]
                    }
                ]
            }

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured['url'] = url
        captured['payload'] = json
        captured['timeout'] = timeout
        return FakeResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1',
        api_type='responses',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-4.1-mini',
        messages=[{'role': 'user', 'content': '请解析'}],
        timeout=12,
    )

    assert text == '解析正文'
    assert captured['url'] == 'https://api.openai.com/v1/responses'
    assert captured['payload']['model'] == 'gpt-4.1-mini'
    assert captured['payload']['input'] == [{'role': 'user', 'content': '请解析'}]
    assert captured['timeout'] == 12


def test_ai_client_openai_chat_uses_current_token_param(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {'choices': [{'message': {'content': '解析正文'}}]}

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured['url'] = url
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1',
        api_type='chat_completions',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-4.1-mini',
        messages=[{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '请解析'}],
        max_tokens=321,
    )

    assert text == '解析正文'
    assert captured['url'] == 'https://api.openai.com/v1/chat/completions'
    assert captured['payload']['max_completion_tokens'] == 321
    assert 'max_tokens' not in captured['payload']
    assert captured['payload']['temperature'] == 0.2
    assert captured['payload']['top_p'] == 0.8
    assert captured['payload']['messages'][0] == {'role': 'system', 'content': '规则'}


def test_ai_client_openai_reasoning_chat_omits_sampling_params(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {'choices': [{'message': {'content': '解析正文'}}]}

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1',
        api_type='chat_completions',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-5',
        messages=[{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '请解析'}],
        temperature=0.2,
        top_p=0.8,
        max_tokens=456,
    )

    assert text == '解析正文'
    assert captured['payload']['max_completion_tokens'] == 456
    assert 'max_tokens' not in captured['payload']
    assert 'temperature' not in captured['payload']
    assert 'top_p' not in captured['payload']
    assert captured['payload']['messages'][0] == {'role': 'developer', 'content': '规则'}


def test_ai_client_openai_reasoning_responses_omits_sampling_params(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {'output_text': '解析正文'}

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured['url'] = url
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1',
        api_type='responses',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-5.1',
        messages=[{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '请解析'}],
        temperature=0.2,
        top_p=0.8,
        max_tokens=789,
    )

    assert text == '解析正文'
    assert captured['url'] == 'https://api.openai.com/v1/responses'
    assert captured['payload']['max_output_tokens'] == 789
    assert 'temperature' not in captured['payload']
    assert 'top_p' not in captured['payload']


def test_ai_client_retries_without_sampling_params_when_upstream_rejects(monkeypatch):
    class FakeErrorResponse:
        status_code = 400
        text = ''

        def json(self):
            return {'error': {'message': 'Unsupported parameter: temperature is not supported'}}

    class FakeSuccessResponse:
        status_code = 200

        def json(self):
            return {'output_text': '重试成功'}

    captured_payloads = []

    def fake_post(url, headers, json, timeout):
        captured_payloads.append(json)
        if len(captured_payloads) == 1:
            return FakeErrorResponse()
        return FakeSuccessResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1',
        api_type='responses',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-4.1-mini',
        messages=[{'role': 'user', 'content': '请解析'}],
        temperature=0.2,
        top_p=0.8,
    )

    assert text == '重试成功'
    assert len(captured_payloads) == 2
    assert 'temperature' in captured_payloads[0]
    assert 'top_p' in captured_payloads[0]
    assert 'temperature' not in captured_payloads[1]
    assert 'top_p' not in captured_payloads[1]


def test_ai_client_responses_empty_output_falls_back_to_chat(monkeypatch):
    class FakeResponsesResponse:
        status_code = 200

        def json(self):
            return {'status': 'completed', 'output': []}

    class FakeChatResponse:
        status_code = 200

        @property
        def content(self):
            return json.dumps(
                {'choices': [{'message': {'content': 'Chat 兜底解析'}}]},
                ensure_ascii=False,
            ).encode('utf-8')

        @property
        def text(self):
            return self.content.decode('latin-1')

        def json(self):
            return {'choices': [{'message': {'content': '乱码兜底不应使用'}}]}

    captured = []

    def fake_post(url, headers, json, timeout):
        captured.append({'url': url, 'payload': json})
        if url.endswith('/responses'):
            return FakeResponsesResponse()
        return FakeChatResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.example.test/v1',
        api_type='responses',
        provider='openai',
    )
    text = client.generate_text(
        model='gpt-5.4-mini',
        messages=[{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '请解析'}],
        max_tokens=555,
    )

    assert text == 'Chat 兜底解析'
    assert [item['url'] for item in captured] == [
        'https://api.example.test/v1/responses',
        'https://api.example.test/v1/chat/completions',
    ]
    assert captured[1]['payload']['max_completion_tokens'] == 555
    assert captured[1]['payload']['messages'][0] == {'role': 'developer', 'content': '规则'}


def test_ai_client_decodes_utf8_json_content_before_requests_text(monkeypatch):
    class FakeResponse:
        status_code = 200

        @property
        def content(self):
            return json.dumps(
                {'choices': [{'message': {'content': '你好，中文正常。'}}]},
                ensure_ascii=False,
            ).encode('utf-8')

        @property
        def text(self):
            return self.content.decode('latin-1')

        def json(self):
            return {'choices': [{'message': {'content': 'ä½\xa0å¥½'}}]}

    monkeypatch.setattr(
        'app.modules.quiz.services.ai_client.requests.post',
        lambda url, headers, json, timeout: FakeResponse(),
    )

    client = AIClient(
        api_key='test-key',
        base_url='https://api.example.test/v1',
        api_type='chat_completions',
        provider='custom',
    )

    assert client.generate_text(
        model='model-a',
        messages=[{'role': 'user', 'content': '请回复中文'}],
    ) == '你好，中文正常。'


def test_ai_client_lists_models(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                'data': [
                    {'id': 'gpt-4.1-mini', 'owned_by': 'openai'},
                    {'id': 'custom-model', 'owner': 'upstream'},
                    {'owned_by': 'missing-id'},
                ]
            }

    monkeypatch.setattr(
        'app.modules.quiz.services.ai_client.requests.get',
        lambda url, headers, timeout: FakeResponse(),
    )

    client = AIClient(
        api_key='test-key',
        base_url='https://api.openai.com/v1/',
        api_type='responses',
        provider='openai',
    )

    assert client.list_models(timeout=10) == [
        {'id': 'gpt-4.1-mini', 'owned_by': 'openai'},
        {'id': 'custom-model', 'owned_by': 'upstream'},
    ]


def test_ai_client_stream_decodes_utf8_sse_without_charset(monkeypatch):
    class FakeStreamResponse:
        status_code = 200
        text = ''

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def iter_lines(self, decode_unicode=False):
            payload = {
                'choices': [
                    {'delta': {'content': '你好，中文正常。'}}
                ]
            }
            line = f"data: {json.dumps(payload, ensure_ascii=False)}".encode('utf-8')
            if decode_unicode:
                yield line.decode('latin-1')
                return
            yield line

    captured = {}

    def fake_post(url, headers, json, timeout, stream):
        captured['stream'] = stream
        return FakeStreamResponse()

    monkeypatch.setattr('app.modules.quiz.services.ai_client.requests.post', fake_post)

    client = AIClient(
        api_key='test-key',
        base_url='https://api.example.test/v1',
        api_type='chat_completions',
        provider='custom',
    )

    chunks = list(client.stream_text(
        model='model-a',
        messages=[{'role': 'user', 'content': '请回复中文'}],
        timeout=10,
    ))

    assert captured['stream'] is True
    assert chunks == ['你好，中文正常。']
