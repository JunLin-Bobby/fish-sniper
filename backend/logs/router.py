"""Fishing logs CRUD routes (P3 + P4 Part 1 vector wiring)."""

import hashlib
import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from deps import (
    FishSniperEmbeddingClientDep,
    PersistenceDep,
    ReferenceTimeUtcCallableDep,
)
from embedding.fish_sniper_log_embedding_text import (
    EMBEDDING_TEXT_VERSION,
    compose_fishing_log_embedding_text,
)
from embedding.port import FishSniperEmbeddingUnavailableError
from error_envelopes import service_temporarily_unavailable_response
from logs.schemas import (
    CreateFishingLogResponseBody,
    CreateOrUpdateFishingLogRequestBody,
    FishingLogResponseBody,
)
from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import FishSniperFishingLogRow
from rate_limiting import fish_sniper_api_limiter
from security import FishSniperUserIdDep

logger = logging.getLogger(__name__)

router = APIRouter()


def _embed_log_text_or_return_none_on_transient_failure(
    *,
    embedding_client,
    request_body: CreateOrUpdateFishingLogRequestBody,
) -> list[float] | None:
    """Compose the embedding text and call Gemini; degrade to None on transient failure."""

    text = compose_fishing_log_embedding_text(
        fishing_location=request_body.fishing_location,
        fishing_scene=request_body.fishing_scene,
        target_species=request_body.target_species,
        water_depth_m=request_body.water_depth_m,
        lure_type=request_body.lure_type,
        lure_color=request_body.lure_color,
        retrieve_speed=request_body.retrieve_speed,
        caught_count=request_body.caught_count,
        weight_lb=request_body.weight_lb,
        length_cm=request_body.length_cm,
        temperature_c=request_body.temperature_c,
        wind_speed_ms=request_body.wind_speed_ms,
        pressure_hpa=request_body.pressure_hpa,
        condition_code=request_body.condition_code,
        notes=request_body.notes,
    )
    try:
        return embedding_client.embed(text=text)
    except FishSniperEmbeddingUnavailableError:
        logger.warning(
            "gemini_embedding_unavailable_degrading_to_pending",
            extra={"embedding_text_version": EMBEDDING_TEXT_VERSION},
        )
        return None


def _weak_etag_from_fingerprint(*, fingerprint: str) -> str:
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f'W/"{digest}"'


def _if_none_match_includes_etag(*, if_none_match: str | None, etag: str) -> bool:
    if if_none_match is None:
        return False
    candidates = [part.strip() for part in if_none_match.split(",") if part.strip()]
    return etag in candidates


def _map_row_to_response_body(row: FishSniperFishingLogRow) -> FishingLogResponseBody:
    return FishingLogResponseBody(
        log_id=row.log_id,
        date=row.log_date,
        fishing_location=row.fishing_location,
        fishing_scene=row.fishing_scene,
        target_species=row.target_species,
        water_depth_m=row.water_depth_m,
        lure_type=row.lure_type,
        lure_color=row.lure_color,
        retrieve_speed=row.retrieve_speed,
        caught_count=row.caught_count,
        weight_lb=row.weight_lb,
        length_cm=row.length_cm,
        temperature_c=row.temperature_c,
        wind_speed_ms=row.wind_speed_ms,
        pressure_hpa=row.pressure_hpa,
        condition_code=row.condition_code,
        notes=row.notes,
        embedding_status=row.embedding_status,
        embedding_text_version=row.embedding_text_version,
        created_at=row.created_at_utc,
        updated_at=row.updated_at_utc,
    )


def _raise_logs_database_unavailable(exc: FishSniperPersistenceUnavailableError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"error": "Database is temporarily unavailable"},
    ) from exc


