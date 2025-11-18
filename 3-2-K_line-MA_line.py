import os
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import Dash, dcc, html, Input, Output, State

# ===============================
# 1. 基本路径设置
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "each_code_k_data")
CODES_FILE = os.path.join(BASE_DIR, "data", "Ashare_codes_all.csv")

if not os.path.exists(DATA_DIR):
    raise FileNotFoundError(f"未找到数据目录：{DATA_DIR}")

# ===============================
# 2. MA 设置（斐波那契均线）
# ===============================
MA_WINDOWS = [3, 5, 8, 13, 21, 34, 55]

def add_ma(df, windows=MA_WINDOWS):
    for w in windows:
        df[f"MA{w}"] = df["close"].rolling(w).mean()
    return df

# ===============================
# 3. 读取本地股票数据
# ===============================
def load_local_stock_data(symbol: str):
    files = [f for f in os.listdir(DATA_DIR)
             if f.startswith(f"Ashare_{symbol}_") and f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"未找到股票 {symbol} 的数据文件")
    filepath = os.path.join(DATA_DIR, files[0])
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df, files[0]

# ===============================
# 4. 数据周期聚合
# ===============================
def resample_k_data(df, period="daily"):
    if period == "daily":
        return df.copy()
    
    df_resampled = df.set_index("date").copy()
    
    if period == "weekly":
        df_resampled = df_resampled.resample("W-FRI").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index()
    elif period == "monthly":
        df_resampled = df_resampled.resample("ME").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index()
    
    return df_resampled

# ===============================
# 5. 绘制 K线 + MA + 成交量
# ===============================
def create_kline_ma_figure(df, symbol: str, stock_name: str = "😊"):
    fig = go.Figure()

    # --- K线 ---
    hover_texts = [
        f"日期: {d.strftime('%Y-%m-%d')}<br>开盘: {o}<br>最高: {h}<br>最低: {l}<br>收盘: {c}"
        for d, o, h, l, c in zip(df["date"], df["open"], df["high"], df["low"], df["close"])
    ]

    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线",
        increasing_line_color='red',
        decreasing_line_color='green',
        hoverinfo='text',
        hovertext=hover_texts
    ))

    # --- 均线 ---
    for col in [f"MA{w}" for w in MA_WINDOWS]:
        y = df[col] if col in df.columns else [None] * len(df)
        fig.add_trace(go.Scatter(
            x=df["date"], y=y, name=col, mode='lines',
            hovertemplate=f'{col}: %{{y:.2f}}<extra></extra>'
        ))

    # --- 成交量柱状图 ---
    if "volume" in df.columns:
        colors = ["red" if o < c else "green" for o, c in zip(df["open"], df["close"])]
        fig.add_trace(go.Bar(
            x=df["date"],
            y=df["volume"],
            name="成交量",
            marker_color=colors,
            opacity=0.3,
            yaxis="y2"
        ))

    # --- 布局 ---
    fig.update_layout(
        title=f"{symbol} {stock_name} K线 + 均线 + 成交量",
        template="plotly_white",
        height=850,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(domain=[0, 1]),
        yaxis=dict(title="价格", side="right", showgrid=True, zeroline=False),
        yaxis2=dict(
            title="成交量",
            overlaying="y",
            side="left",
            showgrid=False,
            range=[0, df["volume"].max() * 5] if "volume" in df.columns else None
        ),
        xaxis_rangeslider_visible=False
    )
    return fig

# ===============================
# 6. Dash 页面布局
# ===============================
app = Dash(__name__)
app.title = "A股本地K线浏览器"

