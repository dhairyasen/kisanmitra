"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class CropEnum(str, Enum):
    wheat = "wheat"
    rice = "rice"
    soybean = "soybean"
    cotton = "cotton"
    sugarcane = "sugarcane"
    onion = "onion"
    tomato = "tomato"

class GrowthStageEnum(str, Enum):
    sowing = "sowing"
    germination = "germination"
    nursery = "nursery"
    transplanting = "transplanting"
    seedling = "seedling"
    vegetative = "vegetative"
    tillering = "tillering"
    squaring = "squaring"
    flowering = "flowering"
    grain_filling = "grain_filling"
    pod_fill = "pod_fill"
    boll_development = "boll_development"
    bulb_development = "bulb_development"
    grand_growth = "grand_growth"
    fruiting = "fruiting"
    ripening = "ripening"
    maturity = "maturity"
    harvest = "harvest"

class SoilTypeEnum(str, Enum):
    sandy = "sandy"
    loamy = "loamy"
    clay = "clay"
    black_cotton = "black-cotton"

class LanguageEnum(str, Enum):
    hi = "hi"   # Hindi
    mr = "mr"   # Marathi
    kn = "kn"   # Kannada
    te = "te"   # Telugu
    ta = "ta"   # Tamil
    pa = "pa"   # Punjabi
    bn = "bn"   # Bengali
    gu = "gu"   # Gujarati
    en = "en"   # English

class FarmerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+91[0-9]{10}$")
    whatsapp: bool = True
    language: LanguageEnum = LanguageEnum.hi
    lat: float = Field(..., ge=8.0, le=37.0)
    lon: float = Field(..., ge=68.0, le=97.0)
    district: str
    state: str
    crop: CropEnum
    growth_stage: GrowthStageEnum
    field_area_acres: float = Field(..., gt=0, le=10000)
    soil_type: SoilTypeEnum = SoilTypeEnum.loamy

class WeatherRequest(BaseModel):
    lat: float
    lon: float
    days: int = Field(default=7, ge=1, le=16)

class AdvisoryRequest(BaseModel):
    lat: float
    lon: float
    crop: CropEnum
    growth_stage: GrowthStageEnum
    field_area_acres: float = 1.0
    soil_type: SoilTypeEnum = SoilTypeEnum.loamy
    language: LanguageEnum = LanguageEnum.hi

class ChatbotRequest(BaseModel):
    farmer_id: Optional[str] = None
    message: str
    language: LanguageEnum = LanguageEnum.hi
    lat: Optional[float] = None
    lon: Optional[float] = None
    crop: Optional[CropEnum] = None
    growth_stage: Optional[GrowthStageEnum] = None