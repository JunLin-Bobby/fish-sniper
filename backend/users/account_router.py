"""Account lifecycle routes (delete signed-in user)."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from persistence.deps import PersistenceDep
from persistence.errors import FishSniperPersistenceUnavailableError
from shared_infras.rate_limiting import fish_sniper_api_limiter
from shared_infras.security import FishSniperUserIdDep
from users.schemas import DeleteFishSniperAccountRequestBody

router = APIRouter()


@router.delete(
    "/me",
    summary="Permanently delete the signed-in FishSniper account",
    description=(
        "Deletes the JWT subject user row (cascades preferences and fishing logs). "
        'Requires JSON body `{"confirmation": "Delete"}` (case-sensitive).'
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": 'Missing or invalid confirmation (must be exactly "Delete").',
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database could not delete the account.",
        },
    },
)
@fish_sniper_api_limiter.limit("3/hour")
def handle_delete_fish_sniper_account_request(
    request: Request,
    request_body: DeleteFishSniperAccountRequestBody,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: PersistenceDep,
) -> Response:
    _ = request
    if request_body.confirmation != "Delete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": 'Confirmation must be exactly "Delete"'},
        )

    try:
        user_row = fish_sniper_persistence.fetch_user_row_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
        )
        if user_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "User not found"},
            )

        deleted = fish_sniper_persistence.delete_fish_sniper_user_account_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "User not found"},
            )
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