app.layout = html.Div([
    html.H2("📈 本地 A股 K线 可视化", style={"textAlign": "center"}),

    html.Div([
        dcc.Input(
            id="stock-code",
            type="text",
            placeholder="输入股票代码（如 000001）",
            value="000007",
            style={"width": "200px", "marginRight": "10px"}
        ),
        html.Button("清空", id="clear-btn", n_clicks=0),
    ], style={"textAlign": "center", "marginBottom": "10px"}),

    # 周期按钮
    html.Div([
        html.Button("日 K", id="btn-daily", n_clicks=0, style={"marginRight": "10px"}),
        html.Button("周 K", id="btn-weekly", n_clicks=0, style={"marginRight": "10px"}),
        html.Button("月 K", id="btn-monthly", n_clicks=0),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    html.Div(id="file-info", style={"textAlign": "center", "marginBottom": "10px", "color": "#555"}),

    dcc.Graph(id="kline-graph"),

    html.Pre(
        id="hover-info",
        style={
            "textAlign": "left",
            "margin": "20px auto",
            "width": "90%",
            "background": "#f8f8f8",
            "padding": "10px",
            "borderRadius": "8px",
            "fontFamily": "monospace"
        }
    ),

    dcc.Store(id="selected-period", data="daily")  # 默认日K
])

# ===============================
# 7. 清空输入框功能
# ===============================
@app.callback(
    Output("stock-code", "value"),
    Input("clear-btn", "n_clicks")
)
def clear_input(n_clicks):
    if n_clicks and n_clicks > 0:
        return ""
    return "000007"

# ===============================
# 8. 周期按钮选择（使用callback_context确定最后点击按钮）
# ===============================
@app.callback(
    Output("selected-period", "data"),
    Input("btn-daily", "n_clicks"),
    Input("btn-weekly", "n_clicks"),
    Input("btn-monthly", "n_clicks"),
)
def select_period(daily, weekly, monthly):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "daily"
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id == "btn-daily":
        return "daily"
    elif button_id == "btn-weekly":
        return "weekly"
    elif button_id == "btn-monthly":
        return "monthly"
    return "daily"

# ===============================
# 9. 高亮显示当前选中周期按钮
# ===============================
@app.callback(
    Output("btn-daily", "style"),
    Output("btn-weekly", "style"),
    Output("btn-monthly", "style"),
    Input("selected-period", "data")
)

def update_button_style(period):
    default_style = {"marginRight": "10px"}
    selected_style = {"marginRight": "10px", "backgroundColor": "#4CAF50", "color": "white"}
    return (
        selected_style if period=="daily" else default_style,
        selected_style if period=="weekly" else default_style,
        selected_style if period=="monthly" else default_style
    )



# ===============================
# 10. 更新图表
# ===============================
@app.callback(
    Output("kline-graph", "figure"),
    Output("file-info", "children"),
    Input("stock-code", "value"),
    Input("selected-period", "data")
)
def update_chart(symbol, period):
    if not symbol:
        return go.Figure(), "请输入股票代码。"

    symbol = symbol.strip().zfill(6)

    # 获取股票名称
    stock_name = "😊"
    if os.path.exists(CODES_FILE):
        try:
            codes_df = pd.read_csv(CODES_FILE, dtype=str)
            match = codes_df[codes_df["code"] == symbol]
            if not match.empty:
                stock_name = match.iloc[0]["name"]
        except:
            stock_name = "😊"

    try:
        df, filename = load_local_stock_data(symbol)
        df = resample_k_data(df, period)
        df = add_ma(df)
        fig = create_kline_ma_figure(df, symbol, stock_name)
        return fig, f"✅ 数据文件：{filename} （周期: {period}, 共 {len(df)} 行）"
    except Exception as e:
        return go.Figure(), f"⚠️ 加载失败：{e}"

# ===============================
# 11. 悬停显示数据
# ===============================
@app.callback(
    Output("hover-info", "children"),
    Input("kline-graph", "hoverData"),
    State("stock-code", "value"),
    State("selected-period", "data")
)
def display_hover(hoverData, symbol, period):
    if not hoverData or "points" not in hoverData:
        return html.Div("😊 等待鼠标悬停显示数据", style={"textAlign": "center", "color": "#777"})
    try:
        if not symbol:
            return html.Div("😊 无股票代码", style={"textAlign": "center"})
        sym = symbol.strip().zfill(6)
        df, _ = load_local_stock_data(sym)
        df = resample_k_data(df, period)
        df = add_ma(df)
    except Exception as e:
        return html.Div(f"😊 无法加载本地数据：{e}", style={"textAlign": "center"})

    try:
        points = hoverData["points"]
        point_index = next((p.get("pointIndex") for p in points if "pointIndex" in p), None)
        if point_index is None or point_index < 0 or point_index >= len(df):
            return html.Div("😊 无法定位悬停点", style={"textAlign": "center"})

        row = df.iloc[int(point_index)]

        def safe(val, fmt="{:.2f}"):
            if pd.isna(val):
                return "—"
            try:
                return fmt.format(val) if isinstance(val, (int, float)) else str(val)
            except:
                return str(val)

        date_str = row["date"].strftime("%Y-%m-%d") if not pd.isna(row["date"]) else "—"
        base_fields = [
            ("📅 日期", date_str),
            ("🟢 开盘", safe(row.get("open"))),
            ("🔴 最高", safe(row.get("high"))),
            ("🔵 最低", safe(row.get("low"))),
            ("🟣 收盘", safe(row.get("close"))),
            ("📊 成交量", safe(row.get("volume"), "{:.0f}")),
        ]

        ma_fields = [(f"MA{w}", safe(row.get(f"MA{w}"))) for w in MA_WINDOWS]

        item_style = {"minWidth": "80px", "textAlign": "center", "padding": "0 8px", "whiteSpace": "nowrap"}
        row_style = {"display": "flex", "justifyContent": "center", "alignItems": "center",
                     "flexWrap": "nowrap", "overflowX": "auto", "padding": "4px 10px"}

        base_row = html.Div([html.Div([html.Span(label+": ", style={"color": "#333", "fontWeight": "bold", "marginRight": "4px"}),
                                       html.Span(value, style={"color": "#000"})], style=item_style) for label, value in base_fields], style=row_style)

        ma_row = html.Div([html.Div([html.Span(label+": ", style={"color": "#555", "fontWeight": "bold", "marginRight": "4px"}),
                                     html.Span(value, style={"color": "#000"})], style=item_style) for label, value in ma_fields], style=row_style)

        return html.Div([base_row, ma_row], style={"display": "flex", "flexDirection": "column",
                                                   "alignItems": "center", "justifyContent": "center",
                                                   "background": "#f8f8f8", "borderTop": "1px solid #ccc",
                                                   "padding": "6px 0", "fontFamily": "monospace",
                                                   "fontSize": "14px", "width": "100%"})
    except Exception as e:
        return html.Div(f"😊 数据解析出错：{e}", style={"textAlign": "center"})

# ===============================
# 12. 启动应用
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
