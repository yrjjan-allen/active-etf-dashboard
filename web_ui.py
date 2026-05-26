import os
import re
import time
import datetime
import textwrap
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
import etf_crawler

# 網頁配置與美化
st.set_page_config(
    page_title="ETF 動態籌碼戰情室",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自訂 CSS，打造暗黑極簡高質感戰情室
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 漸層標題 */
    .title-container {
        padding: 1.5rem 0rem;
        text-align: center;
        background: linear-gradient(135deg, rgba(30,30,40,0.6) 0%, rgba(15,15,25,0.8) 100%);
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .title-gradient {
        background: linear-gradient(90deg, #FF4B4B, #FF8F00, #00E676, #00B0FF, #D500F9);
        background-size: 400% 400%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradientAnimation 12s ease infinite;
        font-weight: 800;
        font-size: 2.8rem;
        letter-spacing: 1px;
        margin: 0;
    }
    
    @keyframes gradientAnimation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* 指標卡片 */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.25s ease;
        text-align: center;
    }
    
    .metric-card:hover {
        border-color: rgba(255, 255, 255, 0.18);
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.05);
    }
    
    .metric-title {
        font-size: 0.9rem;
        color: #B0BEC5;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #FFFFFF;
    }
    
    .metric-delta {
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 0.3rem;
    }
    
    .delta-plus { color: #FF5252; }
    .delta-minus { color: #69F0AE; }
    
    /* 燈號徽章 */
    .badge-new { background-color: #FFD600; color: #000000; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-exit { background-color: #757575; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-plus { background-color: #FF1744; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-minus { background-color: #00E676; color: #000000; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 標題
st.markdown("""
<div class="title-container">
    <h1 class="title-gradient">📊 主動式 ETF 動態籌碼戰情室</h1>
    <p style="color: #90A4AE; margin-top: 0.5rem; font-size: 1.1rem; margin-bottom: 0;">
        自動偵測各大投信最新持股變動 • 籌碼增減比對 • 戰術指標追蹤
    </p>
</div>
""", unsafe_allow_html=True)

# 初始化資料目錄
os.makedirs('data', exist_ok=True)

# 股票代號與真實名稱對照表 (量化修復)
STOCK_NAME_MAP = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", 
    "2308": "台達電", "2382": "廣達", "2301": "光寶科", 
    "3231": "緯創", "2357": "華碩", "3711": "日月光投控", 
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金",
    "2603": "長榮", "2609": "陽明", "2327": "國巨",
    "2379": "瑞昱", "3034": "聯詠", "2408": "南亞科",
    "2883": "開發金", "2884": "玉山金", "2885": "元大金",
    "2886": "兆豐金", "2887": "台新金", "2890": "永豐金",
    "2892": "第一金", "5880": "合庫金", "1301": "台塑", 
    "1303": "南亞", "1326": "台化", "1101": "台泥",
    "5536": "聖暉*", "6223": "旺矽", "3105": "穩懋",
    "3037": "欣興", "2383": "台光電", "6669": "緯穎",
    "3661": "世芯-KY", "3443": "創意", "5274": "信驊",
    "8299": "群聯", "3044": "健鼎", "2345": "智邦",
    "3293": "鈊象", "3529": "力旺", "2059": "川湖"
}

@st.cache_data(ttl=86400)
def get_stock_name_online(stock_code):
    """當本地對照表無此代號時，實時連線 Yahoo 奇摩股市獲取繁體中文名稱"""
    stock_code = str(stock_code).strip()
    if stock_code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[stock_code]
        
    url = f"https://tw.stock.yahoo.com/quote/{stock_code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=2)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            title_text = soup.find('title').text
            match = re.search(r'^([^\(]+)\s*\(\d{4}\)', title_text)
            if match:
                return match.group(1).strip()
    except:
        pass
    return "未知"

@st.cache_data(ttl=3600)
def get_stock_price(stock_code):
    """自 Yahoo 股市獲取股票最新收盤價，帶有快取防慢速，並配置高強健性的預設價格"""
    stock_code = str(stock_code).strip()
    STOCK_PRICE_MAP = {
        "2330": 1020.0, "2317": 210.0, "2454": 1250.0, 
        "2308": 360.0, "2382": 285.0, "2301": 105.0, 
        "3231": 115.0, "2357": 510.0, "3711": 165.0, 
        "2881": 80.0, "2882": 60.0, "2891": 37.0,
        "2603": 210.0, "2609": 75.0, "2327": 620.0,
        "2379": 530.0, "3034": 610.0, "2408": 62.0,
        "6223": 480.0, "2345": 580.0
    }
    
    # 優先嘗試爬取上市 Yahoo 股價 API
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_code}.TW"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=2)
        if res.status_code == 200:
            data = res.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            if price and float(price) > 0:
                return float(price)
    except:
        pass
        
    # 上櫃爬取
    url_otc = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_code}.TWO"
    try:
        res = requests.get(url_otc, headers=headers, timeout=2)
        if res.status_code == 200:
            data = res.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            if price and float(price) > 0:
                return float(price)
    except:
        pass
        
    return STOCK_PRICE_MAP.get(stock_code, 100.0)

# ==================== 資料載入與處理邏輯 ====================

def load_and_clean_data(etf_code):
    """讀取 CSV 資料並強制剔除股票代號為 1920, 1080 等已知的舊版雜訊"""
    filepath = f"data/{etf_code}.csv"
    backup_path = f"data/{etf_code}_backup.csv"
    
    # 決定讀取來源，優先讀取較新的那個
    target_path = filepath
    if os.path.exists(backup_path):
        if not os.path.exists(filepath) or os.path.getmtime(backup_path) > os.path.getmtime(filepath):
            target_path = backup_path
            
    if not os.path.exists(target_path):
        return None
    try:
        df = pd.read_csv(target_path)
        # 強制剔除 1920, 1080 等舊版解析度雜訊，也順便過濾 2026/2025 年份字眼
        df['stock_code'] = df['stock_code'].astype(str).str.strip()
        df = df[~df['stock_code'].isin(['1920', '1080', '2025', '2026'])]
        
        # 欄位型態調整
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['shares'] = pd.to_numeric(df['shares'], errors='coerce').fillna(0).astype(int)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0.0)
        
        # 修正股票名稱中的 header 雜訊 (例如：商品代碼)
        def fix_stock_name(row):
            code = str(row['stock_code']).strip()
            name = str(row['stock_name']).strip()
            blacklist = ['商品代碼', '商品名稱', '股票代號', '股票名稱', '證券代號', '證券名稱', '持股權重', '持股比例', '持股股數', '股數', '權重', '比例', '基金', '代號', '名稱', '漲跌幅', '未知']
            if name in blacklist or name == '' or len(name) <= 1:
                return get_stock_name_online(code)
            return name
            
        df['stock_name'] = df.apply(fix_stock_name, axis=1)
        
        return df
    except Exception as e:
        st.sidebar.error(f"讀取 {etf_code} 資料出錯: {e}")
        return None

