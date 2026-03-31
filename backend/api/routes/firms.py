"""Firm & Profile management routes"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from db.repositories import FirmRepository
from models import (
    Firm, FirmCreate, Profile, ProfileCreate, FirmWithProfiles
)

router = APIRouter()
repo = FirmRepository()


# --- Firms ---

@router.get("/firms", response_model=list[Firm])
async def list_firms():
    """List all firms"""
    return repo.list_firms()


@router.post("/firms", response_model=Firm)
async def create_firm(request: FirmCreate):
    """Create a new firm"""
    firm = repo.create_firm(name=request.name)
    if not firm:
        raise HTTPException(500, "Failed to create firm (name may already exist)")
    return firm


@router.get("/firms/{firm_id}", response_model=FirmWithProfiles)
async def get_firm_with_profiles(
    firm_id: int = Path(..., description="Firm ID")
):
    """Get firm with all its profiles"""
    firm = repo.get_firm_with_profiles(firm_id)
    if not firm:
        raise HTTPException(404, f"Firm {firm_id} not found")
    return firm


@router.delete("/firms/{firm_id}")
async def delete_firm(
    firm_id: int = Path(..., description="Firm ID")
):
    """Delete a firm and all its profiles (cascade)"""
    success = repo.delete_firm(firm_id)
    if not success:
        raise HTTPException(404, f"Firm {firm_id} not found")
    return {"message": f"Firm {firm_id} deleted"}


# --- Profiles ---

@router.get("/profiles", response_model=list[Profile])
async def list_profiles(
    firm_id: Optional[int] = Query(default=None, description="Filter by firm")
):
    """List profiles, optionally filtered by firm"""
    return repo.list_profiles(firm_id)


@router.get("/profiles/names", response_model=list[str])
async def list_profile_names():
    """Get profile names for client dropdowns (excludes default profiles)"""
    return repo.list_profile_names()


@router.post("/profiles", response_model=Profile)
async def create_profile(request: ProfileCreate):
    """Create a new profile"""
    profile = repo.create_profile(
        name=request.name,
        firm_id=request.firm_id,
        is_default=request.is_default
    )
    if not profile:
        raise HTTPException(500, "Failed to create profile (name may already exist)")
    return profile


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: int = Path(..., description="Profile ID")
):
    """Delete a profile"""
    success = repo.delete_profile(profile_id)
    if not success:
        raise HTTPException(404, f"Profile {profile_id} not found")
    return {"message": f"Profile {profile_id} deleted"}
