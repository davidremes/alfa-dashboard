import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import numpy as np
import plotly.express as px
import warnings 
# Potlačení FutureWarnings (které často generuje yfinance)
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. KOSMETIKA & CSS (Styling pro čistě černý motiv - MAXIMÁLNÍ VYNUCENÍ) ---
st.markdown("""
<style>
    /* Hlavní pozadí aplikace - ČISTĚ ČERNÁ (Vynucení, i když to má řešit config.toml) */
    .stApp {
        background-color: #000000 !important;
        color: #fafafa !important;
    }
    
    /* Všechny kontejnery uvnitř app (např. st.container, st.columns) */
    [data-testid="stVerticalBlock"] {
        background-color: #000000 !important;
    }

    /* Původní jednoduché boxy (Karty s metrikami) */
    .custom-card {
        background-color: #1a1a1a !important; /* Tmavě šedá pro karty */
        border: 1px solid #2a2a2a !important; 
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important; 
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2); 
        height: 100%;
        min-height: 120px !important; /* Vynucení minimální výšky pro symetrii */
        color: #fafafa;
    }
    
    /* Speciální styl pro hlavní box (Portfolio Value) - NYNÍ MODRÉ POZADÍ */
    .main-card {
        background-color: #1f77b4 !important; /* Modrá barva pozadí */
        border: 1px solid #1f77b4 !important; /* Modrý border pro odlišení */
        color: #fafafa !important;
        height: 100%;
        min-height: 120px !important; /* Vynucení minimální výšky pro symetrii */
        padding: 15px !important;
        font-size: 20px;
        font-weight: bold;
    }
    
    /* Zajištění kontrastu textu */
    h1, h2, h3, h4, h5, h6, label, div, p, span {
        color: #fafafa !important;
    }
    .value-positive { color: #00ff00 !important; }
    .value-negative { color: #ff0000 !important; }
    /* Neutrální hodnota v hlavním modrém boxu musí být bílá */
    .main-card .main-card-value {
        color: #fafafa !important;
    }
    .value-neutral { color: #fafafa !important; }
    
    /* Tlačítka */
    .stButton > button {
        background-color: #1f77b4 !important;
        color: #fafafa !important;
        border-radius: 5px !important;
        border: 1px solid #1f77b4 !important;
    }


    /* ====================================================== */
    /* === 🎯 CÍLENÁ OPRAVA BÍLÉHO POZADÍ (Tabulky, Inputy, File Uploader) === */
    /* ====================================================== */

    /* 1. Tabulky a Data Editor - Vynucení černé/tmavě šedé barvy pozadí */
    div[data-testid="stDataFrame"], 
    div[data-testid="stTable"], 
    div[data-testid="stDataEditor"] {
        background-color: #000000 !important; /* Čistě černá */
        border: 1px solid #2a2a2a !important;
    }
    /* Všechny vnitřní buňky v datovém editoru (kde se zadávají ceny) */
    .stDataEditor [data-baseweb="table-cell"] {
        background-color: #000000 !important; 
        color: #fafafa !important;
        border-bottom: 1px solid #2a2a2a !important;
    }
    /* Hlavičky tabulek */
    div[data-testid="stDataFrame"] .header,
    div[data-testid="stDataEditor"] .header {
        background-color: #1a1a1a !important; 
        color: #fafafa !important;
    }
    /* Střídání řádků pro čitelnost na černém pozadí */
    div[data-testid="stDataFrame"] .row-odd,
    div[data-testid="stDataEditor"] .row-odd {
        background-color: #0a0a0a !important;
    }
    div[data-testid="stDataFrame"] .row-even,
    div[data-testid="stDataEditor"] .row-even {
        background-color: #000000 !important;
    }

    /* 2. Vstupní pole (Text Input, Slidery, Selectboxy) */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div>div>input,
    .stSlider [data-baseweb="slider"] {
        background-color: #000000 !important; 
        color: #fafafa !important;
        border: 1px solid #2a2a2a !important; 
        border-radius: 5px !important;
    }
    
    /* 3. Nahrávač souborů (st.file_uploader) - TMAVĚ ŠEDÝ (dle požadavku) */
    /* Vnější kontejner */
    div[data-testid="stFileUploader"] {
        background-color: #1a1a1a !important; /* Tmavě šedá */
        border-radius: 10px !important; /* Zaoblené rohy */
        padding: 10px; /* Vnitřní odsazení */
        margin-bottom: 10px;
    }
    /* Oblast pro drag and drop (ta, která byla bílá) */
    .stFileUploader section,
    .stFileUploader section > div,
    .stFileUploader [data-testid="stFileUploadDropzone"] {
        background-color: #1a1a1a !important; /* Tmavě šedá */
        border: 2px dashed #444444 !important; /* Světlejší tečkovaná čára */
        color: #fafafa !important;
        border-radius: 8px !important; /* Mírně zaoblené rohy vnitřní zóny */
    }
    /* Text uvnitř drag and drop oblasti */
    .stFileUploader label span {
        color: #fafafa !important; 
    }
    /* Konkrétní box s textem "Drop file here" */
    [data-testid="stFileUploadDropzone"] > div {
        background-color: #1a1a1a !important; /* Tmavě šedá */
    }

    /* 4. Oprava informačních/statusových boxů (st.info, st.success, st.warning) */
    div[data-testid*="stAlert"] {
        background-color: #1a1a1a !important; /* Tmavě šedá pro info box */
        color: #fafafa !important;
    }
    /* Vynucení barvy textu v Info boxech */
    div[data-testid*="stAlert"] p {
        color: #fafafa !important;
    }
    /* Konkrétní barvy pro Info/Success/Warning proužky */
    div[data-testid="stAlert-info"] {
        border-left: 5px solid #1f77b4 !important; /* Modrý proužek */
    }
    div[data-testid="stAlert-success"] {
        border-left: 5px solid #00ff00 !important; /* Zelený proužek */
    }
    div[data-testid="stAlert-warning"] {
        border-left: 5px solid #ffcc00 !important; /* Žlutý proužek */
    }
</style>
""", unsafe_allow_html=True)


