import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
import re

# 環境変数から設定を取得
TARGET_URL = os.environ.get('TARGET_URL', 'https://example.com')
TARGET_NAME = os.environ.get('TARGET_NAME', 'ウェブサイト')
EMAIL = os.environ.get('EMAIL_ADDRESS')
PASSWORD = os.environ.get('EMAIL_PASSWORD')
CACHE_FILE = 'last_articles.json'

# 除外する定型文（必要に応じてカスタマイズ）
EXCLUDE_TEXTS = os.environ.get('EXCLUDE_TEXTS', '').split('|') if os.environ.get('EXCLUDE_TEXTS') else []

def should_exclude(text):
    """除外すべきテキストか判定"""
    for exclude in EXCLUDE_TEXTS:
        if exclude and exclude in text:
            return True
    return False

def clean_content(content):
    """コンテンツを整形"""
    if not content:
        return ""
    # 除外テキストを削除
    for exclude in EXCLUDE_TEXTS:
        if exclude:
            content = content.replace(exclude, "")
    # 連続する空白や改行を整理
    content = re.sub(r'\n\s*\n', '\n', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content

def get_web_content():
    """ウェブサイトから最新コンテンツを取得"""
    try:
        print(f"Fetching content from: {TARGET_URL}")
        response = requests.get(TARGET_URL, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        
        # 汎用的な記事検出パターン
        article_selectors = [
            ('article', {}),
            ('div', {'class': ['post', 'entry', 'article', 'content-item']}),
            ('section', {'class': ['post', 'article']}),
            ('li', {'class': ['post', 'article-item']})
        ]
        
        article_elements = []
        for tag, attrs in article_selectors:
            if attrs:
                found = soup.find_all(tag, attrs)
            else:
                found = soup.find_all(tag)
            if found:
                article_elements.extend(found[:5])
                break
        
        for element in article_elements[:10]:  # 最大10件まで
            # タイトルを探す
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
            if title_elem:
                title = title_elem.get_text().strip()
                
                # 除外テキストは無視
                if should_exclude(title) or not title:
                    continue
                
                # 日付を探す（複数のパターンを試行）
                date_text = ""
                date_patterns = [
                    ('time', {}),
                    ('span', {'class': ['date', 'post-date', 'entry-date', 'published']}),
                    ('div', {'class': ['date', 'post-date', 'meta-date']}),
                    ('p', {'class': ['date', 'post-meta']})
                ]
                
                for tag, attrs in date_patterns:
                    date_elem = element.find(tag, attrs)
                    if date_elem:
                        date_text = date_elem.get_text().strip()
                        break
                
                # 本文を取得
                content = ""
                content_patterns = [
                    ('div', {'class': ['content', 'entry-content', 'post-content', 'excerpt']}),
                    ('p', {}),
                    ('span', {'class': ['summary', 'description']})
                ]
                
                for tag, attrs in content_patterns:
                    content_elem = element.find(tag, attrs)
                    if content_elem:
                        content = clean_content(content_elem.get_text())
                        if content:
                            break
                
                # リンクを探す
                link = ""
                link_elem = element.find('a', href=True)
                if link_elem:
                    link = link_elem['href']
                    if not link.startswith('http'):
                        base_url = TARGET_URL.rstrip('/')
                        link = base_url + '/' + link.lstrip('/')
                
                if title and not title.startswith(('Menu', 'Navigation', 'Category', 'Tags', 'Archives')):
                    articles.append({
                        'title': title,
                        'date': date_text,
                        'content': content[:300] + '...' if len(content) > 300 else content,
                        'link': link or TARGET_URL,
                        'time': datetime.now().isoformat()
                    })
        
        # 記事が見つからない場合は、h2/h3タグを直接探す
        if not articles:
            headings = soup.find_all(['h2', 'h3'])[:10]
            for heading in headings:
                title = heading.get_text().strip()
                if should_exclude(title):
                    continue
                if title and not title.lower().startswith(('menu', 'nav', 'category', 'tag', 'archive', 'search')):
                    # 親要素からリンクを探す
                    parent = heading.parent
                    link = ""
                    if parent:
                        link_elem = parent.find('a', href=True)
                        if link_elem:
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = TARGET_URL.rstrip('/') + '/' + link.lstrip('/')
                    
                    articles.append({
                        'title': title,
                        'date': '',
                        'content': '',
                        'link': link or TARGET_URL,
                        'time': datetime.now().isoformat()
                    })
        
        print(f"Found {len(articles)} items")
        return articles
        
    except Exception as e:
        print(f"Error fetching content: {e}")
        return []

def load_cache():
    """前回チェック時の記事を読み込み"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_cache(articles):
    """記事情報を保存"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def send_email(new_articles):
    """新着記事をメール送信（HTML形式・目次付き）"""
    if not new_articles:
        return
    
    # HTML形式のメール本文作成
    html_body = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'メイリオ', 'Hiragino Sans', sans-serif; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; }}
          h1 {{ color: #2c3e50; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
          h2 {{ color: #34495e; margin-top: 40px; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }}
          
          .toc {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 20px 0; }}
          .toc h3 {{ color: #495057; margin-top: 0; margin-bottom: 20px; }}
          .toc-item {{ margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #e9ecef; }}
          .toc-item:last-child {{ border-bottom: none; }}
          .toc-title {{ font-size: 16px; font-weight: bold; color: #2c3e50; text-decoration: none; display: block; margin-bottom: 5px; }}
          .toc-title:hover {{ color: #4CAF50; text-decoration: underline; }}
          .toc-date {{ color: #6c757d; font-size: 14px; margin-bottom: 5px; }}
          .toc-excerpt {{ color: #495057; font-size: 14px; line-height: 1.5; margin-bottom: 8px; }}
          .toc-link {{ color: #3498db; text-decoration: none; font-size: 14px; }}
          .toc-link:hover {{ text-decoration: underline; }}
          
          .article {{ margin: 40px 0; padding: 25px; background-color: #ffffff; border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
          .article-title {{ font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
          .article-date {{ color: #7f8c8d; font-size: 14px; margin-bottom: 15px; }}
          .article-content {{ color: #495057; line-height: 1.8; }}
          .article-link {{ margin-top: 15px; padding-top: 15px; border-top: 1px solid #e9ecef; }}
          .article-link a {{ color: #3498db; text-decoration: none; font-weight: 500; }}
          .article-link a:hover {{ text-decoration: underline; }}
          
          hr {{ border: none; border-top: 1px solid #dee2e6; margin: 40px 0; }}
        </style>
      </head>
      <body>
        <h1>🔔 {TARGET_NAME}が更新されました！</h1>
        
        <!-- 目次 -->
        <div class="toc">
          <h3>📋 新着コンテンツ一覧</h3>
    """
    
    # 目次を作成
    for i, article in enumerate(new_articles, 1):
        article_id = f"article-{i}"
        html_body += f"""
          <div class="toc-item">
            <a href="#{article_id}" class="toc-title">{article['title']}</a>
        """
        
        if article.get('date'):
            html_body += f'<div class="toc-date">📅 {article["date"]}</div>'
        
        if article.get('content'):
            excerpt = article['content'][:150] + "..." if len(article['content']) > 150 else article['content']
            html_body += f'<div class="toc-excerpt">{excerpt}</div>'
        
        if article.get('link'):
            html_body += f'<a href="{article["link"]}" class="toc-link">→ 記事を読む</a>'
        
        html_body += "</div>"
    
    html_body += """
        </div>
        
        <hr>
        
        <h2>📝 詳細内容</h2>
    """
    
    # 各記事の本文
    for i, article in enumerate(new_articles, 1):
        article_id = f"article-{i}"
        html_body += f"""
        <div class="article" id="{article_id}">
          <div class="article-title">{article['title']}</div>
        """
        
        if article.get('date'):
            html_body += f'<div class="article-date">📅 {article["date"]}</div>'
        
        if article.get('content'):
            html_body += f'<div class="article-content">{article["content"]}</div>'
        
        if article.get('link'):
            html_body += f'''
            <div class="article-link">
              <a href="{article["link"]}">📖 全文を読む →</a>
            </div>
            '''
        
        html_body += "</div>"
    
    html_body += f"""
        <hr>
        <p style="text-align: center; color: #6c757d; font-size: 14px;">
          監視対象URL: <a href="{TARGET_URL}" style="color: #3498db; text-decoration: none;">{TARGET_URL}</a><br>
          このメールは自動送信されています
        </p>
      </body>
    </html>
    """
    
    # テキスト版も作成
    text_body = f"{TARGET_NAME}が更新されました！\n\n"
    text_body += "="*50 + "\n\n"
    
    for i, article in enumerate(new_articles, 1):
        text_body += f"【{i}】 {article['title']}\n"
        if article.get('date'):
            text_body += f"日付: {article['date']}\n"
        if article.get('content'):
            text_body += f"{article['content'][:200]}...\n"
        if article.get('link'):
            text_body += f"URL: {article['link']}\n"
        text_body += "\n" + "-"*50 + "\n\n"
    
    text_body += f"URL: {TARGET_URL}"
    
    # メール設定
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = f"【更新通知】{TARGET_NAME} - 新着 {len(new_articles)}件"
    
    # テキストパートとHTMLパートを追加
    part1 = MIMEText(text_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')
    
    msg.attach(part1)
    msg.attach(part2)
    
    # Gmail送信
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully: {len(new_articles)} new items")
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    """メイン処理"""
    print("="*50)
    print(f"Website Monitor Started - {datetime.now()}")
    print(f"Target: {TARGET_URL}")
    print("="*50)
    
    # 現在のコンテンツを取得
    current_articles = get_web_content()
    if not current_articles:
        print("No content found or error occurred")
        return
    
    # 前回の記事を読み込み
    cached_articles = load_cache()
    cached_titles = {a['title'] for a in cached_articles}
    
    # 新着記事を判定
    new_articles = [a for a in current_articles if a['title'] not in cached_titles]
    
    if new_articles:
        print(f"New content found: {len(new_articles)} items")
        for article in new_articles:
            print(f"  - {article['title']}")
        send_email(new_articles)
    else:
        print("No new content")
    
    # キャッシュ更新
    save_cache(current_articles)
    print("Process completed")
    print("="*50)

if __name__ == "__main__":
    main()
