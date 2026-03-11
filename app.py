import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta, time, date
import json
import requests
import base64
from io import StringIO

try:
    import holidays
    from streamlit_calendar import calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

# --- Page Config ---
st.set_page_config(page_title="収支管理簿", page_icon="💹", layout="wide")

# --- Custom CSS (Neon Theme) ---
st.markdown("""
<style>
    .main { background-color: #0a0b1e; }
    .stApp { background: radial-gradient(circle at top right, #161b33, #0a0b1e); }
    h1, h2, h3 { color: #00f2ff !important; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); }
    .stMetric { 
        background: rgba(0, 242, 255, 0.05) !important; 
        border: 1px solid rgba(0, 242, 255, 0.3) !important; 
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
    }
    .stDataFrame, .stTable { 
        border: 1px solid rgba(0, 242, 255, 0.2); 
        border-radius: 10px; 
    }
    div[data-testid="stMetricValue"] > div { 
        color: #00f2ff !important; 
        font-weight: bold;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 242, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- Global Timezone (JST) ---
JST = timezone(timedelta(hours=9))

# --- Data Constants ---
GITHUB_USER = "nabesaka499-netizen"
GITHUB_REPO = "my-pachinko-ledger"
DATA_FILE = "records.csv"
DRAFT_FILE = "drafts.json"
SAVINGS_FILE = "savings.csv"

# --- Session State Initialization ---
def init_session_state():
    """セッション状態を初期化"""
    defaults = {
        "active_p": "Player 1",
        "selected_cal_date": None,
        "editing_id": None,
        "view_month": datetime.now().strftime("%Y-%m"),
        "nav_lock": False,
        "preview_date": None,
        "confirm_delete_all": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Helper Functions ---
def get_github_auth():
    """GitHub認証トークンを取得"""
    try:
        return st.secrets.get("GITHUB_TOKEN")
    except Exception:
        return None

def load_data():
    """データを読み込み（キャッシュ対応）"""
    if "records" not in st.session_state:
        token = get_github_auth()
        df = pd.DataFrame()
        
        if token:
            try:
                url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DATA_FILE}"
                headers = {"Authorization": f"token {token}"}
                r = requests.get(url, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    content_json = r.json()
                    content = base64.b64decode(content_json["content"]).decode("utf-8")
                    df = pd.read_csv(StringIO(content))
                    st.session_state.github_sha = content_json["sha"]
            except Exception as e:
                st.warning(f"GitHub読み込みエラー: {e}")
        else:
            try:
                df = pd.read_csv(DATA_FILE)
            except FileNotFoundError:
                pass
        
        # スキーマ修正
        expected_cols = {
            "id": str, "player": str, "game_type": str, "date": str,
            "hall": str, "machine": str, "hours": float, "invest": int,
            "recovery": int, "balance": int, "memo": str,
            "start_savings": int, "end_savings": int, "rate": float,
            "cash_out_yen": int, "start_time": str, "end_time": str
        }
        
        for col, dtype in expected_cols.items():
            if col not in df.columns:
                default_val = "" if dtype == str else 0
                df[col] = default_val
        
        if not df.empty:
            # データクリーニング
            df['player'] = df['player'].astype(str).str.strip()
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df = df.dropna(subset=['date'])
            
            # 数値列の変換
            num_cols = ["invest", "recovery", "balance", "start_savings", 
                       "end_savings", "rate", "cash_out_yen", "hours"]
            for col in num_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 文字列列のNaN処理
            str_cols = ["player", "game_type", "hall", "machine", "memo", 
                       "start_time", "end_time", "id"]
            for col in str_cols:
                df[col] = df[col].fillna("").astype(str)
        
        st.session_state.records = df
    
    return st.session_state.records

def save_data(df):
    """データを保存"""
    st.session_state.records = df
    token = get_github_auth()
    
    if token:
        try:
            url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DATA_FILE}"
            headers = {"Authorization": f"token {token}"}
            r_get = requests.get(url, headers=headers, timeout=10)
            
            sha = r_get.json()["sha"] if r_get.status_code == 200 else None
            csv_content = df.to_csv(index=False)
            
            data = {
                "message": f"Update @ {datetime.now(JST).strftime('%Y-%m-%d %H:%M')}",
                "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
            }
            if sha:
                data["sha"] = sha
            
            res = requests.put(url, json=data, headers=headers, timeout=10)
            
            if res.status_code in [200, 201]:
                st.session_state.github_sha = res.json()["content"]["sha"]
                return True
        except Exception as e:
            st.error(f"保存エラー: {e}")
            return False
    else:
        try:
            df.to_csv(DATA_FILE, index=False)
            return True
        except Exception as e:
            st.error(f"ローカル保存エラー: {e}")
            return False

def load_savings():
    """貯玉データ読み込み"""
    if "savings" not in st.session_state:
        token = get_github_auth()
        df = pd.DataFrame()
        
        if token:
            try:
                url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{SAVINGS_FILE}"
                headers = {"Authorization": f"token {token}"}
                r = requests.get(url, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    content_json = r.json()
                    content = base64.b64decode(content_json["content"]).decode("utf-8")
                    df = pd.read_csv(StringIO(content))
                    st.session_state.github_sha_savings = content_json["sha"]
            except Exception:
                pass
        else:
            try:
                df = pd.read_csv(SAVINGS_FILE)
            except FileNotFoundError:
                pass
        
        expected_cols = ["id", "player", "hall", "saved_medals", "saved_balls", "updated_at"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0 if col in ["saved_medals", "saved_balls"] else ""
        
        st.session_state.savings = df
    
    return st.session_state.savings

def save_savings(df):
    """貯玉データ保存"""
    st.session_state.savings = df
    token = get_github_auth()
    
    if token:
        try:
            url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{SAVINGS_FILE}"
            headers = {"Authorization": f"token {token}"}
            r_get = requests.get(url, headers=headers, timeout=10)
            
            sha = r_get.json()["sha"] if r_get.status_code == 200 else None
            csv_content = df.to_csv(index=False)
            
            data = {
                "message": f"Update savings @ {datetime.now(JST).strftime('%Y-%m-%d %H:%M')}",
                "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
            }
            if sha:
                data["sha"] = sha
            
            res = requests.put(url, json=data, headers=headers, timeout=10)
            
            if res.status_code in [200, 201]:
                st.session_state.github_sha_savings = res.json()["content"]["sha"]
        except Exception as e:
            st.error(f"貯玉保存エラー: {e}")
    else:
        try:
            df.to_csv(SAVINGS_FILE, index=False)
        except Exception as e:
            st.error(f"ローカル保存エラー: {e}")

def load_drafts():
    """下書きデータ読み込み"""
    if "drafts" not in st.session_state:
        try:
            with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                st.session_state.drafts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            st.session_state.drafts = {
                "Player 1": {
                    "start_hour": 9, "start_min": 0,
                    "last_hall": None, "last_machine": None, "last_rate": None
                },
                "Player 2": {
                    "start_hour": 9, "start_min": 0,
                    "last_hall": None, "last_machine": None, "last_rate": None
                }
            }
    return st.session_state.drafts

def save_drafts():
    """下書きデータ保存"""
    try:
        with open(DRAFT_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.drafts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"下書き保存エラー: {e}")

def get_last_player_defaults(df, player):
    """プレイヤーの最後の入力値を取得"""
    p_draft = load_drafts().get(player, {})
    
    if p_draft.get('last_hall') and p_draft.get('last_machine'):
        return p_draft['last_hall'], p_draft['last_machine']
    
    if not df.empty:
        p_history = df[df['player'] == player]
        if not p_history.empty:
            last_record = p_history.iloc[-1]
            return last_record['hall'], last_record['machine']
    
    return "新規入力...", "新規入力..."

def get_last_hall_savings(df, player, hall_name):
    """指定店舗の最終貯玉数を取得"""
    if df.empty or not hall_name or hall_name in ["記録しない", "新規入力..."]:
        return 0
    
    p_df = df[(df['player'] == player) & (df['hall'] == hall_name)]
    
    if p_df.empty:
        return 0
    
    last_record = p_df.sort_values(by=['date', 'id'], ascending=False).iloc[0]
    savings = int(last_record.get('end_savings', 0))
    cash_out = int(last_record.get('cash_out_yen', 0))
    rate = float(last_record.get('rate', 1.0))
    
    return max(0, savings - int(cash_out / 100 * rate))

def calculate_hours(start_time, end_time):
    """開始時刻と終了時刻から稼働時間を計算"""
    if not start_time or not end_time:
        return 0.0
    
    dummy_date = date.today()
    dt_start = datetime.combine(dummy_date, start_time)
    dt_end = datetime.combine(dummy_date, end_time)
    
    if dt_end < dt_start:
        dt_end += timedelta(days=1)
    
    return round((dt_end - dt_start).total_seconds() / 3600.0, 1)

# --- Main Logic ---
df = load_data()
df_s = load_savings()
load_drafts()

# ============================================================
# Sidebar
# ============================================================
st.sidebar.title("💹 収支管理簿")
menu = st.sidebar.radio(
    "メニュー",
    ["ホーム・記録", "分析 (月別/年別)", "貯玉・貯メダル管理", "一括インポート", "設定"],
    label_visibility="collapsed"
)

# Navigation Reset
if "p_menu" not in st.session_state:
    st.session_state.p_menu = menu

if st.session_state.p_menu != menu:
    if menu in ["ホーム・記録", "貯玉・貯メダル管理"]:
        st.session_state.selected_cal_date = None
        st.session_state.editing_id = None
        st.session_state.preview_date = None
        # カレンダー関連のキャッシュをクリア
        for k in list(st.session_state.keys()):
            if str(k).startswith("main_cal"):
                del st.session_state[k]
    st.session_state.p_menu = menu

# ============================================================
# ホーム・記録
# ============================================================
if menu == "ホーム・記録":
    curr_date_str = st.session_state.get("selected_cal_date")
    p_date = st.session_state.get("preview_date")
    
    # 1. フォーム表示モード (新規追加 / 編集)
    if curr_date_str and str(curr_date_str).lower() != "none":
        st.markdown(f"### 📅 {curr_date_str.replace('-', '/')} の記録")
        st.divider()
        
        e_id = st.session_state.get("editing_id")
        ctx_c1, ctx_c2 = st.columns([5, 1])
        ctx_c1.subheader("✏️ 修正" if e_id else "➕ 新規記録")
        
        if ctx_c2.button("🔙 戻る", use_container_width=True):
            st.session_state.selected_cal_date = None
            st.session_state.editing_id = None
            st.session_state.preview_date = None
            for k in list(st.session_state.keys()):
                if str(k).startswith("main_cal"):
                    del st.session_state[k]
            st.rerun()
        
        # 編集対象レコードの取得
        e_row = None
        if e_id:
            matched = df[
                (df['id'] == str(e_id)) &
                (df['player'].astype(str).str.strip() == st.session_state.active_p)
            ]
            if not matched.empty:
                e_row = matched.iloc[0]
        
        f_p = st.session_state.active_p
        
        col1, col2 = st.columns(2)
        
        with col1:
            # ホール名選択
            h_list = sorted([h for h in df['hall'].dropna().unique() if h])
            last_h, last_m = get_last_player_defaults(df, f_p)
            
            h_idx = (h_list.index(last_h) + 1) if last_h in h_list else 0
            hall = st.selectbox("🏪 ホール名", ["新規入力..."] + h_list, index=h_idx)
            
            if hall == "新規入力...":
                hall = st.text_input("ホール名を入力", value=(e_row['hall'] if e_row is not None else ""))
            
            # 機種名選択
            m_list = sorted([m for m in df['machine'].dropna().unique() if m])
            m_idx = (m_list.index(last_m) + 1) if last_m in m_list else 0
            mach = st.selectbox("🎰 機種名", ["新規入力..."] + m_list, index=m_idx)
            
            if mach == "新規入力...":
                mach = st.text_input("機種名を入力", value=(e_row['machine'] if e_row is not None else ""))
            
            # メモ
            memo = st.text_area("📝 メモ", value=(e_row['memo'] if e_row is not None else ""))
        
        with col2:
            # 種別選択
            gt_idx = 0 if e_row is None or e_row['game_type'] == "スロット" else 1
            gt = st.radio("🎮 種別", ["スロット", "パチンコ"], horizontal=True, index=gt_idx)
            
            # 交換率選択（履歴から推測）
            r_idx = 0
            if e_row is not None and e_row['rate'] in [5.06, 5.5, 27.0, 27.5]:
                r_idx = [5.06, 5.5, 27.0, 27.5].index(e_row['rate'])
            else:
                hall_history = df[df['hall'] == hall]
                if not hall_history.empty:
                    last_hall_rate = float(hall_history.iloc[-1]['rate'])
                    if last_hall_rate in [5.06, 5.5, 27.0, 27.5]:
                        r_idx = [5.06, 5.5, 27.0, 27.5].index(last_hall_rate)
                else:
                    drafts = load_drafts()
                    l_r = drafts.get(f_p, {}).get("last_rate")
                    if l_r in [5.06, 5.5, 27.0, 27.5]:
                        r_idx = [5.06, 5.5, 27.0, 27.5].index(l_r)
            
            rate = st.radio("💱 交換率", [5.06, 5.5, 27.0, 27.5], horizontal=True, index=r_idx)
            
            # 投資額
            invest = st.number_input(
                "💴 投資 (¥)", 
                min_value=0, 
                step=500,
                value=int(e_row['invest']) if e_row is not None else 0
            )
            
            # 貯玉・貯メダル
            l_sav = get_last_hall_savings(df, f_p, hall)
            s_s = st.number_input(
                "🏦 開始貯メダル/玉", 
                min_value=0,
                value=int(e_row['start_savings'] if e_row is not None else l_sav)
            )
            s_e = st.number_input(
                "🏦 終了貯メダル/玉", 
                min_value=0,
                value=int(e_row['end_savings'] if e_row is not None else 0)
            )
            
            # 開始・終了時間
            default_start = time(10, 0)
            default_end = time(12, 0)
            
            if e_row is not None:
                if pd.notna(e_row.get('start_time')) and e_row['start_time']:
                    try:
                        default_start = datetime.strptime(str(e_row['start_time']), "%H:%M").time()
                    except Exception:
                        pass
                if pd.notna(e_row.get('end_time')) and e_row['end_time']:
                    try:
                        default_end = datetime.strptime(str(e_row['end_time']), "%H:%M").time()
                    except Exception:
                        pass
            
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                start_time = st.time_input("🕐 開始時間", value=default_start)
            with c_t2:
                end_time = st.time_input("🕑 終了時間", value=default_end)
            
            # 稼働時間計算
            delta_hr = calculate_hours(start_time, end_time)
            st.info(f"⏳ **稼働時間: {delta_hr:.1f} 時間**")
        
        # 保存ボタン
        if st.button("💾 保存する", use_container_width=True, type="primary"):
            # バリデーション
            if not hall or hall == "新規入力...":
                st.error("⚠️ ホール名を入力してください")
            elif not mach or mach == "新規入力...":
                st.error("⚠️ 機種名を入力してください")
            else:
                # 収支計算
                bal = round((s_e - s_s) * (100 / rate) - invest)
                
                n_row = {
                    "id": str(e_id) if e_id else str(int(datetime.now().timestamp())),
                    "player": f_p,
                    "game_type": gt,
                    "date": str(curr_date_str),
                    "hall": hall,
                    "machine": mach,
                    "hours": delta_hr,
                    "invest": invest,
                    "recovery": 0,
                    "balance": bal,
                    "memo": memo,
                    "start_savings": s_s,
                    "end_savings": s_e,
                    "rate": rate,
                    "cash_out_yen": 0,
                    "start_time": start_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M")
                }
                
                # データ更新
                if e_id:
                    df = df[df['id'] != str(e_id)]
                
                df = pd.concat([df, pd.DataFrame([n_row])], ignore_index=True)
                
                if save_data(df):
                    # 貯玉データ更新
                    updated = False
                    for idx, row in df_s.iterrows():
                        if row['player'] == f_p and row['hall'] == hall:
                            if gt == "スロット":
                                df_s.at[idx, 'saved_medals'] = s_e
                            else:
                                df_s.at[idx, 'saved_balls'] = s_e
                            df_s.at[idx, 'updated_at'] = datetime.now(JST).strftime('%Y-%m-%d %H:%M')
                            updated = True
                            break
                    
                    if not updated and s_e > 0:
                        new_s_row = {
                            "id": str(int(datetime.now().timestamp())),
                            "player": f_p,
                            "hall": hall,
                            "saved_medals": s_e if gt == "スロット" else 0,
                            "saved_balls": s_e if gt == "パチンコ" else 0,
                            "updated_at": datetime.now(JST).strftime('%Y-%m-%d %H:%M')
                        }
                        df_s = pd.concat([df_s, pd.DataFrame([new_s_row])], ignore_index=True)
                    
                    save_savings(df_s)
                    
                    # 下書き保存
                    drafts = load_drafts()
                    drafts[f_p].update({
                        "last_hall": hall,
                        "last_machine": mach,
                        "last_rate": rate
                    })
                    save_drafts()
                    
                    # リセット
                    st.session_state.selected_cal_date = None
                    st.session_state.editing_id = None
                    for k in list(st.session_state.keys()):
                        if str(k).startswith("main_cal"):
                            del st.session_state[k]
                    
                    st.success("✅ 保存完了！")
                    st.rerun()
        
        # 削除ボタン
        if e_id:
            if st.button("🗑️ この記録を削除", type="secondary"):
                target = df[(df['id'] == str(e_id)) & (df['player'].astype(str).str.strip() == f_p)]
                if not target.empty:
                    df = df[df['id'] != str(e_id)]
                    if save_data(df):
                        st.session_state.selected_cal_date = None
                        st.session_state.editing_id = None
                        for k in list(st.session_state.keys()):
                            if str(k).startswith("main_cal"):
                                del st.session_state[k]
                        st.success("✅ 削除しました")
                        st.rerun()
    
    # 2. カレンダー / 詳細表示モード
    else:
        # --- TOP SECTION (Metrics & Navigation) ---
        if p_date:
            st.write(f"### 👤 {st.session_state.active_p}")
            c_top = st.container()
        else:
            c_h1, c_h2 = st.columns([1, 1])
            with c_h1:
                p_idx = 0 if st.session_state.active_p == "Player 1" else 1
                st.write("### 👤 プレイヤー選択")
                p_sel = st.radio(
                    "表示プレイヤー",
                    ["Player 1", "Player 2"],
                    horizontal=True,
                    index=p_idx,
                    key="p_main"
                )
                if p_sel != st.session_state.active_p:
                    st.session_state.active_p = p_sel
                    st.session_state.preview_date = None
                    if "records" in st.session_state:
                        del st.session_state["records"]
                    st.rerun()
            c_top = c_h2
        
        # 月次サマリー計算
        v_m = st.session_state.view_month
        v_dt = pd.to_datetime(v_m + "-01")
        df_all = load_data()
        
        if not df_all.empty:
            df_m = df_all.copy()
            df_m['month'] = pd.to_datetime(df_m['date'], errors='coerce').dt.strftime('%Y-%m')
            p_data = df_m[
                (df_m['month'] == v_m) & 
                (df_m['player'].astype(str).str.strip() == st.session_state.active_p)
            ]
            p_bal = int(p_data['balance'].sum())
            p_hours = float(p_data['hours'].sum())
            p_hourly = int(p_bal / p_hours) if p_hours > 0 else 0
        else:
            p_bal, p_hours, p_hourly = 0, 0.0, 0
        
        with c_top:
            m1, m2, m3 = st.columns(3)
            m1.metric(f"💰 {v_dt.strftime('%m月')}収支", f"¥{p_bal:,}")
            m2.metric("⏱️ 稼働時間", f"{p_hours:.1f}h")
            m3.metric("⚡ 平均時給", f"¥{p_hourly:,}")
        
        st.divider()
        
        # Navigation
        nav_c1, nav_c2, nav_c3 = st.columns([1, 6, 1])
        
        with nav_c1:
            if st.button("◀ 前月", use_container_width=True):
                st.session_state.view_month = (v_dt - pd.DateOffset(months=1)).strftime("%Y-%m")
                for k in list(st.session_state.keys()):
                    if str(k).startswith("main_cal"):
                        del st.session_state[k]
                st.rerun()
        
        with nav_c2:
            st.markdown(
                f"<h3 style='text-align: center; color: #00f2ff; margin-top: 0;'>{v_dt.strftime('%Y年%m月')}</h3>",
                unsafe_allow_html=True
            )
        
        with nav_c3:
            if st.button("次月 ▶", use_container_width=True):
                st.session_state.view_month = (v_dt + pd.DateOffset(months=1)).strftime("%Y-%m")
                for k in list(st.session_state.keys()):
                    if str(k).startswith("main_cal"):
                        del st.session_state[k]
                st.rerun()
        
        # --- PREVIEW SECTION ---
        if p_date:
            st.markdown(f"### 🔍 {p_date.replace('-', '/')} の記録詳細")
            
            if not df.empty and 'player' in df.columns:
                day_records = df[
                    (df['date'] == p_date) &
                    (df['player'].astype(str).str.strip() == st.session_state.active_p)
                ]
            else:
                day_records = pd.DataFrame()
            
            if day_records.empty:
                st.info("この日の記録はありません。")
            else:
                for idx, row in day_records.iterrows():
                    with st.container(border=True):
                        c0, c1, c2, c3 = st.columns([3, 3, 3, 3])
                        c0.markdown(f"**🏪 {row['hall']}**")
                        c1.markdown(f"**⏰ {row.get('start_time', '--')} - {row.get('end_time', '--')}**")
                        
                        balance = int(row['balance'])
                        color = "#00ff88" if balance >= 0 else "#ff4466"
                        c2.markdown(f"**💵 <span style='color:{color}'>{balance:+,}円</span>**", unsafe_allow_html=True)
                        
                        btn_col1, btn_col2 = c3.columns(2)
                        if btn_col1.button("✏️ 編集", key=f"edit_{row['id']}", use_container_width=True):
                            st.session_state.editing_id = row['id']
                            st.session_state.selected_cal_date = p_date
                            st.session_state.preview_date = None
                            st.rerun()
                        
                        if btn_col2.button("🗑️", key=f"del_{row['id']}", type="secondary", use_container_width=True):
                            if str(row['player']).strip() == st.session_state.active_p:
                                df = df[df['id'] != row['id']]
                                if save_data(df):
                                    st.success("✅ 削除しました")
                                    st.rerun()
            
            st.write("")
            col_a1, col_a2 = st.columns([4, 1])
            
            with col_a1:
                if st.button("➕ この日に新規記録を追加", use_container_width=True, type="primary"):
                    st.session_state.selected_cal_date = p_date
                    st.session_state.editing_id = None
                    st.session_state.preview_date = None
                    st.rerun()
            
            with col_a2:
                if st.button("✖ 閉じる", use_container_width=True):
                    st.session_state.preview_date = None
                    st.rerun()
            
            st.markdown("---")
        
        # --- CALENDAR ---
        if not CALENDAR_AVAILABLE:
            st.info("📅 カレンダー機能を準備中です。")
            selected_date = st.date_input(
                "日付を選択",
                datetime.now(JST),
                key="tmp_d"
            )
            if st.button("この日の記録を見る"):
                st.session_state.preview_date = selected_date.strftime("%Y-%m-%d")
                st.rerun()
        else:
            events = []
            
            # カスタムCSS
            custom_css = """
            .fc-daygrid-day-number, .fc-toolbar-title { 
                color: #00f2ff !important; 
            }
            .fc-daygrid-day { 
                cursor: pointer; 
            }
            .fc-col-header-cell-cushion { 
                cursor: default; 
            }
            .fc-day-sat .fc-col-header-cell-cushion, 
            .fc-day-sat .fc-daygrid-day-number { 
                color: #4b8bff !important; 
            }
            .fc-day-sun .fc-col-header-cell-cushion, 
            .fc-day-sun .fc-daygrid-day-number { 
                color: #ff4b4b !important; 
            }
            .fc-event { 
                border: none !important; 
                background: transparent !important; 
            }
            .fc-event-main { 
                padding: 0 !important; 
                text-align: center; 
            }
            .fc-event-title { 
                white-space: pre-wrap !important; 
                word-wrap: break-word !important; 
                font-size: clamp(0.6rem, 2.5vw, 0.9rem) !important; 
                line-height: 1.1 !important; 
                letter-spacing: -0.5px !important; 
            }
            .fc-day-today { 
                background: transparent !important; 
            }
            """
            
            # 収支イベント追加
            if not df.empty:
                cal_df = df[df['player'].astype(str).str.strip() == st.session_state.active_p].copy()
                d_bal = cal_df.groupby('date')['balance'].sum().reset_index()
                
                for _, r in d_bal.iterrows():
                    b = int(r['balance'])
                    color = "#00ff88" if b >= 0 else "#ff4466"
                    events.append({
                        "id": f"s_{r['date']}",
                        "title": f"{'+' if b >= 0 else ''}{b:,}円",
                        "start": r['date'],
                        "backgroundColor": "transparent",
                        "borderColor": "transparent",
                        "textColor": color,
                        "extendedProps": {
                            "type": "summary",
                            "date": r['date']
                        }
                    })
            
            # 祝日イベント追加
            try:
                jp_holidays = holidays.Japan(years=range(2024, 2027))
                for holiday_date, holiday_name in jp_holidays.items():
                    date_str = holiday_date.strftime("%Y-%m-%d")
                    events.append({
                        "title": holiday_name,
                        "start": date_str,
                        "display": "background",
                        "backgroundColor": "#ff4b4b1a"
                    })
                    custom_css += f'.fc-day[data-date="{date_str}"] .fc-daygrid-day-number {{ color: #ff4b4b !important; }}\n'
            except Exception:
                pass
            
            # カレンダー表示
            cal_res = calendar(
                events=events,
                options={
                    "headerToolbar": False,
                    "initialDate": f"{st.session_state.view_month}-01",
                    "firstDay": int((v_dt.dayofweek + 1) % 7),
                    "locale": "ja",
                    "height": 700,
                    "selectable": True,
                    "editable": False
                },
                custom_css=custom_css,
                callbacks=['dateClick', 'eventClick', 'select'],
                key=f"main_cal_{st.session_state.view_month}_{st.session_state.active_p}"
            )
            
            # カレンダーイベント処理
            if cal_res and "callback" in cal_res:
                cb = cal_res.get("callback")
                t_d = None
                
                if cb in ["dateClick", "select"]:
                    data = cal_res.get(cb, {})
                    t_d = data.get("dateStr") or data.get("date") or data.get("startStr") or data.get("start")
                elif cb == "eventClick":
                    props = cal_res.get("eventClick", {}).get("event", {}).get("extendedProps", {})
                    if props.get("type") == "summary":
                        t_d = props.get("date")
                
                if t_d:
                    try:
                        dt = pd.to_datetime(t_d)
                        if dt.tzinfo:
                            dt = dt.tz_convert('Asia/Tokyo')
                        clean_date = dt.strftime("%Y-%m-%d")
                    except Exception:
                        clean_date = str(t_d).split("T")[0]
                    
                    st.session_state.preview_date = clean_date
                    st.session_state.selected_cal_date = None
                    st.session_state.editing_id = None
                    st.rerun()

# ============================================================
# 分析 (月別/年別)
# ============================================================
elif menu == "分析 (月別/年別)":
    st.subheader("📊 収支統計")
    
    if df.empty:
        st.warning("⚠️ データがありません。")
    else:
        tab_p1, tab_p2, tab_all = st.tabs(["Player 1", "Player 2", "全員"])
        
        def show_analysis(filter_p):
            """分析画面を表示"""
            if filter_p == "全員":
                df_v = df.copy()
            else:
                df_v = df[df['player'].astype(str).str.strip() == filter_p].copy()
            
            if df_v.empty:
                st.warning("⚠️ データがありません。")
                return
            
            df_v['date_dt'] = pd.to_datetime(df_v['date'], errors='coerce')
            df_v = df_v.dropna(subset=['date_dt'])
            
            min_date = df_v['date_dt'].min().date()
            max_date = df_v['date_dt'].max().date()
            
            # 期間選択
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                start_date = st.date_input(
                    f"{filter_p} - 開始日",
                    min_date,
                    key=f"start_{filter_p}"
                )
            with col_d2:
                end_date = st.date_input(
                    f"{filter_p} - 終了日",
                    max_date,
                    key=f"end_{filter_p}"
                )
            
            # 期間フィルタ
            df_v = df_v[
                (df_v['date_dt'].dt.date >= start_date) &
                (df_v['date_dt'].dt.date <= end_date)
            ]
            
            if df_v.empty:
                st.info("📭 指定された期間のデータはありません。")
                return
            
            # トータルメトリクス
            t_bal = int(df_v['balance'].sum())
            t_hours = float(df_v['hours'].sum())
            h_ly = int(t_bal / t_hours) if t_hours > 0 else 0
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("💰 トータル収支", f"¥{t_bal:,}")
            mc2.metric("⏱️ 合計稼働時間", f"{t_hours:.1f}h")
            mc3.metric("⚡ 平均時給", f"¥{h_ly:,}")
            
            # 直近サマリー
            st.markdown("#### 📈 直近サマリー")
            p_cols = st.columns(4)
            now_dt = pd.Timestamp.now()
            
            if filter_p == "全員":
                df_recent_base = df.copy()
            else:
                df_recent_base = df[df['player'].astype(str).str.strip() == filter_p].copy()
            
            df_recent_base['date_dt'] = pd.to_datetime(df_recent_base['date'], errors='coerce')
            
            for i, months in enumerate([3, 6, 9, 12]):
                start_p = now_dt - pd.DateOffset(months=months)
                label = f"{months}ヶ月" if months < 12 else "1年"
                df_p = df_recent_base[df_recent_base['date_dt'] >= start_p]
                p_bal = int(df_p['balance'].sum())
                p_hours = float(df_p['hours'].sum())
                p_hourly = int(p_bal / p_hours) if p_hours > 0 else 0
                
                with p_cols[i]:
                    st.markdown(f"""
                    <div style="padding:10px; border:1px solid rgba(0,242,255,0.2);
                                border-radius:10px; background:rgba(0,242,255,0.05); text-align:center;">
                        <div style="font-weight:bold; color:#00f2ff; font-size:0.9em;">直近{label}</div>
                        <div style="font-size:1.1em; font-weight:bold; margin:5px 0;">¥{p_bal:,}</div>
                        <div style="font-size:0.8em; opacity:0.8;">{p_hours:.1f}h | ¥{p_hourly:,}/h</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.write("")
            
            # 月別/年別集計
            df_v['year'] = df_v['date_dt'].dt.year
            df_v['month'] = df_v['date_dt'].dt.strftime('%Y/%m')
            
            v_type = st.radio(
                f"{filter_p} - 表示単位",
                ["月別", "年別"],
                horizontal=True,
                key=f"v_type_{filter_p}"
            )
            
            g_col = 'month' if v_type == "月別" else 'year'
            
            import numpy as np
            summ = df_v.groupby(g_col).agg({
                'balance': 'sum',
                'hours': 'sum'
            }).sort_index(ascending=False)
            
            summ['balance'] = summ['balance'].astype(int)
            summ['時給'] = (summ['balance'] / summ['hours'].replace(0, np.nan)).fillna(0).astype(int)
            
            st.dataframe(
                summ.style.format({
                    'balance': '¥{:,}',
                    'hours': '{:.1f}h',
                    '時給': '¥{:,}'
                }),
                use_container_width=True
            )
        
        with tab_p1:
            show_analysis("Player 1")
        with tab_p2:
            show_analysis("Player 2")
        with tab_all:
            show_analysis("全員")

# ============================================================
# 貯玉・貯メダル管理
# ============================================================
elif menu == "貯玉・貯メダル管理":
    st.subheader("🏦 貯玉・貯メダル管理")
    
    p_idx = 0 if st.session_state.active_p == "Player 1" else 1
    p_sel = st.radio(
        "👤 表示プレイヤー",
        ["Player 1", "Player 2"],
        horizontal=True,
        index=p_idx,
        key="p_savings"
    )
    st.session_state.active_p = p_sel
    
    h_list = sorted([h for h in df['hall'].dropna().unique() if h])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 貯玉・貯メダル登録")
        with st.form("savings_form"):
            hall = st.selectbox("🏪 店舗名", h_list)
            s_m = st.number_input("🪙 貯メダル (枚)", min_value=0, step=100)
            s_b = st.number_input("🎱 貯玉 (玉)", min_value=0, step=100)
            
            if st.form_submit_button("💾 更新", use_container_width=True):
                idx_list = df_s[(df_s['player'] == p_sel) & (df_s['hall'] == hall)].index
                
                if not idx_list.empty:
                    df_s.at[idx_list[0], 'saved_medals'] = s_m
                    df_s.at[idx_list[0], 'saved_balls'] = s_b
                    df_s.at[idx_list[0], 'updated_at'] = datetime.now(JST).strftime('%Y-%m-%d %H:%M')
                    st.success("✅ 更新しました")
                else:
                    new_row = {
                        "id": str(int(datetime.now().timestamp())),
                        "player": p_sel,
                        "hall": hall,
                        "saved_medals": s_m,
                        "saved_balls": s_b,
                        "updated_at": datetime.now(JST).strftime('%Y-%m-%d %H:%M')
                    }
                    df_s = pd.concat([df_s, pd.DataFrame([new_row])], ignore_index=True)
                    st.success("✅ 新規登録しました")
                
                save_savings(df_s)
                st.rerun()
    
    with col2:
        st.markdown("### 📊 現在の貯玉・貯メダル一覧")
        p_savings = df_s[df_s['player'] == p_sel]
        
        if p_savings.empty:
            st.info("📭 登録されているデータはありません")
        else:
            st.dataframe(
                p_savings[['hall', 'saved_medals', 'saved_balls', 'updated_at']],
                use_container_width=True,
                hide_index=True
            )

# ============================================================
# 一括インポート
# ============================================================
elif menu == "一括インポート":
    st.subheader("📤 CSVインポート")
    st.info("既存のCSVファイルと同じ形式のレコードを一括で追加します。")
    
    up_file = st.file_uploader("📁 CSVファイルを選択", type="csv")
    
    if up_file:
        try:
            up_df = pd.read_csv(up_file)
            st.write("📋 プレビュー:")
            st.dataframe(up_df.head(), use_container_width=True)
            
            if st.button("📥 インポート実行", type="primary"):
                df = pd.concat([df, up_df], ignore_index=True)
                if save_data(df):
                    st.success("✅ インポート完了！")
                    st.rerun()
        except Exception as e:
            st.error(f"⚠️ ファイル読み込みエラー: {e}")

# ============================================================
# 設定
# ============================================================
elif menu == "設定":
    st.subheader("⚙️ システム設定")
    
    if st.button("🔄 キャッシュをクリア", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success("✅ キャッシュをクリアしました。再読み込みしてください。")
        st.rerun()
    
    st.divider()
    st.write("#### 📥 データの書き出し")
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "💾 records.csv をダウンロード",
            csv,
            "records.csv",
            "text/csv",
            use_container_width=True
        )
    
    if not df_s.empty:
        csv_s = df_s.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "💾 savings.csv をダウンロード",
            csv_s,
            "savings.csv",
            "text/csv",
            use_container_width=True
        )