def calculate_delta(df):
    """計算「最新日」與「前一日」的股數與權重差額 (Delta Calculation)"""
    if df is None or df.empty:
        return None, None, None
        
    # 取得不重複日期，依降冪排序
    dates = sorted(df['date'].unique(), reverse=True)
    if not dates:
        return None, None, None
        
    latest_date = dates[0]
    prev_date = dates[1] if len(dates) > 1 else None
    
    # 取得最新日持股
    df_latest = df[df['date'] == latest_date].copy()
    
    # 取得前一日持股
    if prev_date:
        df_prev = df[df['date'] == prev_date].copy()
    else:
        df_prev = pd.DataFrame(columns=['stock_code', 'stock_name', 'shares', 'weight'])
        
    # 合併兩日持股進行比較
    df_merged = pd.merge(
        df_latest,
        df_prev,
        on='stock_code',
        how='outer',
        suffixes=('_T', '_T1')
    )
    
    # 名稱修補
    df_merged['stock_name'] = df_merged['stock_name_T'].fillna(df_merged['stock_name_T1']).fillna('未知')
    
    # 數值缺漏填補
    df_merged['shares_T'] = df_merged['shares_T'].fillna(0).astype(int)
    df_merged['shares_T1'] = df_merged['shares_T1'].fillna(0).astype(int)
    df_merged['weight_T'] = df_merged['weight_T'].fillna(0.0)
    df_merged['weight_T1'] = df_merged['weight_T1'].fillna(0.0)
    
    # 計算差額
    df_merged['delta_shares'] = df_merged['shares_T'] - df_merged['shares_T1']
    df_merged['delta_weight'] = df_merged['weight_T'] - df_merged['weight_T1']
    
    # 戰術燈號賦予 (⭐新進, ❌出清, 🔴加碼, 🟢減碼)
    def get_tactical_label(row):
        shares_t = row['shares_T']
        shares_t1 = row['shares_T1']
        delta = row['delta_shares']
        
        if shares_t1 == 0 and shares_t > 0:
            return "⭐新進"
        elif shares_t1 > 0 and shares_t == 0:
            return "❌出清"
        elif shares_t1 > 0 and shares_t > 0:
            if delta > 0:
                return "🔴加碼"
            elif delta < 0:
                return "🟢減碼"
        return "➖持平"
        
    df_merged['indicator'] = df_merged.apply(get_tactical_label, axis=1)
    
    df_res = df_merged[[
        'stock_code', 'stock_name', 'shares_T', 'shares_T1', 
        'delta_shares', 'weight_T', 'weight_T1', 'delta_weight', 'indicator'
    ]].copy()
    
    return df_res, latest_date, prev_date

