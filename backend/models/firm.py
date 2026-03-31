"""Firm and Profile models"""
from datetime import datetime
from pydantic import BaseModel


class Firm(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class FirmCreate(BaseModel):
    name: str


class Profile(BaseModel):
    id: int
    name: str
    firm_id: int
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class ProfileCreate(BaseModel):
    name: str
    firm_id: int
    is_default: bool = False


class FirmWithProfiles(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    profiles: list[Profile] = []
