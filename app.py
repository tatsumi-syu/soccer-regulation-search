import streamlit as st
import os
import re
from pypdf import PdfReader
# --- 追加：裏の自動更新ロボットを呼び出すための部品 ---
import auto_update

DOCS_DIR = "documents"

# --- 【新機能】アプリ起動時に自動でスクレイピングを実行する ---
@st.cache_data(show_spinner=False)
def initialize_pdf_files():
    """アプリ起動時に一度だけ裏のauto_updateを実行してPDFを揃える"""
    try:
        # auto_update.py のメイン処理を呼び出す
        auto_update.auto_update_two_step()
    except Exception as e:
        print(f"初期ダウンロード中にエラーが発生しました: {e}")

# アプリが起動したら、まず最初にPDFをネットから集めてこさせる
with st.spinner("最新のレギュレーションデータを取得中...（初回のみ数十秒かかります）"):
    initialize_pdf_files()


def load_pdf_text(file_path):
    """PDFファイルからテキストを抽出する"""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"ファイル読み込みエラー ({os.path.basename(file_path)}): {e}")
    return text

def search_keywords_in_pdf(file_path, keywords):
    """PDF内を検索し、キーワードが含まれる行を抽出する"""
    text = load_pdf_text(file_path)
    lines = text.split("\n")
    results = []
    
    for line in lines:
        if all(kw.lower() in line.lower() for kw in keywords):
            results.append(line.strip())
            
    return results

# --- 画面の構築 ---
st.title("⚽ 少年サッカー公式戦レギュレーション検索")
st.write("登録されている大会のルール（PDF）からキーワードを爆速で検索します。")

# documentsフォルダが存在するか、または中にPDFがあるか確認
if not os.path.exists(DOCS_DIR) or not [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]:
    st.warning("⚠️ documentsフォルダ内にPDFファイルが見つかりません。")
    st.info("右下のメニューから 'Reboot app' を実行するか、しばらくお待ちください。")
else:
    # PDFファイルの一覧を取得
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    
    # 選択ボックスの作成
    selected_file = st.selectbox("検索する大会（PDF）を選択してください", pdf_files)
    
    # 検索キーワードの入力
    search_input = st.text_input("検索キーワードを入力してください（スペース区切りでAND検索）")
    
    if st.button("検索を実行"):
        if search_input.strip() == "":
            st.warning("キーワードを入力してください。")
        else:
            # スペースで区切って複数キーワードに対応
            keywords = search_input.split()
            file_path = os.path.join(DOCS_DIR, selected_file)
            
            with st.spinner("検索中..."):
                hits = search_keywords_in_pdf(file_path, keywords)
                
            st.subheader(f"🔍 検索結果 (ヒット数: {len(hits)}件)")
            
            if hits:
                for i, hit in enumerate(hits, 1):
                    # キーワードを太字で強調表示（簡易版）
                    display_text = hit
                    for kw in keywords:
                        # 大文字小文字を無視して置換
                        insensitive_kw = re.compile(re.escape(kw), re.IGNORECASE)
                        display_text = insensitive_kw.sub(f"**{kw}**", display_text)
                    st.markdown(f"{i}. {display_text}")
            else:
                st.info("一致するキーワードが見つかりませんでした。別の言葉で試してみてください。")