def _build_logs_database_unavailable_response() -> JSONResponse:
    return service_temporarily_unavailable_response(retry_after_seconds=30)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a fishing log for the signed-in user",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "INVALID_PAYLOAD."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "SERVICE_TEMPORARILY_UNAVAILABLE — DB write failed twice.",
        },
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_create_fishing_log_request(
    request: Request,
    request_body: CreateOrUpdateFishingLogRequestBody,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
    embedding_client: FishSniperEmbeddingClientDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
) -> Response:
    _ = request
    reference_time_utc = reference_time_utc_callable()
    embedding_vector = _embed_log_text_or_return_none_on_transient_failure(
        embedding_client=embedding_client,
        request_body=request_body,
    )

    insert_kwargs = {
        "fish_sniper_user_id": fish_sniper_user_id,
        "log_date": request_body.date,
        "fishing_location": request_body.fishing_location,
        "fishing_scene": request_body.fishing_scene,
        "target_species": request_body.target_species,
        "water_depth_m": request_body.water_depth_m,
        "lure_type": request_body.lure_type,
        "lure_color": request_body.lure_color,
        "retrieve_speed": request_body.retrieve_speed,
        "caught_count": request_body.caught_count,
        "weight_lb": request_body.weight_lb,
        "length_cm": request_body.length_cm,
        "temperature_c": request_body.temperature_c,
        "wind_speed_ms": request_body.wind_speed_ms,
        "pressure_hpa": request_body.pressure_hpa,
        "condition_code": request_body.condition_code,
        "notes": request_body.notes,
        "embedding": embedding_vector,
        "embedding_text_version": EMBEDDING_TEXT_VERSION,
        "reference_time_utc": reference_time_utc,
    }

    try:
        log_id = fish_sniper_persistence.insert_fishing_log_for_user_id(**insert_kwargs)
    except FishSniperPersistenceUnavailableError as first_exc:
        logger.warning(
            "fishing_log_insert_first_attempt_failed_retrying",
            extra={"reason": str(first_exc)},
        )
        try:
            log_id = fish_sniper_persistence.insert_fishing_log_for_user_id(**insert_kwargs)
        except FishSniperPersistenceUnavailableError as second_exc:
            logger.error(
                "fishing_log_insert_failed_after_retry",
                extra={"reason": str(second_exc)},
            )
            return _build_logs_database_unavailable_response()

    payload = CreateFishingLogResponseBody(log_id=log_id).model_dump(mode="json")
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder(payload))


