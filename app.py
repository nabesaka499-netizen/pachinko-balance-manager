import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os

# ページ設定
st.set_page_config(
    page_title="パチンコ収支管理 PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1d3a 100%);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00d4ff;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        color: #8b9dc3;
        font-size: 14px;
        font-weight: 600;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
        color: #0a0e27;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.4);
    }
    
    h1, h2, h3 {
        color: #00d4ff !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stSidebar"] {
        background: rgba(15, 18, 35, 0.95);
        backdrop-filter: blur(10px);
    }
    
    .calendar-header {
        text-align: center;
        color: #8b9dc3;
        font-weight: bold;
        font-size: 14px;
        padding: 10px;
        background: rgba(26, 29, 58, 0.5);
        border-radius: 8px 8px 0 0;
        margin-bottom: 5px;
    }
    
    .day-button {
        width: 100%;
        min-height: 80px;
        margin-bottom: 5px;
    }
    
    .balance-positive {
        color: #00ff88;
        font-weight: bold;
        font-size: 14px;
    }
    
    .balance-negative {
        color: #ff4466;
        font-weight: bold;
        font-size: 14px;
    }
    
    .balance-zero {
        color: #666;
        font-size: 12px;
    }
    
    .dataframe {
        background: rgba(26, 29, 58, 0.6) !important;
    }
    
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# データファイル
DATA_FILE = "data/records.csv"
MEDALS_FILE = "data/medals.csv"
os.makedirs("data", exist_ok=True)

# CSV初期化
def init_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "日付", "種類", "レート", "入金額", "出玉数", 
            "遊技時間", "収支", "時給"
        ])
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    
    if not os.path.exists(MEDALS_FILE):
        df = pd.DataFrame(columns=["日付", "店舗", "貯メダル数", "メモ"])
        df.to_csv(MEDALS_FILE, index=False, encoding="utf-8-sig")

# データ読み込み
def load_data():
    init_csv()
    try:
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        # 必須カラムの確認と追加
        for col in ['遊技時間', '時給']:
            if col not in df.columns:
                df[col] = 0
        return df
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame(columns=[
            "日付", "種類", "レート", "入金額", "出玉数", 
            "遊技時間", "収支", "時給"
        ])

def load_medals():
    init_csv()
    try:
        return pd.read_csv(MEDALS_FILE, encoding="utf-8-sig")
    except:
        return pd.DataFrame(columns=["日付", "店舗", "貯メダル数", "メモ"])

# データ保存
def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def save_medals(df):
    df.to_csv(MEDALS_FILE, index=False, encoding="utf-8-sig")

# セッション状態初期化
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False
if 'show_medals' not in st.session_state:
    st.session_state.show_medals = False

# サイドバー
st.sidebar.title("📊 分析メニュー")

# 月選択
current_date = datetime.now()
year = st.sidebar.selectbox(
    "年", 
    range(2020, 2031), 
    index=min(current_date.year - 2020, 10)
)
month = st.sidebar.selectbox(
    "月", 
    range(1, 13), 
    index=current_date.month - 1
)

st.sidebar.markdown("---")

# データ読み込み
df = load_data()
medals_df = load_medals()

# 統計情報
st.sidebar.header("📈 今月の統計")

if len(df) > 0:
    df['日付'] = pd.to_datetime(df['日付'], errors='coerce')
    month_df = df[
        (df['日付'].dt.year == year) & 
        (df['日付'].dt.month == month)
    ].copy()
    
    if len(month_df) > 0:
        total_balance = float(month_df['収支'].sum())
        total_deposit = float(month_df['入金額'].sum())
        total_time = float(month_df['遊技時間'].sum())
        avg_hourly = int(total_balance / total_time) if total_time > 0 else 0
        active_days = len(month_df)
        
        st.sidebar.metric("💰 月間収支", f"{int(total_balance):,}円")
        st.sidebar.metric("💳 月間入金", f"{int(total_deposit):,}円")
        st.sidebar.metric("⏱️ 総遊技時間", f"{total_time:.1f}h")
        st.sidebar.metric("⚡ 平均時給", f"{avg_hourly:,}円")
        st.sidebar.metric("🎯 稼働日数", f"{active_days}日")
    else:
        st.sidebar.info("📭 今月のデータなし")
else:
    st.sidebar.info("📭 データなし")

st.sidebar.markdown("---")

# 貯メダル管理ボタン
if st.sidebar.button("🪙 貯メダル管理", use_container_width=True):
    st.session_state.show_medals = not st.session_state.show_medals

# メインエリア
st.title(f"📅 {year}年{month}月")