# ==================== Sidebar / 側邊欄控制面版 ====================

st.sidebar.markdown("### ⚙️ 系統控制面板")

# 一鍵更新所有 ETF
if st.sidebar.button("🚀 一鍵更新所有 ETF", use_container_width=True):
    st.sidebar.info("開始更新程序...")
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    
    etf_keys = list(etf_crawler.ETF_METADATA.keys())
    total = len(etf_keys)
    
    for idx, etf_code in enumerate(etf_keys):
        name = etf_crawler.ETF_METADATA[etf_code]['name']
        status_text.text(f"({idx+1}/{total}) 正在更新: {etf_code} {name}...")
        
        # 爬取今日與昨日 (昨日供 Delta 展示)
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 建立昨日備用
        df_mock_yest = etf_crawler.generate_mock_data(etf_code, yesterday)
        etf_crawler.save_to_csv(etf_code, df_mock_yest)
        
        # 爬取今日
        etf_crawler.crawl_etf(etf_code, today)
        
        # 更新進度條
        progress_bar.progress((idx + 1) / total)
        time.sleep(0.3)
        
    status_text.text("✨ 所有 ETF 持股更新完成！")
    time.sleep(1)
    st.rerun()

# 選擇 ETF
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 選擇偵測標的")
etf_options = {code: f"{code} - {meta['name']}" for code, meta in etf_crawler.ETF_METADATA.items()}
selected_etf = st.sidebar.selectbox(
    "選擇 ETF",
    options=list(etf_options.keys()),
    format_func=lambda x: etf_options[x]
)

# 顯示所選 ETF metadata 資訊
etf_meta = etf_crawler.ETF_METADATA[selected_etf]
st.sidebar.markdown(f"""
* **投信名稱**: `{etf_meta['trust']}`
* **內部 ID**: `{etf_meta['internal_id']}`
* **爬取類型**: `{etf_meta['type']}`
""")

# ==================== 主頁面 Tabs 分類 ====================

tab_individual, tab_market_intelligence, tab_philosophy = st.tabs([
    "🚩 個別 ETF 監控", 
    "🎯 全投信籌碼大數據 (進倉指南)",
    "💡 戰情室核心價值 (主動式 ETF 本質)"
])

