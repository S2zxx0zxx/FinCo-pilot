"""Actual socket/TLS SMTP tests plus privacy, capacity and configuration boundaries."""
import asyncio
import datetime
import socket
import ssl
import threading
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings
from app.core.smtp_runtime import EmailDeliveryError, smtp_connection
from app.services import email_service
from scripts import verify_production_smtp
from tests.test_config import _production_settings_kwargs


@pytest.fixture
def relay(tmp_path):
    """One real SMTP peer with explicit TLS, AUTH, DATA and failure modes."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(3)
    state = SimpleNamespace(port=listener.getsockname()[1], ca=str(cert_path),
                            messages=[], commands=[], tls=False, implicit=False,
                            advertise_tls=True, reject_auth=False, reject_rcpt=False,
                            reject_data=False, drop_quit=False, done=threading.Event(), errors=[])

    def serve():
        conn = None
        stream = None
        try:
            conn, _ = listener.accept()
            conn.settimeout(3)
            if state.implicit:
                conn = context.wrap_socket(conn, server_side=True)
                state.tls = True
            stream = conn.makefile('rwb')
            def reply(value):
                stream.write(value + b'\r\n')
                stream.flush()
            reply(b'220 localhost ESMTP')
            while True:
                line = stream.readline()
                if not line:
                    break
                command = line.split(b' ', 1)[0].strip().upper()
                state.commands.append(command)
                if command == b'EHLO':
                    reply(b'250-localhost')
                    if state.advertise_tls and not state.tls:
                        reply(b'250-STARTTLS')
                    reply(b'250 AUTH PLAIN')
                elif command == b'STARTTLS':
                    reply(b'220 Ready')
                    stream.close()
                    conn = context.wrap_socket(conn, server_side=True)
                    stream = conn.makefile('rwb')
                    state.tls = True
                elif command == b'AUTH':
                    assert state.tls, 'AUTH must never precede TLS'
                    reply(b'535 synthetic-sensitive-provider-response' if state.reject_auth else b'235 OK')
                elif command == b'MAIL':
                    reply(b'250 OK')
                elif command == b'RCPT':
                    reply(b'550 sensitive@example.com refused' if state.reject_rcpt else b'250 OK')
                elif command == b'DATA':
                    reply(b'354 Continue')
                    data = []
                    while True:
                        row = stream.readline()
                        if row == b'.\r\n':
                            break
                        if not row:
                            raise RuntimeError('Unexpected EOF')
                        data.append(row[1:] if row.startswith(b'..') else row)
                    if not state.reject_data:
                        state.messages.append(b''.join(data))
                    reply(b'554 sensitive@example.com refused' if state.reject_data else b'250 queued')
                elif command in (b'NOOP', b'RSET'):
                    reply(b'250 OK')
                elif command == b'QUIT':
                    if not state.drop_quit:
                        reply(b'221 Goodbye')
                    break
                else:
                    reply(b'500 Unknown')
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError):
            pass  # Expected for client certificate verification refusal.
        except Exception as exc:
            state.errors.append(type(exc).__name__)
        finally:
            if stream:
                stream.close()
            if conn:
                conn.close()
            state.done.set()
    state.thread = threading.Thread(target=serve, daemon=True)
    state.thread.start()
    yield state
    listener.close()
    state.thread.join(timeout=4)
    assert not state.thread.is_alive()
    assert not state.errors


def configure(monkeypatch, relay, **overrides):
    settings = get_settings()
    values = dict(smtp_host='localhost', smtp_port=relay.port,
                  smtp_ssl_ca_file=relay.ca, smtp_username='synthetic-login',
                  smtp_password=SecretStr('synthetic-smtp-password'),
                  smtp_from_email='security@example.com', smtp_timeout_seconds=2,
                  smtp_starttls=True, smtp_use_ssl=False, email_delivery_required=True)
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setattr(settings, key, value)
    return settings


@pytest.mark.parametrize('implicit', [False, True])
async def test_real_tls_auth_and_single_recipient_submission(monkeypatch, relay, implicit):
    relay.implicit = implicit
    configure(monkeypatch, relay, smtp_use_ssl=implicit, smtp_starttls=not implicit)
    assert await email_service.send_password_reset_email('person@example.com', 'synthetic&token')
    assert relay.done.wait(2)
    assert relay.tls
    assert relay.commands.count(b'AUTH') == 1
    assert relay.commands.count(b'RCPT') == 1
    message = BytesParser(policy=policy.default).parsebytes(relay.messages[0])
    assert message['Date'] and message['Message-ID']
    assert message['Auto-Submitted'] == 'auto-generated'
    assert message['To'] == 'person@example.com'
    assert message.is_multipart()
    assert 'synthetic%26token' in message.get_body(preferencelist=('plain',)).get_content()
    assert 'synthetic%26token' in message.get_body(preferencelist=('html',)).get_content()


async def test_untrusted_certificate_refuses_auth_and_data(monkeypatch, relay):
    configure(monkeypatch, relay, smtp_ssl_ca_file='')
    with pytest.raises(EmailDeliveryError, match='tls'):
        await email_service.send_verification_email('person@example.com', 'secret-token')
    assert b'AUTH' not in relay.commands
    assert not relay.messages


async def test_missing_starttls_has_no_plaintext_fallback(monkeypatch, relay):
    relay.advertise_tls = False
    configure(monkeypatch, relay)
    with pytest.raises(EmailDeliveryError, match='unsupported_protocol'):
        await email_service.send_verification_email('person@example.com', 'secret-token')
    assert b'AUTH' not in relay.commands
    assert not relay.messages


@pytest.mark.parametrize('mode,reason', [('reject_auth', 'authentication'),
                                        ('reject_rcpt', 'recipient_refused'),
                                        ('reject_data', 'data_refused')])
async def test_real_provider_rejection_is_safe_and_never_retried(monkeypatch, relay, caplog, mode, reason):
    setattr(relay, mode, True)
    configure(monkeypatch, relay)
    with pytest.raises(EmailDeliveryError, match=reason) as result:
        await email_service.send_verification_email('person@example.com', 'secret-token')
    assert not relay.messages
    assert relay.commands.count(b'AUTH') == 1
    assert 'sensitive@example.com' not in str(result.value) + caplog.text
    assert 'secret-token' not in str(result.value) + caplog.text
    assert 'synthetic-sensitive-provider-response' not in caplog.text
    assert result.value.__suppress_context__


async def test_quit_disconnect_after_data_is_still_accepted(monkeypatch, relay):
    relay.drop_quit = True
    configure(monkeypatch, relay)
    assert await email_service.send_verification_email('person@example.com', 'synthetic-token')
    assert len(relay.messages) == 1


@pytest.mark.parametrize('overrides,match', [
    ({'email_delivery_required': False}, 'EMAIL_DELIVERY_REQUIRED'),
    ({'smtp_starttls': False, 'smtp_use_ssl': False}, 'verified TLS'),
    ({'smtp_host': ''}, 'SMTP_HOST'),
    ({'smtp_username': '', 'smtp_password': ''}, 'authenticated'),
    ({'smtp_password': ''}, 'configured together'),
    ({'smtp_host': 'smtp://user:pass@host'}, 'SMTP_HOST'),
    ({'smtp_from_email': 'a@example.com\r\nBcc: other@example.com'}, 'bare mailbox'),
    ({'smtp_timeout_seconds': 0}, 'SMTP_TIMEOUT_SECONDS'),
    ({'smtp_timeout_seconds': 61}, 'SMTP_TIMEOUT_SECONDS'),
    ({'smtp_max_concurrent_sends': 0}, 'SMTP_MAX_CONCURRENT_SENDS'),
    ({'smtp_max_concurrent_sends': 17}, 'SMTP_MAX_CONCURRENT_SENDS'),
    ({'smtp_use_ssl': True, 'smtp_starttls': True}, 'cannot both'),
])
def test_production_smtp_fails_closed(overrides, match):
    values = _production_settings_kwargs()
    values.update(billing_checkout_enabled=False, **overrides)
    with pytest.raises(ValidationError, match=match):
        Settings(_env_file=None, _secrets_dir=None, **values)


def test_valid_production_tls_and_oidc_only_without_smtp():
    values = _production_settings_kwargs()
    values['billing_checkout_enabled'] = False
    assert Settings(_env_file=None, _secrets_dir=None, **values).smtp_starttls
    values.update(local_auth_enabled=False, email_delivery_required=False,
                  smtp_host='', smtp_from_email='', smtp_username='', smtp_password='',
                  oidc_enabled=True, oidc_client_id='synthetic-id',
                  oidc_discovery_url='https://issuer.example.com/.well-known/openid-configuration')
    assert not Settings(_env_file=None, _secrets_dir=None, **values).email_delivery_available


@pytest.mark.parametrize('recipient', ['a@example.com,b@example.com',
                                     'Name <a@example.com>', 'a@example.com\r\nBcc: b@example.com'])
async def test_envelope_injection_rejected_before_socket(monkeypatch, recipient):
    settings = get_settings()
    monkeypatch.setattr(settings, 'smtp_host', 'smtp.example.com')
    monkeypatch.setattr(settings, 'smtp_from_email', 'security@example.com')
    send = Mock()
    monkeypatch.setattr(email_service, '_send_message', send)
    with pytest.raises(ValueError):
        await email_service.send_email(recipient=recipient, subject='Test', text_body='Test')
    send.assert_not_called()


async def test_capacity_stays_reserved_after_async_cancellation(monkeypatch):
    settings = get_settings()
    for key, value in dict(smtp_host='smtp.example.com', smtp_from_email='security@example.com',
                           smtp_max_concurrent_sends=1, email_delivery_required=True).items():
        monkeypatch.setattr(settings, key, value)
    started, finish = threading.Event(), threading.Event()
    def blocked(message):
        started.set()
        assert finish.wait(3)
    monkeypatch.setattr(email_service, '_send_message', blocked)
    task = asyncio.create_task(email_service.send_verification_email('person@example.com', 'synthetic'))
    try:
        assert await asyncio.to_thread(started.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(EmailDeliveryError, match='capacity'):
            await email_service.send_verification_email('person@example.com', 'synthetic')
    finally:
        finish.set()
        pending = list(email_service._pending_tasks)
        await asyncio.gather(*pending)
    assert email_service._active_sends == 0


async def test_optional_unconfigured_and_failed_delivery_do_not_claim_success(monkeypatch, caplog):
    settings = get_settings()
    monkeypatch.setattr(settings, 'smtp_host', '')
    monkeypatch.setattr(settings, 'email_delivery_required', False)
    assert not await email_service.send_verification_email('person@example.com', 'synthetic')
    monkeypatch.setattr(settings, 'email_delivery_required', True)
    with pytest.raises(EmailDeliveryError, match='not_configured'):
        await email_service.send_verification_email('person@example.com', 'synthetic')
    monkeypatch.setattr(settings, 'smtp_host', 'smtp.example.com')
    monkeypatch.setattr(settings, 'smtp_from_email', 'security@example.com')
    monkeypatch.setattr(settings, 'email_delivery_required', False)
    def fail(message):
        raise TimeoutError('secret-token person@example.com synthetic-password')
    monkeypatch.setattr(email_service, '_send_message', fail)
    assert not await email_service.send_verification_email('person@example.com', 'secret-token')
    assert 'person@example.com' not in caplog.text
    assert 'secret-token' not in caplog.text
    assert 'synthetic-password' not in caplog.text


async def test_html_url_attribute_is_escaped(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'frontend_url', 'https://example.com/a"b')
    captured = {}
    async def capture(**kwargs):
        captured.update(kwargs)
        return True
    monkeypatch.setattr(email_service, 'send_email', capture)
    await email_service.send_verification_email('person@example.com', 'a&b')
    assert '&quot;' in captured['html_body']
    assert 'a%26b' in captured['text_body']


def test_smtp_secret_file_and_deployment_parity(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.delenv('SMTP_PASSWORD', raising=False)
    (tmp_path / 'smtp_password').write_text('synthetic-file-password')
    settings = Settings(_env_file=None, _secrets_dir=tmp_path, smtp_username='synthetic-login')
    assert settings.smtp_password.get_secret_value() == 'synthetic-file-password'
    root = Path(__file__).resolve().parents[2]
    prod = (root / 'docker-compose.prod.yml').read_text()
    assert 'SMTP_PASSWORD:' not in prod
    for key in ('SMTP_TIMEOUT_SECONDS', 'SMTP_MAX_CONCURRENT_SENDS', 'SMTP_SSL_CA_FILE'):
        assert key in prod
    chart = (root / 'charts/fincopilot/values.yaml').read_text()
    for key in ('smtpTimeoutSeconds', 'smtpMaxConcurrentSends', 'emailDeliveryRequired'):
        assert key in chart


def test_probe_default_does_not_send(monkeypatch, relay, capsys):
    settings = configure(monkeypatch, relay)
    monkeypatch.setattr(settings, 'deployment_environment', 'production')
    monkeypatch.setattr(settings, 'local_auth_enabled', False)
    assert verify_production_smtp.main([]) == 0
    assert not relay.messages
    assert b'NOOP' in relay.commands
    assert 'message_sent=false' in capsys.readouterr().out


@pytest.mark.parametrize('args', [['--send-test'], ['--recipient', 'person@example.com']])
def test_probe_send_requires_explicit_pair(args):
    with pytest.raises(SystemExit):
        verify_production_smtp.main(args)


def test_probe_sanitizes_invalid_settings(monkeypatch, capsys):
    def fail():
        raise ValueError('smtp-password person@example.com secret-token')
    monkeypatch.setattr(verify_production_smtp, 'get_settings', fail)
    assert verify_production_smtp.main([]) == 1
    assert capsys.readouterr().err == 'FinCo-Pilot SMTP acceptance: FAIL (internal)\n'


def test_tls_context_checks_hostname_and_minimum_version(monkeypatch):
    settings = Settings(_env_file=None, _secrets_dir=None, smtp_host='smtp.example.com',
                        smtp_from_email='security@example.com', smtp_use_ssl=True, smtp_starttls=False)
    smtp = Mock()
    smtp.ehlo.return_value = (250, b'OK')
    factory = Mock(return_value=smtp)
    monkeypatch.setattr('app.core.smtp_runtime.smtplib.SMTP_SSL', factory)
    with smtp_connection(settings):
        pass
    context = factory.call_args.kwargs['context']
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_probe_explicit_send_is_one_harmless_message(monkeypatch, relay, capsys):
    settings = configure(monkeypatch, relay)
    monkeypatch.setattr(settings, 'deployment_environment', 'production')
    monkeypatch.setattr(settings, 'local_auth_enabled', False)
    assert verify_production_smtp.main(['--send-test', '--recipient', 'person@example.com']) == 0
    assert len(relay.messages) == 1
    assert b'authentication token is included' in relay.messages[0]
    output = capsys.readouterr().out
    assert 'submission=accepted' in output
    assert 'operator_verification_required' in output
    assert 'person@example.com' not in output


def test_probe_refuses_nonproduction_without_socket(monkeypatch, capsys):
    monkeypatch.setattr(get_settings(), 'deployment_environment', 'development')
    assert verify_production_smtp.main([]) == 1
    assert 'production_required' in capsys.readouterr().err


def test_smtp_inventory_discloses_scoped_auth_links_and_all_consumers():
    from app.core.processor_inventory import get_third_party_boundary, BoundaryStatus
    from app.core.secret_management import get_production_secret
    boundary = get_third_party_boundary('smtp_provider')
    assert boundary.status is BoundaryStatus.UNRESOLVED
    assert boundary.sends_secrets_or_credentials
    assert not boundary.sends_financial_data
    assert 'short_lived_authentication_link' in boundary.data_classes
    assert {'backend', 'celery-worker', 'celery-beat', 'migration', 'mcp-server'} <= set(
        get_production_secret('SMTP_PASSWORD').consumers)
