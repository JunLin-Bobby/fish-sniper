Code quality constraints (apply to all generated code):
1. NEVER expose API keys in frontend code. All external API calls must go through the FastAPI backend.
2. All async operations must have strict TypeScript interfaces. No `any` types.
3. Handle timeouts and errors gracefully. Provide fallback UI when AI generation fails.
4. Use functional components and separate business logic into custom hooks.
5. All environment variables must be read from `.env` files. Never hardcode secrets.
6. All Python functions must have type hints. Use Pydantic for all request/response validation.
7. Each LangGraph node must log its execution via Langfuse span or generation.
8. Database operations must handle connection errors and return meaningful HTTP status codes.
9. CORS must only allow the configured frontend origin, not wildcard `*`.
10. Generated code must be compatible with Docker multi-stage build and Railway deployment.
11. All code comments must be written in English.
12. All naming must follow Document as Code principles — names must be specific and self-explanatory.
    - Functions: describe the exact action and subject (e.g. `embedFishingLogToVector` not `embed`, `fetchCurrentWeatherByRegion` not `getWeather`, `generateBassLureStrategy` not `generate`)
    - Variables: reflect the exact data they hold (e.g. `retrievedFishingLogList` not `data`, `agentRetryCount` not `count`, `pineconeUpsertResult` not `result`)
    - React hooks: prefix with `use` and describe the resource (e.g. `useBassLureStrategy` not `useData`, `useFishingLogList` not `useLogs`)
    - API route handlers: name after the operation and resource (e.g. `handleCreateFishingLog` not `handleCreate`, `handleGenerateBassStrategy` not `handleStrategy`)
    - Avoid all generic names: `data`, `result`, `item`, `info`, `temp`, `obj`, `handle`, `process`, `manage`
13. All FastAPI route handlers must include complete Swagger documentation using FastAPI's built-in parameters:
    - `summary`: one-line description of what the endpoint does (e.g. `summary="Generate bass lure strategy based on weather and fishing log"`)
    - `description`: multi-line explanation covering purpose, business logic, and any side effects
    - `response_description`: describe what a successful response contains (e.g. `response_description="Returns the generated lure strategy with confidence score"`)
    - All Pydantic request/response models must have `Field(description="...")` on every field so Swagger renders meaningful schema documentation
    - Example:
```python
      @router.post(
          "/strategy/generate",
          summary="Generate bass lure strategy based on weather and fishing log",
          description=(
              "Accepts the current weather condition and a list of recent fishing logs, "
              "runs the LangGraph strategy agent, and returns a recommended lure strategy. "
              "Each invocation creates a new Langfuse trace for observability."
          ),
          response_description="Returns the recommended lure type, color, and confidence score",
      )
      async def handleGenerateBassStrategy(
          request: GenerateBassStrategyRequest,
      ) -> GenerateBassStrategyResponse:
          ...

      class GenerateBassStrategyRequest(BaseModel):
          weatherCondition: str = Field(description="Current weather condition at the fishing location, e.g. 'cloudy', 'sunny'")
          recentFishingLogList: list[FishingLog] = Field(description="List of fishing logs from the past 7 days used as context for strategy generation")
```