import streamlit as st
import os
import re
from pypdf import PdfReader
import auto_update

DOCS_DIR = "documents"
GITHUB_USERNAME = "tatsumi-syu"
REPOSITORY_NAME = "soccer-regulation-search"

# --- パソコンでもスマホでも綺麗に見える、程よい横幅の設定 ---
st.markdown("""
    <style>
    .main .block-container {
        max-width: 1000px; /* 画面が狭くなりすぎんよう、ゆったり広げる */
        padding-top: 2rem;
    }
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
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

# --- 画面の構築 ---
st.title("⚽ 少年サッカー公式戦レギュレーション検索")
st.write("登録されている大会のルール（PDF）からキーワードを検索します。")
st.write("---")

if not os.path.exists(DOCS_DIR) or not [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]:
    st.warning("⚠️ documentsフォルダ内にPDFファイルが見つかりません。")
else:
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    selected_file = st.selectbox("検索する大会（PDF）を選択してください", pdf_files)
    
    # PDFのGitHub直リンクURL（Public運用を想定）
    pdf_github_url = f"https://github.com/{GITHUB_USERNAME}/{REPOSITORY_NAME}/blob/main/{DOCS_DIR}/{selected_file}"
    
    # 分かりやすい原本リンクボタン
    st.markdown(f"### 🔗 [📄 この大会の公式PDF（原本）を別タブで開く]({pdf_github_url})")
    
    search_input = st.text_input("検索キーワードを入力してください（スペース区切りでAND検索）")
    
    if st.button("検索を実行"):
        if search_input.strip() == "":
            st.warning("キーワードを入力してください。")
        else:
            keywords = search_input.split()
            file_path = os.path.join(DOCS_DIR, selected_file)
            
            with st.spinner("検索中..."):
                hits = search_keywords_in_pdf_by_page(file_path, keywords)
                
            st.subheader(f"🔍 検索結果 (ヒット数: {len(hits)}件)")
            
            if hits:
                for i, hit in enumerate(hits, 1):
                    display_text = hit["text"]
                    for kw in keywords:
                        insensitive_kw = re.compile(re.escape(kw), re.IGNORECASE)
                        display_text = insensitive_kw.sub(f"**{kw}**", display_text)
                    
                    # ページ番号に直リンクを仕込む
                    page_url = f"{pdf_github_url}#page={hit['page']}"
                    st.markdown(f"{i}. [[P.{hit['page']}]({page_url})] {display_text}")
            else:
                st.info("一致するキーワードが見つかりませんでした。別の言葉で試してみてください。")