# --- 2. FUNKCE PRO ZÍSKÁNÍ DAT (PŮVODNÍ, FUNKČNÍ LOGIKA) ---

# Funkce pro mapování XTB symbolů na yfinance tickery a měny
def get_ticker_and_currency(symbol):
    symbol_upper = symbol.upper()
    
    if symbol_upper == 'CSPX.UK' or symbol_upper == 'CSPX':
        return 'CSPX.L', 'USD' 
    if symbol_upper == 'CNDX.UK' or symbol_upper == 'CNDX':
        return 'CNDX.L', 'USD' 
    if 'TUI' in symbol_upper and symbol_upper.endswith('.DE'):
        return 'TUI1.DE', 'EUR'
    elif symbol_upper.endswith('.US'):
        return symbol_upper[:-3], 'USD'
    elif symbol_upper.endswith('.DE'):
        return symbol_upper[:-3] + '.DE', 'EUR'
    elif symbol_upper.endswith('.IT'):
        return symbol_upper[:-3] + '.MI', 'EUR'
    elif symbol_upper.endswith('.UK'):
        return symbol_upper[:-3] + '.L', 'GBP' 
    return symbol, 'USD'

# Funkce pro stažení aktuálních cen (batch processing + Caching)
@st.cache_data(ttl=600)
def get_current_prices(symbols):
    if not symbols:
        return {}
    ticker_map = {symbol: get_ticker_and_currency(symbol) for symbol in symbols}
    yf_tickers = [v[0] for v in ticker_map.values()]
    currencies_to_fetch = set(v[1] for v in ticker_map.values() if v[1] != 'USD')
    currency_rates = {'USD': 1.0}
    currency_tickers = [f"{curr}USD=X" for curr in currencies_to_fetch]
    
    # Původní, méně agresivní ošetření chyb pro aktuální ceny
    if currency_tickers:
        try:
            rates_data = yf.download(currency_tickers, period='1d', progress=False)['Close']
            if isinstance(rates_data, pd.Series):
                currency = currency_tickers[0].split('USD=X')[0]
                currency_rates[currency] = rates_data.iloc[-1]
            else:
                for curr_ticker in currency_tickers:
                    currency = curr_ticker.split('USD=X')[0]
                    rate = rates_data[curr_ticker].iloc[-1] if not rates_data[curr_ticker].empty else 1.0
                    currency_rates[currency] = rate
        except:
            st.warning("Problém se stažením kurzu, používám výchozí 1.0.")
            pass 
            
    prices = {}
    
    try:
        data = yf.download(yf_tickers, period='1d', progress=False)['Close']
        if isinstance(data, pd.Series): 
            ticker = yf_tickers[0]
            price = data.iloc[-1]
            for symbol, (t, curr) in ticker_map.items():
                if t == ticker:
                    prices[symbol] = price * currency_rates.get(curr, 1.0)
                    break
        else: 
            for symbol, (ticker, currency) in ticker_map.items():
                try:
                    price = data[ticker].iloc[-1]
                    prices[symbol] = price * currency_rates.get(currency, 1.0)
                except (KeyError, IndexError):
                    prices[symbol] = 0
    except:
        st.error("Nepodařilo se stáhnout ceny pro jeden nebo více symbolů (pravděpodobně chyba Yahoo Finance). Používám 0 pro chybějící data.")
        for symbol in symbols:
             prices[symbol] = 0
             
    return prices

