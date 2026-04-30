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
    "PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA",
    "BBAS3.SA","WEGE3.SA","ABEV3.SA","B3SA3.SA",
    "RENT3.SA","EQTL3.SA","PRIO3.SA","RADL3.SA"
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
