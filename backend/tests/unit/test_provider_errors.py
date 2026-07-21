from app.infrastructure.llm.provider_errors import (
    NonRetryableError,
    RetryableError,
    classify_provider_error,
)


class FakeRetryableError(Exception):
    status_code = 429


class FakeNonRetryableError(Exception):
    status_code = 401


class FakeNamedRetryableError(Exception):
    pass


class TestClassifyProviderError:
    def test_classifies_rate_limit_as_retryable(self):
        exc = FakeRetryableError("rate limit")
        classified = classify_provider_error(exc)
        assert isinstance(classified, RetryableError)

    def test_classifies_auth_as_non_retryable(self):
        exc = FakeNonRetryableError("unauthorized")
        classified = classify_provider_error(exc)
        assert isinstance(classified, NonRetryableError)

    def test_classifies_named_errors(self):
        classified = classify_provider_error(FakeNamedRetryableError())
        # Unknown exception names default to retryable.
        assert isinstance(classified, RetryableError)
