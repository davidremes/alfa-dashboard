import streamlit as st
import pandas as pd
from yahooquery import Ticker as yf # <--- OPRAVA: Zde se mění knihovna pro spolehlivost
from datetime import datetime
import numpy as np
import plotly.express as px
import warnings 
# Potlačení FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. KOSMETIKA & CSS (Styling pro karty) ---
st.markdown("""
<style>
    /* Původní jednoduché boxy (Karty s metrikami) */
    .custom-card {
        background-color: #1a1a1a !important; 
        border: 1px solid #2a2a2a !important; 
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important; 
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4) !important;
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
</style>
""", unsafe_allow_html=True)


# --- 2. CACHING A DATA MANAGEMENT ---

@st.cache_data(ttl=60*60*4) # Kešování na 4 hodiny
def load_and_preprocess_data(uploaded_file):
    """Načte, vyčistí a předzpracuje data z XTB."""
    try:
        # Použijte pandas k přečtení souboru (XTB často exportuje CSV s oddělovačem ';')
        df = pd.read_csv(uploaded_file, sep=';', decimal=',')
    except Exception as e:
        st.error(f"Chyba při čtení souboru. Zkontrolujte, zda je CSV formát a oddělovač je ';'. Chyba: {e}")
        return None

    # Normalizace názvů sloupců (očištění od mezer a speciálních znaků)
    df.columns = df.columns.str.strip().str.replace('[^A-Za-z0-9_ -]', '', regex=True).str.replace(' ', '_')
    
    # Filtrování transakcí, které nejsou relevance (např. vklady/výběry)
    df = df[df['Type'].isin(['BUY', 'SELL', 'Deposit', 'Withdrawal', 'Fee', 'Dividend', 'Taxes'])]
    
    # Převod datumu
    df['Time'] = pd.to_datetime(df['Time'])
    
    # Ponechání pouze důležitých sloupců
    required_cols = [
        'Time', 'Type', 'Symbol', 'ISIN', 'Volume', 'Price', 'Commission', 
        'Currency', 'Profit', 'Comment', 'Nominal_value', 'Reference_price', 
        'Settle_date', 'Contract_size', 'Profit_in_currency', 'Margin_used', 
        'Open_price', 'Close_price', 'Taxes', 'Coupon', 'Pips', 'Amount'
    ]
    df = df[[col for col in required_cols if col in df.columns]]

    # Přepočet sloupce 'Amount' (který bývá klíčový u XTB pro poplatky, vklady/výběry a dividendy)
    # NaN nahradíme nulou
    if 'Amount' in df.columns:
        df['Amount'] = df['Amount'].fillna(0)
    
    return df

@st.cache_data(ttl=60*60*4)
def get_current_prices(tickers):
    """
    Načte aktuální ceny z Yahoo Finance pomocí yahooquery. (OPRAVENÁ FUNKCE)
    """
    
    if not tickers:
        return {}
    
    # yf je nyní Ticker z yahooquery
    try:
        data = yf(tickers).price
        prices = {}
        for ticker in tickers:
            if isinstance(data, dict):
                # Standardní chování pro více tickerů
                try:
                    price = data[ticker]['regularMarketPrice']
                except (KeyError, TypeError):
                    price = 0.0 # Pokud cena chybí
            else:
                # Chování pro jeden ticker
                try:
                    price = data.get('regularMarketPrice', 0.0)
                except AttributeError:
                    price = 0.0
            
            # Kontrola, že cena je platná
            prices[ticker] = price if price is not None and price != 0 else 0.0
            
        return prices
        
    except Exception as e:
        st.warning(f"Chyba při načítání aktuálních cen pro {tickers}: {e}")
        return {ticker: 0.0 for ticker in tickers}


