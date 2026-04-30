import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 EDGE INSTITUCIONAL V6.1")
st.write("Probabilidade real + robustez de dados + fallback completo")

# =========================
# LISTA COMPLETA (SUA)
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
# PREPARAÇÃO
# =========================
def preparar(df):
    df = df.copy()

    if df.empty:
        return df

    try:
        df.index = df.index.tz_localize(None)
    except:
        pass

    df = df[~df.index.duplicated()]
    df = df.ffill().bfill()

    return df

# =========================
# INDICADORES
# =========================
def indicadores(df):
    try:
        df["EMA69"] = EMAIndicator(df["Close"], 69).ema_indicator()

        adx = ADXIndicator(df["High"], df["Low"], df["Close"], 14)
        df["DI+"] = adx.adx_pos()
        df["DI-"] = adx.adx_neg()
        df["ADX"] = adx.adx()

        stoch = StochasticOscillator(df["High"], df["Low"], df["Close"], 14, 3)
        df["%K"] = stoch.stoch()
        df["%D"] = stoch.stoch_signal()

        return df.ffill().bfill()

    except Exception as e:
        return pd.DataFrame()

# =========================
# PROBABILIDADE
# =========================
def probabilidade(df, gain):
    ganhos = 0
    perdas = 0

    for i in range(70, len(df) - JANELA):
        entry = df.iloc[i]["Close"]
        future = df.iloc[i+1:i+1+JANELA]

        for _, row in future.iterrows():
            if row["High"] >= entry * (1 + gain):
                ganhos += 1
                break

            if row["Low"] <= entry * (1 - STOP):
                perdas += 1
                break

    total = ganhos + perdas

    if total == 0:
        return 0

    return ganhos / total

# =========================
# SCORE
# =========================
def score(df):
    try:
        u = df.iloc[-1]
        s = 0

        if u["Close"] > u["EMA69"]: s += 2
        if u["DI+"] > u["DI-"]: s += 2
        if u["%K"] > u["%D"]: s += 1

        return s
    except:
        return 0

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
            erros.append(f"{ativo} - vazio")
            continue

        df = preparar(df)

        if len(df) < 100:
            erros.append(f"{ativo} - poucos dados")
            continue

        df = indicadores(df)

        if df.empty:
            erros.append(f"{ativo} - erro indicadores")
            continue

        prob6 = probabilidade(df, GAIN6)
        prob8 = probabilidade(df, GAIN8)

        melhor = max(prob6, prob8)

        sc = score(df)
        adx = df.iloc[-1]["ADX"] if "ADX" in df.columns else 0

        score_final = (
            (melhor * 0.5) +
            ((sc / 5) * 0.3) +
            ((adx / 50) * 0.2)
        )

        res.append({
            "Ativo": ativo.replace(".SA",""),
            "Prob 6%": round(prob6*100,2),
            "Prob 8%": round(prob8*100,2),
            "Melhor (%)": round(melhor*100,2),
            "Score Tec": sc,
            "ADX": round(adx,2),
            "Score Final": round(score_final,4)
        })

    except Exception as e:
        erros.append(f"{ativo} - erro geral")

    progress.progress((i+1)/len(ativos))

df_res = pd.DataFrame(res)

# =========================
# OUTPUT
# =========================
if not df_res.empty:
    df_res = df_res.sort_values(by="Score Final", ascending=False)
    st.dataframe(df_res, use_container_width=True)
else:
    st.error("Nenhum ativo processado com sucesso.")

# LOG DE ERROS (IMPORTANTE)
with st.expander("🔍 Ver erros de dados"):
    for e in erros[:50]:
        st.write(e)

st.write("⏱ Atualizado em:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
