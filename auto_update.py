import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse

DOCS_DIR = "documents"
URL_LIST_FILE = "urls.txt"

def load_target_urls():
    targets = {}
    if not os.path.exists(URL_LIST_FILE):
        print(f"エラー: 設定ファイル `{URL_LIST_FILE}` が見つかりません。")
        return targets
        
    with open(URL_LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:
                filename, url = line.split(",", 1)
                targets[filename.strip()] = url.strip()
    return targets

def auto_update_two_step():
    print("定期自動更新処理（学年別キーワード最適化モード）を開始します...")
    
    current_year = str(datetime.now().year)
    print(f"今年度の対象キーワード: [{current_year}]")
    
    target_list = load_target_urls()
    if not target_list:
        print("処理を終了します（監視対象が登録されていません）。")
        return
        
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        
    print(f"現在の監視対象ファイル（設定数: {len(target_list)} 個）")
    print("--------------------------------------------------")

    updated_count = 0

    for local_filename, parent_url in target_list.items():
        base_name = os.path.splitext(local_filename)[0]  # 例: 「U12_2026」
        
        # 【ここを大幅に強化！】学年ごとに確実にヒットするキーワードを再設定
        exclude_keyword = None
        if "AQUA" in base_name:
            target_keyword = "AQUA"
        elif "U12" in base_name:
            target_keyword = "U12"  # ハイフンなしでも引っかかるように
            # AQUAカップの「直接PDFリンク」を誤爆して掴まないようにURLだけで除外制限
            exclude_keyword = "AQUA" 
        elif "U11" in base_name:
            target_keyword = "U11"
            exclude_keyword = "AQUA"
        elif "U10" in base_name:
            target_keyword = "U10"
            exclude_keyword = "AQUA"
        else:
            target_keyword = base_name.replace(f"_{current_year}", "")
            exclude_keyword = None
        
        print(f"📄 巡回開始: [{local_filename}] の親ページへアクセス中...")
        
        try:
            # --- ステップ1: 親ページから今年の特設ページのリンクを探す ---
            response = requests.get(parent_url, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"   ⚠️ 親ページへのアクセス失敗 (Status Code: {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            child_url = None
            
            for link in soup.find_all('a'):
                href = link.get('href', '')
                link_text = link.get_text().strip()
                
                # 検索用に文字を全部大文字、かつハイフンを抜いて統一（表記ブレ対策）
                search_text = (link_text + href).upper().replace("-", "")
                
                # 「今年の西暦」と「各学年のキーワード」が含まれているか
                if (target_keyword in search_text) and (current_year in search_text):
                    # AQUAの誤爆を防ぐ
                    if exclude_keyword and exclude_keyword in search_text:
                        # ただし、リンク名自体が「U12リーグ」など本命っぽい場合は救済
                        if "LEAGUE" in search_text or "リーグ" in link_text or "選手権" in link_text:
                            pass
                        else:
                            continue
                            
                    child_url = urllib.parse.urljoin(parent_url, href)
                    print(f"   🎯 対象のリンクを自動検出しました: {link_text}")
                    break
            
            # 適切な子リンクが見つからなければ、そのページ自体を直接スキャン
            if not child_url:
                print(f"   💡 固有の特設ページリンクが見つからないため、このページ内を直接スキャンします。")
                child_url = parent_url
                
            # --- ステップ2: PDFのダウンロード処理 ---
            # 拾ったURLが直接PDFやった場合
            if child_url.split('?')[0].endswith('.pdf'):
                save_path = os.path.join(DOCS_DIR, local_filename)
                print("   -> 直接PDFリンクを検出しました。ダウンロードし、上書き更新します...")
                pdf_response = requests.get(child_url, timeout=10)
                with open(save_path, "wb") as f:
                    f.write(pdf_response.content)
                print(f"   -> [{local_filename}] の上書き更新が完了しました。")
                updated_count += 1
                print("--------------------------------------------------")
                continue

            # 普通のWebページやった場合、その中にあるPDFリンクをスキャン
            child_response = requests.get(child_url, timeout=10)
            child_response.encoding = 'utf-8'
            child_soup = BeautifulSoup(child_response.text, 'html.parser')
            
            found_pdf = False
            for link in child_soup.find_all('a'):
                href = link.get('href', '')
                link_text = link.get_text().strip()
                
                if href.split('?')[0].endswith('.pdf'):
                    pdf_search_text = (link_text + href).upper().replace("-", "")
                    
                    if target_keyword in pdf_search_text or "規定" in link_text or "要項" in link_text:
                        if exclude_keyword and exclude_keyword in pdf_search_text and not ("リーグ" in link_text or "選手権" in link_text):
                            continue
                            
                        pdf_url = urllib.parse.urljoin(child_url, href)
                        save_path = os.path.join(DOCS_DIR, local_filename)
                        print(f"   ✨ 最新のPDFを検出しました: {link_text}")
                        print("   -> データをダウンロードし、上書き更新します...")
                        
                        pdf_response = requests.get(pdf_url, timeout=10)
                        with open(save_path, "wb") as f:
                            f.write(pdf_response.content)
                            
                        print(f"   -> [{local_filename}] の上書き更新が完了しました。")
                        updated_count += 1
                        found_pdf = True
                        break
                        
            if not found_pdf:
                print(f"   🔍 ページ内に [{local_filename}] に一致するPDFリンクが見つかりませんでした。")
                
        except Exception as e:
            print(f"   ❌ エラーが発生しました: {e}")
        print("--------------------------------------------------")
        
    print(f"巡回完了。合計 {updated_count} 個のファイルを最新データに上書き更新しました。")

if __name__ == "__main__":
    auto_update_two_step()