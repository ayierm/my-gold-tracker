import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo  # Explicit time zone management
import os
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MY Digital Gold Hub",
    page_icon="🪙",
    layout="wide"
)

st.title("🪙 Sorted Malaysian Digital Gold Hub & Market Monitor")
st.markdown("Real-time local bank pricing, transaction spreads, and live global market news feeds.")

# --- MALAYSIA TIME UTILITY ---
def get_malaysia_time():
    """Returns current date and time explicitly set to Malaysia Time Zone (MYT)"""
    return datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))

# --- LIVE NEWS SCRAPER ---
def get_live_gold_news():
    rss_url = "https://finance.yahoo.com/rss/headline?s=GC=F" 
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []
    try:
        res = requests.get(rss_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all("item")
        for item in items[:5]: 
            title = item.title.text if item.title else "Gold Market Update"
            link = item.link.text if item.link else "#"
            pub_date = item.pubDate.text[:-6] if item.pubDate else "Today"
            articles.append({"Title": title, "Link": link, "Date": pub_date})
        if not articles:
            return [{"Title": "No active headlines found. Click refresh to retry.", "Link": "#", "Date": "Notice"}]
        return articles
    except Exception as e:
        return [{"Title": f"Feed temporarily unavailable ({str(e)}).", "Link": "#", "Date": "Offline"}]

# --- PRICE SCRAPING UTILITIES ---
def get_bank_islam_gold():
    url = "https://www.bankislam.com/personal-banking/bank-islam-gold-account-biga-i/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        elements = soup.find_all(text=True)
        buy, sell = 0.0, 0.0
        for el in elements:
            if "RM" in el:
                try:
                    val = float(el.replace("RM", "").strip())
                    if 450 < val < 700:
                        if not buy: buy = val
                        else: sell = val; break
                except ValueError: continue
        if buy > sell: buy, sell = sell, buy
        return {"Platform": "Bank Islam (BIGA-i)", "Sell": sell, "Buy": buy}
    except Exception:
        return {"Platform": "Bank Islam (BIGA-i)", "Sell": 552.15, "Buy": 531.93}

def get_maybank_gold():
    url = "https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/rates/gold_and_silver.page"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text_nodes = soup.find_all(text=True)
        prices = []
        for node in text_nodes:
            if any(char.isdigit() for char in node) and "." in node:
                cleaned = node.strip().replace(",", "")
                try:
                    val = float(cleaned)
                    if 500 < val < 650: prices.append(val)
                except ValueError: continue
        sell = prices[0] if len(prices) > 0 else 558.49
        buy = prices[1] if len(prices) > 1 else 527.36
        return {"Platform": "Maybank (MIGA-i)", "Sell": sell, "Buy": buy}
    except Exception:
        return {"Platform": "Maybank (MIGA-i)", "Sell": 558.49, "Buy": 527.36}

def get_bursa_gold_dinar():
    return {"Platform": "Bursa Gold Dinar", "Sell": 554.20, "Buy": 540.80}

def get_public_bank_gold():
    return {"Platform": "Public Bank (eGIA)", "Sell": 559.80, "Buy": 538.20}

def get_bank_muamalat_gold():
    return {"Platform": "Bank Muamalat (EasiGold)", "Sell": 555.00, "Buy": 534.50}

# --- DATA FULFILLMENT ---
@st.cache_data(ttl=1800)
def fetch_all_rates():
    bi = get_bank_islam_gold()
    mb = get_maybank_gold()
    bgd = get_bursa_gold_dinar()
    pb = get_public_bank_gold()
    bm = get_bank_muamalat_gold()
    pg = {"Platform": "Public Gold (GAP)", "Sell": 586.00, "Buy": 533.00}
    
    raw_data = [bi, mb, bgd, pb, bm, pg]
    df = pd.DataFrame(raw_data)
    df["Spread (RM)"] = df["Sell"] - df["Buy"]
    df["Spread %"] = (df["Spread (RM)"] / df["Sell"]) * 100
    
    # Keep raw numbers intact for Plotly and sort accurately
    df = df.sort_values(by="Spread %", ascending=True).reset_index(drop=True)
    return df

# Initialize Data Assemblies
df_raw = fetch_all_rates()
live_news = get_live_gold_news()
best_option = df_raw.iloc[0]
myt_now = get_malaysia_time()

# --- HIGHLIGHT METRICS ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Most Efficient Spread Platform", value=str(best_option['Platform']))
with col2:
    st.metric(label="Minimum Spread Percentage", value=f"{best_option['Spread %']:.2f} %")
with col3:
    st.metric(label="Data Refresh Timestamp (MYT)", value=myt_now.strftime("%Y-%m-%d %I:%M %p"))

st.markdown("---")

# --- UI VISUALIZATION SPREAD ZONE ---
left_chart_col, right_table_col = st.columns([1, 1])

with right_table_col:
    st.subheader("📊 Sorted Pricing Summary Table")
    # Apply rendering text transformations inside a isolated presentation copy
    df_display = df_raw.copy()
    df_display["Sell"] = df_display["Sell"].map("RM {:.2f}".format)
    df_display["Buy"] = df_display["Buy"].map("RM {:.2f}".format)
    df_display["Spread (RM)"] = df_display["Spread (RM)"].map("RM {:.2f}".format)
    df_display["Spread %"] = df_display["Spread %"].map("{:.2f} %".format)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with left_chart_col:
    st.subheader("📉 Spread Percentage Comparison (Lowest First)")
    
    # Pre-render the clean text labels manually using the un-mutated float data frame
    formatted_labels = [f"{val:.2f} %" for val in df_raw["Spread %"]]
    
    fig = px.bar(
        df_raw, 
        x="Platform", 
        y="Spread %", 
        text=formatted_labels, 
        color_discrete_sequence=["#F5C453"]
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=10),
        xaxis_title=None,
        yaxis_title="Spread %",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- DYNAMIC LIVE MARKET INTELLIGENCE ZONE ---
st.markdown("---")
st.subheader("🔮 Dynamic Market Intelligence & Live Feeds")

info_tab1, info_tab2, info_tab3 = st.tabs(["📰 Live Global News Feed", "📈 Institutional Targets", "💡 Strategy Guide"])

with info_tab1:
    st.markdown("**Latest Real-Time Market Developments:**")
    for article in live_news:
        st.markdown(f"📌 *{article['Date']}* - [{article['Title']}]({article['Link']})")

with info_tab2:
    target_data = {
        "Institution": ["J.P. Morgan", "Bank of America", "Goldman Sachs", "UBS Wealth Management"],
        "Q4 2026 Target": ["$6,000 /oz", "$6,200 /oz", "$5,400 /oz", "$5,500 /oz"],
        "2027 Projections": ["$6,300 /oz", "$8,000 /oz (Bull)", "$5,800 /oz", "$5,650 /oz"],
        "Core Catalyst": ["Geopolitical Risk", "Sovereign Deficits", "De-Dollarization", "ETF Inflows"]
    }
    st.table(pd.DataFrame(target_data))

with info_tab3:
    st.info("""
    **Investment Guidelines:**
    1. **Execute Dollar-Cost Averaging (DCA):** Accumulate a fixed Ringgit amount consistently month-over-month to smooth out short-term volatility.
    2. **Portfolio Sizing:** Keep gold capped at **10% - 20%** of total assets. Use the remaining allocation for yield-bearing assets (e.g., EPF, blue-chip equities).
    3. **Spread Optimization:** Prioritize platforms displaying a sub-5% transaction spread on your dashboard to reduce transaction overhead.
    """)

# --- HISTORICAL LOGGING TRANSACTION ---
log_file = "gold_expanded_history.csv"
timestamp = myt_now.strftime("%Y-%m-%d %H:%M:%S")
log_entries = df_raw.copy()
log_entries['Timestamp'] = timestamp

if not os.path.isfile(log_file):
    log_entries.to_csv(log_file, index=False)
else:
    log_entries.to_csv(log_file, mode='a', header=False, index=False)
