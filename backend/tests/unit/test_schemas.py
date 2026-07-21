import pytest
from pydantic import ValidationError

from app.api.schemas.chat import ChatRequest
from app.api.schemas.document import DocumentResponse
from app.domain.models.document import Document, DocumentStatus


class TestChatRequest:
    def test_valid_chat_request(self):
        request = ChatRequest(question="What are the inclusion criteria?")
        assert request.question == "What are the inclusion criteria?"
        assert request.strict_mode is False
        assert request.provider is None
        assert request.model is None

    def test_chat_request_accepts_provider_and_model(self):
        request = ChatRequest(
            question="What are the inclusion criteria?",
            provider="openai",
            model="gpt-5.4",
        )
        assert request.provider == "openai"
        assert request.model == "gpt-5.4"

    def test_question_must_not_be_empty(self):
        with pytest.raises(ValidationError):
            ChatRequest(question="")

    def test_question_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(question="x" * 2001)


class TestDocumentResponse:
    def test_model_validate_from_domain(self):
        document = Document(
            filename="protocol.pdf",
            content_type="application/pdf",
            status=DocumentStatus.COMPLETED,
        )
        response = DocumentResponse.model_validate(document)
        assert response.filename == "protocol.pdf"
        assert response.status == DocumentStatus.COMPLETED
