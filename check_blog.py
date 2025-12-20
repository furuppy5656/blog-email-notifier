import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime

# 設定
BLOG_URL = "https://www.tachibana-akira.com/"
EMAIL = os.environ.get('EMAIL_ADDRESS')
PASSWORD = os.environ.get('EMAIL_PASSWORD')
CACHE_FILE = 'last_articles.json'

def get_blog_articles():
    """ブログから最新記事を取得"""
    try:
        response = requests.get(BLOG_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        # 記事のセレクタ（サイト構造により調整が必要な場合あり）
        article_elements = soup.find_all('article') or soup.find_all('div', class_='post')
        
        if not article_elements:
            # 一般的なブログ構造を試す
            article_elements = soup.find_all('h2') or soup.find_all('h3')
        
        for element in article_elements[:5]:  # 最新5件まで
            title = element.get_text().strip()
            if title:
                articles.append({
                    'title': title,
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
    """新着記事をメール送信"""
    if not new_articles:
        return
    
    # メール本文作成
    body = "橘明さんのブログが更新されました！\n\n"
    for article in new_articles:
        body += f"■ {article['title']}\n"
        body += f"  更新時刻: {article['time']}\n\n"
    body += f"\n詳細はこちら: {BLOG_URL}"
    
    # メール設定
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = f"【ブログ更新通知】新着記事 {len(new_articles)}件"
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
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
