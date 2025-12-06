import streamlit as st
import google.generativeai as genai
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# 設定網頁
st.set_page_config(page_title="AI 爆款短影音複製機 (秒數精準版)", page_icon="⏱️", layout="wide")

# ================= 側邊欄：API Key =================
with st.sidebar:
    st.header("🔑 啟動設定 (Bring Your Own Key)")
    st.info("請輸入 API Key 以啟動工具")
    
    youtube_key = st.text_input("1. YouTube API Key", type="password")
    gemini_key = st.text_input("2. Gemini API Key", type="password")
    kling_token = st.text_input("3. Kling Token", type="password")
    
    st.divider()
    st.caption("Updated for Jiang Mo | Precision Duration Filter")

# ================= 檢查鑰匙 =================
def check_keys():
    if not youtube_key or not gemini_key:
        st.warning("⚠️ 請先在左側側邊欄填入 API Key！")
        st.stop()

# ================= 輔助功能：解析 YouTube 時間格式 (PT1M15S -> 75秒) =================
def parse_duration(duration_iso):
    """將 ISO 8601 格式 (如 PT1M5S) 轉為秒數 (65)"""
    try:
        # 使用正規表達式抓取 分(M) 和 秒(S)
        match = re.match(r'PT((\d+)M)?((\d+)S)?', duration_iso)
        if not match: return 0
        
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(4) or 0)
        return minutes * 60 + seconds
    except:
        return 0

# ================= 核心搜尋邏輯 =================
def search_youtube(api_key, query, days, min_views, max_seconds):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        pub_after = (datetime.now() - timedelta(days=days)).isoformat("T") + "Z"
        
        # 1. 初步搜尋 (先抓 50 筆短片，因為過濾秒數後會變少)
        res = youtube.search().list(
            q=query, part='id,snippet', maxResults=50, 
            order='viewCount', publishedAfter=pub_after, 
            type='video', videoDuration='short' # 這裡只能過濾 < 4分鐘
        ).execute()
        
        v_ids = [i['id']['videoId'] for i in res['items']]
        if not v_ids: return []
        
        # 2. 抓取詳細資料 (包含 duration 和 viewCount)
        stats = youtube.videos().list(
            part='statistics,snippet,contentDetails', # 多抓了 contentDetails
            id=','.join(v_ids)
        ).execute()
        
        final = []
        for i in stats['items']:
            # 取得觀看數
            views = int(i['statistics'].get('viewCount', 0))
            # 取得並計算秒數
            duration_str = i['contentDetails']['duration']
            seconds = parse_duration(duration_str)
            
            # ⭐️ 這裡進行雙重過濾：觀看數夠高 AND 秒數夠短
            if views >= min_views and 0 < seconds <= max_seconds:
                final.append({
                    'title': i['snippet']['title'], 
                    'img': i['snippet']['thumbnails']['high']['url'], 
                    'views': views, 
                    'duration': seconds, # 存起來顯示用
                    'id': i['id'],
                    'url': f"https://www.youtube.com/watch?v={i['id']}"
                })
                
        # 依照觀看數排序
        return sorted(final, key=lambda x: x['views'], reverse=True)
    except Exception as e:
        st.error(f"YouTube 搜尋失敗: {e}")
        return []

def make_prompt(gemini_key, title, duration):
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 提示詞中加入秒數限制
        prompt = f"你是一位短影音導演。請分析爆款標題：「{title}」。請構思一個 {duration} 秒左右的短影片。請直接給我一段【英文 Prompt】給 Kling AI 生成，包含：主體描述、環境光影、運鏡方式。不要有其他廢話。"
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Gemini 分析失敗: {e}"

# ================= 主畫面 (UI) =================
st.title("⏱️ AI 爆款複製機 (精準秒數版)")
check_keys()

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    q = st.text_input("輸入關鍵字", "貓咪 療癒")
    days = st.slider("幾天內的爆款?", 1, 90, 7)
with col2:
    # ⭐️ 新增的秒數拉桿
    max_sec = st.slider("影片長度上限 (秒)", 5, 60, 15, help="只會搜尋比這個時間短的影片")
with col3:
    v = st.number_input("最低觀看數", 10000)
    
if st.button("🔍 搜尋爆款", type="primary"):
    with st.spinner(f"正在挖掘 {max_sec} 秒以內的爆款..."):
        res = search_youtube(youtube_key, q, days, v, max_sec)
        if res:
            st.success(f"找到 {len(res)} 支符合條件的影片！")
            st.session_state['results'] = res
        else:
            st.warning("找不到影片，請嘗試放寬秒數或觀看數條件。")

if 'results' in st.session_state:
    st.divider()
    for item in st.session_state['results
