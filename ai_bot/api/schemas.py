"""Pydantic схемы для API AI News Bot."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ai_bot.db.models_utils import SourceType, PostStatus
class SourceBase(BaseModel):
    name: str = Field(..., description="Название источника")
    type: SourceType = Field(..., description="Тип источника (site/tg)")
    url: str = Field(..., description="URL источника или username для TG")
    enabled: bool = Field(True, description="Включен ли источник")

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SourceType] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None

class SourceResponse(SourceBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class KeywordBase(BaseModel):
    word: str = Field(..., description="Ключевое слово для фильтрации")

class KeywordCreate(KeywordBase):
    pass

class KeywordUpdate(KeywordBase):
    pass

class KeywordResponse(KeywordBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class NewsItemResponse(BaseModel):
    id: str
    source: str
    title: str
    summary: str
    url: Optional[str]
    img: Optional[str]
    author: str
    published_at: datetime
    created_at: datetime
    raw_text: Optional[str]

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: str
    news_id: str
    generated_text: Optional[str]
    published_at: Optional[datetime]
    status: PostStatus
    created_at: datetime

    # Связанные объекты
    news_item: Optional[NewsItemResponse] = None

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    news_id: str = Field(..., description="ID новости для генерации поста")

class GenerateResponse(BaseModel):
    success: bool
    message: str
    post_id: Optional[str] = None
    generated_text: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    pages: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None