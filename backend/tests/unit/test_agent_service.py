import pytest

from app.application.services.agent_service import AgentService
from app.domain.models.conversation import Message, MessageRole
from app.domain.value_objects import AgentChunkEvent, AgentDoneEvent, AgentMetadataEvent
from tests.fixtures.fakes import (
    FakeLLMProvider,
    FakeSearchEngine,
    FakeStreamingLLMProvider,
    make_fake_chunk,
)


class TestAgentService:
    @pytest.mark.asyncio
    async def test_search_intent_returns_result(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="The answer is 42."),
        )

        result = await agent.handle("What is the answer?")

        assert result.answer == "The answer is 42."
        assert result.intent == "search"
        assert result.confidence == "high"
        assert len(result.citations) == 1

    @pytest.mark.asyncio
    async def test_classification_failure_falls_back_to_search(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="not valid json"),
        )

        result = await agent.handle("Any question?")

        assert result.intent == "search"

    @pytest.mark.asyncio
    async def test_compare_intent_routes_to_compare_tool(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(
                response='{"intent": "compare", "params": {"document_names": ["a.pdf", "b.pdf"]}}'
            ),
        )

        result = await agent.handle("Compare these two protocols")

        assert result.intent == "compare"

    @pytest.mark.asyncio
    async def test_extract_intent_routes_to_extract_tool(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(
                response='{"intent": "extract", "params": {"document_names": ["protocol.pdf"]}}'
            ),
        )

        result = await agent.handle("Extract the primary endpoint")

        assert result.intent == "extract"

    @pytest.mark.asyncio
    async def test_handle_stream_yields_metadata_chunks_and_done(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeStreamingLLMProvider(chunks=["The ", "answer ", "is ", "42."]),
        )

        events = []
        async for event in agent.handle_stream("What is the answer?"):
            events.append(event)

        assert len(events) == 6  # metadata + 4 chunks + done
        assert isinstance(events[0], AgentMetadataEvent)
        assert events[0].intent == "search"
        assert events[0].confidence == "high"
        assert isinstance(events[1], AgentChunkEvent)
        assert isinstance(events[-1], AgentDoneEvent)
        assert (
            "".join(e.content for e in events if isinstance(e, AgentChunkEvent))
            == "The answer is 42."
        )

    @pytest.mark.asyncio
    async def test_handle_stream_no_chunks_yields_no_info_message(self):
        search_engine = FakeSearchEngine(chunks=[])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeStreamingLLMProvider(chunks=[]),
        )

        events = []
        async for event in agent.handle_stream("What is the answer?"):
            events.append(event)

        assert len(events) == 3  # metadata + 1 chunk + done
        assert isinstance(events[0], AgentMetadataEvent)
        assert isinstance(events[1], AgentChunkEvent)
        assert "don't have enough information" in events[1].content
        assert isinstance(events[2], AgentDoneEvent)

    @pytest.mark.asyncio
    async def test_compare_method_runs_without_routing(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk(document_name="a.pdf")])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="Documents are similar."),
        )

        result = await agent.compare("Compare safety windows", document_names=["a.pdf", "b.pdf"])

        assert result.intent == "compare"
        assert result.answer == "Documents are similar."

    @pytest.mark.asyncio
    async def test_extract_method_runs_without_routing(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk(document_name="protocol.pdf")])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="Primary endpoint: ACR20"),
        )

        result = await agent.extract("Extract endpoints", document_names=["protocol.pdf"])

        assert result.intent == "extract"
        assert result.answer == "Primary endpoint: ACR20"

    @pytest.mark.asyncio
    async def test_clarify_intent_returns_clarify_message(self):
        search_engine = FakeSearchEngine(chunks=[])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response='{"intent": "clarify", "params": {}}'),
        )

        result = await agent.handle("Tell me about the protocol")

        assert result.intent == "clarify"
        assert "upload" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_invalid_params_fall_back_to_search(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response='{"intent": "compare", "params": "not-a-dict"}'),
        )

        result = await agent.handle("Compare these protocols")

        # Should fallback to search because params validation failed.
        assert result.intent == "search"

    @pytest.mark.asyncio
    async def test_document_filter_without_matches_returns_no_info(self):
        # Chunks from other documents must NOT be used to answer a
        # document-scoped question (no silent fallback to unfiltered chunks).
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk(document_name="other.pdf")])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="Documents are similar."),
        )

        result = await agent.compare("Compare safety windows", document_names=["a.pdf", "b.pdf"])

        assert result.intent == "compare"
        assert "don't have enough information" in result.answer
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_document_filter_matches_human_readable_names(self):
        # The router returns human names, not exact filenames: "ICH E9(R1)"
        # must match chunks ingested from "ICH_E9_R1_Estimands.pdf".
        search_engine = FakeSearchEngine(
            chunks=[make_fake_chunk(document_name="ICH_E9_R1_Estimands.pdf")]
        )
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(response="Compared both guidelines."),
        )

        result = await agent.compare("Compare ITT vs estimands", document_names=["ICH E9(R1)"])

        assert result.intent == "compare"
        assert result.answer == "Compared both guidelines."


