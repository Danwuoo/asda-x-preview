import pytest
from src.core.prompt_context import (
    LogParser,
    FreeTextParser,
    InjectionSanitizer,
)

def test_log_parser_entity_extraction():
    log_parser = LogParser()
    log_message = "User 'admin' logged in from 192.168.1.1 with request_id=xyz-123"
    context = log_parser.parse(log_message)

    assert len(context.entities) == 4  # message, ip, user, request_id

    entity_types = [e.type for e in context.entities]
    assert "ip" in entity_types
    assert "user" in entity_types
    assert "request_id" in entity_types

    ip_entity = next(e for e in context.entities if e.type == "ip")
    assert ip_entity.value == "192.168.1.1"

    user_entity = next(e for e in context.entities if e.type == "user")
    assert user_entity.value == "admin"

    id_entity = next(e for e in context.entities if e.type == "request_id")
    assert id_entity.value == "xyz-123"

def test_free_text_parser_ip_extraction():
    text_parser = FreeTextParser()
    text = "A suspicious connection was detected from 10.0.0.5."
    context = text_parser.parse(text)

    assert any(e.type == "ip" and e.value == "10.0.0.5" for e in context.entities)

@pytest.mark.parametrize("malicious_input", [
    "{{ config.SECRET_KEY }}",
    "<script>alert('XSS')</script>",
    "javascript:void(0)",
    "<img src='x' onerror='alert(1)'>",
    "exec('import os; os.system(\"ls\")')",
    "__import__('os').system('ls')",
])
def test_injection_sanitizer_expanded(malicious_input):
    sanitizer = InjectionSanitizer()
    with pytest.raises(ValueError, match="Possible prompt injection detected"):
        sanitizer.check(malicious_input)

def test_injection_sanitizer_mixed_language():
    sanitizer = InjectionSanitizer()
    # This test is tricky because langdetect is not perfect.
    # A mix of English and Cyrillic characters.
    text = "This is a test with some Cyrillic characters: Пример"
    # This should not raise an error, but in a real-world scenario,
    # we might want to log a warning.
    sanitizer.check(text)
