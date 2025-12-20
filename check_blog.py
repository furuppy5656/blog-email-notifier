import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
import re

# 設定
BLOG_URL = "https://www.tachibana-akira.com/"
EMAIL = os.environ.get('EMAIL_ADDRESS')
PASSWORD = os.environ.get('EMAIL_PASSWORD')
CACHE_FILE = 'last_articles.json'

# 除外する定型文
EXCLUDE_TEXTS = [
    "作家・橘玲（たちばなあきら）の公式サイトです",
    "はじめての方は、最初にこちらの「ABOUT THIS SITE」",
    "橘玲からの「ご挨拶」をご覧ください",
    "自己紹介を兼ねた「橘玲 6つのQ&A」はこちら"
]

def should_exclude(text):
    """除外すべきテキストか判定"""
    for exclude in EXCLUDE_TEXTS:
        if exclude in text:
            return True
    return False

def clean_content(content):
    """コンテンツから定型文を削除して整形"""
    if not content:
        return ""
    # 除外テキストを削除
    for exclude in EXCLUDE_TEXTS:
        content = content.replace(exclude, "")
    # 連続する空白や改行を整理
    content = re.sub(r'\n\s*\n', '\n', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content

def get_blog_articles():
    """ブログから最新記事を取得"""
    try:
        response = requests.get(BLOG_URL, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        
        # 記事を探す（サイト構造に合わせて調整）
        article_elements = soup.find_all('article')
        if not article_elements:
            article_elements = soup.find_all('div', class_=['post', 'entry', 'article'])
        
        for element in article_elements[:5]:
            # タイトルを探す
            title_elem = element.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                title = title_elem.get_text().strip()
                
                # 除外テキストは無視
                if should_exclude(title):
                    continue
                
                # 日付を探す
                date_elem = element.find(['time', 'span', 'div'], class_=['date', 'post-date', 'entry-date'])
                date_text = date_elem.get_text().strip() if date_elem else ""
                
                # 本文の最初の部分を取得
                content = ""
                content_elem = element.find(['div', 'p'], class_=['content', 'entry-content', 'post-content'])
                if content_elem:
                    content = clean_content(content_elem.get_text())
                
                # リンクを探す
                link = ""
                link_elem = element.find('a')
                if link_elem and link_elem.get('href'):
                    link = link_elem['href']
                    if not link.startswith('http'):
                        link = BLOG_URL.rstrip('/') + '/' + link.lstrip('/')
                
                if title:
                    articles.append({
                        'title': title,
                        'date': date_text,
                        'content': content,
                        'link': link,
                        'time': datetime.now().isoformat()
                    })
        
        # 記事が見つからない場合は、h2タグを直接探す
        if not articles:
            h2_elements = soup.find_all('h2')
            for h2 in h2_elements[:5]:
                title = h2.get_text().strip()
                # 除外テキストと一般的なナビゲーション要素をスキップ
                if should_exclude(title):
                    continue
                if title and not title.startswith(('Menu', 'Navigation', 'カテゴリ')):
                    articles.append({
                        'title': title,
                        'date': '',
                        'content': '',
                        'link': BLOG_URL,
                        'time': datetime.now().isoformat()
                    })
        
        return articles
    except Exception as e:
        print(f"記事取得エラー: {e}")
        return []

def load_cache():
    """前回チェック時の記事を読み込み"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_cache(articles):
    """記事情報を保存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def send_email(new_articles):
    """新着記事をメール送信（HTML形式・目次付き）"""
    if not new_articles:
        return
    
    # HTML形式のメール本文作成
    html_body = """
    <html>
      <head>
        <style>
          body { font-family: 'メイリオ', 'Hiragino Sans', sans-serif; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; }
          h1 { color: #2c3e50; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
          h2 { color: #34495e; margin-top: 40px; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }
          
          /* 目次スタイル */
          .toc { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 20px 0; }
          .toc h3 { color: #495057; margin-top: 0; margin-bottom: 20px; }
          .toc-item { margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #e9ecef; }
          .toc-item:last-child { border-bottom: none; }
          .toc-title { font-size: 16px; font-weight: bold; color: #2c3e50; text-decoration: none; display: block; margin-bottom: 5px; }
          .toc-title:hover { color: #4CAF50; text-decoration: underline; }
          .toc-date { color: #6c757d; font-size: 14px; margin-bottom: 5px; }
          .toc-excerpt { color: #495057; font-size: 14px; line-height: 1.5; margin-bottom: 8px; }
          .toc-link { color: #3498db; text-decoration: none; font-size: 14px; }
          .toc-link:hover { text-decoration: underline; }
          
          /* 記事本文スタイル */
          .article { margin: 40px 0; padding: 25px; background-color: #ffffff; border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          .article-title { font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
          .article-date { color: #7f8c8d; font-size: 14px; margin-bottom: 15px; }
          .article-content { color: #495057; line-height: 1.8; }
          .article-link { margin-top: 15px; padding-top: 15px; border-top: 1px solid #e9ecef; }
          .article-link a { color: #3498db; text-decoration: none; font-weight: 500; }
          .article-link a:hover { text-decoration: underline; }
          
          hr { border: none; border-top: 1px solid #dee2e6; margin: 40px 0; }
        </style>
      </head>
      <body>
        <h1>🔔 橘玲さんのブログが更新されました！</h1>
        
        <!-- 目次 -->
        <div class="toc">
          <h3>📋 新着記事一覧</h3>
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
        
        <h2>📝 記事詳細</h2>
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
            # 本文は最大500文字まで表示
            full_content = article['content'][:500] + "..." if len(article['content']) > 500 else article['content']
            html_body += f'<div class="article-content">{full_content}</div>'
        
        if article.get('link'):
            html_body += f'''
            <div class="article-link">
              <a href="{article["link"]}">📖 記事全文を読む →</a>
            </div>
            '''
        
        html_body += "</div>"
    
    html_body += f"""
        <hr>
        <p style="text-align: center; color: #6c757d; font-size: 14px;">
          ブログURL: <a href="{BLOG_URL}" style="color: #3498db; text-decoration: none;">{BLOG_URL}</a><br>
          このメールは自動送信されています
        </p>
      </body>
    </html>
    """
    
    # テキスト版も作成（HTMLをサポートしないメーラー用）
    text_body = "橘明さんのブログが更新されました！\n\n"
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
    
    text_body += f"ブログURL: {BLOG_URL}"
    
    # メール設定
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = f"【ブログ更新通知】新着記事 {len(new_articles)}件"
    
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
        print(f"メール送信成功: {len(new_articles)}件の新着記事")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def main():
    """メイン処理"""
    print("ブログチェック開始...")
    
    # 現在の記事を取得
    current_articles = get_blog_articles()
    if not current_articles:
        print("記事が取得できませんでした")
        return
    
    # 前回の記事を読み込み
    cached_articles = load_cache()
    cached_titles = {a['title'] for a in cached_articles}
    
    # 新着記事を判定
    new_articles = [a for a in current_articles if a['title'] not in cached_titles]
    
    if new_articles:
        print(f"新着記事発見: {len(new_articles)}件")
        send_email(new_articles)
    else:
        print("新着記事なし")
    
    # キャッシュ更新
    save_cache(current_articles)
    print("処理完了")

if __name__ == "__main__":
    main()
