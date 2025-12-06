import os
import urllib.request
import subprocess
import time

# ================= 1. 安裝環境 =================
print("📦 正在檢查與安裝必要套件...")
os.system("pip install -q streamlit google-generativeai google-api-python-client requests")

# 下載更穩定的連線工具 (Cloudflare)
if not os.path.exists("cloudflared"):
    print("⬇️ 正在下載 Cloudflare 通道工具 (比 localtunnel 更穩)...")
    os.system("wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x cloudflared")

# ================= 2. 寫入軟體程式碼 (app.py) =================
app_code = """
import streamlit as st
import google.generativeai as genai
from googleapiclient.discovery import build
from datetime import datetime, timedelta

st.set_page_config(page_title="AI 爆款短影音複製機 (公開版)", page_icon="🎬", layout="wide")

# 側邊欄：使用者 Key
with st.sidebar:
    st.header("🔑 啟動設定 (Bring Your Own Key)")
    st.info("請輸入 API Key 以啟動工具 (不會儲存)")
    youtube_key = st.text_input("1. YouTube API Key", type="password")
    gemini_key = st.text_input("2. Gemini API Key", type="password")
    kling_token = st.text_input("3. Kling Token", type="password")
    st.divider()

def check_keys():
    if not youtube_key or not gemini_key:
        st.warning("⚠️ 請先在左側側邊欄填入 API Key！")
        st.stop()

def search_youtube(api_key, query, days, min_views):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        pub_after = (datetime.now() - timedelta(days=days)).isoformat("T") + "Z"
        res = youtube.search().list(q=query, part='id,snippet', maxResults=20, order='viewCount', publishedAfter=pub_after, type='video', videoDuration='short').execute()
        v_ids = [i['id']['videoId'] for i in res['items']]
        if not v_ids: return []
        stats = youtube.videos().list(part='statistics,snippet', id=','.join(v_ids)).execute()
        final = []
        for i in stats['items']:
            views = int(i['statistics'].get('viewCount',0))
            if views >= min_views:
                final.append({'title': i['snippet']['title'], 'img': i['snippet']['thumbnails']['high']['url'], 'views': views, 'id': i['id'], 'url': f"https://www.youtube.com/watch?v={i['id']}"})
        return sorted(final, key=lambda x: x['views'], reverse=True)
    except Exception as e:
        st.error(f"YouTube 搜尋失敗: {e}")
        return []

def make_prompt(gemini_key, title):
    try:
        genai.configure(api_key=gemini_key)
        prompt = f"你是短影音導演。請分析標題「{title}」，寫一段英文 Prompt 適合 Kling AI 生成 5 秒短片 (含運鏡、光影、主體)。"
        return genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text
    except: return "Gemini 分析失敗"

st.title("🚀 AI 爆款短影音複製機")
check_keys()

col1, col2 = st.columns([3, 1])
with col1:
    q = st.text_input("輸入關鍵字", "貓咪 療癒")
    days = st.slider("幾天內?", 1, 90, 7)
with col2:
    v = st.number_input("觀看數門檻", 10000)
    
if st.button("🔍 搜尋爆款", type="primary"):
    with st.spinner("挖掘數據中..."):
        res = search_youtube(youtube_key, q, days, v)
        if res:
            st.session_state['results'] = res
        else:
            st.warning("無結果或 Key 錯誤")

if 'results' in st.session_state:
    st.divider()
    for item in st.session_state['results']:
        with st.container(border=True):
            c1, c2 = st.columns([1,3])
            c1.image(item['img'])
            c2.subheader(item['title'])
            c2.caption(f"👀 {item['views']:,} | [連結]({item['url']})")
            if c2.button("✨ 生成 Prompt", key=item['id']):
                with st.spinner("分析中..."):
                    c2.text_area("Prompt:", make_prompt(gemini_key, item['title']))
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

print("✅ 軟體已準備就緒！")

# ================= 3. 啟動 Web App =================
print("🚀 正在啟動伺服器... (請等待下方出現 trycloudflare 網址)")

# 背景執行 Streamlit
subprocess.Popen(["streamlit", "run", "app.py"])

# 使用 Cloudflare 建立通道 (不需密碼)
time.sleep(3) # 等待 Streamlit 啟動
os.system("./cloudflared tunnel --url http://localhost:8501")