import streamlit as st
import os
import re
from pypdf import PdfReader
import base64
import auto_update

DOCS_DIR = "documents"
GITHUB_USERNAME = "tatsumi-syu"
REPOSITORY_NAME = "soccer-regulation-search"

# --- スマホ・PC最適化CSS ---
st.markdown("""
    <style>
    /* パソコン（大画面） */
    html { font-size: 16px; }
    .main .block-container { max-width: 900px; padding-top: 2rem; }

    /* スマホ */
    @media (max-width: 768px) {
        html { font-size: 14px; }
        .main .block-container { max-width: 100%; padding-left: 0.5rem; padding-right: 0.5rem; padding-top: 1rem; }
        .stButton button { width: 100%; padding: 0.5rem; }
    }
    
    /* PDF埋め込み用のコンテナ */
    .pdf-container {
        width: 100%;
        height: 80vh; /* 画面の高さの80%を使う */
        border: 1px solid #ccc;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def initialize_pdf_files():
    """アプリ起動時に一度だけ裏のauto_updateを実行してPDFを揃える"""
    try:
        auto_update.auto_update_two_step()
    except Exception as e:
        print(f"初期ダウンロード中にエラーが発生しました: {e}")

with st.spinner("最新のレギュレーションデータを取得中..."):
    initialize_pdf_files()


def get_pdf_page_count(file_path):
    """PDFの総ページ数を取得する"""
    try:
        reader = PdfReader(file_path)
        return len(reader.pages)
    except:
        return 0

def search_keywords_in_pdf_by_page(file_path, keywords):
    """PDFをページごとに検索し、ヒットしたページ番号と行を抽出する"""
    results = []
    try:
        reader = PdfReader(file_path)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split("\n")
            for line in lines:
                if all(kw.lower() in line.lower() for kw in keywords):
                    results.append({
                        "page": page_num,
                        "text": line.strip()
                    })
    except Exception as e:
        st.error(f"ファイル読み込みエラー ({os.path.basename(file_path)}): {e}")
        
    return results

def display_pdf_page(file_path, page_num):
    """PDFの特定のページをStreamlitに埋め込んで表示する"""
    try:
        # PDFファイルをブラウザが読める形式（base64）に変換する
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # ブラウザにPDFを埋め込むためのHTML。末尾に「#page=〇」をつけてページを指定
        # (※スマホブラウザの仕様により1ページ目が表示されることもあるが、ボタンで切り替え可能にする)
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#page={page_num}" class="pdf-container" type="application/pdf"></iframe>'
        
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PDF表示エラー: {e}")

# --- 画面の構築 ---
st.title("⚽ 少年サッカー公式戦レギュレーション検索")
st.write("登録されている大会のルール（PDF）からキーワードを爆速で検索します。")

if not os.path.exists(DOCS_DIR) or not [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]:
    st.warning("⚠️ documentsフォルダ内にPDFファイルが見つかりません。")
else:
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    selected_file = st.selectbox("検索する大会（PDF）を選択してください", pdf_files)
    file_path = os.path.join(DOCS_DIR, selected_file)
    
    # 【新機能】PDFの総ページ数を取得
    total_pages = get_pdf_page_count(file_path)
    
    # 【新機能】ページを切り替えるための「状態」を管理する
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1 # 初期ページは1

    # --- 🔍 検索フォーム ---
    search_input = st.text_input("検索キーワードを入力してください（スペース区切りでAND検索）")
    
    if st.button("検索を実行"):
        if search_input.strip() == "":
            st.warning("キーワードを入力してください。")
        else:
            keywords = search_input.split()
            
            with st.spinner("検索中..."):
                st.session_state.hits = search_keywords_in_pdf_by_page(file_path, keywords)
                # 検索したら、最初のヒットページにPDFを切り替える
                if st.session_state.hits:
                    st.session_state.current_page = st.session_state.hits[0]["page"]
    
    st.write("---")
    
    # --- 📄 PDFビューアー & 検索結果 ---
    col1, col2 = st.columns([1, 2]) # 画面を1:2の幅で分割

    with col1:
        # 左側に検索結果リスト
        st.subheader(f"🔍 ヒット数: {len(st.session_state.get('hits', []))}件")
        if st.session_state.get('hits'):
            for i, hit in enumerate(st.session_state.hits, 1):
                display_text = hit["text"]
                for kw in keywords:
                    insensitive_kw = re.compile(re.escape(kw), re.IGNORECASE)
                    display_text = insensitive_kw.sub(f"**{kw}**", display_text)
                
                # ページ番号をクリックしたら、そのページにジャンプするボタンにする
                if st.button(f"[P.{hit['page']}] {display_text[:20]}...", key=f"hit_{i}"):
                    st.session_state.current_page = hit["page"]

    with col2:
        # 右側にPDF埋め込み & 日本語操作ボタン
        st.subheader("📄 原本 PDF")
        
        # 【神機能】自作の日本語ページ切り替えボタン！
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅ 前のページ"):
                if st.session_state.current_page > 1:
                    st.session_state.current_page -= 1
        with c2:
            st.write(f"**{st.session_state.current_page} / {total_pages} ページ**")
        with c3:
            if st.button("次のページ ➡"):
                if st.session_state.current_page < total_pages:
                    st.session_state.current_page += 1
        
        # PDFを埋め込んで表示
        display_pdf_page(file_path, st.session_state.current_page)
