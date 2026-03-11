import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import os

# ページ設定
st.set_page_config(page_title="パチンコ収支管理", layout="wide", initial_sidebar_state="expanded")

# カスタムCSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1d3a 100%);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 32px;
        color: #00d4ff;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        color: #8b9dc3;
        font-size: 16px;
    }
    
    .calendar-day {
        background: rgba(26, 29, 58, 0.8);
        border: 1px solid #404558;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s;
        height: 100px;
    }
    
    .calendar-day:hover {
        background: rgba(0, 212, 255, 0.1);
        border-color: #00d4ff;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
    }
    
    .calendar-day-number {
        color: #dfe3ee;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    
    .calendar-day-balance {
        color: #00d4ff;
        font-size: 16px;
        font-weight: bold;
    }
    
    .calendar-day-positive {
        color: #00ff88;
    }
    
    .calendar-day-negative {
        color: #ff4444;
    }
    
    .stButton>button {
        background-color: #00d4ff;
        color: #0a0e27;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 12px 24px;
    }
    
    .stButton>button:hover {
        background-color: #00b8e6;
    }
    
    h1, h2, h3 {
        color: #00d4ff !important;
    }
    
    [data-testid="stSidebar"] {
        background: rgba(26, 29, 58, 0.95);
    }
</style>
""", unsafe_allow_html=True)

# データファイル
DATA_FILE = "data/records.csv"
os.makedirs("data", exist_ok=True)

def init_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["日付", "種類", "レート", "入金額", "出玉数", "遊技時間", "収支", "時給"])
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def load_data():
    init_csv()
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    for col in ['遊技時間', '時給']:
        if col not in df.columns:
            df[col] = 0
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# セッション状態の初期化
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False

# サイドバー
st.sidebar.title("📊 分析メニュー")

# 月選択
current_date = datetime.now()
year = st.sidebar.selectbox("年", range(2020, 2030), index=current_date.year - 2020)
month = st.sidebar.selectbox("月", range(1, 13), index=current_date.month - 1)

st.sidebar.markdown("---")

# データ読み込み
df = load_data()

# 統計情報（サイドバー）
st.sidebar.header("📈 今月の統計")

if len(df) > 0:
    df['日付'] = pd.to_datetime(df['日付'])
    month_df = df[(df['日付'].dt.year == year) & (df['日付'].dt.month == month)]
    
    if len(month_df) > 0:
        total_balance = float(month_df['収支'].sum())
        total_deposit = float(month_df['入金額'].sum())
        total_time = float(month_df['遊技時間'].sum())
        avg_hourly = int(total_balance / total_time) if total_time > 0 else 0
        
        st.sidebar.metric("💰 月間収支", f"{int(total_balance):,}円")
        st.sidebar.metric("💳 月間入金", f"{int(total_deposit):,}円")
        st.sidebar.metric("⏱️ 総遊技時間", f"{total_time:.1f}h")
        st.sidebar.metric("⚡ 平均時給", f"{avg_hourly:,}円")
        st.sidebar.metric("🎯 稼働日数", f"{len(month_df)}日")
    else:
        st.sidebar.info("今月のデータなし")
else:
    st.sidebar.info("データなし")

# メインエリア：カレンダー
st.title(f"📅 {year}年{month}月")

# カレンダー生成
cal = calendar.monthcalendar(year, month)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]

# 曜日ヘッダー
cols = st.columns(7)
for i, day in enumerate(weekdays):
    with cols[i]:
        st.markdown(f"<div style='text-align: center; color: #8b9dc3; font-weight: bold; margin-bottom: 10px;'>{day}</div>", unsafe_allow_html=True)

# カレンダー表示
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # その日のデータを取得
                day_data = df[df['日付'].astype(str) == date_str]
                
                if len(day_data) > 0:
                    balance = int(day_data['収支'].sum())
                    color_class = "calendar-day-positive" if balance > 0 else "calendar-day-negative"
                    balance_text = f"<div class='calendar-day-balance {color_class}'>{balance:+,}円</div>"
                else:
                    balance_text = "<div style='color: #555; font-size: 12px;'>未入力</div>"
                
                # クリック可能なボタン
                if st.button(f"{day}", key=f"day_{day}", use_container_width=True):
                    st.session_state.selected_date = date_str
                    st.session_state.show_modal = True
                    st.rerun()
                
                st.markdown(balance_text, unsafe_allow_html=True)

# モーダル（データ入力/編集）
if st.session_state.show_modal and st.session_state.selected_date:
    st.markdown("---")
    st.header(f"📝 {st.session_state.selected_date} のデータ")
    
    # 既存データ取得
    existing_data = df[df['日付'].astype(str) == st.session_state.selected_date]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if len(existing_data) > 0:
            st.subheader("既存データ")
            st.dataframe(existing_data[['種類', 'レート', '入金額', '出玉数', '遊技時間', '収支', '時給']], use_container_width=True, hide_index=True)
            
            if st.button("🗑️ このデータを削除", type="secondary"):
                df = df[df['日付'].astype(str) != st.session_state.selected_date]
                save_data(df)
                st.success("削除しました！")
                st.session_state.show_modal = False
                st.rerun()
        
        st.subheader("新規入力/追加")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            game_type = st.selectbox("種類", ["パチンコ", "スロット"], key="modal_type")
            rate = st.number_input("レート（円）", min_value=1, value=4 if game_type == "パチンコ" else 20, key="modal_rate")
        
        with col_b:
            deposit = st.number_input("入金額（円）", min_value=0, value=0, step=1000, key="modal_deposit")
            payout = st.number_input("出玉数", min_value=0, value=0, step=100, key="modal_payout")
        
        with col_c:
            play_time = st.number_input("遊技時間（h）", min_value=0.0, value=0.0, step=0.5, format="%.1f", key="modal_time")
            
            balance = (payout * rate) - deposit
            hourly_wage = int(balance / play_time) if play_time > 0 else 0
            
            st.metric("収支", f"{balance:,}円")
            st.metric("時給", f"{hourly_wage:,}円")
        
        col_x, col_y = st.columns(2)
        
        with col_x:
            if st.button("💾 データを追加", use_container_width=True, type="primary"):
                new_row = {
                    "日付": st.session_state.selected_date,
                    "種類": game_type,
                    "レート": rate,
                    "入金額": deposit,
                    "出玉数": payout,
                    "遊技時間": play_time,
                    "収支": balance,
                    "時給": hourly_wage
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success("追加しました！")
                st.rerun()
        
        with col_y:
            if st.button("✖️ 閉じる", use_container_width=True):
                st.session_state.show_modal = False
                st.rerun()
