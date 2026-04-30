import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 EDGE INSTITUCIONAL V5.6")
st.write("Sistema completo: setup + expectativa real + confirmação semanal + ranking")

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
"RECV3","ENAT3","ORVR3","AURE3","ENEV3","UGPA3",

"BOVA11","IVVB11","SMAL11","HASH11","GOLD11","DIVO11","NDIV11",

"HGLG11","XPLG11","VISC11","MXRF11","KNRI11","KNCR11","KNIP11",
"CPTS11","IRDM11","TRXF11","TGAR11","HGRU11","ALZR11","AUVP11",
"IEEX11","UTLL11", 

"AAPL34","AMZO34","GOGL34","MSFT34","TSLA34","META34","NFLX34",
"NVDC34","MELI34","BABA34","DISB34","PYPL34","JNJB34","VISA34",
"WMTB34","NIKE34","ADBE34","CSCO34","INTC34","JPMC34","ORCL34",
"QCOM34","SBUX34","TXN34","ABTT34","AMGN34","AXPB34","BERK34",

"C2OL34"
]

STOP = 0.05
JANELA = 20

# =========================
# TRATAMENTO DE DADOS
# =========================
def preparar_dados(df):
    df = df.copy()

    if df.empty:
        return df

    try:
        df.index = df.index.tz_localize(None)
    except:
        pass

    df = df[~df.index.duplicated()]
    df = df.dropna()

    return df

# =========================
# INDICADORES
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

    return df.dropna()

# =========================
# SEMANAL
# =========================
def gerar_semanal(df):
    semanal = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

    return calcular_indicadores(semanal)

# =========================
# SCORE TÉCNICO
# =========================
def score_setup(df_d, df_w):
    d = df_d.iloc[-1]
    w = df_w.iloc[-1]

    score = 0

    # Diário
    if d["Close"] > d["EMA69"]: score += 2
    if d["DI+"] > d["DI-"]: score += 2
    if d["%K"] > d["%D"]: score += 1

    # Semanal
    if w["Close"] > w["EMA69"]: score += 2
    if w["DI+"] > w["DI-"]: score += 2
    if w["%K"] > w["%D"]: score += 1

    return score

# =========================
# BACKTEST REALISTA
# =========================
def backtest_realista(df):
    retornos = []
    tempos = []
    wins = 0

    if len(df) < 100:
        return 0, 0, 0

    for i in range(70, len(df) - JANELA):
        linha = df.iloc[i]

        # leve filtro de tendência
        if linha["Close"] > linha["EMA69"]:

            entrada = linha["Close"]
            futuro = df.iloc[i+1:i+1+JANELA]

            if futuro.empty:
                continue

            max_price = futuro["High"].max()
            min_price = futuro["Low"].min()

            retorno = (max_price - entrada) / entrada
            drawdown = (min_price - entrada) / entrada

            # aplica stop
            if drawdown <= -STOP:
                retorno = -STOP

            if retorno > 0:
                wins += 1

            retornos.append(retorno)

            # tempo até topo
            idx = futuro["High"].idxmax()
            tempo = futuro.index.get_loc(idx) + 1
            tempos.append(tempo)

    if len(retornos) == 0:
        return 0, 0, 0

    expectativa = np.mean(retornos)
    win_rate = wins / len(retornos)
    tempo_medio = np.mean(tempos)

    return expectativa, win_rate, tempo_medio

# =========================
# EXECUÇÃO
# =========================
resultados = []
progress = st.progress(0)

for i, ativo in enumerate(ativos):
    try:
        df = yf.download(ativo, period="2y", interval="1d", progress=False)

        if df.empty:
            continue

        df = preparar_dados(df)

        if len(df) < 100:
            continue

        df = calcular_indicadores(df)
        df_w = gerar_semanal(df)

        if df_w.empty or len(df_w) < 20:
            continue

        expectativa, win_rate, tempo = backtest_realista(df)
        score_tec = score_setup(df, df_w)

        adx = df.iloc[-1]["ADX"]

        # SCORE FINAL (NÃO BLOQUEIA)
        score_final = (
            (expectativa * 0.4) +
            (win_rate * 0.2) +
            ((score_tec / 10) * 0.2) +
            ((1 / (tempo + 1)) * 0.1) +
            ((adx / 50) * 0.1)
        )

        resultados.append({
            "Ativo": ativo.replace(".SA",""),
            "Score Setup": score_tec,
            "Expectativa": round(expectativa, 4),
            "Win Rate (%)": round(win_rate * 100, 2),
            "Tempo Médio": round(tempo, 1),
            "ADX": round(adx, 2),
            "Score Final": round(score_final, 4)
        })

    except:
        continue

    progress.progress((i + 1) / len(ativos))

df_res = pd.DataFrame(resultados)

if not df_res.empty:
    df_res = df_res.sort_values(by="Score Final", ascending=False)
    st.dataframe(df_res, use_container_width=True)
else:
    st.warning("⚠️ Nenhum ativo com dados suficientes ou consistentes.")

st.write("⏱ Atualizado em:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

