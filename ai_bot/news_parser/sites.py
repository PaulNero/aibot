"""Парсеры для веб-сайтов."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

from ai_bot.news_parser.base import BaseParser


class SiteParser(BaseParser):
    """Абстрактный базовый класс для парсеров сайтов."""
    
    def __init__(self, url: str, articles_path: str = ''):
        """
        Инициализация парсера сайта.
        
        Args:
            url: Базовый URL сайта
            articles_path: Путь к разделу со статьями
        """
        self.base_url = url
        self.articles_url = articles_path
    
class HabrParser(SiteParser):
    """Парсер для сайта Habr.com."""

    def __init__(self):
        """Инициализация парсера Habr.com."""
        super().__init__('https://habr.com', '/ru/articles/')
        self.source = 'habr'
        
    def parse(self, limit: int = 50) -> list[dict]:
        """
        Парсит последние статьи с Habr.com.
        
        Args:
            limit: Максимальное количество статей (не используется, парсятся все доступные)
        
        Returns:
            Список словарей с данными статей (source, title, summary, url, img, author, published_at)
        """
        response = requests.get(self._normalize_url(), timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        articles_data = []
        for article in soup.find('div', class_='tm-articles-list').find_all('article'):
            # Извлекаем данные статьи
            title = article.find('h2').a.span.text if article.find('h2') else None
            summary = article.find('div', class_='article-formatted-body').text if article.find('div', class_='article-formatted-body') else None

            # Если summary пустой, используем альтернативный текст или первые слова заголовка
            if not summary:
                # Пытаемся найти альтернативный summary
                alt_summary = article.find('div', class_='article-formatted-body article-formatted-body_version-1')
                if alt_summary:
                    summary = alt_summary.text
                else:
                    # Используем первые слова заголовка как fallback
                    summary = title[:200] + "..." if title else "Без описания"
            author = article.find('a', attrs={'data-test-id': 'user-info-username'}).get_text(strip=True) if article.find('a', attrs={'data-test-id': 'user-info-username'}) else None

            # Используем базовую фильтрацию из BaseParser
            if self.should_skip_item(title=title, summary=summary, author=author, min_title_length=10):
                continue

            articles_data.append({
                'source': self.source,
                'title': title,
                'summary': summary,
                'url': self._normalize_url_with_id(article.get('id')) if article.get('id') else None,
                'img': article.find('div', class_='lead').find('img').get('src') if article.find('div', class_='lead') and article.find('div', class_='lead').find('img') else None,
                'author': author,
                'published_at': datetime.fromisoformat(article.find('time').get('datetime')) if article.find('time').get('datetime') else None
            })

        return articles_data
            
    def _normalize_url_with_id(self, article_id: str) -> str:
        """Формирует полный URL статьи по её ID."""
        return self.base_url + self.articles_url + article_id
    
    def _normalize_url(self) -> str:
        """Возвращает базовый URL для парсинга."""
        return self.base_url + self.articles_url

class TProgerParser(SiteParser):
    """Парсер для сайта TProger.ru."""

    def __init__(self):
        """Инициализация парсера TProger.ru."""
        super().__init__('https://tproger.ru', '/news')
        self.source = 'tproger'
        
    def parse(self, limit: int = 50) -> list[dict]:
        """
        Парсит последние статьи с TProger.ru.
        
        Args:
            limit: Максимальное количество статей для парсинга
        
        Returns:
            Список словарей с данными статей (source, title, summary, url, img, author, published_at)
        """
        response = requests.get(self._normalize_url(), timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        articles_data = []
        
        # Ищем контейнер со статьями
        articles_container = (
            soup.find('div', class_='tp-grid') or
            soup.find('main') or
            soup
        )
        
        if not articles_container:
            return articles_data
        
        # Ищем div с классом содержащим 'feed-posts' или 'post'
        feed_container = articles_container.find('div', class_=lambda x: x and ('feed' in str(x).lower() or 'post' in str(x).lower()))
        
        if not feed_container:
            # Если не нашли feed_container, ищем карточки напрямую в tp-grid
            articles = articles_container.find_all('div', class_=lambda x: x and 'tp-new-design-post-card' in str(x), limit=limit)
        else:
            # Ищем все карточки статей по классу tp-new-design-post-card
            articles = feed_container.find_all('div', class_=lambda x: x and 'tp-new-design-post-card' in str(x), limit=limit)
        
        if not articles:
            return articles_data
        
        # Используем set для отслеживания уже обработанных URL (дедупликация)
        seen_urls = set()
        
        for article in articles:
            try:
                # Ищем ссылку с классом tp-new-design-post-card__title - это заголовок и ссылка
                title_link = article.find('a', class_='tp-new-design-post-card__title')
                if not title_link:
                    continue
                
                # Извлекаем заголовок
                title = title_link.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                # Извлекаем URL
                url = title_link.get('href')
                if url and not url.startswith('http'):
                    url = self.base_url + url if url.startswith('/') else self.base_url + '/' + url
                
                # Пропускаем дубликаты по URL
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Ищем описание (может быть в разных местах)
                summary_elem = (
                    article.find('div', class_=lambda x: x and ('summary' in str(x).lower() or 'excerpt' in str(x).lower() or 'description' in str(x).lower())) or
                    article.find('p', class_=lambda x: x and ('summary' in str(x).lower() or 'excerpt' in str(x).lower()))
                )
                summary = summary_elem.get_text(strip=True) if summary_elem else None
                if not summary or len(summary) < 20:
                    # Используем заголовок как fallback для summary
                    summary = title[:200] + "..." if title else "Без описания"
                
                # Ищем изображение в обёртке tp-new-design-post-card__image-wrapper
                img_wrapper = article.find('div', class_='tp-new-design-post-card__image-wrapper')
                img = None
                if img_wrapper:
                    img_elem = img_wrapper.find('img', class_='tp-ui-image__image')
                    if img_elem:
                        img = img_elem.get('src')
                        # Берем первый URL из srcset если есть
                        if not img or img.startswith('data:'):
                            srcset = img_elem.get('srcset')
                            if srcset:
                                # Берем первый URL из srcset
                                first_url = srcset.split()[0] if srcset else None
                                if first_url and first_url.startswith('http'):
                                    img = first_url
                
                # Ищем дату в time с атрибутом datetime
                time_elem = article.find('time')
                published_at = None
                if time_elem:
                    datetime_attr = time_elem.get('datetime')
                    if datetime_attr:
                        try:
                            # Обрабатываем формат "2026-01-26T20:06:25+03:00"
                            published_at = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            pass
                
                # Используем базовую фильтрацию из BaseParser
                if self.should_skip_item(title=title, summary=summary, min_title_length=10):
                    continue
                
                articles_data.append({
                    'source': self.source,
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'img': img,
                    'author': 'TProger',  # TProger обычно не показывает автора в списке, используем название сайта
                    'published_at': published_at
                })
                
            except Exception as e:
                # Пропускаем статьи с ошибками парсинга
                continue
        
        return articles_data
            
    def _normalize_url_with_id(self, article_id: str) -> str:
        """Формирует полный URL статьи по её ID."""
        return self.base_url + self.articles_url + article_id
    
    def _normalize_url(self) -> str:
        """Возвращает базовый URL для парсинга."""
        return self.base_url + self.articles_url
