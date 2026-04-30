import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 EDGE INSTITUCIONAL V4")
st.write("Comparador automático: Gain 6% vs 8% + confirmação semanal")

# =========================
# CONFIG
# =========================
ativos = [
    "PETR4","VALE3","BBAS3","ITUB4","BBDC4","WEGE3","PRIO3","RENT3",
"ELET3","ELET6","CPLE6","CMIG4","TAEE11","EGIE3","VIVT3","TIMS3",
"ABEV3","RADL3","SUZB3","GGBR4","GOAU4","USIM5","CSNA3","RAIL3",
"SBSP3","EQTL3","HYPE3","MULT3","LREN3","ARZZ3","TOTS3","EMBR3",
"JBSS3","BEEF3","MRFG3","BRFS3","SLCE3","SMTO3","B3SA3","BBSE3",
"BPAC11","SANB11","ITSA4","BRSR6","CXSE3","POMO4","STBP3","TUPY3",
"DIRR3","CYRE3","EZTC3","JHSF3","KEPL3","POSI3","MOVI3","PETZ3",
"COGN3","YDUQ3","MGLU3","NTCO3","AZUL4","GOLL4","CVCB3","RRRP3",
"RECV3","ENAT3","ORVR3","AURE3","ENEV3","UGPA3","CMIG4",

"BOVA11","IVVB11","SMAL11","HASH11","GOLD11","DIVO11","NDIV11",

"HGLG11","XPLG11","VISC11","MXRF11","KNRI11","KNCR11","KNIP11",
"CPTS11","IRDM11","TRXF11","TGAR11","HGRU11","ALZR11","IEEX11",
"UTLL11",

"AAPL34","AMZO34","GOGL34","MSFT34","TSLA34","META34","NFLX34",
"NVDC34","MELI34","BABA34","DISB34","PYPL34","JNJB34","VISA34",
"WMTB34","NIKE34","ADBE34","CSCO34","INTC34","JPMC34","ORCL34",
"QCOM34","SBUX34","TXN34","ABTT34","AMGN34","AXPB34","BERK34",

"C2OL34"
]

STOP = 0.05
GAINS = [0.06, 0.08]

# =========================
# FUNÇÕES
# =========================

def calcular_indicadores(df):
    df["EMA69"] = EMAIndicator(close=df["Close"], window=69).ema_indicator()

    adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14)
    df["DI+"] = adx.adx_pos()
    df["DI-"] = adx.adx_neg()
    df["ADX"] = adx.adx()

    stoch = StochasticOscillator(
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        window=14,
        smooth_window=3
    )
    df["%K"] = stoch.stoch()
    df["%D"] = stoch.stoch_signal()

    return df


def resample_semanal(df):
    semanal = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

    return calcular_indicadores(semanal)


def condicao(df):
    u = df.iloc[-1]
    return (
        u["Close"] > u["EMA69"] and
        u["DI+"] > u["DI-"] and
        u["%K"] > u["%D"]
    )


def backtest(df, gain):
    ganhos, perdas, total = 0, 0, 0

    for i in range(70, len(df) - 10):
        linha = df.iloc[i]

        cond = (
            linha["Close"] > linha["EMA69"] and
            linha["DI+"] > linha["DI-"] and
            linha["%K"] > linha["%D"]
        )

        if cond:
            entrada = linha["Close"]
            future = df.iloc[i+1:i+10]

            for _, row in future.iterrows():
                if row["High"] >= entrada * (1 + gain):
                    ganhos += 1
                    break
                if row["Low"] <= entrada * (1 - STOP):
                    perdas += 1
                    break
            else:
                perdas += 1

            total += 1

    if total == 0:
        return 0, 0, 0

    prob_gain = ganhos / total
    prob_loss = perdas / total
    edge = prob_gain - prob_loss

    return prob_gain, prob_loss, edge


def score(prob_gain, edge, adx):
    forca = min(adx / 50, 1)
    return (prob_gain * 0.5) + (edge * 0.3) + (forca * 0.2)


# =========================
# EXECUÇÃO
# =========================

resultado = []
progress = st.progress(0)

for i, ativo in enumerate(ativos):
    try:
        df = yf.download(ativo, period="2y", interval="1d")

        if df.empty:
            continue

        df = calcular_indicadores(df)
        semanal = resample_semanal(df)

        if not condicao(df):
            continue

        if not condicao(semanal):
            continue

        adx_atual = df.iloc[-1]["ADX"]

        cenarios = []

        for g in GAINS:
            prob_gain, prob_loss, edge = backtest(df, g)
            sc = score(prob_gain, edge, adx_atual)

            cenarios.append({
                "gain": int(g*100),
                "prob_gain": prob_gain,
                "prob_loss": prob_loss,
                "edge": edge,
                "score": sc
            })

        melhor = max(cenarios, key=lambda x: x["score"])

        resultado.append({
            "Ativo": ativo.replace(".SA",""),
            "Melhor Gain (%)": melhor["gain"],
            "Prob Gain (%)": round(melhor["prob_gain"] * 100, 2),
            "Prob Loss (%)": round(melhor["prob_loss"] * 100, 2),
            "Edge": round(melhor["edge"], 4),
            "Score": round(melhor["score"], 4),
            "ADX": round(adx_atual, 2),
            "Gain 6 Score": round(cenarios[0]["score"], 4),
            "Gain 8 Score": round(cenarios[1]["score"], 4)
        })

    except:
        continue

    progress.progress((i + 1) / len(ativos))

df_result = pd.DataFrame(resultado)

if not df_result.empty:
    df_result = df_result.sort_values(by="Score", ascending=False)
    st.dataframe(df_result, use_container_width=True)
else:
    st.warning("Nenhuma oportunidade encontrada com confirmação semanal.")

st.write("⏱ Atualizado em:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
