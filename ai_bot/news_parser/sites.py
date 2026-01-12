from abc import ABC
import requests
import pprint
from bs4 import BeautifulSoup
from datetime import datetime

class SiteParser(ABC):
    def __init__(self, url: str, articles_path:str=''):
        self.base_url = url
        self.articles_url = articles_path
        
        
    def parse(self):
        raise NotImplementedError
    
class HabrParser(SiteParser):
    def __init__(self):
        super().__init__('https://habr.com', '/ru/articles/' )
        self.source = 'habr'
        
    def parse(self):
        response = requests.get(self._normalize_url(), headers={
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
        return [
            {
                'source': self.source,
                'title': article.find('h2').a.span.text if article.find('h2') else None,
                'summary': article.find('div', class_='article-formatted-body').text if article.find('div', class_='article-formatted-body') else None,
                'url': self._normalize_url_with_id(article.get('id')) if article.get('id') else None,
                'img': article.find('div', class_='lead').find('img').get('src') if article.find('div', class_='lead') and article.find('div', class_='lead').find('img') else None,
                'author': article.find('a', attrs={'data-test-id': 'user-info-username'}).get_text(strip=True) if article.find('a', attrs={'data-test-id': 'user-info-username'}) else None,
                'published_at': datetime.fromisoformat(article.find('time').get('datetime')) if article.find('time').get('datetime') else None
            }
            for article in soup.find('div', class_='tm-articles-list').find_all('article')
        ]
            
    def _normalize_url_with_id(self, article_id: str):
        return self.base_url + self.articles_url + article_id
    
    def _normalize_url(self):
        return self.base_url + self.articles_url
        
if __name__ == '__main__':
    pprint.pprint(HabrParser().parse())
