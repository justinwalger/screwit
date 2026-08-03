from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check - intentionally unauthenticated so load balancers/orchestrators can call it."""
    return {"status": "ok"}