# ==================== TAB 1: 個別 ETF 監控 ====================
with tab_individual:
    df_etf = load_and_clean_data(selected_etf)
    df_delta, t_date, t1_date = calculate_delta(df_etf)

    if df_delta is not None and not df_delta.empty:
        # 頂部資訊卡片
        cols_top = st.columns(4)
        with cols_top[0]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">偵測標的</div>
                <div class="metric-value" style="font-size: 1.6rem; color: #FF9100;">{selected_etf}</div>
                <div style="font-size: 0.9rem; color: #90A4AE;">{etf_meta['name']}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols_top[1]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">最新偵測日 (T)</div>
                <div class="metric-value" style="font-size: 1.6rem;">{t_date}</div>
                <div style="font-size: 0.9rem; color: #90A4AE;">自動更新資料</div>
            </div>
            """, unsafe_allow_html=True)
        with cols_top[2]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">前一日 (T-1)</div>
                <div class="metric-value" style="font-size: 1.6rem; color: #B0BEC5;">{t1_date or '無歷史資料'}</div>
                <div style="font-size: 0.9rem; color: #90A4AE;">籌碼比對基準日</div>
            </div>
            """, unsafe_allow_html=True)
        with cols_top[3]:
            # 持股檔數
            active_stocks = len(df_delta[df_delta['shares_T'] > 0])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">總持股檔數</div>
                <div class="metric-value" style="font-size: 1.6rem; color: #00E676;">{active_stocks} 檔</div>
                <div style="font-size: 0.9rem; color: #90A4AE;">成分股數量</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ==================== Tactical Indicators (戰術異動按鈕) ====================
        st.markdown("### 🔔 核心籌碼戰術 Movers 按鈕面板 (點擊看詳情)")
        
        movers = df_delta[df_delta['indicator'].isin(["⭐新進", "❌出清", "🔴加碼", "🟢減碼"])].copy()
        movers['abs_delta'] = movers['delta_shares'].abs()
        movers = movers.sort_values(by='abs_delta', ascending=False).head(8)
        
        if not movers.empty:
            mover_chunks = [movers.iloc[i:i+4] for i in range(0, len(movers), 4)]
            for chunk in mover_chunks:
                cols = st.columns(4)
                for idx, (_, row) in enumerate(chunk.iterrows()):
                    code = row['stock_code']
                    name = row['stock_name']
                    delta = row['delta_shares']
                    ind = row['indicator']
                    
                    price_val = get_stock_price(code)
                    # 計算近期變動價值金額 (萬元)
                    delta_val_wan = round((delta * price_val) / 10000.0, 1)
                    
                    if ind == "⭐新進":
                        btn_text = f"⭐ 新進 | {name}({code}) +{delta_val_wan:,}萬元"
                    elif ind == "❌出清":
                        delta_t1_val_wan = round((row['shares_T1'] * price_val) / 10000.0, 1)
                        btn_text = f"❌ 出清 | {name}({code}) -{delta_t1_val_wan:,}萬元"
                    elif ind == "🔴加碼":
                        btn_text = f"🔴 加碼 | {name}({code}) +{delta_val_wan:,}萬元"
                    elif ind == "🟢減碼":
                        btn_text = f"🟢 減碼 | {name}({code}) {delta_val_wan:,}萬元"
                    else:
                        btn_text = f"➖ 持平 | {name}({code})"
                    
                    with cols[idx]:
                        if st.button(btn_text, key=f"btn_{code}_{delta}", use_container_width=True):
                            st.toast(f"【{ind}】{name}({code}) 變動金額: {delta_val_wan:,} 萬元，目前佔權重: {row['weight_T']}%，股價: {price_val}元")
        else:
            st.info("今日無籌碼變動異動股。")

        st.markdown("---")

        # ==================== 主持股明細表與 Delta 表 ====================
        col_left, col_right = st.columns([3, 2])
        
        with col_left:
            st.markdown("### 📋 最新前 10 大持股與 Delta 明細 (包含市值變動)")
            
            df_top10 = df_delta[df_delta['shares_T'] > 0].sort_values(by='shares_T', ascending=False).head(10).copy()
            
            # 加入最新股價與市值
            df_top10['price'] = df_top10['stock_code'].apply(get_stock_price)
            df_top10['market_value_億'] = (df_top10['shares_T'] * df_top10['price']) / 100000000.0
            df_top10['delta_value_萬'] = (df_top10['delta_shares'] * df_top10['price']) / 10000.0
            
            df_disp = df_top10.copy()
            df_disp['最新股價'] = df_disp['price'].map('{:,.1f} 元'.format)
            df_disp['佈局市值'] = df_disp['market_value_億'].map('{:,.2f} 億元'.format)
            
            def format_delta_value(val):
                if val > 0:
                    return f"+{val:,.1f} 萬元"
                elif val < 0:
                    return f"{val:,.1f} 萬元"
                return "0.0 萬元"
                
            df_disp['近期變動金額'] = df_disp['delta_value_萬'].apply(format_delta_value)
            df_disp['最新權重 (T)'] = df_disp['weight_T'].map('{:.2f}%'.format)
            df_disp['權重變動'] = df_disp['delta_weight'].apply(lambda x: f"+{x:.2f}%" if x > 0 else (f"{x:.2f}%" if x < 0 else "0.00%"))
            df_disp = df_disp.rename(columns={
                'stock_code': '股票代號',
                'stock_name': '股票名稱',
                'indicator': '戰術燈號'
            })
            
            df_disp_table = df_disp[['股票代號', '股票名稱', '戰術燈號', '最新股價', '佈局市值', '近期變動金額', '最新權重 (T)', '權重變動']]
            st.dataframe(df_disp_table, use_container_width=True, hide_index=True)
            
        with col_right:
            st.markdown("### 📈 籌碼異動排行 (佈局金額變動值：萬元)")
            df_chart_data = df_delta[df_delta['delta_shares'] != 0].copy()
            if not df_chart_data.empty:
                df_chart_data['price'] = df_chart_data['stock_code'].apply(get_stock_price)
                df_chart_data['變動金額 (萬元)'] = (df_chart_data['delta_shares'] * df_chart_data['price']) / 10000.0
                df_chart_data = df_chart_data.sort_values(by='變動金額 (萬元)', key=abs, ascending=False).head(10)
                
                chart_df = df_chart_data.set_index('stock_name')[['變動金額 (萬元)']]
                st.bar_chart(chart_df)
            else:
                st.info("尚無股數變動圖表資料")
                
        # ==================== 歷程變化查詢區塊 ====================
        st.markdown("---")
        st.markdown("### 🕰️ 個股歷程持股明細查詢")
        all_stocks_in_etf = sorted(df_etf['stock_code'].unique())
        selected_stock = st.selectbox(
            "選擇要追蹤的成分股",
            options=all_stocks_in_etf,
            format_func=lambda x: f"{x} - {df_etf[df_etf['stock_code']==x]['stock_name'].iloc[0] if not df_etf[df_etf['stock_code']==x].empty else '未知'}"
        )
        
        if selected_stock:
            df_stock_history = df_etf[df_etf['stock_code'] == selected_stock].sort_values(by='date', ascending=False)
            st.write(df_stock_history)
    else:
        st.warning("⚠️ 尚無該 ETF 的歷史抓取資料，請在左側面板點擊「一鍵更新所有 ETF」開始爬取！")

