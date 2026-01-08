from typing import Annotated, Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, Boolean, DateTime
from datetime import datetime
from uuid import uuid4
from enum import StrEnum, Enum
# from ai_bot.db.models_utils import id_column, url_column, text_column, timestamp_column, PostStatus, SourceType
from ai_bot.db.models_utils import ID, URL, TextContent, TimeStamp, OptionalURL, OptionalText, PostStatus, SourceType

class Base(DeclarativeBase):
    pass

class NewsItem(Base):
    __tablename__ = 'news_items'
    
    id: Mapped[ID]
    source: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[TextContent]
    url: Mapped[URL]
    img: Mapped[OptionalURL]
    author: Mapped[str] = mapped_column(String, nullable=False)
    published_at: Mapped[TimeStamp] = mapped_column(DateTime, nullable=False, default=datetime.now)
    created_atL: Mapped[TimeStamp]
    raw_text: Mapped[OptionalText]
    
    posts = relationship('Post', back_populates='news_item')

class Post(Base):
    __tablename__ = 'posts'
    
    id: Mapped[ID]
    news_id: Mapped[ID]
    generated_text: Mapped[OptionalText]
    published_at: Mapped[TimeStamp]
    status: Mapped[PostStatus] = mapped_column(default=PostStatus.NEW)
    created_at: Mapped[TimeStamp]
    
    news_item = relationship('NewsItem', back_populates='posts')

class Source(Base):
    __tablename__ = 'sources'

    id: Mapped[ID]
    type: Mapped[SourceType]
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[URL]
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[TimeStamp]

class Keyword(Base):
    __tablename__ = 'keywords'
    
    id: Mapped[ID]
    word: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[TimeStamp]



