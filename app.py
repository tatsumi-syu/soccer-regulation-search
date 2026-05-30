import streamlit as st
import os
import re
from pypdf import PdfReader
import auto_update

DOCS_DIR = "documents"
GITHUB_USERNAME = "tatsumi-syu"
REPOSITORY_NAME = "soccer-regulation-search"

# --- 【新機能】スマホとPCで文字サイズや横幅を自動調整する魔法のCSS ---
st.markdown("""
    <style>
    /* ─── ① パソコン（大画面）用の設定 ─── */
    html {
        font-size: 16px; /* PCは普通の文字サイズ */
    }
    .main .block-container {
        max-width: 900px; /* PC画面では横に広がりすぎんよう中央に寄せる */
        padding-top: 2rem;
    }

    /* ─── ② スマホ（横幅が768px以下の画面）用の設定 ─── */
    @media (max-width: 768px) {
        html {
            font-size: 14px; /* スマホは文字を少し小さくしてギュッと収める */
        }
        .main .block-container {
            max-width: 100%; /* スマホは画面の端までいっぱいに使う */
            padding-left: 0.5rem;  /* 左右の無駄な余白をギリギリまで削る */
            padding-right: 0.5rem;
            padding-top: 1rem;
        }
        /* 検索ボタンとか入力欄をスマホでタップしやすく大きくする */
        .stButton button {
            width: 100%; /* スマホの時はボタンを横いっぱいに広げて押しやすくする */
            padding: 0.5rem;
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
st.write("登録されている大会のルール（PDF）からキーワードを爆速で検索します。")

if not os.path.exists(DOCS_DIR) or not [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]:
    st.warning("⚠️ documentsフォルダ内にPDFファイルが見つかりません。")
    st.info("しばらく待つか、アプリを再起動してください。")
else:
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    selected_file = st.selectbox("検索する大会（PDF）を選択してください", pdf_files)
    
    pdf_github_url = f"https://github.com/{GITHUB_USERNAME}/{REPOSITORY_NAME}/blob/main/{DOCS_DIR}/{selected_file}"
    
    st.markdown(f"🔗 [📄 選択中のPDFを開く]({pdf_github_url})")
    st.write("---")
    
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
                    
                    page_url = f"{pdf_github_url}#page={hit['page']}"
                    st.markdown(f"{i}. [[P.{hit['page']}]({page_url})] {display_text}")
            else:
                st.info("一致するキーワードが見つかりませんでした。別の言葉で試してみてください。")
