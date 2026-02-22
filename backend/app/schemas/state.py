"""
Global State Schema.
Implements the Strict State Schema from the roadmap (Rule AR2, AR3).

CRITICAL: Every key is predefined. If an agent tries to write a variable
that isn't in the schema, the system kills the process.
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .event import EventResult
from .search import SearchRequest


class AgentPhase(str, Enum):
    """Current phase of the agent workflow."""

    IDLE = "idle"
    PROMPT_ENGINEERING = "prompt_engineering"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    PROCESSING = "processing"
    WEATHER_CHECK = "weather_check"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class ToolCallLog(BaseModel):
    """Log entry for a single tool call (Rule A5)."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_name: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    success: bool
    result_summary: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    source_url: str | None = None


class LLMCall(BaseModel):
    """Log entry for LLM API calls."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str  # claude, openai, gemini, perplexity
    model: str
    purpose: str  # prompt_engineering, processing, etc.
    input_tokens: int | None = None
    output_tokens: int | None = None
    success: bool
    error: str | None = None


class SearchState(BaseModel):
    """State for search operations."""

    perplexity_results: list[dict[str, Any]] = Field(default_factory=list)
    serpapi_results: list[dict[str, Any]] = Field(default_factory=list)
    serper_results: list[dict[str, Any]] = Field(default_factory=list)
    firecrawl_results: list[dict[str, Any]] = Field(default_factory=list)
    exa_results: list[dict[str, Any]] = Field(default_factory=list)
    ticketmaster_results: list[dict[str, Any]] = Field(default_factory=list)
    scraped_results: list[dict[str, Any]] = Field(default_factory=list)
    merged_results: list[dict[str, Any]] = Field(default_factory=list)
    perplexity_success: bool = False
    serpapi_success: bool = False
    serper_success: bool = False
    firecrawl_success: bool = False
    exa_success: bool = False
    ticketmaster_success: bool = False
    scraper_success: bool = False


class WeatherState(BaseModel):
    """State for weather checks."""

    checked: bool = False
    location: str | None = None
    date: str | None = None
    conditions: dict[str, Any] = Field(default_factory=dict)
    outdoor_safe: bool = True


class GlobalState(BaseModel):
    """
    Global State Object - Single Source of Truth.

    RULES:
    - AR2: All state changes go through this object
    - AR3: Reject any write to undefined schema keys

    Every field is predefined. No dynamic keys allowed.
    """

    # === Request Context ===
    request_id: str = Field(..., description="Unique request identifier")
    user_id: str | None = Field(default=None, description="User ID if authenticated")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # === Search Request ===
    search_request: SearchRequest | None = None

    # === Agent Workflow ===
    phase: AgentPhase = AgentPhase.IDLE
    phase_history: list[tuple[AgentPhase, datetime]] = Field(default_factory=list)

    # === Generated Prompts ===
    search_prompt_perplexity: str | None = None
    search_prompt_serpapi: str | None = None
    search_prompt_scraper: str | None = None

    # === Search Results ===
    search_state: SearchState = Field(default_factory=SearchState)

    # === Weather ===
    weather_state: WeatherState = Field(default_factory=WeatherState)

    # === Processed Events ===
    raw_events: list[dict[str, Any]] = Field(default_factory=list)
    validated_events: list[EventResult] = Field(default_factory=list)
    rejected_events: list[dict[str, Any]] = Field(
        default_factory=list, description="Events that failed validation"
    )
    final_events: list[EventResult] = Field(default_factory=list)

    # === Tool Call Logs (Rule A5) ===
    tool_calls: list[ToolCallLog] = Field(default_factory=list)
    llm_calls: list[LLMCall] = Field(default_factory=list)

    # === Error Tracking ===
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # === Performance ===
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_duration_ms: float | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_unknown_keys(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Reject any keys not defined in the schema (Rule AR3).
        This prevents agents from writing arbitrary data.
        """
        allowed_keys = set(cls.model_fields.keys())
        provided_keys = set(values.keys())
        unknown_keys = provided_keys - allowed_keys

        if unknown_keys:
            raise ValueError(
                f"SCHEMA VIOLATION (Rule AR3): Unknown keys not allowed: {unknown_keys}. "
                f"Allowed keys: {allowed_keys}"
            )

        return values

    def set_phase(self, new_phase: AgentPhase) -> None:
        """Transition to a new phase with logging."""
        self.phase_history.append((self.phase, datetime.utcnow()))
        self.phase = new_phase
        self.updated_at = datetime.utcnow()

    def log_tool_call(
        self,
        tool_name: str,
        action: str,
        params: dict[str, Any] | None = None,
        success: bool = True,
        result_summary: str | None = None,
        error: str | None = None,
        duration_ms: float | None = None,
        source_url: str | None = None,
    ) -> None:
        """Log a tool call (Rule A5)."""
        self.tool_calls.append(
            ToolCallLog(
                tool_name=tool_name,
                action=action,
                params=params or {},
                success=success,
                result_summary=result_summary,
                error=error,
                duration_ms=duration_ms,
                source_url=source_url,
            )
        )
        self.updated_at = datetime.utcnow()

    def log_llm_call(
        self,
        provider: str,
        model: str,
        purpose: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log an LLM API call."""
        self.llm_calls.append(
            LLMCall(
                provider=provider,
                model=model,
                purpose=purpose,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=success,
                error=error,
            )
        )
        self.updated_at = datetime.utcnow()

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(f"[{datetime.utcnow().isoformat()}] {error}")
        self.updated_at = datetime.utcnow()

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(f"[{datetime.utcnow().isoformat()}] {warning}")
        self.updated_at = datetime.utcnow()

    def finalize(self) -> None:
        """Mark the state as finalized and calculate duration."""
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.total_duration_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000
        self.set_phase(AgentPhase.COMPLETED)


class StateManager:
    """
    Manager for GlobalState operations.
    Ensures all state modifications go through validated methods.
    """

    def __init__(self, request_id: str, user_id: str | None = None):
        self.state = GlobalState(
            request_id=request_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
        )

    def get_state(self) -> GlobalState:
        """Get the current state (read-only view)."""
        return self.state

    def update(self, **kwargs: Any) -> None:
        """
        Update state with validation.
        Only allows updates to defined fields.
        """
        for key, value in kwargs.items():
            if key not in GlobalState.model_fields:
                raise ValueError(
                    f"SCHEMA VIOLATION (Rule AR3): Cannot update unknown key '{key}'"
                )
            setattr(self.state, key, value)
        self.state.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Export state as dictionary."""
        return self.state.model_dump()

    def to_json(self) -> str:
        """Export state as JSON string."""
        return self.state.model_dump_json(indent=2)
