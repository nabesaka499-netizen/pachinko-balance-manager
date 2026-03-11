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
