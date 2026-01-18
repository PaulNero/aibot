"""API endpoints для управления AI News Bot."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ai_bot.db.db_manager import get_db_sync
from ai_bot.db.models import Source, Keyword, Post, NewsItem
from ai_bot.api.schemas import (
    SourceCreate, SourceUpdate, SourceResponse,
    KeywordCreate, KeywordUpdate, KeywordResponse,
    PostResponse,
    GenerateRequest, GenerateResponse,
    PaginatedResponse, ErrorResponse
)
from ai_bot.ai.generator import generate_posts
from ai_bot.db.models_utils import PostStatus

router = APIRouter()

@router.get("/sources/", response_model=List[SourceResponse], tags=["Источники"])
async def get_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db_sync)
):
    """Получить список источников"""
    query = db.query(Source)
    if enabled_only:
        query = query.filter(Source.enabled == True)
    sources = query.offset(skip).limit(limit).all()
    return sources

@router.get("/sources/{source_id}", response_model=SourceResponse, tags=["Источники"])
async def get_source(source_id: str, db: Session = Depends(get_db_sync)):
    """Получить источник по ID"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return source

@router.post("/sources/", response_model=SourceResponse, tags=["Источники"])
async def create_source(source: SourceCreate, db: Session = Depends(get_db_sync)):
    """Создать новый источник"""
    # Проверяем уникальность имени
    existing = db.query(Source).filter(Source.name == source.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Источник с таким именем уже существует")

    db_source = Source(**source.model_dump(), created_at=datetime.now())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

@router.put("/sources/{source_id}", response_model=SourceResponse, tags=["Источники"])
async def update_source(source_id: str, source_update: SourceUpdate, db: Session = Depends(get_db_sync)):
    """Обновить источник"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")

    update_data = source_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    return source

@router.delete("/sources/{source_id}", tags=["Источники"])
async def delete_source(source_id: str, db: Session = Depends(get_db_sync)):
    """Удалить источник"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")

    db.delete(source)
    db.commit()
    return {"message": "Источник удален"}



@router.get("/keywords/", response_model=List[KeywordResponse], tags=["Ключевые слова"])
async def get_keywords(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db_sync)
):
    """Получить список ключевых слов"""
    keywords = db.query(Keyword).offset(skip).limit(limit).all()
    return keywords

@router.get("/keywords/{keyword_id}", response_model=KeywordResponse, tags=["Ключевые слова"])
async def get_keyword(keyword_id: str, db: Session = Depends(get_db_sync)):
    """Получить ключевое слово по ID"""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Ключевое слово не найдено")
    return keyword

@router.post("/keywords/", response_model=KeywordResponse, tags=["Ключевые слова"])
async def create_keyword(keyword: KeywordCreate, db: Session = Depends(get_db_sync)):
    """Создать новое ключевое слово"""
    # Проверяем уникальность слова
    existing = db.query(Keyword).filter(Keyword.word == keyword.word).first()
    if existing:
        raise HTTPException(status_code=400, detail="Такое ключевое слово уже существует")

    db_keyword = Keyword(**keyword.model_dump(), created_at=datetime.now())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

@router.put("/keywords/{keyword_id}", response_model=KeywordResponse, tags=["Ключевые слова"])
async def update_keyword(keyword_id: str, keyword_update: KeywordUpdate, db: Session = Depends(get_db_sync)):
    """Обновить ключевое слово"""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Ключевое слово не найдено")

    update_data = keyword_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(keyword, field, value)

    db.commit()
    db.refresh(keyword)
    return keyword

@router.delete("/keywords/{keyword_id}", tags=["Ключевые слова"])
async def delete_keyword(keyword_id: str, db: Session = Depends(get_db_sync)):
    """Удалить ключевое слово"""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Ключевое слово не найдено")

    db.delete(keyword)
    db.commit()
    return {"message": "Ключевое слово удалено"}



@router.get("/posts/", response_model=List[PostResponse], tags=["История постов"])
async def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status: Optional[PostStatus] = None,
    db: Session = Depends(get_db_sync)
):
    """Получить историю постов"""
    query = db.query(Post)
    if status:
        query = query.filter(Post.status == status)

    posts = query.offset(skip).limit(limit).all()

    # Загружаем связанные новости
    for post in posts:
        if post.news_item is None:
            post.news_item = db.query(NewsItem).filter(NewsItem.id == post.news_id).first()

    return posts

@router.get("/posts/{post_id}", response_model=PostResponse, tags=["История постов"])
async def get_post(post_id: str, db: Session = Depends(get_db_sync)):
    """Получить пост по ID"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    # Загружаем связанную новость
    if post.news_item is None:
        post.news_item = db.query(NewsItem).filter(NewsItem.id == post.news_id).first()

    return post



@router.post("/generate/", response_model=GenerateResponse, tags=["Генерация постов"])
async def generate_post_manual(request: GenerateRequest, db: Session = Depends(get_db_sync)):
    """Вручную сгенерировать пост для новости"""
    # Проверяем существование новости
    news_item = db.query(NewsItem).filter(NewsItem.id == request.news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверяем, есть ли уже пост для этой новости
    existing_post = db.query(Post).filter(Post.news_id == request.news_id).first()
    if existing_post and existing_post.generated_text:
        return GenerateResponse(
            success=True,
            message="Пост уже сгенерирован ранее",
            post_id=existing_post.id,
            generated_text=existing_post.generated_text
        )

    try:
        # Генерируем пост
        generated_text = generate_posts(news_item)

        if not generated_text:
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать пост")

        # Создаем или обновляем пост
        if existing_post:
            existing_post.generated_text = generated_text
            existing_post.status = PostStatus.GENERATED
            post = existing_post
        else:
            post = Post(
                news_id=request.news_id,
                generated_text=generated_text,
                status=PostStatus.GENERATED,
                created_at=datetime.now()
            )
            db.add(post)

        db.commit()
        db.refresh(post)

        return GenerateResponse(
            success=True,
            message="Пост успешно сгенерирован",
            post_id=post.id,
            generated_text=generated_text
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка генерации поста: {str(e)}")


# === HEALTH CHECK ===

@router.get("/health/", tags=["Системные"])
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "healthy", "timestamp": datetime.now()}


# === STATISTICS ===

@router.get("/stats/", tags=["Статистика"])
async def get_stats(db: Session = Depends(get_db_sync)):
    """Получить статистику системы"""
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.enabled == True).count()
    total_keywords = db.query(Keyword).count()
    total_news = db.query(NewsItem).count()
    total_posts = db.query(Post).count()
    published_posts = db.query(Post).filter(Post.status == PostStatus.PUBLISHED).count()

    return {
        "sources": {
            "total": total_sources,
            "active": active_sources
        },
        "keywords": total_keywords,
        "news": total_news,
        "posts": {
            "total": total_posts,
            "published": published_posts
        }
    }