@router.get(
    "",
    response_model=list[FishingLogResponseBody],
    summary="List fishing logs for the signed-in user",
    responses={
        status.HTTP_304_NOT_MODIFIED: {"description": "List unchanged (ETag match)."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable."},
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_list_fishing_logs_request(
    request: Request,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
    if_none_match: str | None = Header(default=None),
) -> Response:
    _ = request
    try:
        fingerprint = fish_sniper_persistence.fetch_fishing_logs_list_etag_fingerprint_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
        )
        etag = _weak_etag_from_fingerprint(fingerprint=fingerprint)
        if _if_none_match_includes_etag(if_none_match=if_none_match, etag=etag):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

        rows = fish_sniper_persistence.list_fishing_logs_for_user_id_ordered_by_date_desc(
            fish_sniper_user_id=fish_sniper_user_id,
        )
    except FishSniperPersistenceUnavailableError as exc:
        _raise_logs_database_unavailable(exc)

    payload = jsonable_encoder(
        [_map_row_to_response_body(row).model_dump(mode="json") for row in rows]
    )
    return JSONResponse(content=payload, headers={"ETag": etag})


@router.get(
    "/{log_id}",
    response_model=FishingLogResponseBody,
    summary="Fetch one fishing log for the signed-in user",
    responses={
        status.HTTP_304_NOT_MODIFIED: {"description": "Log unchanged (ETag match)."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_404_NOT_FOUND: {"description": "Log not found."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable."},
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_get_fishing_log_request(
    request: Request,
    log_id: UUID,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
    if_none_match: str | None = Header(default=None),
) -> Response:
    _ = request
    try:
        fingerprint = fish_sniper_persistence.fetch_fishing_log_etag_fingerprint_for_user_id(
            log_id=log_id,
            fish_sniper_user_id=fish_sniper_user_id,
        )
        if fingerprint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found"},
            )

        etag = _weak_etag_from_fingerprint(fingerprint=fingerprint)
        if _if_none_match_includes_etag(if_none_match=if_none_match, etag=etag):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

        row = fish_sniper_persistence.fetch_fishing_log_by_id_for_user_id(
            log_id=log_id,
            fish_sniper_user_id=fish_sniper_user_id,
        )
    except FishSniperPersistenceUnavailableError as exc:
        _raise_logs_database_unavailable(exc)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not found"})

    payload = jsonable_encoder(_map_row_to_response_body(row).model_dump(mode="json"))
    return JSONResponse(content=payload, headers={"ETag": etag})


@router.patch(
    "/{log_id}",
    summary="Replace fields on an owned fishing log",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "INVALID_PAYLOAD."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_404_NOT_FOUND: {"description": "Log not found."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "SERVICE_TEMPORARILY_UNAVAILABLE — DB write failed twice.",
        },
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_update_fishing_log_request(
    request: Request,
    log_id: UUID,
    request_body: CreateOrUpdateFishingLogRequestBody,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
    embedding_client: FishSniperEmbeddingClientDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
) -> Response:
    _ = request
    reference_time_utc = reference_time_utc_callable()
    embedding_vector = _embed_log_text_or_return_none_on_transient_failure(
        embedding_client=embedding_client,
        request_body=request_body,
    )

    update_kwargs = {
        "log_id": log_id,
        "fish_sniper_user_id": fish_sniper_user_id,
        "log_date": request_body.date,
        "fishing_location": request_body.fishing_location,
        "fishing_scene": request_body.fishing_scene,
        "target_species": request_body.target_species,
        "water_depth_m": request_body.water_depth_m,
        "lure_type": request_body.lure_type,
        "lure_color": request_body.lure_color,
        "retrieve_speed": request_body.retrieve_speed,
        "caught_count": request_body.caught_count,
        "weight_lb": request_body.weight_lb,
        "length_cm": request_body.length_cm,
        "temperature_c": request_body.temperature_c,
        "wind_speed_ms": request_body.wind_speed_ms,
        "pressure_hpa": request_body.pressure_hpa,
        "condition_code": request_body.condition_code,
        "notes": request_body.notes,
        "embedding": embedding_vector,
        "embedding_text_version": EMBEDDING_TEXT_VERSION,
        "reference_time_utc": reference_time_utc,
    }

    try:
        updated = fish_sniper_persistence.update_fishing_log_for_user_id(**update_kwargs)
    except FishSniperPersistenceUnavailableError as first_exc:
        logger.warning(
            "fishing_log_update_first_attempt_failed_retrying",
            extra={"reason": str(first_exc)},
        )
        try:
            updated = fish_sniper_persistence.update_fishing_log_for_user_id(**update_kwargs)
        except FishSniperPersistenceUnavailableError as second_exc:
            logger.error(
                "fishing_log_update_failed_after_retry",
                extra={"reason": str(second_exc)},
            )
            return _build_logs_database_unavailable_response()

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not found"})

    payload = _map_row_to_response_body(updated).model_dump(mode="json")
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(payload))


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete an owned fishing log",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_404_NOT_FOUND: {"description": "Log not found."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable."},
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_delete_fishing_log_request(
    request: Request,
    log_id: UUID,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
) -> Response:
    _ = request
    try:
        deleted = fish_sniper_persistence.delete_fishing_log_for_user_id(
            log_id=log_id,
            fish_sniper_user_id=fish_sniper_user_id,
        )
    except FishSniperPersistenceUnavailableError as exc:
        _raise_logs_database_unavailable(exc)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Not found"})

    return Response(status_code=status.HTTP_204_NO_CONTENT)
