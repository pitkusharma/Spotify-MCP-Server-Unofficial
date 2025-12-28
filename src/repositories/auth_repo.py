from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.persistance.auth import Client


async def create_client(
    db: AsyncSession,
    *,
    client_id: str,
    issued_at: int,
    client_name: str,
    redirect_uris: list[str],
    grant_types: list[str],
    response_types: list[str],
    scope: str | None,
) -> Client:
    client = Client(
        client_id=client_id,
        client_id_issued_at=issued_at,
        client_name=client_name,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        response_types=response_types,
        token_endpoint_auth_method="none",
        scope=scope,
    )

    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def get_client_by_id(
    db: AsyncSession,
    client_id: str,
) -> Client | None:
    stmt = select(Client).where(Client.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
