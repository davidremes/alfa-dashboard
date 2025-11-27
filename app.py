import streamlit as st
import pandas as pd
from yahooquery import Ticker as yf # <--- OPRAVENÝ IMPORT
from datetime import datetime
import numpy as np
import plotly.express as px
import warnings 
# Potlačení FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. KOSMETIKA & CSS (Styling pro čistě černý motiv - MAXIMÁLNÍ VYNUCENÍ) ---
st.markdown("""
<style>
    /* Hlavní pozadí aplikace - ČISTĚ ČERNÁ */
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
        min-height: 120px !important;
        color: #fafafa;
    }
    .custom-card-title {
        color: #A9A9A9 !important;
        font-size: 14px;
        margin-bottom: 5px;
    }
    .custom-card-value {
        color: #ffffff !important;
        font-size: 24px;
        font-weight: bold;
    }
    /* Vynucení černé pro tabulky a pozadí pro tmavý vzhled */
    div[data-testid="stDataFrame"], 
    div[data-testid="stTable"], 
    div[data-testid="stDataEditor"] {
        background-color: #000000 !important;
        border: 1px solid #2a2a2a !important;
    }
    .stFileUploader section,
    .stFileUploader section > div,
    .stFileUploader [data-testid="stFileUploadDropzone"] {
        background-color: #1a1a1a !important; 
        border: 2px dashed #444444 !important;
        color: #fafafa !important;
    }
    
</style>
""", unsafe_allow_html=True)


# --- 2. FUNKCE PRO ZÍSKÁNÍ DAT ---

# Funkce pro mapování XTB symbolů na yahooquery tickery
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

# Funkce pro stažení aktuálních cen
@st.cache_data(ttl=600)
def get_current_prices(symbols):
    if not symbols:
        return {}
        
    ticker_map = {symbol: get_ticker_and_currency(symbol) for symbol in symbols}
    yf_tickers = [v[0] for v in ticker_map.values()]
    currencies_to_fetch = set(v[1] for v in ticker_map.values() if v[1] != 'USD')
    
    currency_rates = {'USD': 1.0}
    currency_tickers = [f"{curr}USD=X" for curr in currencies_to_fetch]
    
    # Načtení kurzů
    if currency_tickers:
        try:
            rates_data = yf(currency_tickers).price
            for curr_ticker in currency_tickers:
                currency = curr_ticker.split('USD=X')[0]
                if isinstance(rates_data, dict) and curr_ticker in rates_data:
                    rate = rates_data[curr_ticker].get('regularMarketPrice', 1.0)
                    currency_rates[currency] = rate
                elif isinstance(rates_data, dict) and len(rates_data) == 1 and curr_ticker.split('=')[0] in rates_data:
                    rate = rates_data[curr_ticker.split('=')[0]].get('regularMarketPrice', 1.0)
                    currency_rates[currency] = rate
                else:
                    currency_rates[currency] = 1.0

        except Exception as e:
            st.warning(f"Problém se stažením kurzu, používám výchozí 1.0. Chyba: {e}")
            pass 
            
    prices = {}
    
    # Načtení cen akcií
    try:
        data = yf(yf_tickers).price
        
        for symbol, (ticker, currency) in ticker_map.items():
            price = 0.0
            
            if isinstance(data, dict):
                if ticker in data:
                    price = data[ticker].get('regularMarketPrice', 0.0)
                elif len(data) > 0 and 'regularMarketPrice' in data and len(yf_tickers) == 1:
                    price = data.get('regularMarketPrice', 0.0)
            
            prices[symbol] = price * currency_rates.get(currency, 1.0)
            
    except Exception as e:
        st.error(f"Nepodařilo se stáhnout ceny pro jeden nebo více symbolů. Chyba: {e}")
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
        
        # <<< OPRAVA CHYBY KEYERROR: Zkusí 'Nominal value', jinak 'Purchase value' >>>
        try:
            purchase_value = row['Nominal value'] 
        except KeyError:
            try:
                purchase_value = row['Purchase value']
            except KeyError:
                raise KeyError("Sloupec 'Nominal value' ani 'Purchase value' nebyl nalezen. Zkontrolujte prosím přesný název sloupce pro nákupní hodnotu ve vašem Excel reportu.")

        # <<< KONEC OPRAVY KEYERROR >>>
        
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

# Historická data
@st.cache_data(ttl=3600)
def get_historical_prices(symbols, start_date, end_date):
    hist_prices = {}
    currencies = set(get_ticker_and_currency(s)[1] for s in symbols if get_ticker_and_currency(s)[1] != 'USD')
    hist_rates = {}
    
    # Načtení historických kurzů
    currency_tickers = [f"{curr}USD=X" for curr in currencies]
    if currency_tickers:
        try:
            rate_data = yf(currency_tickers).history(start=start_date, end=end_date)
            for curr in currencies:
                ticker = f"{curr}USD=X"
                if isinstance(rate_data.index, pd.MultiIndex):
                    rates_df = rate_data.loc[ticker, 'close'].to_frame()
                else:
                    rates_df = rate_data['close'].to_frame()
                
                hist_rates[curr] = rates_df['close'].fillna(method='ffill')
        except Exception as e:
            st.warning(f"Chyba při stahování historických kurzů: {e}")
            pass
            
    for symbol in symbols:
        ticker, currency = get_ticker_and_currency(symbol)
        try:
            df = yf(ticker).history(start=start_date, end=end_date)
            prices = df['close'].fillna(method='ffill')
            
            if currency != 'USD' and currency in hist_rates:
                rates = hist_rates[currency].reindex(prices.index, method='ffill')
                prices = prices * rates.fillna(1.0)
            
            hist_prices[symbol] = prices
            
        except Exception as e:
            st.warning(f"Chyba při stahování historických cen pro {symbol}: {e}")
            hist_prices[symbol] = pd.Series()
            
    return hist_prices


