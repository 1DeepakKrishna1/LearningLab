"""Pipeline orchestrator: input guardrails → LLM → output guardrails."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, List, Optional

from guardrails.models.types import GuardrailResult, GuardrailStatus, PipelineContext
from guardrails.registry.registry import GuardrailRegistry
from guardrails.utils.exceptions import PipelineBlockedError

logger = logging.getLogger(__name__)

LLMInvokeFn = Callable[[str], Awaitable[str]]


class GuardrailExecutor:
    """Runs the full guardrail pipeline for a single request.

    Bitmask parameters control which guardrails are active:
      - *input_mapped_number* — bitmask for input (pre-LLM) guardrails
      - *output_mapped_number* — bitmask for output (post-LLM) guardrails

    A guardrail with sequence_id N is active when::

        mapped_number & N != 0
    """

    def __init__(
        self,
        registry: GuardrailRegistry,
        input_mapped_number: int = 0xFFFF,
        output_mapped_number: int = 0xFFFF,
        block_on_input_failure: bool = True,
        block_on_output_failure: bool = False,
        max_concurrent: int = 4,
    ) -> None:
        self.registry = registry
        self.input_mapped_number = input_mapped_number
        self.output_mapped_number = output_mapped_number
        self.block_on_input_failure = block_on_input_failure
        self.block_on_output_failure = block_on_output_failure
        self._semaphore = asyncio.Semaphore(max_concurrent)

    # ------------------------------------------------------------------
    # Input phase (sequential — each guardrail may modify content)
    # ------------------------------------------------------------------

    async def run_input_guardrails(
        self, context: PipelineContext
    ) -> List[GuardrailResult]:
        guardrails = self.registry.get_input_guardrails(self.input_mapped_number)
        content = context.effective_input
        results: List[GuardrailResult] = []

        for guardrail in guardrails:
            async with self._semaphore:
                result = await guardrail.execute(content, context)
            results.append(result)

            if result.modified_content is not None:
                context.sanitized_input = result.modified_content
                content = result.modified_content

            if result.failed and self.block_on_input_failure:
                context.input_results.extend(results)
                logger.warning(
                    "Pipeline blocked at input phase",
                    extra={
                        "guardrail": guardrail.name,
                        "correlation_id": context.correlation_id,
                        "reason": result.message,
                    },
                )
                raise PipelineBlockedError([result.guardrail_name])

        context.input_results.extend(results)
        return results

    # ------------------------------------------------------------------
    # Output phase (sequential — guardrails may refine content)
    # ------------------------------------------------------------------

    async def run_output_guardrails(
        self, context: PipelineContext
    ) -> List[GuardrailResult]:
        guardrails = self.registry.get_output_guardrails(self.output_mapped_number)
        content = context.llm_response or ""
        results: List[GuardrailResult] = []
        failed: List[str] = []

        for guardrail in guardrails:
            async with self._semaphore:
                result = await guardrail.execute(content, context)
            results.append(result)

            if result.modified_content is not None:
                context.final_output = result.modified_content
                content = result.modified_content

            if result.failed:
                failed.append(result.guardrail_name)

        context.output_results.extend(results)

        if context.final_output is None:
            context.final_output = context.llm_response

        if failed and self.block_on_output_failure:
            raise PipelineBlockedError(failed)

        return results

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def execute_pipeline(
        self,
        user_input: str,
        llm_invoke: Optional[LLMInvokeFn] = None,
    ) -> PipelineContext:
        """Run the end-to-end guardrail pipeline.

        Args:
            user_input: Raw user prompt.
            llm_invoke: Async callable that accepts the (possibly sanitised) prompt
                        and returns the LLM response string.  If *None*, no LLM
                        call is made and output guardrails are skipped.

        Returns:
            Populated :class:`PipelineContext` with all results attached.

        Raises:
            PipelineBlockedError: If an input guardrail fails and
                *block_on_input_failure* is True, or an output guardrail fails
                and *block_on_output_failure* is True.
        """
        context = PipelineContext(original_input=user_input)
        logger.info(
            "Pipeline started",
            extra={
                "correlation_id": context.correlation_id,
                "input_length": len(user_input),
                "input_mask": bin(self.input_mapped_number),
                "output_mask": bin(self.output_mapped_number),
            },
        )

        await self.run_input_guardrails(context)

        if llm_invoke is not None:
            logger.debug(
                "Invoking LLM", extra={"correlation_id": context.correlation_id}
            )
            context.llm_response = await llm_invoke(context.effective_input)

        if context.llm_response is not None:
            await self.run_output_guardrails(context)

        if context.final_output is None:
            context.final_output = context.llm_response

        logger.info(
            "Pipeline complete",
            extra={
                "correlation_id": context.correlation_id,
                "input_guardrails": len(context.input_results),
                "output_guardrails": len(context.output_results),
                "input_passed": context.input_passed,
                "output_passed": context.output_passed,
            },
        )
        return context
