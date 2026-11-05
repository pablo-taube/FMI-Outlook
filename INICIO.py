import streamlit as st
from func import config_page, header_cni

# %%
###### CONFIGURAÇÕES INICIAIS

# Adicionar logo CNI
config_page("Início: CNI-SRI-GCII")
header_cni()

st.write("# **📈CNI-SRI-GCII📊**")

st.markdown(
    """
    Esse é o app do desempennho da indústria no mundo.
    """
)
