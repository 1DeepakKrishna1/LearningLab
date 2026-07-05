"""Public organization config endpoint (branding + logo). No auth required."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import org_config

router = APIRouter()


@router.get("")
def get_org_config():
    logo = org_config.has_logo()
    logo_url = None
    if logo:
        # Append a content-based version so the URL changes when the logo file
        # changes, defeating browser caching of the fixed /config/logo path.
        logo_url = f"/config/logo?v={org_config.get_logo_version()}"
    return {
        "org_name": org_config.get_org_name(),
        "org_domain": org_config.get_org_domain(),
        "has_logo": logo,
        "logo_url": logo_url,
    }


@router.get("/logo")
def get_org_logo():
    path = org_config.get_logo_path()
    if not path:
        raise HTTPException(status_code=404, detail="No logo configured")
    return FileResponse(
        path,
        media_type=org_config.get_logo_media_type(),
        headers={"Cache-Control": "no-cache"},
    )
