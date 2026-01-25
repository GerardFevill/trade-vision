"""Alert routes - CRUD for alerts and alert history"""
from fastapi import APIRouter, HTTPException, Query, Path, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.alert_service import alert_service
from models import Alert, AlertHistory
from config.settings import settings
from config.alerts import AlertType, AlertCondition, AlertStatus

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class AlertCreate(BaseModel):
    """Alert creation request"""
    account_id: int
    alert_type: str
    condition: str
    threshold: float
    message: str | None = None


class AlertUpdate(BaseModel):
    """Alert update request"""
    threshold: float | None = None
    message: str | None = None
    condition: str | None = None
    status: str | None = None


@router.get("/alerts", response_model=list[Alert])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_alerts(
    request: Request,
    account_id: int | None = Query(default=None, description="Filter by account ID"),
    status: str | None = Query(default=None, description="Filter by status (active, triggered, disabled)")
):
    """Get all alerts, optionally filtered"""
    return alert_service.get_alerts(account_id, status)


@router.get("/alerts/{alert_id}", response_model=Alert)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_alert(
    request: Request,
    alert_id: int = Path(..., description="Alert ID")
):
    """Get a specific alert by ID"""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@router.post("/alerts", response_model=dict)
@limiter.limit("30/minute")
async def create_alert(
    request: Request,
    alert_data: AlertCreate
):
    """Create a new alert"""
    # Validate alert_type and condition
    if alert_data.alert_type not in [e.value for e in AlertType]:
        raise HTTPException(400, f"Invalid alert_type. Must be one of: {[e.value for e in AlertType]}")
    if alert_data.condition not in [e.value for e in AlertCondition]:
        raise HTTPException(400, f"Invalid condition. Must be one of: {[e.value for e in AlertCondition]}")

    alert = Alert(
        account_id=alert_data.account_id,
        alert_type=alert_data.alert_type,
        condition=alert_data.condition,
        threshold=alert_data.threshold,
        message=alert_data.message
    )

    alert_id = alert_service.create_alert(alert)
    if not alert_id:
        raise HTTPException(500, "Failed to create alert")

    return {"id": alert_id, "message": "Alert created successfully"}


@router.put("/alerts/{alert_id}", response_model=dict)
@limiter.limit("30/minute")
async def update_alert(
    request: Request,
    alert_id: int = Path(..., description="Alert ID"),
    alert_data: AlertUpdate = None
):
    """Update an existing alert"""
    if not alert_data:
        raise HTTPException(400, "No update data provided")

    updates = {}
    if alert_data.threshold is not None:
        updates["threshold"] = alert_data.threshold
    if alert_data.message is not None:
        updates["message"] = alert_data.message
    if alert_data.condition is not None:
        if alert_data.condition not in [e.value for e in AlertCondition]:
            raise HTTPException(400, f"Invalid condition. Must be one of: {[e.value for e in AlertCondition]}")
        updates["condition"] = alert_data.condition
    if alert_data.status is not None:
        if alert_data.status not in [e.value for e in AlertStatus]:
            raise HTTPException(400, f"Invalid status. Must be one of: {[e.value for e in AlertStatus]}")
        updates["status"] = alert_data.status

    if not updates:
        raise HTTPException(400, "No valid fields to update")

    success = alert_service.update_alert(alert_id, **updates)
    if not success:
        raise HTTPException(404, "Alert not found or update failed")

    return {"message": "Alert updated successfully"}


@router.delete("/alerts/{alert_id}", response_model=dict)
@limiter.limit("30/minute")
async def delete_alert(
    request: Request,
    alert_id: int = Path(..., description="Alert ID")
):
    """Delete an alert"""
    success = alert_service.delete_alert(alert_id)
    if not success:
        raise HTTPException(404, "Alert not found")
    return {"message": "Alert deleted successfully"}


@router.post("/alerts/{alert_id}/reset", response_model=dict)
@limiter.limit("30/minute")
async def reset_alert(
    request: Request,
    alert_id: int = Path(..., description="Alert ID")
):
    """Reset a triggered alert back to active status"""
    success = alert_service.reset_alert(alert_id)
    if not success:
        raise HTTPException(404, "Alert not found")
    return {"message": "Alert reset to active"}


@router.get("/alerts/history", response_model=list[AlertHistory])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_alert_history(
    request: Request,
    account_id: int | None = Query(default=None, description="Filter by account ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records")
):
    """Get alert trigger history"""
    return alert_service.get_alert_history(account_id, limit)


@router.get("/alerts/types")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_alert_types(request: Request):
    """Get available alert types and conditions"""
    return {
        "types": [{"value": e.value, "label": e.name.replace("_", " ").title()} for e in AlertType],
        "conditions": [{"value": e.value, "label": e.name.title()} for e in AlertCondition],
        "statuses": [{"value": e.value, "label": e.name.title()} for e in AlertStatus]
    }