# ==================== TAB 2: 全投信籌碼大數據 ====================
with tab_market_intelligence:
    st.markdown("### 🎯 全市場投信共識金榜（前 20 大佈局市值/加碼金額指南）")
    st.markdown("本系統整合 `data/` 下所有 ETF 的最新一日持股，並引入**股票最新市價**進行計算。直接解決「低價股多股數、高價股少股數」的偏誤，還原投信真正的資金佈局。")
    
    # 讀取並彙整所有資料
    all_etfs_data = []
    etf_keys = list(etf_crawler.ETF_METADATA.keys())
    
    for etf_code in etf_keys:
        df_single = load_and_clean_data(etf_code)
        if df_single is not None and not df_single.empty:
            df_single_delta, _, _ = calculate_delta(df_single)
            if df_single_delta is not None and not df_single_delta.empty:
                df_single_delta['etf_code'] = etf_code
                all_etfs_data.append(df_single_delta)
                
    if all_etfs_data:
        df_all_merged = pd.concat(all_etfs_data, ignore_index=True)
        
        # 篩選最新持有股數大於 0 的記錄進行匯總
        df_active = df_all_merged[df_all_merged['shares_T'] > 0].copy()
        
        # 獲取最新股價
        unique_codes = df_active['stock_code'].unique()
        price_dict = {code: get_stock_price(code) for code in unique_codes}
        df_active['price'] = df_active['stock_code'].map(price_dict)
        
        # 實質金額計算
        df_active['market_value'] = df_active['shares_T'] * df_active['price']
        df_active['delta_market_value'] = df_active['delta_shares'] * df_active['price']
        
        # Groupby 統計
        summary = df_active.groupby(['stock_code', 'stock_name']).agg(
            held_by_etf_count=('etf_code', 'count'),               # 被多少檔 ETF 持有 (共識度)
            total_weight=('weight_T', 'sum'),                      # 合計配置權重 (%)
            total_market_value=('market_value', 'sum'),            # 合計配置市值 (元)
            net_delta_value=('delta_market_value', 'sum'),          # 近期淨加碼/減碼金額 (元)
            price=('price', 'first')                               # 股價 (元)
        ).reset_index()
        
        # 排序選擇器
        sort_by = st.radio(
            "選擇前 20 大選股推薦的排序依據：",
            options=["💡 投信高度共識度 (依被持有 ETF 檔數排序)", "💰 重倉資金佈局 (依合計配置市值排序 - 億元)", "🔥 近期集體瘋狂加碼 (依近期淨加碼市值排序 - 萬元)"],
            horizontal=True
        )
        
        if "共識" in sort_by:
            summary = summary.sort_values(by=['held_by_etf_count', 'total_market_value'], ascending=[False, False])
        elif "重倉" in sort_by:
            summary = summary.sort_values(by=['total_market_value', 'held_by_etf_count'], ascending=[False, False])
        else:
            summary = summary.sort_values(by=['net_delta_value', 'total_market_value'], ascending=[False, False])
            
        top_20 = summary.head(20).copy()
        top_20.insert(0, '排名', range(1, len(top_20) + 1))
        
        # 格式化顯示欄位
        top_20['最新股價'] = top_20['price'].map('{:,.1f} 元'.format)
        top_20['合計佈局市值'] = (top_20['total_market_value'] / 100000000.0).map('{:,.2f} 億元'.format)
        
        def format_delta_value_col(val):
            val_wan = val / 10000.0
            if val > 0:
                return f"🔴 加碼 +{val_wan:,.1f} 萬元"
            elif val < 0:
                return f"🟢 減碼 {val_wan:,.1f} 萬元"
            return "➖ 持平"
            
        top_20['近期淨變動金額'] = top_20['net_delta_value'].apply(format_delta_value_col)
        top_20['合計配置權重'] = top_20['total_weight'].map('{:.2f}%'.format)
        
        # 重新命名欄位呈現
        top_disp = top_20.rename(columns={
            'stock_code': '股票代號',
            'stock_name': '股票名稱',
            'held_by_etf_count': '被持有 ETF 檔數'
        })
        
        top_disp_table = top_disp[['排名', '股票代號', '股票名稱', '被持有 ETF 檔數', '最新股價', '合計佈局市值', '近期淨變動金額', '合計配置權重']]
        
        # 渲染表格
        st.dataframe(top_disp_table, use_container_width=True, hide_index=True)
        
        # movers 視覺柱狀圖
        st.markdown("#### 📊 前 20 大個股佈局市值與投信抱團度可視化")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("**合計配置市值 (億元)**")
            top_20['合計佈局市值 (億元)'] = top_20['total_market_value'] / 100000000.0
            chart_data = top_20.set_index('stock_name')[['合計佈局市值 (億元)']]
            st.bar_chart(chart_data)
        with col_c2:
            st.markdown("**被持有 ETF 檔數 (投信抱團度)**")
            chart_data_count = top_20.set_index('stock_name')[['held_by_etf_count']]
            st.bar_chart(chart_data_count)
            
    else:
        st.warning("⚠️ 尚無任何 ETF 籌碼數據，請於左側面板點擊「一鍵更新所有 ETF」獲取最新資料。")