def aggregate_positions(df, current_prices):
    """
    Agreguje transakce do aktuálních pozic a přepočítá hodnoty.
    """
    
    # Odstranit vklady/výběry pro zjištění pozic
    df_positions = df[df['Type'].isin(['BUY', 'SELL'])]
    
    # Agregace pozic
    positions = df_positions.groupby('Symbol').agg(
        Total_Volume=('Volume', 'sum'),
        Total_Cost=('Amount', 'sum') # 'Amount' je zde celková částka za transakci
    ).reset_index()

    # Filtrovat pouze otevřené pozice (Total_Volume != 0)
    positions = positions[positions['Total_Volume'] != 0].copy()

    if positions.empty:
        return pd.DataFrame()

    # --- Výpočty ---
    
    positions['Název'] = positions['Symbol']
    positions['Kusů'] = positions['Total_Volume'].abs().round(4)
    positions['Průměrná nákupní cena (USD)'] = (positions['Total_Cost'] / positions['Total_Volume']).abs().round(4)
    positions['Aktuální cena (USD)'] = positions['Název'].map(current_prices).fillna(0.0).round(4)
    
    # Manuální úprava - pokud cena z yf je 0, přidáme sloupec pro manuální úpravu
    positions['Aktuální cena (USD) - Manuální úprava'] = positions['Aktuální cena (USD)'].apply(
        lambda x: x if x > 0.0 else positions['Průměrná nákupní cena (USD)']
    )

    positions['Tržní hodnota (USD)'] = (positions['Kusů'] * positions['Aktuální cena (USD)']).round(2)
    positions['Náklady (USD)'] = (positions['Kusů'] * positions['Průměrná nákupní cena (USD)']).round(2)
    positions['Nezrealizovaný zisk/ztráta (USD)'] = (positions['Tržní hodnota (USD)'] - positions['Náklady (USD)']).round(2)
    
    # Procento zisku/ztráty
    positions['Nezrealizovaný zisk/ztráta (%)'] = np.where(
        positions['Náklady (USD)'] != 0,
        ((positions['Tržní hodnota (USD)'] / positions['Náklady (USD)']) - 1) * 100,
        0
    ).round(2)

    # Typ pozice
    positions['Typ'] = np.where(positions['Total_Volume'] > 0, 'LONG', 'SHORT')

    return positions[['Název', 'Typ', 'Kusů', 'Průměrná nákupní cena (USD)', 
                      'Aktuální cena (USD)', 'Aktuální cena (USD) - Manuální úprava',
                      'Náklady (USD)', 'Tržní hodnota (USD)', 
                      'Nezrealizovaný zisk/ztráta (USD)', 'Nezrealizovaný zisk/ztráta (%)']]

def calculate_totals(positions_df, original_df):
    """
    Vypočítá celkové metriky pro Dashboard.
    """
    
    # 1. Neinvestiční cashflow (Vklady/Výběry/Poplatky/Dividendy)
    total_deposits = original_df[original_df['Type'] == 'Deposit']['Amount'].sum()
    total_withdrawals = original_df[original_df['Type'] == 'Withdrawal']['Amount'].sum()
    total_fees = original_df[original_df['Type'].isin(['Fee', 'Commission'])]['Amount'].sum()
    total_dividends = original_df[original_df['Type'].isin(['Dividend', 'Coupon'])]['Amount'].sum()
    
    total_investment = total_deposits - total_withdrawals
    
    # 2. Celkové portfolio
    current_market_value = positions_df['Tržní hodnota (USD)'].sum()
    total_cost_basis = positions_df['Náklady (USD)'].sum()
    total_unrealized_pnl = current_market_value - total_cost_basis
    
    # 3. Zrealizovaný zisk (Zisk/Ztráta ze SELL transakcí)
    realized_profit = original_df['Profit'].fillna(0).sum().round(2)
    
    # 4. Celkový zisk
    total_profit = total_unrealized_pnl + realized_profit + total_dividends
    
    return {
        'current_market_value': current_market_value,
        'total_cost_basis': total_cost_basis,
        'total_unrealized_pnl': total_unrealized_pnl,
        'realized_profit': realized_profit,
        'total_dividends': total_dividends,
        'total_profit': total_profit,
        'total_investment': total_investment,
    }

# --- STREAMLIT UI A HLAVNÍ LOGIKA ---