# 貯メダル管理画面
if st.session_state.show_medals:
    st.markdown("---")
    st.header("🪙 貯メダル管理")
    
    # 新規追加
    with st.expander("➕ 新規追加", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            medal_date = st.date_input("日付", datetime.now(), key="medal_date")
        with col2:
            medal_store = st.text_input("店舗名", key="medal_store")
        with col3:
            medal_count = st.number_input("貯メダル数", min_value=0, step=100, key="medal_count")
        with col4:
            medal_memo = st.text_input("メモ", key="medal_memo")
        
        if st.button("💾 貯メダルを追加", use_container_width=True):
            if medal_store:
                new_medal = {
                    "日付": str(medal_date),
                    "店舗": medal_store,
                    "貯メダル数": medal_count,
                    "メモ": medal_memo
                }
                medals_df = pd.concat([medals_df, pd.DataFrame([new_medal])], ignore_index=True)
                save_medals(medals_df)
                st.success("✅ 追加しました！")
                st.rerun()
            else:
                st.warning("⚠️ 店舗名を入力してください")
    
    # 既存データ表示
    st.subheader("📋 貯メダル一覧")
    
    if len(medals_df) > 0:
        # 編集可能なテーブル
        edited_medals = st.data_editor(
            medals_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="medals_editor"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 変更を保存", use_container_width=True, type="primary"):
                save_medals(edited_medals)
                st.success("✅ 保存しました！")
                st.rerun()
        
        with col2:
            if st.button("🗑️ 全削除", use_container_width=True, type="secondary"):
                if st.session_state.get('confirm_delete_all'):
                    medals_df = pd.DataFrame(columns=["日付", "店舗", "貯メダル数", "メモ"])
                    save_medals(medals_df)
                    st.session_state.confirm_delete_all = False
                    st.success("✅ 全削除しました！")
                    st.rerun()
                else:
                    st.session_state.confirm_delete_all = True
                    st.warning("⚠️ もう一度クリックで確定")
        
        # 合計表示
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🏪 登録店舗数", f"{medals_df['店舗'].nunique()}店舗")
        with col2:
            st.metric("🪙 総貯メダル数", f"{medals_df['貯メダル数'].sum():,}枚")
    else:
        st.info("📭 貯メダルデータがありません")
    
    st.markdown("---")

# カレンダー表示
cal = calendar.monthcalendar(year, month)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]

# 曜日ヘッダー
cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    with cols[i]:
        st.markdown(
            f"<div class='calendar-header'>{day_name}</div>",
            unsafe_allow_html=True
        )

# カレンダー本体
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # その日のデータ取得
                day_data = df[df['日付'].astype(str) == date_str]
                
                # 収支表示
                if len(day_data) > 0:
                    balance = int(day_data['収支'].sum())
                    if balance > 0:
                        balance_html = f"<div class='balance-positive'>+{balance:,}円</div>"
                    elif balance < 0:
                        balance_html = f"<div class='balance-negative'>{balance:,}円</div>"
                    else:
                        balance_html = f"<div class='balance-zero'>±0円</div>"
                else:
                    balance_html = "<div class='balance-zero'>未入力</div>"
                
                # ボタン
                if st.button(
                    f"**{day}**",
                    key=f"day_{year}_{month}_{day}",
                    use_container_width=True
                ):
                    st.session_state.selected_date = date_str
                    st.session_state.show_modal = True
                    st.rerun()
                
                st.markdown(balance_html, unsafe_allow_html=True)

# モーダル（データ入力/編集）
if st.session_state.show_modal and st.session_state.selected_date:
    st.markdown("---")
    st.header(f"📝 {st.session_state.selected_date}")
    
    existing_data = df[df['日付'].astype(str) == st.session_state.selected_date]
    
    # 既存データ表示
    if len(existing_data) > 0:
        st.subheader("📊 既存データ")
        st.dataframe(
            existing_data[[
                '種類', 'レート', '入金額', '出玉数', 
                '遊技時間', '収支', '時給'
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("🗑️ このデータを削除", type="secondary"):
            df = df[df['日付'].astype(str) != st.session_state.selected_date]
            save_data(df)
            st.success("✅ 削除しました！")
            st.session_state.show_modal = False
            st.rerun()
        
        st.markdown("---")
    
    # 新規入力
    st.subheader("➕ 新規入力")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        game_type = st.selectbox(
            "種類",
            ["パチンコ", "スロット"],
            key="input_type"
        )
        rate = st.number_input(
            "レート（円）",
            min_value=1,
            value=4 if game_type == "パチンコ" else 20,
            key="input_rate"
        )
    
    with col2:
        deposit = st.number_input(
            "入金額（円）",
            min_value=0,
            value=0,
            step=1000,
            key="input_deposit"
        )
        payout = st.number_input(
            "出玉数（発/枚）",
            min_value=0,
            value=0,
            step=100,
            key="input_payout"
        )
    
    with col3:
        play_time = st.number_input(
            "遊技時間（時間）",
            min_value=0.0,
            value=0.0,
            step=0.5,
            format="%.1f",
            key="input_time"
        )
        
        # 収支計算
        balance = (payout * rate) - deposit
        hourly_wage = int(balance / play_time) if play_time > 0 else 0
        
        st.metric("💵 収支", f"{balance:,}円")
        st.metric("⏰ 時給", f"{hourly_wage:,}円")
    
    # ボタン
    col_a, col_b = st.columns(2)
    
    with col_a:
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
            st.success("✅ 追加しました！")
            st.rerun()
    
    with col_b:
        if st.button("✖️ 閉じる", use_container_width=True):
            st.session_state.show_modal = False
            st.rerun()