# Funkce pro výpočet otevřených pozic (statická data z reportu)
def calculate_positions(transactions):
    positions = {}
    for _, row in transactions.iterrows():
        if pd.isna(row['Symbol']): continue
        symbol = row['Symbol']
        quantity = row['Volume']
        purchase_value = row['Purchase value']
        transaction_type = row['Type']
        if symbol not in positions:
            positions[symbol] = {'quantity': 0, 'total_cost': 0}
        if 'BUY' in transaction_type.upper():
            positions[symbol]['quantity'] += quantity
            positions[symbol]['total_cost'] += purchase_value
    for symbol in positions:
        if positions[symbol]['quantity'] > 0:
            positions[symbol]['avg_price'] = positions[symbol]['total_cost'] / positions[symbol]['quantity']
        else:
            positions[symbol]['avg_price'] = 0
    return {k: v for k, v in positions.items() if v['quantity'] > 0} 

# Historická data (s cachingem) - PŮVODNÍ, FUNKČNÍ LOGIKA
@st.cache_data(ttl=3600)
def get_historical_prices(symbols, start_date, end_date):
    hist_prices = {}
    currencies = set(get_ticker_and_currency(s)[1] for s in symbols if get_ticker_and_currency(s)[1] != 'USD')
    hist_rates = {}
    currency_tickers = [f"{curr}USD=X" for curr in currencies]
    
    if currency_tickers:
        try:
            rates_df = yf.download(currency_tickers, start=start_date, end=end_date, progress=False)['Close']
            if isinstance(rates_df, pd.Series):
                currency = currency_tickers[0].split('USD=X')[0]
                hist_rates[currency] = rates_df.fillna(method='ffill')
            else:
                for curr in currencies:
                    ticker = f"{curr}USD=X"
                    hist_rates[curr] = rates_df[ticker].fillna(method='ffill')
        except:
            pass
            
    for symbol in symbols:
        ticker, currency = get_ticker_and_currency(symbol)
        try:
            # Původní metoda Ticker().history()
            df = yf.Ticker(ticker).history(start=start_date, end=end_date) 
            prices = df['Close'].fillna(method='ffill')
            if currency != 'USD' and currency in hist_rates:
                rates = hist_rates[currency].reindex(prices.index, method='ffill')
                prices = prices * rates
            hist_prices[symbol] = prices
            
        except Exception:
            hist_prices[symbol] = pd.Series()
            
    return hist_prices


