from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.integrations.fund_data.catalog import DataSourceEntry, get_data_source, list_data_sources
from app.modules.fund_analytics import models

router = APIRouter(prefix="/api/v1/data-sources", tags=["data-sources"])


def _to_out(entry: DataSourceEntry) -> models.DataSourceOut:
    return models.DataSourceOut(
        id=entry.id,
        name=entry.name,
        status=entry.status,
        providerName=entry.provider_name,
        pythonPackage=entry.python_package,
        packageInstalled=entry.package_installed,
        installCommand=entry.install_command,
        homepage=entry.homepage,
        repository=entry.repository,
        license=entry.license,
        markets=list(entry.markets),
        assetClasses=list(entry.asset_classes),
        dataTypes=list(entry.data_types),
        frequencies=list(entry.frequencies),
        strengths=list(entry.strengths),
        limitations=list(entry.limitations),
        termsNote=entry.terms_note,
    )


@router.get("", response_model=list[models.DataSourceOut])
def data_sources(
    market: str | None = None,
    assetClass: str | None = None,
    status: str | None = None,
) -> list[models.DataSourceOut]:
    entries = list_data_sources(market=market, asset_class=assetClass, status=status)
    return [_to_out(entry) for entry in entries]


@router.get("/{source_id}", response_model=models.DataSourceOut)
def data_source(source_id: str) -> models.DataSourceOut:
    try:
        return _to_out(get_data_source(source_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown data source") from exc
