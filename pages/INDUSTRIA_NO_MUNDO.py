import streamlit as st
import pandas as pd
import altair as alt
import locale
from func import (
    config_page,
    to_excel2,
    set_y_min,
    set_y_max,
    google_sheets,
    check_password,
    manual_update_unido,
    header_cni,
)
import xmltodict
from indmundo.comtrade.main import comtrade_fragment
from indmundo.oecd.main import oecd_fragment
from indmundo.unido.main import unido_fragment

###### CONFIGURAÇÕES INICIAIS

# Adicionar logo CNI
config_page("Indústria no mundo | CNI-ECON-GERAL")
header_cni()

# Especificar locale
locale.setlocale(locale.LC_TIME, locale="pt_BR")


# Código CSS e Markdown para tirar índices das tabelas
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """
st.markdown(hide_table_row_index, unsafe_allow_html=True)


"""
# Desempenho da indústria no mundo: CNI
Desempenho da indústria no mundo é uma publicação anual da CNI com análise dos dados da UNIDO e OCDE que busca medir a evolução da importância da indústria brasileira para a produção mundial e para as exportações mundiais da indústria.
"""

# Abas
tab1, tab2 = st.tabs(["DADOS INTERNOS", "DADOS DIVULGADOS"])

# %%
with tab2:
    """
    Serão adicionados em breve.
    """

# %%
with tab1:
    if check_password():
        tab3, tab4, tab5, tab6 = st.tabs(
            [
                "DADOS UNIDO (PRODUÇÃO)",
                "DADOS OCDE (EXPORTAÇÃO)",
                "DADOS COMTRADE (EXPORTAÇÃO)",
                "ATUALIZAR BASES",
            ]
        )

        # %%

        # ABA ATUALIZAR BASES
        with tab6:
            st.info(
                """
            ##### Atenção! Clicar no botão abaixo iniciará o processo de atualização das bases. 
            O processo é demorado e envolve várias requisições para as APIs da UNIDO e OCDE, então só usar quando estritamente necessário.
            """,
                icon="⚠️",
            )

            col1, col2 = st.columns(2)

            with col1:
                update_message = st.empty()  # Placeholder for the update message

                if st.button("Atualizar UNIDO (produção)"):

                    try:
                        update_message.warning(
                            "Processando, aguarde...", icon="⚠️"
                        )  # Update message
                        manual_update_unido()
                        update_message.success(
                            "##### Base da UNIDO atualizada com sucesso!", icon="✅"
                        )  # Update message
                    except Exception as e:
                        f"Erro: {e}"

        # ABA DADOS UNIDO (PRODUÇÃO)
        with tab3:
            unido_fragment()

        # ABA DADOS OCDE (EXPORTAÇÃO)
        with tab4:
            oecd_fragment()

        # ABA DADOS OCDE-COMTRADE (EXPORTAÇÃO)
        with tab5:
            comtrade_fragment()