def main_app():
    st.title("💰 Alfa Dashboard - Analýza XTB Výpisu")
    st.markdown("---")

    # --- Uploader souborů ---
    uploaded_file = st.file_uploader(
        "Nahrajte CSV výpis transakční historie z XTB (Používá se pro beta testování. Data nejsou ukládána.)", 
        type=["csv"]
    )

    if uploaded_file is not None:
        
        # Načtení a předzpracování dat
        df = load_and_preprocess_data(uploaded_file)
        if df is None or df.empty:
            st.warning("Nahraný soubor neobsahuje platné transakce po filtraci. Zkuste jiný CSV soubor.")
            return

        # Uložit DataFrame do session_state, aby se při znovunačtení stránky nečetl znovu
        if 'original_df' not in st.session_state:
            st.session_state['original_df'] = df

        # --- Načtení aktuálních cen ---
        unique_tickers = st.session_state['original_df']['Symbol'].unique().tolist()
        
        # Načtení aktuálních cen
        current_prices = get_current_prices(unique_tickers)
        
        # Agregace pozic
        positions_df = aggregate_positions(st.session_state['original_df'], current_prices)

        if positions_df.empty:
            st.success("Žádné otevřené pozice k analýze. Gratuluji k čistému portfoliu!")
            return

        # Uložení pozic do session_state pro úpravy cen
        if 'positions_df' not in st.session_state:
            st.session_state['positions_df'] = positions_df

        # --- Výpočty celkových metrik ---
        totals = calculate_totals(st.session_state['positions_df'], st.session_state['original_df'])


        # --- 4. Zobrazení metrik (Karty) ---
        st.header("Celkový Přehled Portfolia")
        
        col1, col2, col3, col4 = st.columns(4)

        # Funkce pro vykreslení metrické karty (pro čistší UI)
        def metric_card(col, title, value, prefix='', suffix=' USD', color_threshold=None):
            html = f"""
            <div class="custom-card">
                <div class="custom-card-title">{title}</div>
                <div class="custom-card-value">{prefix}{value:,.2f}{suffix}</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
            
        metric_card(col1, "Tržní Hodnota (Market Value)", totals['current_market_value'])
        metric_card(col2, "Celkové Náklady (Cost Basis)", totals['total_cost_basis'])
        metric_card(col3, "Celkový Nerealizovaný Zisk/Ztráta", totals['total_unrealized_pnl'])
        metric_card(col4, "Celkový Zisk (Realizovaný + Nerealizovaný + Dividendy)", totals['total_profit'])

        st.markdown("---")

        # --- 5. Grafy (Donut Charts) ---
        st.header("Grafické Rozložení")
        
        col_chart1, col_chart2 = st.columns(2)

        # Graf 1: Rozdělení tržní hodnoty podle aktiva
        with col_chart1:
            st.subheader("Tržní Rozložení Podle Aktiva (USD)")
            fig1 = px.pie(
                st.session_state['positions_df'],
                names='Název',
                values='Tržní hodnota (USD)',
                hole=.6,
                title='Tržní Hodnota',
                color_discrete_sequence=px.colors.sequential.Plotly3
            )
            # Nastavení tmavého pozadí pro Plotly
            fig1.update_layout(
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                font_color='#FAFAFA',
                legend_title_text='Aktiva'
            )
            fig1.update_traces(textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)

        # Graf 2: Rozdělení nákladů
        with col_chart2:
            st.subheader("Nákladové Rozložení Podle Aktiva (USD)")
            fig2 = px.pie(
                st.session_state['positions_df'],
                names='Název',
                values='Náklady (USD)',
                hole=.6,
                title='Náklady',
                color_discrete_sequence=px.colors.sequential.Plasma
            )
            # Nastavení tmavého pozadí pro Plotly
            fig2.update_layout(
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                font_color='#FAFAFA',
                legend_title_text='Aktiva'
            )
            fig2.update_traces(textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")

        # --- 6. Tabulka a Manuální úpravy ---
        st.header("Detailní Pozice a Úpravy Cen")
        st.info("Pokud se Aktuální cena (USD) nenačetla, můžete ji ručně zadat do sloupce 'Aktuální cena (USD) - Manuální úprava'.")

        # Příprava DF pro úpravy (zobrazujeme jen relevantní sloupce)
        editable_df = st.session_state['positions_df'][['Název', 'Kusů', 'Průměrná nákupní cena (USD)', 
                                                        'Aktuální cena (USD)', 'Aktuální cena (USD) - Manuální úprava',
                                                        'Náklady (USD)', 'Tržní hodnota (USD)']]
        
        # Nastavení cen z manuální úpravy
        if 'manual_prices' not in st.session_state:
            st.session_state['manual_prices'] = {}
        
        editable_df_filtered = editable_df.copy()

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
            for index, row in st.session_state['positions_df'].iterrows():
                new_price = price_updates.get(row['Název'])
                if new_price is not None and new_price != row['Aktuální cena (USD)']:
                    st.session_state['positions_df'].loc[index, 'Aktuální cena (USD)'] = new_price
            
            st.success("Manuální úpravy byly uloženy. Pro přepočet klikněte na 'Rerun' v pravém horním rohu.")
            st.session_state['positions_df'] = aggregate_positions(st.session_state['original_df'], current_prices)


if __name__ == "__main__":
    main_app()
