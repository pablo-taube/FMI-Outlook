# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 10:22:57 2023

@author: danilo.sousa
"""

import streamlit as st
import tempfile
from io import BytesIO
import pandas as pd
import json
import gspread
import os
import requests
from docx import Document
from streamlit.components.v1 import html
import altair as alt


def tooltip_rework(chart_df, chart, medida):
    nearest = alt.selection_point(
        nearest=True, on="mouseover", fields=["Data"], empty=False, clear="click"
    )

    selectors = (
        alt.Chart(chart_df)
        .mark_point()
        .encode(
            x=alt.X("Data", axis=alt.Axis(format="%Y"), title="Data"),
            opacity=alt.value(0),
        )
        .add_params(nearest)
    )

    points = chart.mark_point().encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    )

    # Draw text labels near the points, and highlight based on selection
    text2 = chart.mark_text(align="left", dx=5, dy=-5).encode(
        text=alt.condition(
            nearest, alt.Text(f"{medida}:Q", format=".2f"), alt.value(" ")
        )
    )

    # Draw a rule at the location of the selection
    rules = (
        alt.Chart(chart_df)
        .mark_rule(color="gray")
        .encode(
            x="Data",
        )
        .transform_filter(nearest)
    )

    chart = chart + selectors + points + rules + text2
    return chart


def config_page(page_title):
    page_title = f"{page_title}"
    st.set_page_config(
        page_title=page_title, initial_sidebar_state="expanded", layout="wide"
    )

    with st.sidebar:
        st.image(
            "https://staticportaldaindustria.azureedge.net/static/img/logos/atualizado/cni.svg",
            width=280,
        )

        html(
            """
        <script>
            var imgSrc = "https://staticportaldaindustria.azureedge.net/static/img/logos/novas/cni.svg";
            var imgElem = window.parent.document.querySelector(`img[src="${imgSrc}"]`);
            imgElem.style.width = '100%';
            imgElem.style.marginBottom = '-50px';

        </script>
        """,
            width=0,
            height=0,
        )

        st.page_link("INICIO.py", label="Início", icon="🏠")

        st.page_link(
            "pages/INDUSTRIA_NO_MUNDO.py", label="Indústria no Mundo", icon="📉"
        )
        st.page_link("pages/CAC_SHWEB.py", label="CAC SHWEB", icon="📉")

    custom_style()


def custom_style():
    st.html(
        """
        <style>
            /* Tratar espaço entre items da sidebar */ 
            [class='stPageLink'] {
                margin: -0.25rem; /* Adjust this value to reduce the gap */
                font-variant: small-caps;
                }

            /* Tratar espaço em branco no topo e no fim */ 
            .block-container {
                padding-top: 0rem;
                padding-bottom: 0rem;
             }

            /* Tirar header branco padrão do Streamlit */ 
            [data-testid="stHeader"] {
                pointer-events: none;
                background: rgb(255 255 255 / 0%)
                }

            /* Lidar com espaço em branco adicionado com o st.logo */ 
            [data-testid="stSidebarHeader"] {
                height: 0px;
                padding-top: 20px;
                padding-bottom: 0px
            }

            /* Tratar botão de colapsar a sidebar */ 
            [data-testid="stSidebarCollapseButton"] {
                z-index: 99999999;
                border-radius: 12px;
            }

            /* Retirar botão de fullscreen */ 
            [data-testid="StyledFullScreenButton"] {
                display: none;
            }

            /* Tratar botão de expandir sidebar */ 
            [data-testid="collapsedControl"] {
                background: rgb(255 255 255);
                border-radius: 12px;
                }
            
            /* Tratar container do menu principal */ 
            [data-testid="stToolbar"] {
                pointer-events: auto;
                background: transparent;
                border-radius: 12px;
                }
        </style>
        """
    )


def header_cni():
    html(
        """
        <script>
            var elem = window.parent.document.querySelector('[tabindex="0"]');
            if (!window.parent.document.getElementById('myIframe')) {
                var iframe = document.createElement('iframe');
                iframe.id = 'myIframe';
                iframe.className = 'myIframe';
                iframe.src = 'https://www.portaldaindustria.com.br/iframe-2015/iframe-cni-topo-2015';
                iframe.style.position = 'relative';
                iframe.style.border = '0';
                iframe.style.width = '100%';
                iframe.style.height = '50px';
                iframe.style.marginBottom = '-40px';
                iframe.scrolling = 'no';
                if (elem.firstChild) {
                    elem.insertBefore(iframe, elem.firstChild);
                } else {
                    elem.appendChild(iframe);
                }
            }
            var wrapper = document.createElement('div');
            wrapper.style.height = 'auto';
            wrapper.style.width = '100%';
            elem.appendChild(wrapper);
            if (!window.parent.document.getElementById('myIframe2')) {
                iframe = document.createElement('iframe');
                iframe.id = 'myIframe2';
                iframe.className = 'myIframe2';
                iframe.src = 'https://www.portaldaindustria.com.br/iframe-2015/iframe-cni-rodape-2015';
                iframe.style.position = 'relative';
                iframe.style.border = '0';
                iframe.style.width = '100%';
                iframe.style.height = '980px';
                iframe.style.marginTop = '20px';
                iframe.scrolling = 'no';
                wrapper.appendChild(iframe);
            }
        </script>
        """,
        width=0,
        height=0,
    )


# Função gerar planilha excel com os dados
def to_excel(x):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    for i, df in enumerate(x):
        if "Data" in df.columns:
            df["Data"] = df["Data"].dt.date
        if "Trimestre móvel terminado em" in df.columns:
            df["Trimestre móvel terminado em"] = df[
                "Trimestre móvel terminado em"
            ].dt.date
        df.to_excel(writer, index=False, sheet_name=f"Dataframe {i}")
    writer.close()
    processed_data = output.getvalue()
    return processed_data


def to_word_translate(title, original, text):
    output = BytesIO()
    document = Document()
    document.add_heading(f"Tradução {title}", level=1)
    table = document.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Texto original"
    hdr_cells[1].text = "Texto traduzido GPT"
    body_cells = table.rows[1].cells
    body_cells[0].text = f"{original}"
    body_cells[1].text = f"{text}"

    document.save(output)
    processed_data = output.getvalue()
    return processed_data


def to_excel2(x):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    for i, df in enumerate(x):
        if "Data" in df.columns:
            df["Data"] = df["Data"].dt.date
        if "Trimestre móvel terminado em" in df.columns:
            df["Trimestre móvel terminado em"] = df[
                "Trimestre móvel terminado em"
            ].dt.date
        df.to_excel(writer, index=True, sheet_name=f"Dataframe {i}")
    writer.close()
    processed_data = output.getvalue()
    return processed_data


# Função cor de background das tabelas
def color_background(x):
    color = ""
    if x > 0:
        color = "#85AEFF"  # Azul: #85AEFF ; Verde: #C6EFCE
    elif x < 0:
        color = "#FFC7CE"
    return f"background-color: {color}"


# Função cor de background das tabelas2
def color_background2(x):
    color = ""
    if x > 50:
        color = "#85AEFF"
    elif x < 50:
        color = "#FFC7CE"
    return f"background-color: {color}"


# Limites eixo y
def set_y_min(x):
    if x < 0:
        return x * 1.05
    elif x >= 0:
        return x * 0.95


# Limites eixo y
def set_y_max(x):
    if x < 0:
        return x * 0.95
    elif x >= 0:
        return x * 1.05


# Função cor de checar senha
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Os dados internos são confidenciais. Para acessar, insira a senha e tecle ENTER:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Os dados internos são confidenciais. Para acessar, insira a senha e tecle ENTER:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error(
            "😕 Senha incorreta. Consulte o grupo do Teams ou procure a Gerência de Análise Econômica para informações sobre a senha."
        )
        return False
    else:
        # Password correct.
        return True


# Função cor de checar senha
def check_password2():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password2"] == st.secrets["password2"]:
            st.session_state["password_correct"] = True
            del st.session_state["password2"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Os dados internos são confidenciais. Para acessar, insira a senha e tecle ENTER:",
            type="password",
            on_change=password_entered,
            key="password2",
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Os dados internos são confidenciais. Para acessar, insira a senha e tecle ENTER:",
            type="password",
            on_change=password_entered,
            key="password2",
        )
        st.error(
            "😕 Senha incorreta. Consulte o grupo do Teams ou procure a Gerência de Análise Econômica para informações sobre a senha."
        )
        return False
    else:
        # Password correct.
        return True


# Função de ler base de dados Google Sheets
@st.cache_data(ttl=31622400)
def google_sheets(db):
    cred = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"][
            "auth_provider_x509_cert_url"
        ],
        "client_x509_cert_url": st.secrets["gcp_service_account"][
            "client_x509_cert_url"
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tfile:
        json.dump(cred, tfile)
        tfile.flush()
        gc = gspread.service_account(filename=tfile.name)

    os.remove(tfile.name)  # Delete the file

    sh = gc.open(db)
    worksheet = sh.worksheet("Dados")
    df = pd.DataFrame(worksheet.get_all_records(numericise_ignore=["all"]))
    if "Data" in df.columns:
        try:
            df["Data"] = df["Data"].astype("datetime64[ns]")
            df["Data"] = df["Data"].dt.date
        except:
            pass

    if "Trimestre móvel terminado em" in df.columns:
        try:
            df["Trimestre móvel terminado em"] = df[
                "Trimestre móvel terminado em"
            ].astype("datetime64[ns]")
            df["Trimestre móvel terminado em"] = df[
                "Trimestre móvel terminado em"
            ].dt.date
        except:
            pass

    if "Valor" in df.columns:
        try:
            df["Valor"] = df["Valor"].str.replace(",", ".")
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        except:
            pass

    return df


def manual_update_unido():
    payload = requests.get(
        "https://stat.unido.org/portal/dataset/getDataset/NATIONAL_ACCOUNTS"
    )

    meta = json.loads(payload.content.decode("utf8"))
    meta_cou = pd.json_normalize(meta["countries"])
    meta_var = pd.json_normalize(meta["variables"])

    url = "https://stat.unido.org/portal/dataset/getDataWithoutActivities"

    headers = {
        "accept": "*/*",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "cookie": "_ga=GA1.1.18094010.1723153576; _ga_1VM9H38V8B=GS1.1.1723153576.1.1.1723153649.52.0.1239623752",
        "origin": "https://stat.unido.org",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Referer": "",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    }

    min_per = min(meta["periods"])
    max_per = max(meta["periods"])

    dfs = []
    for cc in meta_cou["c"]:
        payload = json.dumps(
            {
                "datasetId": meta["id"],
                "countryCode": cc,
                "periods": meta["periods"],
                "fullPrecision": True,
            }
        )
        response = requests.request("POST", url, headers=headers, data=payload)
        data = json.loads(response.content.decode("utf8"))
        df = pd.json_normalize(data["data"])
        df["country"] = cc
        dfs.append(df)

    df = pd.concat(dfs, axis=0)
    df = df.loc[df["c"].isin([v for v in meta_var["c"] if "Iva" in v or "Mva" in v])]

    meta_cou = meta_cou.rename(columns={"lang.en": "País", "c": "country_code"})
    meta_var = meta_var.rename(columns={"lang.en": "Variável", "c": "var_code"})

    df = df.merge(meta_cou, how="left", left_on="country", right_on="country_code")

    df = df.merge(meta_var, how="left", left_on="c", right_on="var_code")

    df = df.rename(
        columns={
            "p": "Data",
            "v": "Valor",
        }
    )
    df = df[["Data", "Valor", "País", "Variável"]]

    cred = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"][
            "auth_provider_x509_cert_url"
        ],
        "client_x509_cert_url": st.secrets["gcp_service_account"][
            "client_x509_cert_url"
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tfile:
        json.dump(cred, tfile)
        tfile.flush()
        gc = gspread.service_account(filename=tfile.name)

    os.remove(tfile.name)  # Delete the file

    sh = gc.open("IND_MUNDO_UNIDO")
    worksheet = sh.worksheet("Dados")

    df["Data"] = df["Data"].astype(str)
    df = df.fillna("")
    gc.set_timeout(9999)
    worksheet.clear()
    worksheet.update(
        range_name="A1", values=[df.columns.values.tolist()] + df.values.tolist()
    )

    st.cache_data.clear()
