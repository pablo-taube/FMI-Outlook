import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

# Configuração da página do Streamlit
st.set_page_config(
    page_page_title="Visualizador SDMX - FMI (WEO)",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Visualizador de Dados SDMX (FMI - World Economic Outlook)")
st.markdown("Carregue seu arquivo XML do FMI ou use o arquivo padrão para visualizar as séries temporais e exportar para o Excel.")

# Cache da função de parse do XML para garantir excelente performance
@st.cache_data
def parse_sdmx_xml(xml_content):
    """
    Realiza o parse de um arquivo XML no padrão SDMX (StructureSpecificData do IMF WEO)
    retornando um DataFrame do pandas com os dados das séries temporais.
    """
    root = ET.fromstring(xml_content)
    
    # Namespaces padrão do SDMX
    namespaces = {
        'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
        'ss': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/structurespecific',
    }
    
    # Procura a tag DataSet
    dataset = root.find('.//message:DataSet', namespaces)
    if dataset is None:
        # Busca sem namespace caso haja variação
        dataset = root.find('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}DataSet')
    
    data = []
    
    if dataset is not None:
        # Percorre todos os elementos Series do dataset
        for series in dataset:
            if series.tag.endswith('Series'):
                country = series.attrib.get('COUNTRY', 'N/A')
                indicator = series.attrib.get('INDICATOR', 'N/A')
                scale = series.attrib.get('SCALE', '0')
                decimals = series.attrib.get('DECIMALS_DISPLAYED', 'N/A')
                
                # Percorre cada observação (ano/período) dentro da série
                for obs in series:
                    if obs.tag.endswith('Obs'):
                        time_period = obs.attrib.get('TIME_PERIOD')
                        obs_value = obs.attrib.get('OBS_VALUE')
                        
                        try:
                            val = float(obs_value)
                        except (ValueError, TypeError):
                            val = None
                            
                        data.append({
                            'País': country,
                            'Indicador': indicator,
                            'Ano / Período': time_period,
                            'Valor': val,
                            'Escala': scale,
                            'Casas Decimais': decimals
                        })
                        
    return pd.DataFrame(data)

# Componente de Upload de Arquivo
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo XML (SDMX)", type=["xml"])

xml_bytes = None
if uploaded_file is not None:
    xml_bytes = uploaded_file.read()
else:
    # Caso não seja feito o upload, tenta ler o arquivo local se existir
    try:
        with open("dataset_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.xml", "rb") as f:
            xml_bytes = f.read()
        st.sidebar.info("Exibindo dados do arquivo XML padrão.")
    except FileNotFoundError:
        st.sidebar.warning("Por favor, faça o upload de um arquivo XML para continuar.")

if xml_bytes:
    try:
        # Parsing do XML
        df = parse_sdmx_xml(xml_bytes)
        
        if df.empty:
            st.error("Nenhum dado da tag <Series> foi encontrado no arquivo XML.")
        else:
            # --- Barra Lateral de Filtros ---
            st.sidebar.header("🔍 Filtros de Busca")
            
            paises_disponiveis = sorted(df['País'].unique())
            paises_selecionados = st.sidebar.multiselect(
                "Filtrar por País:",
                options=paises_disponiveis,
                default=paises_disponiveis
            )
            
            indicadores_disponiveis = sorted(df['Indicador'].unique())
            indicadores_selecionados = st.sidebar.multiselect(
                "Filtrar por Indicador:",
                options=indicadores_disponiveis,
                default=indicadores_disponiveis
            )
            
            # Aplicação dos filtros no DataFrame
            df_filtrado = df[
                (df['País'].isin(paises_selecionados)) & 
                (df['Indicador'].isin(indicadores_selecionados))
            ]
            
            # --- Opções de Exibição ---
            st.sidebar.header("⚙️ Formato da Tabela")
            formato_exibicao = st.sidebar.radio(
                "Visualização:",
                ("Tabela Longa (Lista)", "Tabela Dinâmica (Anos nas Colunas)")
            )
            
            if formato_exibicao == "Tabela Dinâmica (Anos nas Colunas)":
                df_exibicao = df_filtrado.pivot_table(
                    index=['País', 'Indicador', 'Escala'], 
                    columns='Ano / Período', 
                    values='Valor'
                ).reset_index()
            else:
                df_exibicao = df_filtrado.copy()
            
            # --- Métricas e Resumo ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Registros", len(df_filtrado))
            col2.metric("Países Selecionados", len(df_filtrado['País'].unique()))
            col3.metric("Indicadores Selecionados", len(df_filtrado['Indicador'].unique()))
            
            st.divider()
            
            # --- Exibição da Tabela ---
            st.subheader("📋 Tabela de Dados")
            st.dataframe(df_exibicao, use_container_width=True)
            
            # --- Exportação para Excel ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_exibicao.to_excel(writer, sheet_name='Dados_FMI_SDMX', index=False)
            
            st.download_button(
                label="📥 Baixar Tabela em Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name="dados_fmi_sdmx.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Erro ao processar o arquivo XML: {e}")
