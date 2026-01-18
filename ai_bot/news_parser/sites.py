"""Парсеры для веб-сайтов."""

from abc import ABC
import requests
import pprint
from bs4 import BeautifulSoup
from datetime import datetime


class SiteParser(ABC):
    """Абстрактный базовый класс для парсеров сайтов."""
    def __init__(self, url: str, articles_path:str=''):
        self.base_url = url
        self.articles_url = articles_path
        
        
    def parse(self):
        raise NotImplementedError
    
class HabrParser(SiteParser):
    """Парсер для сайта Habr.com."""

    def __init__(self):
        super().__init__('https://habr.com', '/ru/articles/')
        self.source = 'habr'
        
    def parse(self):
        response = requests.get(self._normalize_url(), timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        # ===== Test =====
        # articles = soup.find('div', class_='tm-articles-list').find_all('article')
        # for article in articles:
            
        #     lead_div = article.find('div', class_='lead')
        #     author_tag = article.find('a', attrs={'data-test-id': 'user-info-username'})
            
        #     article_source = self.source
        #     article_title = article.find('h2').a.span.text if article.find('h2') else None
        #     article_summary = article.find('div', class_='article-formatted-body').text if article.find('div', class_='article-formatted-body') else None
        #     article_url = self._normalize_url_with_id(article.get('id')) if article.get('id') else None
        #     article_img = lead_div.find('img').get('src') if lead_div and lead_div.find('img') else None
        #     article_time = datetime.fromisoformat(article.find('time').get('datetime')) if article.find('time').get('datetime') else None
        #     article_author = author_tag.get_text(strip=True) if author_tag else None
            
        #     print('=' * 50)
        #     print(f'\n|| Source: {article_source} \n|| Title: {article_title} \n|| Summary: {article_summary} \n|| Url: {article_url} \n|| Img: {article_img} \n|| Date: {article_time} \n|| Author: {article_author} \n||')
        
        # ===== End Test =====
        articles_data = []
        for article in soup.find('div', class_='tm-articles-list').find_all('article'):
            # Извлекаем данные статьи
            title = article.find('h2').a.span.text if article.find('h2') else None
            summary = article.find('div', class_='article-formatted-body').text if article.find('div', class_='article-formatted-body') else None
            author = article.find('a', attrs={'data-test-id': 'user-info-username'}).get_text(strip=True) if article.find('a', attrs={'data-test-id': 'user-info-username'}) else None

            # Базовая фильтрация рекламы на уровне парсинга
            if not title or len(title.strip()) < 10:
                continue  # Пропускаем статьи без заголовка или с слишком коротким заголовком

            title_lower = title.lower()
            summary_lower = (summary or '').lower()

            # Пропускаем статьи с явными признаками рекламы
            ad_indicators = [
                'анонс', 'реклама', 'спонсор', 'партнер', 'pr',
                'купить', 'цена', 'скидка', 'акция'
            ]

            is_ad = any(indicator in title_lower or indicator in summary_lower for indicator in ad_indicators)
            if is_ad:
                print(f"Пропускаем рекламную статью: {title}")
                continue

            # Пропускаем статьи только с заглавными буквами
            if title.isupper() and len(title) > 10:
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
            
    def _normalize_url_with_id(self, article_id: str):
        return self.base_url + self.articles_url + article_id
    
    def _normalize_url(self):
        return self.base_url + self.articles_url
        
if __name__ == '__main__':
    pprint.pprint(HabrParser().parse())
