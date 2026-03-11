import streamlit as st

st.set_page_config(page_title="収支管理簿", layout="wide")
st.title("🎰 収支管理簿")
import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ページ設定
st.set_page_config(page_title="パチンコ/給料管理システム", layout="wide")

# データファイルのパス
DATA_FILE = "data/records.csv"

# データフォルダが存在しない場合は作成
os.makedirs("data", exist_ok=True)

# CSVファイルの初期化
def init_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["日付", "種類", "レート", "入金額", "出玉数", "収支"])
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# データ読み込み
def load_data():
    init_csv()
    return pd.read_csv(DATA_FILE, encoding="utf-8-sig")

# データ保存
def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# メインタイトル
st.title("🎰 パチンコ|給料管理システム")

# サイドバー：データ入力
st.sidebar.header("📝 データ入力")

date = st.sidebar.date_input("日付", datetime.now())
game_type = st.sidebar.selectbox("種類", ["パチンコ", "スロット"])
rate = st.sidebar.number_input("貸玉レート（円）", min_value=1, value=4 if game_type == "パチンコ" else 20)
deposit = st.sidebar.number_input("入金額（円）", min_value=0, value=0, step=1000)
payout = st.sidebar.number_input("出玉数（発/枚）", min_value=0, value=0, step=100)

# 収支計算
balance = (payout * rate) - deposit

st.sidebar.metric("収支", f"{balance:,}円", delta=f"{balance:+,}円")

# データ追加ボタン
if st.sidebar.button("💾 データを追加"):
    df = load_data()
    new_row = {
        "日付": str(date),
        "種類": game_type,
        "レート": rate,
        "入金額": deposit,
        "出玉数": payout,
        "収支": balance
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.sidebar.success("データを追加しました！")
    st.rerun()

# メインエリア：データ表示
st.header("📊 収支データ")

df = load_data()

if len(df) > 0:
    # 統計情報
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総収支", f"{df['収支'].sum():,}円")
    with col2:
        st.metric("総入金額", f"{df['入金額'].sum():,}円")
    with col3:
        st.metric("平均収支", f"{df['収支'].mean():.0f}円")
    with col4:
        st.metric("データ件数", f"{len(df)}件")
    
    # データテーブル
    st.dataframe(df, use_container_width=True)
    
    # グラフ表示
    st.line_chart(df.set_index("日付")["収支"])
else:
    st.info("まだデータがありません。左のサイドバーからデータを入力してください。")
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import calendar

# ページ設定
st.set_page_config(page_title="パチンコ/給料管理システム", layout="wide", initial_sidebar_state="expanded")

# カスタムCSS（ダークモード + シアンアクセント）
st.markdown("""
<style>
    /* 背景色 */
    .stApp {
        background-color: #0e1117;
    }
    
    /* メトリクス */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00d4ff;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        color: #8b9dc3;
        font-size: 14px;
    }
    
    /* データテーブル */
    .stDataFrame {
        background-color: #1a1d29;
        border-radius: 10px;
    }
    
    /* サイドバー */
    [data-testid="stSidebar"] {
        background-color: #1a1d29;
    }
    
    /* ボタン */
    .stButton>button {
        background-color: #00d4ff;
        color: #0e1117;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
    }
    
    .stButton>button:hover {
        background-color: #00b8e6;
    }
    
    /* タイトル */
    h1, h2, h3 {
        color: #00d4ff !important;
    }
    
    /* テキスト */
    p, label {
        color: #dfe3ee;
    }
    
    /* 入力フィールド */
    input, select {
        background-color: #262b3d !important;
        color: #dfe3ee !important;
        border: 1px solid #404558 !important;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# データファイルのパス
DATA_FILE = "data/records.csv"

# データフォルダが存在しない場合は作成
os.makedirs("data", exist_ok=True)

# CSVファイルの初期化
def init_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["日付", "種類", "レート", "入金額", "出玉数", "遊技時間", "収支", "時給"])
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# データ読み込み
def load_data():
    init_csv()
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    if '遊技時間' not in df.columns:
        df['遊技時間'] = 0.0
    if '時給' not in df.columns:
        df['時給'] = 0
    return df

# データ保存
def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# メインタイトル
st.title("🎰 パチンコ収支管理システム PRO")
st.markdown("---")

# サイドバー：データ入力
st.sidebar.header("📝 データ入力")

date = st.sidebar.date_input("📅 日付", datetime.now())
game_type = st.sidebar.selectbox("🎮 種類", ["パチンコ", "スロット"])
rate = st.sidebar.number_input("💴 貸玉レート（円）", min_value=1, value=4 if game_type == "パチンコ" else 20)
deposit = st.sidebar.number_input("💰 入金額（円）", min_value=0, value=0, step=1000)
payout = st.sidebar.number_input("🎯 出玉数（発/枚）", min_value=0, value=0, step=100)
play_time = st.sidebar.number_input("⏱️ 遊技時間（時間）", min_value=0.0, value=0.0, step=0.5, format="%.1f")

# 収支計算
balance = (payout * rate) - deposit
hourly_wage = int(balance / play_time) if play_time > 0 else 0

st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("💵 収支", f"{balance:,}円")
with col2:
    st.metric("⏰ 時給", f"{hourly_wage:,}円")

# データ追加ボタン
if st.sidebar.button("💾 データを追加", use_container_width=True):
    df = load_data()
    new_row = {
        "日付": str(date),
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
    st.sidebar.success("✅ データを追加しました！")
    st.rerun()

# メインエリア
df = load_data()

if len(df) > 0:
    # 統計情報
    st.header("📊 収支統計")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 総収支", f"{df['収支'].sum():,}円")
    with col2:
        st.metric("💳 総入金額", f"{df['入金額'].sum():,}円")
    with col3:
        st.metric("⏱️ 総遊技時間", f"{df['遊技時間'].sum():.1f}時間")
    with col4:
        avg_hourly = int(df['収支'].sum() / df['遊技時間'].sum()) if df['遊技時間'].sum() > 0 else 0
        st.metric("⚡ 平均時給", f"{avg_hourly:,}円")
    with col5:
        st.metric("📁 データ件数", f"{len(df)}件")
    
    st.markdown("---")
    
    # 月別集計
    st.header("📅 月別カレンダー")
    
    df['日付'] = pd.to_datetime(df['日付'])
    df['年月'] = df['日付'].dt.to_period('M')
    
    monthly_summary = df.groupby('年月').agg({
        '収支': 'sum',
        '入金額': 'sum',
        '遊技時間': 'sum'
    }).reset_index()
    
    monthly_summary['年月'] = monthly_summary['年月'].astype(str)
    monthly_summary['平均時給'] = (monthly_summary['収支'] / monthly_summary['遊技時間']).fillna(0).astype(int)
    
    st.dataframe(
        monthly_summary.rename(columns={
            '年月': '📅 年月',
            '収支': '💰 収支',
            '入金額': '💳 入金額',
            '遊技時間': '⏱️ 遊技時間',
            '平均時給': '⚡ 平均時給'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # データテーブル（編集可能）
    st.header("📋 全データ")
    
    # 編集機能
    edited_df = st.data_editor(
        df[['日付', '種類', 'レート', '入金額', '出玉数', '遊技時間', '収支', '時給']],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )
    
    # 保存ボタン
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 変更を保存", use_container_width=True):
            save_data(edited_df)
            st.success("✅ 変更を保存しました！")
            st.rerun()
    
else:
    st.info("📝 まだデータがありません。左のサイドバーからデータを入力してください。")
