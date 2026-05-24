import os
import re
import streamlit as str
from pypdf import PdfReader
from datetime import datetime

# --- 1. 画面の基本設定 ---
str.set_page_config(page_title="公式戦レギュレーション検索", page_icon="⚽")
str.title("⚽ 少年サッカー公式戦レギュレーション検索")
str.write("大会を選択し、キーワードを入力して規定を検索してください。")

DOCS_DIR = "documents"

if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]

# --- 2. PDFから改定日付（〇年〇月〇日）をスキャンする関数 ---
def extract_revision_date(target_file):
    file_path = os.path.join(DOCS_DIR, target_file)
    try:
        reader = PdfReader(file_path)
        # 最初に見つかった日付を信頼するため、1ページ目から順番にスキャン
        for page in reader.pages[:2]:  # 表紙や最初のページに書かれていることが多いので2ページ目までスキャン
            text = page.extract_text()
            
            # 「〇年〇月〇日」「〇/〇/〇」などのパターンを探す正規表現
            # 「改定」「現在」「制定」「発行」などの前後の文脈も一緒に拾う
            date_patterns = [
                r'(\d{4}年\d{1,2}月\d{1,2}日\s*(?:改定|現在|制定|発行|施行))',
                r'((?:令和|平成)\d{1,2}年\d{1,2}月\d{1,2}日\s*(?:改定|現在|制定|発行|施行))',
                r'(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass
    return None

# --- 3. PDFからキーワードを検索する関数 ---
def search_keyword_in_selected_pdf(target_file, keyword):
    results = []
    file_path = os.path.join(DOCS_DIR, target_file)
    
    try:
        reader = PdfReader(file_path)
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            
            if keyword.lower() in text.lower():
                lines = text.split('\n')
                matched_lines = []
                for line in lines:
                    if keyword.lower() in line.lower():
                        matched_lines.append(line)
                
                results.append({
                    "page": page_num,
                    "text": matched_lines
                })
    except Exception as e:
        str.error(f"ファイル {target_file} の読み込みエラー: {e}")
            
    return results

# --- 4. サイドバー設定 ---
with str.sidebar:
    str.header("⚙️ 管理メニュー")
    str.write(f"`{DOCS_DIR}/` フォルダに対象の大会規定PDFを配置してください。")
    str.write(f"現在の登録ファイル数: {len(pdf_files)} 個")

# --- 5. メイン検索エリア ---
if not pdf_files:
    str.warning(f"⚠️ `{DOCS_DIR}/` フォルダ内にPDFファイルが見つかりません。")
else:
    # 大会選択ドロップダウン
    selected_tournament = str.selectbox(
        "1. 調べたい大会を選択してください：",
        options=pdf_files,
        placeholder="大会を選択してください"
    )
    
    # 選択されたPDFの情報を表示
    if selected_tournament:
        # ① パソコン側への保存日時を取得
        file_path = os.path.join(DOCS_DIR, selected_tournament)
        timestamp = os.path.getmtime(file_path)
        last_sync = datetime.fromtimestamp(timestamp).strftime('%Y年%m月%d日 %H:%M')
        
        # ② 【ここがポイント！】PDFの中身から改定日付を抽出
        revision_date = extract_revision_date(selected_tournament)
        
        # 画面に二つの日付を端的に並べて表示
        if revision_date:
            str.caption(f"📄 本文内の記載: **{revision_date}** ｜ 🔄 システム最終同期: {last_sync}")
        else:
            str.caption(f"📄 本文内の記載: [改定日の自動検出不可] ｜ 🔄 システム最終同期: {last_sync}")
    
    # 検索キーワードの入力
    user_query = str.text_input("2. 検索キーワードを入力してください：", placeholder="例：交代、試合時間、警告、PK")

    if selected_tournament and user_query:
        with str.spinner(f"【{selected_tournament}】内を検索中..."):
            search_results = search_keyword_in_selected_pdf(selected_tournament, user_query)
            
            if search_results:
                str.success(f"✨ 「{user_query}」に関する規定が {len(search_results)} ページで見つかりました。")
                
                for res in search_results:
                    with str.expander(f"📄 {selected_tournament}（{res['page']} ページ目）"):
                        for hit_line in res['text']:
                            highlighted = hit_line.replace(user_query, f"**:red[{user_query}]**")
                            str.write(f"・ {highlighted}")
            else:
                str.info(f"🔍 選択された大会の中に、「{user_query}」に一致する規定は見つかりませんでした。")