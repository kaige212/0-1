import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calc_price_from_input(current_price, value):
    """如果是数字直接返回，否则解析百分比"""
    if isinstance(value, str) and value.endswith("%"):
        pct = float(value.strip("%"))
        return current_price * (1 + pct / 100)
    else:
        return float(value)

def analyze_order(order, capital, leverage=1):
    current_price = order["current_price"]
    stop_loss = order["stop_loss"]
    take_profit = order["take_profit"]
    win_rate = order["win_rate"]
    direction = order["direction"]

    # 计算保证金和持仓规模
    margin = capital / leverage
    position_value = capital * leverage
    position_size = position_value / current_price

    if direction == "多":
        if stop_loss >= current_price or take_profit <= current_price:
            return None
        potential_profit = (take_profit - current_price) * position_size
        potential_loss = (current_price - stop_loss) * position_size
        pct_profit = (take_profit - current_price) / current_price * 100
        pct_loss = (stop_loss - current_price) / current_price * 100
    else:
        if stop_loss <= current_price or take_profit >= current_price:
            return None
        potential_profit = (current_price - take_profit) * position_size
        potential_loss = (stop_loss - current_price) * position_size
        pct_profit = (current_price - take_profit) / current_price * 100
        pct_loss = (stop_loss - current_price) / current_price * 100

    if potential_loss == 0:
        return None

    profit_loss_ratio = abs(potential_profit / potential_loss)
    expected_val = win_rate * potential_profit - (1 - win_rate) * potential_loss

    return {
        "方向": direction,
        "开仓价": current_price,
        "止盈价": take_profit,
        "止损价": stop_loss,
        "盈亏比": profit_loss_ratio,
        "潜在盈利": potential_profit,
        "潜在亏损": potential_loss,
        "止盈幅度%": pct_profit,
        "止损幅度%": pct_loss,
        "保证金": capital,  # 本金就是保证金
        "持仓规模": position_value,
        "杠杆": leverage,
        "胜率": win_rate,
        "期望收益": expected_val
    }

def plot_heatmap(orders_data):
    win_rates = np.linspace(0.01, 0.99, 100)
    profit_loss_ratios = np.linspace(0.01, 5.0, 100)
    X, Y = np.meshgrid(win_rates, profit_loss_ratios)
    
    Z = X * Y - (1 - X)
    
    fig = make_subplots(rows=1, cols=1)
    
    fig.add_trace(go.Contour(
        z=Z,
        x=win_rates*100,
        y=profit_loss_ratios,
        colorscale="RdYlGn",
        contours=dict(showlines=False),
        coloraxis="coloraxis",
        showscale=True,
        opacity=0.7
    ))
    
    # 盈亏平衡线
    breakeven_x = np.linspace(1, 99, 100)
    breakeven_y = (1 - breakeven_x/100) / (breakeven_x/100)
    breakeven_y = np.clip(breakeven_y, 0, 5)
    
    fig.add_trace(go.Scatter(
        x=breakeven_x,
        y=breakeven_y,
        mode="lines",
        line=dict(color="black", width=3, dash="dash"),
        name="盈亏平衡线",
        hoverinfo="skip"
    ))
    
    # 添加订单标记
    for idx, row in orders_data.iterrows():
        color = "green" if row["方向"]=="多" else "red"
        hover_text = (
            f"订单 {idx+1}<br>"
            f"方向: {row['方向']}<br>"
            f"开仓价: {row['开仓价']:.2f}<br>"
            f"止盈价: {row['止盈价']:.2f}<br>"
            f"止损价: {row['止损价']:.2f}<br>"
            f"胜率: {row['胜率']:.2%}<br>"
            f"盈亏比: {row['盈亏比']:.2f}<br>"
            f"期望收益: {row['期望收益']:.2f}<br>"
            f"潜在盈利: {row['潜在盈利']:.2f}<br>"
            f"潜在亏损: {row['潜在亏损']:.2f}<br>"
            f"止盈幅度: {row['止盈幅度%']:.2f}%<br>"
            f"止损幅度: {row['止损幅度%']:.2f}%<br>"
            f"保证金: {row['保证金']:.2f}<br>"
            f"持仓规模: {row['持仓规模']:.2f}<br>"
            f"杠杆: {row['杠杆']}x"
        )
        
        fig.add_trace(go.Scatter(
            x=[row["胜率"]*100],
            y=[row["盈亏比"]],
            mode="markers+text",
            text=[f"{idx+1}"],
            textposition="top center",
            marker=dict(
                size=15,
                color=color,
                line=dict(width=2, color="black")
            ),
            name=f"{row['方向']} {idx+1}",
            hovertext=hover_text,
            hoverinfo="text"
        ))

    fig.update_layout(
        title={
            'text': "期望值热力图 + 订单标记",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="胜率 (%)",
        yaxis_title="盈亏比",
        legend_title="订单类型",
        width=900,
        height=700,
        autosize=False,
        coloraxis_colorbar=dict(
            title="期望值",
            x=-0.2,
            y=0.5,
            xanchor='left',
            yanchor='middle'
        )
    )
    
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(range=[0, 5])
    
    fig.show()

def analyze_trading_orders(capital, leverage, orders_input):
    """
    分析交易订单的主函数
    
    参数:
    capital: 本金/保证金金额
    leverage: 杠杆倍数
    orders_input: 订单列表，格式为 [方向, 胜率, 当前价格, 止盈, 止损]
    """
    # 转换成字典列表
    orders = []
    for o in orders_input:
        orders.append({
            "direction": o[0],
            "win_rate": o[1],
            "current_price": o[2],
            "take_profit": calc_price_from_input(o[2], o[3]),
            "stop_loss": calc_price_from_input(o[2], o[4])
        })

    # 分析订单
    results = []
    for order in orders:
        res = analyze_order(order, capital, leverage)
        if res:
            results.append(res)

    if results:
        df = pd.DataFrame(results)
        pd.set_option('display.float_format', '{:.2f}'.format)
        print("订单分析结果:")
        display(df)
        
        plot_heatmap(df)
        return df
    else:
        print("没有有效的订单数据")
        return None

'''
if __name__ == "__main__":
    # 只需要设置这些参数即可调用
    capital = 100.0  # 本金
    leverage = 20
    orders_input = [
        ["多", 0.6, 4420, "3%", "-8.7%"],
        ["空", 0.5, 4420, 4000, 5000],
        ["多", 0.5, 4420, 5000, "-4%"],
    ]
    
    # 调用主函数进行分析
    result_df = analyze_trading_orders(capital, leverage, orders_input)
'''