class TestConversationMemory:
    @staticmethod
    def _history() -> list[Message]:
        return [
            Message(
                role=MessageRole.USER,
                content="What is the primary objective of NCT04084769?",
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="The primary objective is to demonstrate vaccine seroresponse.",
            ),
        ]

    @pytest.mark.asyncio
    async def test_history_is_included_in_answer_messages(self):
        llm = FakeLLMProvider(response="More details about the objective.")
        agent = AgentService(
            search_engine=FakeSearchEngine(chunks=[make_fake_chunk()]),
            llm_provider=llm,
        )

        await agent.handle("give me more details", history=self._history())

        # Last complete call is the answer-generation call (after
        # contextualization and intent classification).
        answer_messages = llm.complete_calls[-1]
        assert answer_messages[0]["role"] == "system"
        assert answer_messages[1] == {
            "role": "user",
            "content": "What is the primary objective of NCT04084769?",
        }
        assert answer_messages[2] == {
            "role": "assistant",
            "content": "The primary objective is to demonstrate vaccine seroresponse.",
        }
        assert answer_messages[-1] == {"role": "user", "content": "give me more details"}

    @pytest.mark.asyncio
    async def test_contextualized_question_is_used_for_retrieval(self):
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FakeLLMProvider(
                response="Tell me more about the primary objective of NCT04084769"
            ),
        )

        await agent.handle("give me more details", history=self._history())

        assert search_engine.queries == ["Tell me more about the primary objective of NCT04084769"]

    @pytest.mark.asyncio
    async def test_no_history_skips_contextualization(self):
        llm = FakeLLMProvider(response="The answer is 42.")
        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(search_engine=search_engine, llm_provider=llm)

        await agent.handle("What is the answer?")

        # Only intent classification + answer generation, no rewriting call.
        assert len(llm.complete_calls) == 2
        assert search_engine.queries == ["What is the answer?"]

    @pytest.mark.asyncio
    async def test_contextualization_failure_falls_back_to_original_question(self):
        class FlakyLLMProvider(FakeLLMProvider):
            def __init__(self) -> None:
                super().__init__(response="The answer is 42.")
                self._failed = False

            async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
                if not self._failed:
                    self._failed = True
                    raise RuntimeError("provider boom")
                return await super().complete(messages, tools, temperature, max_tokens)

        search_engine = FakeSearchEngine(chunks=[make_fake_chunk()])
        agent = AgentService(
            search_engine=search_engine,
            llm_provider=FlakyLLMProvider(),
        )

        result = await agent.handle("give me more details", history=self._history())

        assert result.answer == "The answer is 42."
        assert search_engine.queries == ["give me more details"]
