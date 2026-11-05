from func import set_y_max, set_y_min
import altair as alt
import streamlit as st


def medida_desempenho(x):
    if x == "Valor (bilhões US$)":
        return "Valor"
    if x == "Participação (%)":
        return "Participação no mundo (%)"


def format_number(x):
    # Convert to integer and replace commas with dots as thousands separator
    return f"{x:,.2f}".replace(".", "|").replace(",", ".").replace("|", ",")


def func(values, ranks):
    total = values.sum()
    s = (
        "Total: "
        + f"{int(total):,}".replace(",", ".")
        + """
            Fonte: UNIDO"""
    )
    return {"x": 0.99, "y": 0.05, "s": s, "ha": "right", "size": 9}


def func2(values, ranks):
    total = values.sum()
    s = (
        "Total: "
        + f"{int(total):,}".replace(",", ".")
        + """
            Fonte: OCDE"""
    )
    return {"x": 0.99, "y": 0.05, "s": s, "ha": "right", "size": 9}


def color_function(values, ranks):
    colors = []
    for country in ranks.index:
        if country == "Brazil":
            colors.append("#f28e2b")
        else:
            colors.append("#4e79a7")
    return colors


def bar_chart_race(df, medida, rank):
    y_min = 0
    y_max = set_y_max(df[medida_desempenho(medida)].max())

    # Create a slider for the 'Ano' parameter
    year_slider = alt.binding_range(
        min=int(df["Ano"].min()), max=int(df["Ano"].max()), step=1
    )
    year_select = alt.selection_point(
        name="Year", fields=["Ano"], bind=year_slider, value=int(df["Ano"].max())
    )

    # Create the bar chart
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{medida_desempenho(medida)}:Q",
                title=medida_desempenho(medida),
                scale=alt.Scale(domain=[y_min, y_max]),
            ),
            y=alt.Y("País:N", sort="-x", axis=alt.Axis(minExtent=180)),
            color=alt.condition(
                alt.datum.País == "Brazil",
                alt.value("orange"),
                alt.value("grey"),
            ),
        )
        .add_params(year_select)
        .transform_filter(year_select)
        .transform_window(
            rank=f"rank(desc({medida_desempenho(medida)}))",
            sort=[alt.SortField(medida_desempenho(medida), order="descending")],
        )
        .transform_filter(alt.datum.rank <= rank)
    )

    # Add text labels to the bars
    text = chart.mark_text(align="left", baseline="middle", dx=3).encode(
        text=alt.Text(f"{medida_desempenho(medida)}:Q", format=".2f")
    )

    # Combine the chart and text labels
    final_chart = chart + text

    # Display the chart
    return st.altair_chart(final_chart, use_container_width=True, theme=None)
