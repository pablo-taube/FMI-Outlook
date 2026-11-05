import json
import streamlit as st
import pandas as pd
import xmltodict
from func import set_y_max, set_y_min, to_excel2, tooltip_rework
from indmundo.utils import bar_chart_race, medida_desempenho
import altair as alt
import numpy as np

with open("pt-BR-format.json", "rb") as f:
    pt_format = json.load(f)
with open("pt-BR-time-format.json", "rb") as f:
    pt_time_format = json.load(f)


@st.fragment
def comtrade_fragment():
    col1, col2 = st.columns(2)
    with col1:
        # Definir arquivo ICI_BD a ser processado
        BD = st.file_uploader(
            label="Arquivo Parquet",
            type="parquet",
            key="bd",
            help='Selecione um arquivo Parquet que contém a extração de dados da Comtrade conforme o notebook "COMTRADE Desempenho Indústria no mundo" do Databricks',
        )

    # Lidar com arquivo vazio
    if BD is None:
        st.info(
            """Os dados internos do Desempenho da Indústria no mundo com Comtrade
                são analisados por meio da base de dados parquet EXP_PARTNERWORLD_COMTRADE.parquet,
                localizada no caminho _"Desempenho da Indústria no Mundo\Trabalho"_ do Microsoft Sharepoint.
                
                Por favor, insira um base de dados EXP_PARTNERWORLD_COMTRADE.parquet válida para continuar.
                """,
            icon="ℹ️",
        )

    # Arquivo carregado
    else:
        try:
            # Ler planilha de dados compilados do ICI trimestral
            df = pd.read_parquet(BD)

        except Exception as e:
            st.error(
                f"Erro: {e}. Você selecionou um arquivo EXP_PARTNERWORLD_COMTRADE.parquet válido? Verifique o arquivo enviado e tente novamente.",
                icon="🚨",
            )

        with col1:
            FMI = st.file_uploader(
                label="Arquivo projeções FMI",
                type="xml",
                key="fmi",
                help="Selecione um arquivo xls do World Economic Outlook do FMI detalhado por país",
            )

        if FMI is not None:

            try:
                # Ler planilha de dados compilados do ICI trimestral
                fmiest = xmltodict.parse(FMI)
                fmis = []
                for var in fmiest["message:StructureSpecificData"]["message:DataSet"][
                    "Series"
                ]:
                    if var["@CONCEPT"] == "TXG_RPCH":
                        fmi = pd.json_normalize(var["Obs"])
                        fmi["Code"] = var["@REF_AREA"]
                        fmis.append(fmi)

                fmiest = pd.concat(fmis, axis=0)

                # Transformar variável quantitativa
                var_quant = ["@OBS_VALUE"]

                for h in var_quant:
                    fmiest[h] = pd.to_numeric(fmiest[h], errors="coerce")

                fmiest = fmiest.loc[~fmiest["@OBS_VALUE"].isna()]

            except Exception as e:
                st.error(
                    f"Erro: {e}. Você selecionou um arquivo válido? Verifique o arquivo enviado e tente novamente.",
                    icon="🚨",
                )

        df = df.rename(
            columns={
                "sum(VL_FOB)": "Valor",
                "NR_YEAR": "Data",
                "CD_REPORTER_ISO_ALPHA3": "COU",
                "DS_REPORTER": "País",
            }
        )

        df["Data"] = df["Data"].astype(str)

        # Mudar unidade para bilhões
        df["Valor"] = (df["Valor"]) / 1000000000

        year_est = df["Data"].max()

        if FMI is not None:

            value_vars = df["Data"].unique()

            df = df.pivot(
                columns="Data",
                index=["CD_REPORTER", "País", "COU"],
                values="Valor",
            )

            df = df.reset_index(drop=False)

            auxfmi = pd.read_excel(
                "indmundo/Dicionário países FMI.xlsx",
                sheet_name="Dados",
                dtype="str",
            )

            fmiest = fmiest.merge(auxfmi, how="left", left_on="Code", right_on="Code")

            fmiest["ISO"] = fmiest["ISO"].str.replace("TWN", "S19")

            fmiest2 = fmiest.copy()

            fmiest = fmiest.loc[fmiest["@TIME_PERIOD"] == year_est[0:4]]

            fmiest = fmiest.loc[~fmiest["ISO"].isna()]

            fmiest = fmiest[["@OBS_VALUE", "ISO"]]

            df = df.merge(fmiest, how="left", left_on="COU", right_on="ISO")

            df[year_est].loc[df[year_est].isna()] = df[year_est] * (
                1 + df["@OBS_VALUE"] / 100
            )

            df = df.drop(columns=["ISO", "@OBS_VALUE"])

            df = df.melt(
                id_vars=["COU", "País"],
                value_vars=value_vars,
                var_name="Data",
                value_name="Valor",
            )

        orig_att = df[["COU", "País"]]

        orig_att = orig_att.drop_duplicates(subset="COU", keep="first")

        if FMI is not None:
            ####### Estimativas

            if "2018" in fmiest2["@TIME_PERIOD"].unique():
                default = list(fmiest2["@TIME_PERIOD"].unique()).index("2018")
            else:
                default = None
            iniciar_estimativa = st.selectbox(
                "Iniciar estimativa FMI em",
                options=fmiest2["@TIME_PERIOD"].unique(),
                index=default,
            )

            start_est = iniciar_estimativa
            end_est = df["Data"].max()
            fmiest2 = fmiest2.loc[
                (fmiest2["@TIME_PERIOD"] >= start_est)
                & (fmiest2["@TIME_PERIOD"] <= end_est)
            ]

            fmiest2 = fmiest2.loc[~fmiest2["ISO"].isna()]

            fmiest2 = fmiest2[["@TIME_PERIOD", "@OBS_VALUE", "ISO"]]

            fmiest2 = fmiest2.pivot(
                columns="@TIME_PERIOD", index="ISO", values="@OBS_VALUE"
            )

            fmiest2 = fmiest2.add_suffix("_est")

            fmiest2 = fmiest2.reset_index(drop=False)

            ####### Dados

            df = df.groupby(["COU", "Data"]).sum().reset_index(drop=False)

            df = df.pivot(columns="Data", index="COU", values="Valor")

            df = df.reset_index(drop=False)

            df = df.merge(fmiest2, how="left", left_on="COU", right_on="ISO")

            for year in range(int(start_est), int(end_est) + 1):
                df[str(year)] = df[str(year)].replace(0, np.nan)
                df[str(year)].loc[df[str(year)].isna()] = df[str(year - 1)] * (
                    1 + df[f"{year}_est"] / 100
                )

            cols_to_drop = df.filter(like="_est").columns
            df = df.drop(columns=cols_to_drop)
            df = df.drop(columns="ISO")
            df = df.melt(
                id_vars=["COU"],
                value_vars=[col for col in df.columns if col != "COU"],
                var_name="Data",
                value_name="Valor",
            )

            df = df.merge(orig_att, how="left", left_on="COU", right_on="COU")

            df["Data"] = df["Data"].astype("datetime64[ns]")
            df["Data"] = df["Data"].dt.tz_localize("America/Sao_Paulo")

            # %%

        # Outra maneira de ler a variável data
        df["Data"] = pd.to_datetime(df["Data"], format="%Y")
        df["Data pt"] = df["Data"].dt.strftime("%Y")

        with col2:
            medida = st.radio(
                label="Medida",
                options=["Valor (bilhões US$)", "Participação (%)"],
                index=1,
                key="medida3",
            )

        st.write(
            """
        #### Evolução país
        """
        )
        cou = st.multiselect(
            label="País",
            options=df["País"].unique(),
            default=["Brazil"],
            key="cou3",
        )

        g1 = df
        g1["Participação no mundo (%)"] = (
            g1["Valor"] / g1.groupby("Data")["Valor"].transform("sum")
        ) * 100
        g1 = g1.loc[g1["País"].isin(cou)]

        # Criar intervalo para gráfico de linha
        ano_inicial, ano_final = st.select_slider(
            "Intervalo",
            options=g1["Data pt"].unique(),
            value=(
                (g1["Data"].min()).strftime("%Y"),
                (g1["Data"].max()).strftime("%Y"),
            ),
            key="intervalo3",
        )

        g1 = g1.loc[
            (g1["Data"] >= g1["Data"].loc[g1["Data pt"] == ano_inicial].min())
            & (g1["Data"] <= g1["Data"].loc[g1["Data pt"] == ano_final].min())
        ]

        # Definir mínimos e máximos do eixo y
        y_min = set_y_min(g1[medida_desempenho(medida)].min())
        y_max = set_y_max(g1[medida_desempenho(medida)].max())

        # Criar gráfico de linha
        line_chart = (
            alt.Chart(g1)
            .mark_line(strokeWidth=3)
            .encode(
                x=alt.X("Data", axis=alt.Axis(format="%Y", labelAngle=-90)),
                y=alt.Y(
                    medida_desempenho(medida),
                    scale=alt.Scale(domain=[y_min, y_max]),
                ),
                color="País",
            )
        )

        line_chart = tooltip_rework(g1, line_chart, medida_desempenho(medida))

        line_chart["usermeta"] = {
            "embedOptions": {
                "formatLocale": pt_format,
                "timeFormatLocale": pt_time_format,
            }
        }

        # Renderizar gráfico de linha

        st.altair_chart(line_chart, theme=None, use_container_width=True)

        st.write(
            """
        #### Variação anual: 15 maiores e 15 menores
        """
        )

        g4 = df
        g4["Participação no mundo (%)"] = (
            g4["Valor"] / g4.groupby("Data")["Valor"].transform("sum")
        ) * 100

        g4 = g4.sort_values(["País", "Data"])

        g4["Variação anual"] = g4.groupby(["País"])[medida_desempenho(medida)].diff()

        ano = st.select_slider(
            "Ano variações",
            options=sorted(g4["Data pt"].unique()),
            value=(g4["Data"].max()).strftime("%Y"),
            key="ano_var3",
        )

        g4 = g4.loc[g4["Data pt"] == ano]

        g4 = g4.sort_values("Variação anual", ascending=False)

        g4 = g4.loc[~g4["Variação anual"].isna()]

        g4 = pd.concat([g4.head(15), g4.tail(15)], axis=0)

        chart = (
            alt.Chart(g4)
            .mark_bar()
            .encode(
                x="Variação anual:Q",
                y=alt.Y(
                    "País:N",
                    sort=alt.EncodingSortField(field="Variação anual:Q"),
                ),
                color=alt.condition(
                    alt.datum["Variação anual"] > 0,  # condition
                    alt.value("#376092"),  # color for positive values
                    alt.value("#b90e0c"),  # color for negative values
                ),
            )
            .properties(height=800)
        )

        # Add text labels on top of the bars
        text1 = chart.mark_text(align="center", dx=15).encode(
            text=alt.Text("Variação anual:Q", format=".3f"),
            y=alt.Y(
                "País:N",
                sort=alt.EncodingSortField(field="Variação anual:Q"),
                axis=None,
            ),
            color=alt.value("#000000"),
        )

        chart = (chart + text1).resolve_scale(y="independent")

        # Renderizar
        st.altair_chart(chart, theme=None, use_container_width=True)

        st.write(
            """
        #### Evolução ranking países
        """
        )

        g2 = df
        g2["Participação no mundo (%)"] = (
            g2["Valor"] / g2.groupby("Data")["Valor"].transform("sum")
        ) * 100

        g2 = g2.sort_values(["Data", "País"])

        g2s = []
        for ano in g2["Data pt"].unique():
            gw = g2.loc[g2["Data pt"] == ano]
            gw = gw.sort_values(medida_desempenho(medida), ascending=False)
            gw = gw.head(40)
            g2s.append(gw)

        g2 = pd.concat(g2s, axis=0)

        g2[medida_desempenho(medida)] = g2[medida_desempenho(medida)].apply(
            lambda x: round(x, 2)
        )

        g2 = g2.rename(columns={"Data pt": "Ano"})

        # Convert 'Ano' to numeric type
        g2["Ano"] = pd.to_numeric(g2["Ano"])

        bar_chart_race(g2, medida, 40)

        st.write(
            """
        #### Dados detalhados
        """
        )

        g3 = df
        g3["Participação no mundo (%)"] = (
            g3["Valor"] / g3.groupby("Data")["Valor"].transform("sum")
        ) * 100

        g3 = g3.pivot(columns="Data pt", index="País", values=medida_desempenho(medida))

        g3 = g3.sort_values(g3.columns.max(), ascending=False)

        st.dataframe(g3)

        df_xlsx = to_excel2([g1, g3, g4])
        st.download_button(
            label="📥 Baixar dados",
            data=df_xlsx,
            file_name="Dados.xlsx",
            use_container_width=True,
            key="ocde_download3",
        )