# --- 3. HLAVNÍ ČÁST APLIKACE ---

def main_app():
    st.title('💰 Alfa Dashboard - Analýza XTB Výpisu')
    st.info('Nahraj Excel/CSV report z XTB. Všechny hodnoty jsou automaticky převedeny do USD. Data jsou aktuální díky Yahoo Finance.')

    uploaded_file = st.file_uploader('Nahraj CSV nebo Excel report z XTB', type=['csv', 'xlsx'])

    df_open = pd.DataFrame()
    df_closed = pd.DataFrame() 
    df_cash = pd.DataFrame() 

    # Načítání souboru
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                excel = pd.ExcelFile(uploaded_file)
                sheets = excel.sheet_names
                open_sheet = next((s for s in sheets if 'OPEN POSITION' in s.upper() or 'OTEVŘENÁ POZICE' in s.upper()), None)
                closed_sheet = next((s for s in sheets if 'CLOSED POSITION' in s.upper() or 'UZAVŘENÁ POZICE' in s.upper()), None)
                cash_sheet = next((s for s in sheets if 'CASH OPERATION' in s.upper() or 'HOTOVOSTNÍ OPERACE' in s.upper()), None)
                
                # --- Robustní hledání hlaviček ---
                
                if open_sheet:
                    df_full = pd.read_excel(uploaded_file, sheet_name=open_sheet, header=None)
                    header_index_candidates = df_full[df_full.iloc[:, 0].astype(str).str.contains('Position|Pozice|Symbol', case=False, na=False)].index
                    header_index = header_index_candidates.min() if not header_index_candidates.empty else 9 
                    
                    df_open = pd.read_excel(uploaded_file, sheet_name=open_sheet, header=header_index).dropna(how='all')
                    st.success(f"Načten list Otevřené pozice: {open_sheet}")

                if closed_sheet:
                    df_full_closed = pd.read_excel(uploaded_file, sheet_name=closed_sheet, header=None)
                    header_index_candidates = df_full_closed[df_full_closed.iloc[:, 0].astype(str).str.contains('Position|Pozice|Symbol', case=False, na=False)].index
                    header_index_closed = header_index_candidates.min() if not header_index_candidates.empty else 9
                    df_closed = pd.read_excel(uploaded_file, sheet_name=closed_sheet, header=header_index_closed).dropna(how='all')
                    st.success(f"Načten list Uzavřené pozice: {closed_sheet}")
                
                # NAČTENÍ CASH OPERATION HISTORY
                if cash_sheet:
                    df_full_cash = pd.read_excel(uploaded_file, sheet_name=cash_sheet, header=None)
                    header_index_candidates = df_full_cash[df_full_cash.iloc[:, 1].astype(str).str.contains('ID|Type|Typ', case=False, na=False)].index
                    header_index_cash = header_index_candidates.min() if not header_index_candidates.empty else 9
                    df_cash = pd.read_excel(uploaded_file, sheet_name=cash_sheet, header=header_index_cash).dropna(how='all')
                    st.success(f"Načtena historie hotovostních operací (pro dividendy): {cash_sheet}.")

            else: # HANDLING CSV FILES
                # Pro CSV je obtížné detekovat sheet, načítá se jako jedna tabulka
                df_temp = pd.read_csv(uploaded_file, header=10).dropna(how='all')
                
                if 'Gross P/L' in df_temp.columns and 'Position' in df_temp.columns:
                    df_closed = df_temp
                    st.success("Načten CSV soubor: Uzavřené pozice.")
                    
                elif 'Purchase value' in df_temp.columns or 'Nominal value' in df_temp.columns:
                    df_open = df_temp
                    st.success("Načten CSV soubor: Otevřené pozice.")
                
                elif 'Type' in df_temp.columns and 'Amount' in df_temp.columns:
                    df_cash = df_temp
                    st.success("Načten CSV soubor: Hotovostní operace (pro dividendy).")
                
                else:
                    st.warning("Načten CSV soubor, ale nebyl rozpoznán. Zpracovávám jako Otevřené pozice.")
                    df_open = df_temp

                
        except Exception as e:
            st.error(f"Chyba při čtení souboru. Zkontroluj formát (CSV s oddělovačem ';'). Chyba: {e}")
            df_open = pd.DataFrame()
            df_closed = pd.DataFrame()
            df_cash = pd.DataFrame()
            

    # Tlačítko pro spuštění trackování a uložení stavu
    if st.button('Trackuj Portfolio a Získej Aktuální Data') or 'positions_df' in st.session_state:
        
        # --- 4. Inicializace, stažení dat a přepočet ---
        
        if 'positions_df' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
            with st.spinner('Počítám metriky a stahuji data z Yahoo Finance...'):
                try:
                    positions = calculate_positions(df_open)
                except KeyError as e:
                    st.error(f"Kritická chyba: {e}. Zkontrolujte přesný název sloupce pro nákupní hodnotu v listu Otevřené pozice.")
                    st.stop()
                
                # VÝPOČET DIVIDEND
                if 'Type' in df_cash.columns and 'Amount' in df_cash.columns:
                    dividends_df = df_cash[df_cash['Type'].astype(str).str.upper().str.contains('DIVIDENT', na=False)]
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
                    
                    # <<< OPRAVA: Odfiltruje prázdné a nečisté symboly před dotazem na Yahoo >>>
                    symbols = [s for s in symbols if s and s.strip() != '']
                    
                    if not symbols:
                         st.warning('Žádné platné symboly k trackování. Zkontrolujte report.')
                         st.session_state['positions_df'] = pd.DataFrame()
                         st.stop()
                    # <<< KONEC OPRAVY >>>
                    
                    current_prices = get_current_prices(symbols)

                    table_data = []
                    total_invested = sum(pos['total_cost'] for pos in positions.values())
                    
                    for symbol, pos in positions.items():
                        # POUZE PRO PLATNÉ SYMBOLY
                        if symbol not in symbols: continue
                        
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
        
        # --- 6. VÝKONNOSTNÍ BOXY ---
        
        st.header('Přehled Výkonnosti')
        
        col1, col2, col3 = st.columns(3) 

        # Box 1: HODNOTA PORTFOLIA 
        with col1:
            st.markdown(f"""
            <div class="custom-card main-card">
                <div class="card-title">HODNOTA PORTFOLIA</div>
                <p class="main-card-value">{round(total_portfolio_value, 2):,.2f} USD</p>
                <p style="font-size:12px; margin-top:5px; color:#fafafa;">K {datetime.now().strftime('%d. %m. %Y')}</p>
            </div>
            """, unsafe_allow_html=True)

        # Box 2: CELKEM VYPLACENÉ DIVIDENDY
        with col2:
            val_class = "value-positive" if total_dividends >= 0 else "value-negative"
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-title">CELKEM VYPLACENÉ DIVIDENDY</div>
                <p class="card-value {val_class}">{round(total_dividends, 2):,.2f} USD</p>
                <p style="font-size:12px; color:#999999;">Od počátku reportu</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Box 3: NEREALIZOVANÝ ZISK
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
            # OPRAVENO: Filtruje prázdné/neplatné symboly
            symbols_hist = [s for s in positions_df['Název'].unique() if s and s.strip() != '']
            
            if not symbols_hist:
                st.warning("Nebyl nalezen žádný platný symbol pro historický graf.")
                st.stop()
                
            hist_prices = get_historical_prices(symbols_hist, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            portfolio_history = pd.DataFrame(index=pd.to_datetime(pd.date_range(start=start_date, end=end_date)))
            
            for symbol in symbols_hist:
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
        
        st.subheader('Rozdělení Portfolia')
        
        def categorize_asset(symbol):
            symbol_upper = symbol.upper()
            if symbol_upper.endswith('.UK') or symbol_upper.endswith('.DE') or symbol_upper.endswith('.IT') or 'CSPX' in symbol_upper or 'CNDX' in symbol_upper:
                return 'ETF / Akcie EU' 
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
                pass
            
        st.write('---')

        # --- 9. Tabulka s finálními hodnotami a manuální korekcí ---
        
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
        st.warning('Tato tabulka slouží k manuální úpravě aktuální ceny (např. pokud data nefungují). Změna se projeví po kliknutí na "Trackuj Portfolio".')

        editable_df = positions_df[['Název', 'Aktuální cena (USD)']].copy()
        editable_df.rename(columns={'Aktuální cena (USD)': 'Aktuální cena (USD) - Manuální úprava'}, inplace=True)
        
        search_term = st.text_input("Filtruj tabulku podle názvu akcie:", value="")
        if search_term:
            editable_df_filtered = editable_df[editable_df['Název'].str.contains(search_term, case=False, na=False)]
        else:
            editable_df_filtered = editable_df

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
        
        if edited_data is not None:
            price_updates = edited_data.set_index('Název')['Aktuální cena (USD) - Manuální úprava'].to_dict()
            
            st.session_state['positions_df']['Aktuální cena (USD)'] = st.session_state['positions_df'].apply(
                lambda row: price_updates.get(row['Název'], row['Aktuální cena (USD)']), 
                axis=1
            )
            
            st.success("Manuální úpravy byly uloženy. Pro zobrazení nového přehledu **musíte znovu kliknout na 'Trackuj Portfolio a Získej Aktuální Data'.**")
            

if __name__ == "__main__":
    main_app()
