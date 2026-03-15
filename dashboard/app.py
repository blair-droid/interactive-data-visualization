import pandas as pd
import numpy as np

from dash import Dash, dcc, html, dash_table, Input, Output
import plotly.express as px
import plotly.graph_objects as go

# =========================
# Load data
# =========================
DATA_PATH = "credit_cards_clean.csv"
df = pd.read_csv(DATA_PATH)

if "CUST_ID" not in df.columns:
    df["CUST_ID"] = [f"CUST_{i}" for i in range(len(df))]

df = df.reset_index().rename(columns={"index": "row_id"})

numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
dropdown_numeric_columns = [c for c in numeric_columns if c != "row_id"]

scatter_x_default = "PURCHASES"
scatter_y_default = "CASH_ADVANCE"
bubble_size_default = "BALANCE"
color_default = "PRC_FULL_PAYMENT"

table_columns = [
    "CUST_ID",
    "BALANCE",
    "PURCHASES",
    "ONEOFF_PURCHASES",
    "INSTALLMENTS_PURCHASES",
    "CASH_ADVANCE",
    "PURCHASES_TRX",
    "CREDIT_LIMIT",
    "PAYMENTS",
    "MINIMUM_PAYMENTS",
    "PRC_FULL_PAYMENT",
    "TENURE",
]
table_columns = [c for c in table_columns if c in df.columns]

# =========================
# App
# =========================
app = Dash(__name__)
app.title = "Credit Card Dashboard"

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "16px"},
    children=[
        html.H2("Interactive Credit Card Dashboard"),
        html.P(
            "Vyber body v levém bubble scatter plotu pomocí box select nebo lasso. "
            "Tabulka dole se automaticky přefiltruje. Korelační heatmap vpravo je statická."
        ),

        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "16px",
                "marginBottom": "16px",
            },
            children=[
                html.Div(
                    style={
                        "border": "1px solid #ddd",
                        "padding": "12px",
                        "borderRadius": "8px",
                    },
                    children=[
                        html.H4("Bubble Scatter Plot"),
                        html.Label("X axis"),
                        dcc.Dropdown(
                            id="x-col",
                            options=[{"label": c, "value": c} for c in dropdown_numeric_columns],
                            value=scatter_x_default,
                            clearable=False,
                        ),
                        html.Br(),

                        html.Label("Y axis"),
                        dcc.Dropdown(
                            id="y-col",
                            options=[{"label": c, "value": c} for c in dropdown_numeric_columns],
                            value=scatter_y_default,
                            clearable=False,
                        ),
                        html.Br(),

                        html.Label("Bubble size"),
                        dcc.Dropdown(
                            id="size-col",
                            options=[{"label": c, "value": c} for c in dropdown_numeric_columns],
                            value=bubble_size_default,
                            clearable=False,
                        ),
                        html.Br(),

                        html.Label("Color"),
                        dcc.Dropdown(
                            id="color-col",
                            options=[{"label": c, "value": c} for c in dropdown_numeric_columns],
                            value=color_default,
                            clearable=False,
                        ),
                        html.Br(),

                        dcc.Graph(
                            id="main-scatter",
                            config={"displayModeBar": True},
                        ),
                    ],
                ),

                html.Div(
                    style={
                        "border": "1px solid #ddd",
                        "padding": "12px",
                        "borderRadius": "8px",
                    },
                    children=[
                        html.H4("Correlation Matrix"),
                        dcc.Graph(
                            id="corr-heatmap",
                            config={"displayModeBar": False},
                            figure={}
                        ),
                    ],
                ),
            ],
        ),

        html.Div(
            style={
                "border": "1px solid #ddd",
                "padding": "12px",
                "borderRadius": "8px",
            },
            children=[
                html.H4("Filtered Dataset"),
                html.Div(
                    id="selection-summary",
                    style={"marginBottom": "10px", "fontWeight": "bold"},
                ),
                dash_table.DataTable(
                    id="data-table",
                    columns=[{"name": c, "id": c} for c in table_columns],
                    data=[],
                    page_size=15,
                    sort_action="native",
                    filter_action="native",
                    style_table={
                        "overflowX": "auto",
                        "overflowY": "auto",
                        "maxHeight": "450px",
                    },
                    style_cell={
                        "textAlign": "left",
                        "minWidth": "120px",
                        "width": "120px",
                        "maxWidth": "180px",
                        "whiteSpace": "normal",
                    },
                ),
            ],
        ),
    ],
)

# =========================
# Static correlation matrix
# =========================
corr_cols = [c for c in numeric_columns if c != "row_id"]
corr = df[corr_cols].corr(numeric_only=True)

heatmap_fig = go.Figure(
    data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        zmin=-1,
        zmax=1,
        colorscale="RdBu_r",   # 1 = red, -1 = blue
        colorbar=dict(title="Correlation"),
    )
)

heatmap_fig.update_layout(
    height=650,
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(tickangle=45),
    yaxis=dict(autorange="reversed")  # klasické pořadí shora dolů
)

# =========================
# Callbacks
# =========================
@app.callback(
    Output("main-scatter", "figure"),
    Input("x-col", "value"),
    Input("y-col", "value"),
    Input("size-col", "value"),
    Input("color-col", "value"),
)
def update_main_scatter(x_col, y_col, size_col, color_col):
    try:
        plot_df = df.copy()

        # Keep only relevant columns and remove rows with missing values
        required_cols = ["row_id", "CUST_ID", x_col, y_col, size_col, color_col]
        required_cols = [c for c in required_cols if c in plot_df.columns]
        plot_df = plot_df[required_cols].dropna()

        # Bubble size must be non-negative
        if size_col in plot_df.columns:
            plot_df = plot_df[plot_df[size_col] >= 0].copy()

            # If size values are all zero, use a fallback constant size
            if len(plot_df) == 0 or plot_df[size_col].max() == 0:
                plot_df["__bubble_size__"] = 10
                size_to_use = "__bubble_size__"
            else:
                size_to_use = size_col
        else:
            plot_df["__bubble_size__"] = 10
            size_to_use = "__bubble_size__"

        # If color column has too many weird continuous values, Plotly still handles it,
        # but we keep it numeric if possible
        fig = px.scatter(
            plot_df,
            x=x_col,
            y=y_col,
            size=size_to_use,
            color=color_col if color_col in plot_df.columns else None,
            hover_data=["CUST_ID"],
            custom_data=["row_id"],
            opacity=0.7,
            title=f"{y_col} vs {x_col}",
        )

        fig.update_layout(
            height=650,
            dragmode="select",
            margin=dict(l=40, r=20, t=50, b=40),
        )
        return fig

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error while rendering scatter plot:<br>{str(e)}",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(height=650)
        return fig


@app.callback(
    Output("corr-heatmap", "figure"),
    Output("data-table", "data"),
    Output("selection-summary", "children"),
    Input("main-scatter", "selectedData"),
)
def update_filtered_table(selected_data):
    filtered_df = df.copy()

    if selected_data and "points" in selected_data and len(selected_data["points"]) > 0:
        selected_ids = [p["customdata"][0] for p in selected_data["points"]]
        filtered_df = filtered_df[filtered_df["row_id"].isin(selected_ids)]
        summary = f"Selected rows: {len(filtered_df)} / {len(df)}"
    else:
        summary = f"No selection applied. Showing all rows: {len(df)}"

    table_data = filtered_df[table_columns].round(3).to_dict("records")
    return heatmap_fig, table_data, summary


# =========================
# Run server
# =========================
if __name__ == "__main__":
    app.run(debug=True)