# --- 3. HLAVNÍ ČÁST APLIKACE ---

st.title('Alfa Dashboard')
st.info('Nahraj Excel/CSV report z XTB. Všechny hodnoty jsou automaticky převedeny do USD. Data jsou aktuální díky Yahoo Finance.')

uploaded_file = st.file_uploader('Nahraj CSV nebo Excel report z XTB', type=['csv', 'xlsx'])

df_open = pd.DataFrame()
df_closed = pd.DataFrame() # Bude sice stále načten pro kompatibilitu, ale nepoužit pro zisk
df_cash = pd.DataFrame() # Nový DataFrame pro hotovostní operace (dividendy)

# Načítání souboru
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            excel = pd.ExcelFile(uploaded_file)
            sheets = excel.sheet_names
            open_sheet = next((s for s in sheets if 'OPEN POSITION' in s.upper()), None)
            closed_sheet = next((s for s in sheets if 'CLOSED POSITION' in s.upper()), None)
            # NOVÝ SHEET pro hotovostní operace
            cash_sheet = next((s for s in sheets if 'CASH OPERATION' in s.upper()), None)
            
            # --- Robustní hledání hlaviček ---
            
            if open_sheet:
                df_full = pd.read_excel(uploaded_file, sheet_name=open_sheet, header=None)
                header_index = df_full[df_full.iloc[:, 0].astype(str) == 'Position'].index.min()
                if not pd.isna(header_index):
                    df_open = pd.read_excel(uploaded_file, sheet_name=open_sheet, header=header_index).dropna(how='all')
                else:
                    df_open = pd.read_excel(uploaded_file, sheet_name=open_sheet, header=10).dropna(how='all')
            
            if closed_sheet:
                df_full_closed = pd.read_excel(uploaded_file, sheet_name=closed_sheet, header=None)
                header_index_closed = df_full_closed[df_full_closed.iloc[:, 0].astype(str) == 'Position'].index.min()
                if not pd.isna(header_index_closed):
                    df_closed = pd.read_excel(uploaded_file, sheet_name=closed_sheet, header=header_index_closed).dropna(how='all')
                else:
                    df_closed = pd.read_excel(uploaded_file, sheet_name=closed_sheet, header=9).dropna(how='all')
            
            # NAČTENÍ CASH OPERATION HISTORY
            if cash_sheet:
                 df_full_cash = pd.read_excel(uploaded_file, sheet_name=cash_sheet, header=None)
                 # Hledání hlavičky 'ID' - předpokládáme 10 řádek nad "ID"
                 header_index_cash = df_full_cash[df_full_cash.iloc[:, 1].astype(str) == 'ID'].index.min()
                 if not pd.isna(header_index_cash):
                     df_cash = pd.read_excel(uploaded_file, sheet_name=cash_sheet, header=header_index_cash).dropna(how='all')
                 else:
                     df_cash = pd.read_excel(uploaded_file, sheet_name=cash_sheet, header=10).dropna(how='all')
                 st.success("Načtena historie hotovostních operací (pro dividendy).")

        else: # HANDLING CSV FILES
            df_temp = pd.read_csv(uploaded_file, header=10).dropna(how='all')
            
            # Zjednodušená detekce pro CSV
            if 'Gross P/L' in df_temp.columns and 'Position' in df_temp.columns:
                df_closed = df_temp
                st.success("Načten CSV soubor: Uzavřené pozice.")
                
            elif 'Purchase value' in df_temp.columns and 'Volume' in df_temp.columns:
                df_open = df_temp
                st.success("Načten CSV soubor: Otevřené pozice.")
            
            elif 'Type' in df_temp.columns and 'Amount' in df_temp.columns and 'DIVIDENT' in df_temp['Type'].astype(str).unique():
                 df_cash = df_temp
                 st.success("Načten CSV soubor: Hotovostní operace (pro dividendy).")
            
            else:
                st.warning("Načten CSV soubor, ale nebyl rozpoznán jako standardní report. Zkusíme jej zpracovat jako Otevřené pozice.")
                df_open = df_temp

            
    except Exception as e:
        st.error(f"Chyba při čtení souboru. Zkontroluj formát. Chyba: {e}")
        df_open = pd.DataFrame()
        df_closed = pd.DataFrame()
        df_cash = pd.DataFrame()
        

    # Tlačítko pro spuštění trackování a uložení stavu
    if st.button('Trackuj Portfolio a Získej Aktuální Data') or 'positions_df' in st.session_state:
        
        # --- 4. Inicializace, stažení dat a přepočet ---
        
        if 'positions_df' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
            with st.spinner('Počítám metriky a stahuji data z Yahoo Finance...'):
                positions = calculate_positions(df_open)
                
                # VÝPOČET DIVIDEND
                if 'Type' in df_cash.columns and 'Amount' in df_cash.columns:
                    # Filter for 'DIVIDENT' type and sum the 'Amount' column
                    dividends_df = df_cash[df_cash['Type'].astype(str).str.upper().str.contains('DIVIDENT', na=False)]
                    # Suma je v USD, protože report je v USD
                    total_dividends = dividends_df['Amount'].sum() if not dividends_df.empty else 0
                else:
                    total_dividends = 0
                
                if not positions:
                    st.warning('Žádné aktivní otevřené pozice nebyly nalezeny ve vstupních datech.')
                    st.session_state['positions_df'] = pd.DataFrame()
                    st.session_state['total_invested'] = 0
                    st.session_state['total_dividends'] = 0 
                else:
                    symbols = list(positions.keys())
                    current_prices = get_current_prices(symbols)

                    table_data = []
                    total_invested = sum(pos['total_cost'] for pos in positions.values())
                    
                    for symbol, pos in positions.items():
                        qty = pos['quantity']
                        avg_price = pos['avg_price']
                        current_price = current_prices.get(symbol, 0)
                        
                        table_data.append({
                            'Název': symbol, 'Množství': qty, 
                            'Průměrná cena (USD)': avg_price,
                            'Aktuální cena (USD)': current_price, 
                            'Velikost pozice (USD)': 0.0, 
                            'Nerealizovaný Zisk (USD)': 0.0, 
                            'Nerealizovaný % Zisk': 0.0, 
                            'Náklad pozice (USD)': avg_price * qty
                        })

                    positions_df_init = pd.DataFrame(table_data)
                    
                    st.session_state['positions_df'] = positions_df_init
                    st.session_state['total_invested'] = total_invested
                    st.session_state['total_dividends'] = total_dividends 
                    st.session_state['uploaded_file_name'] = uploaded_file.name

        
        if st.session_state['positions_df'].empty:
            st.warning("Žádné aktivní pozice pro zobrazení. Nahrajte prosím soubor s daty a stiskněte 'Trackuj Portfolio'.")
            st.stop() 

        # --- 5. Přepočet metrik (Na základě dat v Session State) ---
        
        edited_df = st.session_state['positions_df'].copy()
        total_dividends = st.session_state['total_dividends'] # Načtení dividend

        edited_df['Velikost pozice (USD)'] = edited_df['Množství'] * edited_df['Aktuální cena (USD)']
        edited_df['Nerealizovaný Zisk (USD)'] = (edited_df['Aktuální cena (USD)'] - edited_df['Průměrná cena (USD)']) * edited_df['Množství']
        edited_df['Nerealizovaný % Zisk'] = (edited_df['Nerealizovaný Zisk (USD)'] / edited_df['Náklad pozice (USD)'] * 100).fillna(0)
        
        total_portfolio_value = edited_df['Velikost pozice (USD)'].sum()
        unrealized_profit = edited_df['Nerealizovaný Zisk (USD)'].sum()
        total_invested = st.session_state['total_invested']
        
        unrealized_profit_pct = (unrealized_profit / total_invested * 100) if total_invested > 0 else 0
        
        edited_df['% v portfoliu'] = edited_df['Velikost pozice (USD)'].apply(
            lambda x: (x / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        )
        
        positions_df = edited_df.copy() 
        
        # --- 6. VÝKONNOSTNÍ BOXY (Preferovaný layout) ---
        
        st.header('Přehled Výkonnosti')
        
        col1, col2, col3 = st.columns(3) 

        # Box 1: HODNOTA PORTFOLIA (Hlavní - MODRÁ)
        with col1:
            st.markdown(f"""
            <div class="custom-card main-card">
                <div class="card-title">HODNOTA PORTFOLIA</div>
                <p class="main-card-value">{round(total_portfolio_value, 2):,.2f} USD</p>
                <p style="font-size:12px; margin-top:5px; color:#fafafa;">K {datetime.now().strftime('%d. %m. %Y')}</p>
            </div>
            """, unsafe_allow_html=True)

        # Box 2: CELKEM VYPLACENÉ DIVIDENDY (Symetrická karta)
        with col2:
            val_class = "value-positive" if total_dividends >= 0 else "value-negative"
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-title">CELKEM VYPLACENÉ DIVIDENDY</div>
                <p class="card-value {val_class}">{round(total_dividends, 2):,.2f} USD</p>
                <p style="font-size:12px; color:#999999;">Od počátku reportu</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Box 3: NEREALIZOVANÝ ZISK (Symetrická karta)
        with col3:
            val_class = "value-positive" if unrealized_profit >= 0 else "value-negative"
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-title">NEREALIZOVANÝ ZISK</div>
                <p class="card-value {val_class}">{round(unrealized_profit, 2):,.2f} USD</p>
                <p style="font-size:12px; color:#999999;">{round(unrealized_profit_pct, 2):,.2f} % celkové investice</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Druhý řádek: CELKOVÁ HODNOTA a INVESTOVANÁ ČÁSTKA
        col4, col5 = st.columns(2)
        
        # Box 4: CELKOVÁ HODNOTA (Portfolio + Dividendy)
        with col4:
            total_value_with_profit = total_portfolio_value + total_dividends
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-title">CELKOVÁ HODNOTA (Portfolio + Dividendy)</div>
                <p class="card-value value-neutral">{round(total_value_with_profit, 2):,.2f} USD</p>
            </div>
            """, unsafe_allow_html=True)

        # Box 5: INVESTOVANÁ ČÁSTKA
        with col5:
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-title">INVESTOVANÁ ČÁSTKA</div>
                <p class="card-value value-neutral">{round(total_invested, 2):,.2f} USD</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.write('---')

        # --- 7. Historický Graf (Line Chart) ---
        
        st.subheader('Historický vývoj portfolia')
        
        period = st.select_slider(
            'Vyberte časový horizont grafu:',
            options=['3m', '6m', '1y', '2y', '5y', 'max'],
            value='1y'
        )

        today = datetime.now()
        delta_map = {'3m': 90, '6m': 180, '1y': 365, '2y': 365*2, '5y': 365*5, 'max': 365*10}
        days = delta_map.get(period, 365)
        start_date = today - pd.Timedelta(days=days)
        end_date = today

        with st.spinner(f'Načítám historická data pro {period}...'):
            symbols_hist = [s for s in positions_df['Název'].unique()]
            hist_prices = get_historical_prices(symbols_hist, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            portfolio_history = pd.DataFrame(index=pd.to_datetime(pd.date_range(start=start_date, end=end_date)))
            
            for symbol in symbols_hist:
                # Ošetření, pokud pozice neexistuje nebo je 0
                pos_data = positions_df[positions_df['Název'] == symbol]
                if pos_data.empty: continue
                
                pos = pos_data.iloc[0]
                qty = pos['Množství']
                if qty == 0: continue
                
                if symbol in hist_prices and not hist_prices[symbol].empty:
                    prices = hist_prices[symbol]
                    prices.index = prices.index.tz_localize(None)
                    prices = prices.reindex(portfolio_history.index, method='ffill')
                    portfolio_history[symbol] = prices * qty
            
            portfolio_history['Celková hodnota'] = portfolio_history.sum(axis=1).replace(0, np.nan).fillna(method='ffill')
            
            if not portfolio_history.empty and 'Celková hodnota' in portfolio_history.columns:
                
                fig_hist = px.line(
                    portfolio_history.reset_index(), 
                    x='index', 
                    y='Celková hodnota', 
                    title='Historický vývoj hodnoty portfolia',
                    labels={'index': 'Datum', 'Celková hodnota': 'Hodnota (USD)'},
                    template='plotly_dark' 
                )
                
                # Sjednocené pozadí grafu - ČISTĚ ČERNÁ
                PLOTLY_BG_COLOR = '#000000' 
                fig_hist.update_layout(
                    plot_bgcolor=PLOTLY_BG_COLOR,
                    paper_bgcolor=PLOTLY_BG_COLOR,
                    font=dict(color="#fafafa"),
                    margin=dict(t=50, b=50, l=50, r=50) 
                )
                
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                 st.warning("Historická data pro graf nebyla nalezena pro všechny pozice.")
        
        st.write('---')

        # --- 8. Koláčové grafy rozložení portfolia (Donut Charts) ---
        
        st.subheader('Rozložení Portfolia')
        
        # 8a. Rozdělení na ETF vs. Akcie (Stocks)
        
        def categorize_asset(symbol):
            symbol_upper = symbol.upper()
            # Explicitně identifikujeme ETF (CSPX, CNDX), zbytek s evropskou koncovkou budou Akcie EU.
            if 'CSPX' in symbol_upper or 'CNDX' in symbol_upper:
                return 'ETF (EU)' 
            elif symbol_upper.endswith('.UK') or symbol_upper.endswith('.DE') or symbol_upper.endswith('.IT'):
                return 'Akcie (EU)' # Sem spadne TUI a Stellantis
            else:
                return 'Akcie (US/Jiné)'

        positions_df['Kategorie'] = positions_df['Název'].apply(categorize_asset)
        
        allocation_df = positions_df.groupby('Kategorie')['Velikost pozice (USD)'].sum().reset_index()
        allocation_df = allocation_df[allocation_df['Velikost pozice (USD)'] > 0]
        
        col_pie_1, col_pie_2 = st.columns(2)
        
        with col_pie_1:
            if not allocation_df.empty:
                fig_allocation = px.pie(
                    allocation_df,
                    values='Velikost pozice (USD)',
                    names='Kategorie',
                    title='**Alokace: ETF vs. Akcie**',
                    template='plotly_dark' 
                )
                
                fig_allocation.update_traces(
                    textposition='inside', 
                    textinfo='percent+label', 
                    hole=.4 
                )
                
                PLOTLY_BG_COLOR = '#000000'
                fig_allocation.update_layout(
                    plot_bgcolor=PLOTLY_BG_COLOR,
                    paper_bgcolor=PLOTLY_BG_COLOR,
                    font=dict(color="#fafafa"),
                    showlegend=True, 
                    margin=dict(t=30, b=0, l=0, r=0)
                )
                
                st.plotly_chart(fig_allocation, use_container_width=True)
            else:
                st.info('Pro zobrazení alokačního grafu musíte mít otevřené pozice.')
                
        # 8b. Rozdělení podle jednotlivých tickerů (původní graf)
        
        with col_pie_2:
            pie_data = positions_df[positions_df['Velikost pozice (USD)'] > 0]
            
            if not pie_data.empty:
                fig_ticker = px.pie(
                    pie_data,
                    values='Velikost pozice (USD)',
                    names='Název',
                    title='**Rozdělení podle Tickeru**',
                    hover_data=['Velikost pozice (USD)', 'Nerealizovaný % Zisk'],
                    template='plotly_dark' 
                )
                
                fig_ticker.update_traces(
                    textposition='inside', 
                    textinfo='percent+label', 
                    hole=.4 
                )
                
                PLOTLY_BG_COLOR = '#000000'
                fig_ticker.update_layout(
                    plot_bgcolor=PLOTLY_BG_COLOR,
                    paper_bgcolor=PLOTLY_BG_COLOR,
                    font=dict(color="#fafafa"),
                    showlegend=True, 
                    margin=dict(t=30, b=0, l=0, r=0)
                )
                
                st.plotly_chart(fig_ticker, use_container_width=True)
            else:
                # Už zobrazeno v prvním sloupci, ale pro jistotu
                pass
            
        st.write('---')

        # --- 9. Zobrazení tabulky s finálními hodnotami (Pouze pro čtení) ---
        
        st.subheader('Přepočítané Otevřené Pozice (Finální Přehled)')
        
        final_df = positions_df.drop(columns=['Náklad pozice (USD)']).copy()

        st.dataframe(final_df.style.format({
            'Množství': '{:.4f}',
            'Průměrná cena (USD)': '{:.2f}',
            'Aktuální cena (USD)': '{:.2f}',
            'Velikost pozice (USD)': '{:,.2f}',
            'Nerealizovaný Zisk (USD)': '{:,.2f}',
            '% v portfoliu': '{:.2f}%',
            'Nerealizovaný % Zisk': '{:.2f}%'
        }))

        # ====================================================================
        # === MANUÁLNÍ KOREKCE ===============================================
        # ====================================================================
        
        st.header('Manuální Korekce Aktuálních Cen')
        st.warning('Tato tabulka slouží k manuální úpravě aktuální ceny (např. pokud yfinance vrací chybnou hodnotu 0). Změna se projeví v celém přehledu.')

        editable_df = positions_df[['Název', 'Aktuální cena (USD)']].copy()
        editable_df.rename(columns={'Aktuální cena (USD)': 'Aktuální cena (USD) - Manuální úprava'}, inplace=True)
        
        # Přidání vyhledávání
        search_term = st.text_input("Filtruj tabulku podle názvu akcie:", value="")
        if search_term:
            editable_df_filtered = editable_df[editable_df['Název'].str.contains(search_term, case=False, na=False)]
        else:
            editable_df_filtered = editable_df

        # Zobrazení a úprava
        edited_data = st.data_editor(
            editable_df_filtered,
            hide_index=True,
            column_config={
                "Aktuální cena (USD) - Manuální úprava": st.column_config.NumberColumn(
                    "Aktuální cena (USD) - Manuální úprava",
                    format="%.2f",
                    min_value=0.01,
                    help="Zadejte aktuální cenu, pokud se automatická cena nenačetla správně (např. nula)."
                )
            },
            num_rows="dynamic"
        )
        
        # Uložení úprav do session_state pro další přepočet
        if edited_data is not None:
            # Vytvoření slovníku pro snadné mapování (Název -> Nová Cena)
            price_updates = edited_data.set_index('Název')['Aktuální cena (USD) - Manuální úprava'].to_dict()
            
            # Aplikace změn pouze u těch, které byly editovány
            st.session_state['positions_df']['Aktuální cena (USD)'] = st.session_state['positions_df'].apply(
                lambda row: price_updates.get(row['Název'], row['Aktuální cena (USD)']), 
                axis=1
            )
            
            st.success("Manuální úpravy byly uloženy. Pro zobrazení nového přehledu **musíte znovu kliknout na 'Trackuj Portfolio a Získej Aktuální Data'.**")
            
        # ====================================================================
