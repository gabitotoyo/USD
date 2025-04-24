from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

app = Flask(__name__)

# Configuración API
API_BASE = "https://api.cambiocuba.money/api/v1/x-rates-by-date-range-history"
PARAMS = {
    "trmi": "true",
    "cur": "USD",
    "date_from": "2021-01-01 00:00:00"
}

def obtener_datos_actuales():
    """Obtiene y procesa datos de la API"""
    try:
        fecha_hasta = datetime.now().strftime("%Y-%m-%d 23:59:59")
        params = {**PARAMS, "date_to": fecha_hasta}
        response = requests.get(API_BASE, params=params)
        response.raise_for_status()
        datos = response.json()
        return procesar_datos_crudos(datos)
    except Exception as e:
        print(f"Error API: {e}")
        return pd.DataFrame()

def procesar_datos_crudos(datos_api):
    """Procesa datos crudos"""
    registros = []
    for item in datos_api:
        try:
            fecha = item.get("_id", "")
            median = str(item.get("median", "")).split("JS:")[0].strip()
            registros.append({
                "Fecha": pd.to_datetime(fecha),
                "CUPs": float(median) if median.replace('.','',1).isdigit() else None
            })
        except (ValueError, AttributeError):
            continue
    
    if registros:
        df = pd.DataFrame(registros).sort_values('Fecha')
        df.set_index('Fecha', inplace=True)
        return df
    return pd.DataFrame()

def calcular_indicadores(df):
    """Calcula indicadores técnicos"""
    if df.empty:
        return df
    
    # Medias móviles
    df['SMA30'] = df['CUPs'].rolling(30, min_periods=1).mean()
    df['SMA200'] = df['CUPs'].rolling(200, min_periods=1).mean()
    
    # RSI
    delta = df['CUPs'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14, min_periods=1).mean()
    avg_loss = loss.rolling(14, min_periods=1).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['CUPs'].ewm(span=12, adjust=False).mean()
    ema26 = df['CUPs'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands
    df['SMA20'] = df['CUPs'].rolling(20).mean()
    df['UpperBB'] = df['SMA20'] + (2 * df['CUPs'].rolling(20).std())
    df['LowerBB'] = df['SMA20'] - (2 * df['CUPs'].rolling(20).std())
    
    # Señales de trading
    df['Cruce'] = np.where(df['SMA30'] > df['SMA200'], 1, -1)
    df['Señal'] = df['Cruce'].diff()
    
    return df.dropna()

def generar_grafico_plotly(df):
    """Crea gráficos interactivos con Plotly"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(
            "Precio y Bandas de Bollinger", 
            "RSI", 
            "MACD", 
            "Volatilidad"
        ),
        row_heights=[0.5, 0.2, 0.2, 0.1]
    )
    
    # Gráfico principal
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['CUPs'],
            name="Precio",
            line=dict(color='#1f77b4')
        ),
        row=1, col=1
    )
    
    # Bandas de Bollinger
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['UpperBB'],
            name="Banda Superior",
            line=dict(color='rgba(255, 0, 0, 0.3)', width=1),
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['LowerBB'],
            name="Banda Inferior",
            line=dict(color='rgba(0, 255, 0, 0.3)', width=1),
            fill='tonexty',
            fillcolor='rgba(100, 100, 100, 0.1)',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Medias móviles
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['SMA30'],
            name="SMA 30",
            line=dict(dash='dot', color='orange')
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['SMA200'],
            name="SMA 200",
            line=dict(dash='dot', color='purple')
        ),
        row=1, col=1
    )
    
    # Señales de compra/venta
    compras = df[df['Señal'] == 2]
    ventas = df[df['Señal'] == -2]
    
    if not compras.empty:
        fig.add_trace(
            go.Scatter(
                x=compras.index,
                y=compras['CUPs'],
                mode='markers',
                name='Compra',
                marker=dict(
                    symbol='triangle-up',
                    color='green',
                    size=17
                )
            ),
            row=1, col=1
        )
    
    if not ventas.empty:
        fig.add_trace(
            go.Scatter(
                x=ventas.index,
                y=ventas['CUPs'],
                mode='markers',
                name='Venta',
                marker=dict(
                    symbol='triangle-down',
                    color='red',
                    size=17
                )
            ),
            row=1, col=1
        )
    
    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['RSI'],
            name="RSI",
            line=dict(color='#ff7f0e')
        ),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
    
    # MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MACD'],
            name="MACD",
            line=dict(color='#2ca02c')
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Signal'],
            name="Señal",
            line=dict(color='#d62728')
        ),
        row=3, col=1
    )
    
    # Volatilidad
    volatilidad = df['CUPs'].pct_change().abs() * 100
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=volatilidad,
            name="Volatilidad",
            marker_color='#17becf'
        ),
        row=4, col=1
    )
    
    fig.update_layout(
        height=1000,
        title_text=" ",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=100)
    )
    
    return fig.to_html(full_html=False)

@app.route("/")
def home():
    """Endpoint principal: muestra el gráfico"""
    df = obtener_datos_actuales()
    if not df.empty:
        try:
            df = calcular_indicadores(df)
            if df.empty:
                return render_template("index.html", grafico="<p>No hay datos suficientes</p>")
            grafico = generar_grafico_plotly(df)
            return render_template("index.html", grafico=grafico)
        except Exception as e:
            print(f"Error generando gráfico: {str(e)}")
            return render_template("index.html", grafico="<p>Error interno</p>")
    return render_template("index.html", grafico="<p>Error cargando datos</p>")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
