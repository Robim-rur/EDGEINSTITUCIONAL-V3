import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 EDGE INSTITUCIONAL V6.2")
st.write("Correção definitiva de dados + probabilidade real")

# =========================
# LISTA (SUA)
# =========================
ativos = [
"PETR4.SA","VALE3.SA","BBAS3.SA","ITUB4.SA","BBDC4.SA","WEGE3.SA","PRIO3.SA","RENT3.SA",
"ELET3.SA","ELET6.SA","CPLE6.SA","CMIG4.SA","TAEE11.SA","EGIE3.SA","VIVT3.SA","TIMS3.SA",
"ABEV3.SA","RADL3.SA","SUZB3.SA","GGBR4.SA","GOAU4.SA","USIM5.SA","CSNA3.SA","RAIL3.SA",
"SBSP3.SA","EQTL3.SA","HYPE3.SA","MULT3.SA","LREN3.SA","ARZZ3.SA","TOTS3.SA","EMBR3.SA",
"JBSS3.SA","BEEF3.SA","MRFG3.SA","BRFS3.SA","SLCE3.SA","SMTO3.SA","B3SA3.SA","BBSE3.SA",
"BPAC11.SA","SANB11.SA","ITSA4.SA","BRSR6.SA","CXSE3.SA","POMO4.SA","STBP3.SA","TUPY3.SA",
"DIRR3.SA","CYRE3.SA","EZTC3.SA","JHSF3.SA","KEPL3.SA","POSI3.SA","MOVI3.SA","PETZ3.SA",
"COGN3.SA","YDUQ3.SA","MGLU3.SA","NTCO3.SA","AZUL4.SA","GOLL4.SA","CVCB3.SA","RRRP3.SA",
"RECV3.SA","ENAT3.SA","ORVR3.SA","AURE3.SA","ENEV3.SA","UGPA3.SA",

"BOVA11.SA","IVVB11.SA","SMAL11.SA","HASH11.SA","GOLD11.SA","DIVO11.SA","NDIV11.SA",

"HGLG11.SA","XPLG11.SA","VISC11.SA","MXRF11.SA","KNRI11.SA","KNCR11.SA","KNIP11.SA",
"CPTS11.SA","IRDM11.SA","TRXF11.SA","TGAR11.SA","HGRU11.SA","ALZR11.SA","AUVP11.SA",
"IEEX11.SA","UTLL11.SA",

"AAPL34.SA","AMZO34.SA","GOGL34.SA","MSFT34.SA","TSLA34.SA","META34.SA","NFLX34.SA",
"NVDC34.SA","MELI34.SA","BABA34.SA","DISB34.SA","PYPL34.SA","JNJB34.SA","VISA34.SA",
"WMTB34.SA","NIKE34.SA","ADBE34.SA","CSCO34.SA","INTC34.SA","JPMC34.SA","ORCL34.SA",
"QCOM34.SA","SBUX34.SA","TXN34.SA","ABTT34.SA","AMGN34.SA","AXPB34.SA","BERK34.SA",

"C2OL34.SA"
]

STOP = 0.05
GAIN6 = 0.06
GAIN8 = 0.08
JANELA = 20

# =========================
# NORMALIZAÇÃO (CRÍTICO)
# =========================
def normalizar(df):
    if df.empty:
        return df

    df = df.copy()

    # remove multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # garante colunas padrão
    df = df.rename(columns={
        "Adj Close": "Close"
    })

    colunas = ["Open","High","Low","Close","Volume"]

    for c in colunas:
        if c not in df.columns:
            return pd.DataFrame()

    df = df[colunas]

    # força tipo float
    df = df.astype(float)

    df = df.ffill().bfill()

    return df

# =========================
# INDICADORES (AGORA FUNCIONA)
# =========================
def indicadores(df):
    df["EMA69"] = EMAIndicator(df["Close"], 69).ema_indicator()

    adx = ADXIndicator(df["High"], df["Low"], df["Close"], 14)
    df["DI+"] = adx.adx_pos()
    df["DI-"] = adx.adx_neg()
    df["ADX"] = adx.adx()

    stoch = StochasticOscillator(df["High"], df["Low"], df["Close"], 14, 3)
    df["%K"] = stoch.stoch()
    df["%D"] = stoch.stoch_signal()

    return df.dropna()

# =========================
# PROBABILIDADE
# =========================
def probabilidade(df, gain):
    g, l = 0, 0

    for i in range(70, len(df) - JANELA):
        entry = df.iloc[i]["Close"]
        fut = df.iloc[i+1:i+1+JANELA]

        for _, row in fut.iterrows():
            if row["High"] >= entry * (1 + gain):
                g += 1
                break
            if row["Low"] <= entry * (1 - STOP):
                l += 1
                break

    total = g + l
    return g / total if total > 0 else 0

# =========================
# EXECUÇÃO
# =========================
res = []
erros = []

progress = st.progress(0)

for i, ativo in enumerate(ativos):
    try:
        df = yf.download(ativo, period="2y", interval="1d", progress=False)

        if df.empty:
            erros.append(f"{ativo} vazio")
            continue

        df = normalizar(df)

        if df.empty or len(df) < 100:
            erros.append(f"{ativo} dados inválidos")
            continue

        df = indicadores(df)

        if df.empty:
            erros.append(f"{ativo} indicadores falharam")
            continue

        p6 = probabilidade(df, GAIN6)
        p8 = probabilidade(df, GAIN8)

        res.append({
            "Ativo": ativo.replace(".SA",""),
            "Prob 6%": round(p6*100,2),
            "Prob 8%": round(p8*100,2),
            "Melhor": round(max(p6,p8)*100,2)
        })

    except Exception as e:
        erros.append(f"{ativo} erro geral")

    progress.progress((i+1)/len(ativos))

df_res = pd.DataFrame(res)

if not df_res.empty:
    st.dataframe(df_res.sort_values(by="Melhor", ascending=False), use_container_width=True)
else:
    st.error("Nenhum ativo processado — verificar logs")

with st.expander("Logs"):
    for e in erros[:50]:
        st.write(e)

st.write("⏱ Atualizado em:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