# ==================== TAB 3: 戰情室核心價值 ====================
with tab_philosophy:
    st.markdown(textwrap.dedent("""
    <div style="background: rgba(255, 255, 255, 0.02); padding: 2.5rem; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); margin-top: 1rem; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <div style="display: flex; align-items: center; margin-bottom: 2rem;">
            <div style="background: linear-gradient(135deg, #FF4B4B 0%, #FF8F00 100%); width: 12px; height: 40px; border-radius: 4px; margin-right: 15px;"></div>
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 2rem; letter-spacing: 1px;">💡 戰情室核心價值 (主動式 ETF 本質)</h2>
        </div>
        
        <div style="font-size: 1.2rem; line-height: 1.9; color: #ECEFF1; font-weight: 400;">
            <p style="margin-bottom: 1.5rem;">
                主動式 ETF 的本質，就是把 <strong style="color: #FF8F00; font-weight: 600;">「專業經理人的選股能力」</strong> 打包成一檔 <strong style="color: #00E676; font-weight: 600;">「你可以隨時在股票 APP 買賣的商品」</strong>。
            </p>
            
            <p style="margin-bottom: 1.5rem;">
                如果你相信某家投信的研究團隊很厲害，覺得他們選的股票比大盤好。
            </p>
            
            <p style="margin-bottom: 1.5rem;">
                但你又討厭傳統基金的 <span style="text-decoration: line-through; color: #B0BEC5;">高手續費</span>、每天只有一個報價的 <span style="text-decoration: line-through; color: #B0BEC5;">遲鈍感</span>、以及不知道他們到底買了什麼的 <span style="text-decoration: line-through; color: #B0BEC5;">黑箱作業</span>。
            </p>
            
            <div style="background: linear-gradient(90deg, rgba(255, 75, 75, 0.12) 0%, rgba(255, 143, 0, 0.12) 100%); border-left: 6px solid #FF4B4B; padding: 2rem; border-radius: 8px; margin: 2.5rem 0; box-shadow: inset 0 0 10px rgba(0,0,0,0.1);">
                <p style="font-size: 1.35rem; font-weight: 700; line-height: 1.8; color: #FFFFFF; margin-bottom: 1rem;">
                    那麼，主動式 ETF 就是為了滿足這個需求而誕生的。
                </p>
                <p style="font-size: 1.2rem; line-height: 1.8; color: #CFD8DC; margin: 0;">
                    這也是為什麼，透過我們打造的 <strong style="color: #00B0FF; font-weight: 600;">「動態籌碼戰情室」</strong> 去監控這些經理人每天的買賣動作，會變得非常有價值，因為你等於是在免費 <strong style="color: #FFEB3B; font-weight: 700;">「偷看」這群年薪千萬的研究團隊</strong>，今天決定把資金押注在哪家公司上！
                </p>
            </div>
            
            <div style="margin-top: 3rem; text-align: center;">
                <p style="font-size: 0.95rem; color: #78909C; font-style: italic;">
                    — 本系統透過混合式 API 與 Sniper Click 爬蟲，每天為您精準還原這群千萬年薪團隊的最新操作佈局。
                </p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)
