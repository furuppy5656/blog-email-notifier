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
                    # テキストを取得して整形
                    content = content_elem.get_text().strip()
                    # 除外テキストを削除
                    for exclude in EXCLUDE_TEXTS:
                        content = content.replace(exclude, "")
                    # 連続する空白や改行を整理
                    content = re.sub(r'\n\s*\n', '\n', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                    # 最初の200文字まで
                    content = content[:200] + "..." if len(content) > 200 else content
                
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
    """新着記事をメール送信（HTML形式）"""
    if not new_articles:
        return
    
    # HTML形式のメール本文作成
    html_body = """
    <html>
      <head>
        <style>
          body { font-family: 'メイリオ', 'Hiragino Sans', sans-serif; line-height: 1.6; }
          h2 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }
          .article { margin-bottom: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }
          .title { font-weight: bold; font-size: 18px; color: #2c3e50; margin-bottom: 5px; }
          .date { color: #7f8c8d; font-size: 14px; margin-bottom: 10px; }
          .content { color: #34495e; margin-top: 10px; }
          .link { margin-top: 10px; }
          a { color: #3498db; text-decoration: none; }
          a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <h2>橘明さんのブログが更新されました！</h2>
    """
    
    # テキスト版も作成（HTMLをサポートしないメーラー用）
    text_body = "橘明さんのブログが更新されました！\n\n"
    
    for i, article in enumerate(new_articles, 1):
        # HTML版
        html_body += f"""
        <div class="article">
          <div class="title">{article['title']}</div>
        """
        
        if article.get('date'):
            html_body += f'<div class="date">{article["date"]}</div>'
        
        if article.get('content'):
            html_body += f'<div class="content">{article["content"]}</div>'
        
        if article.get('link'):
            html_body += f'<div class="link"><a href="{article["link"]}">→ 記事を読む</a></div>'
        
        html_body += "</div>"
        
        # テキスト版
        text_body += f"【{i}】 {article['title']}\n"
        if article.get('date'):
            text_body += f"日付: {article['date']}\n"
        if article.get('content'):
            text_body += f"{article['content'][:100]}...\n"
        if article.get('link'):
            text_body += f"URL: {article['link']}\n"
        text_body += "\n" + "-"*50 + "\n\n"
    
    html_body += f"""
        <hr>
        <p>ブログURL: <a href="{BLOG_URL}">{BLOG_URL}</a></p>
      </body>
    </html>
    """
    
    text_body += f"\nブログURL: {BLOG_URL}"
    
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
