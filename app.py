import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página Streamlit
st.set_page_config(
    page_title="WEO Economic Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CUPERTINO (APPLE DESIGN SYSTEM + TONS DE AZUL) ---
st.markdown("""
<style>
    /* Tipografia e Fundo Geral */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
        color: #1d1d1f;
        background-color: #f5f5f7;
    }

    /* Ocultar elementos desnecessários da interface padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Cartões e Métricas Cupertino (Glassmorphic look) */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(229, 229, 234, 0.8);
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(0, 122, 255, 0.08);
    }

    div[data-testid="stMetricLabel"] > label {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #8e8e93 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    div[data-testid="stMetricValue"] > div {
        font-size: 26px !important;
        font-weight: 600 !important;
        color: #007aff !important;
    }

    /* Menu Lateral Cupertino */
    section[data-testid="stSidebar"] {
        background-color: rgba(242, 242, 247, 0.85);
        border-right: 1px solid #e5e5ea;
    }

    /* Botões Cupertino */
    .stButton > button {
        background-color: #007aff;
        color: #ffffff;
        border-radius: 12px;
        border: none;
        padding: 8px 18px;
        font-weight: 500;
        font-size: 14px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 122, 255, 0.25);
    }

    .stButton > button:hover {
        background-color: #0062cc;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.35);
        color: #ffffff;
    }

    /* Abas Estilo Segmented Control */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #e3e3e8;
        padding: 4px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 36px;
        border-radius: 8px;
        border: none;
        color: #636366;
        font-weight: 500;
        font-size: 14px;
        padding: 0 16px;
        background-color: transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #007aff !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        font-weight: 600;
    }

    /* Ajuste de Headers */
    h1, h2, h3 {
        color: #1d1d1f;
        font-weight: 600 !important;
        letter-spacing: -0.5px;
    }
</style>
""", unsafe_allow_html=True)

# Paleta de Cores Cupertino para Gráficos
BLUE_PRIMARY = "#007aff"      # Azul Apple vibrante (Projeção)
BLUE_SECONDARY = "#144d8c"    # Azul Marinho profundo (Dado Real)
BLUE_LIGHT = "#5ac8fa"        # Azul claro complementar
BG_CONTAINER = "rgba(255, 255, 255, 0.6)"

@st.cache_data
def load_data(file):
    df = pd.read_json(file)
    df['IS_PROJECTION'] = df['IS_PROJECTION'].fillna(False).astype(bool)
    df['TIME_PERIOD'] = df['TIME_PERIOD'].astype(str)
    df['OBS_VALUE'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')
    return df

# --- CARREGAMENTO DE DADOS ---
st.sidebar.title("􀍟 Configurações")
uploaded_file = st.sidebar.file_uploader("Carregar arquivo WEO (JSON)", type=["json"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    try:
        df = load_data("weo_9.0.0_2025.json")
        st.sidebar.caption("🟢 Base local carregada.")
    except Exception:
        st.info("👋 Por favor, faça o upload do arquivo `weo_9.0.0_2025.json` no menu lateral.")
        st.stop()

# --- FILTROS DE SIDEBAR ---
st.sidebar.subheader("Filtros")

status_filter = st.sidebar.multiselect(
    "Tipo de Registro",
    options=["Projeção", "Dado Efetivo/Histórico"],
    default=["Projeção", "Dado Efetivo/Histórico"]
)

proj_mask = pd.Series(False, index=df.index)
if "Projeção" in status_filter:
    proj_mask |= (df['IS_PROJECTION'] == True)
if "Dado Efetivo/Histórico" in status_filter:
    proj_mask |= (df['IS_PROJECTION'] == False)

df_filtered = df[proj_mask]

all_countries = sorted(df['COUNTRY_NAME'].unique().tolist())
selected_countries = st.sidebar.multiselect("Países", options=all_countries, default=all_countries[:6])

all_indicators = sorted(df['INDICATOR_NAME'].unique().tolist())
selected_indicators = st.sidebar.multiselect("Indicadores", options=all_indicators, default=all_indicators[:4])

df_filtered = df_filtered[
    (df_filtered['COUNTRY_NAME'].isin(selected_countries)) &
    (df_filtered['INDICATOR_NAME'].isin(selected_indicators))
]

# --- CABEÇALHO ---
st.title("World Economic Outlook")
st.caption("Painel interativo de indicadores e projeções macroeconômicas do FMI")

st.markdown("<br>", unsafe_allow_html=True)

# --- KPIs SUPERIORES ---
col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)

time_periods = df['TIME_PERIOD'].unique()
latest_actuals = df['LATEST_ACTUAL'].dropna().unique()

with col_meta1:
    st.metric("Período de Análise", ", ".join(time_periods))
with col_meta2:
    st.metric("Ano Efetivo Médio", f"{int(latest_actuals.mean())}" if len(latest_actuals) > 0 else "N/A")
with col_meta3:
    st.metric("Registros Exibidos", f"{len(df_filtered)}")
with col_meta4:
    proj_count = df_filtered['IS_PROJECTION'].sum()
    pct_proj = (proj_count / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric("Proporção Projeções", f"{pct_proj:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)

# --- ABAS DE NAVEGAÇÃO ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Comparativa", "🌍 Perfil do País", "💡 Insights Automáticos", "📋 Tabela de Dados"])

# ==========================================
# ABA 1: VISÃO COMPARATIVA
# ==========================================
with tab1:
    if df_filtered.empty:
        st.warning("Nenhum dado disponível para os filtros selecionados.")
    else:
        indicator_for_chart = st.selectbox("Selecione o Indicador:", options=selected_indicators)
        
        df_chart = df_filtered[df_filtered['INDICATOR_NAME'] == indicator_for_chart].sort_values(by="OBS_VALUE", ascending=False)
        
        if not df_chart.empty:
            df_chart['STATUS_LABEL'] = df_chart['IS_PROJECTION'].apply(lambda x: 'Projeção' if x else 'Dado Efetivo')
            
            fig = px.bar(
                df_chart,
                x='COUNTRY_NAME',
                y='OBS_VALUE',
                color='STATUS_LABEL',
                hover_data=['UNIT', 'SCALE', 'LATEST_ACTUAL'],
                labels={'OBS_VALUE': 'Valor', 'COUNTRY_NAME': 'País', 'STATUS_LABEL': 'Tipo'},
                title=f"<b>{indicator_for_chart}</b> ({df_chart['TIME_PERIOD'].iloc[0]})",
                color_discrete_map={'Projeção': BLUE_PRIMARY, 'Dado Efetivo': BLUE_SECONDARY}
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_family="-apple-system, SF Pro Display",
                font_color="#1d1d1f",
                margin=dict(l=20, r=20, t=50, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor="#e5e5ea", title=""),
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de Dispersão Cruzado
            if len(selected_indicators) >= 2 and len(selected_countries) > 1:
                st.markdown("### Análise Cruzada de Indicadores")
                c_x, c_y = st.columns(2)
                with c_x:
                    ind_x = st.selectbox("Eixo X:", options=selected_indicators, index=0)
                with c_y:
                    ind_y = st.selectbox("Eixo Y:", options=selected_indicators, index=min(1, len(selected_indicators)-1))
                
                df_x = df_filtered[df_filtered['INDICATOR_NAME'] == ind_x][['COUNTRY_NAME', 'OBS_VALUE', 'IS_PROJECTION']].rename(columns={'OBS_VALUE': ind_x})
                df_y = df_filtered[df_filtered['INDICATOR_NAME'] == ind_y][['COUNTRY_NAME', 'OBS_VALUE']].rename(columns={'OBS_VALUE': ind_y})
                
                df_scatter = pd.merge(df_x, df_y, on='COUNTRY_NAME').dropna()
                df_scatter['STATUS_LABEL'] = df_scatter['IS_PROJECTION'].apply(lambda x: 'Projeção' if x else 'Dado Efetivo')
                
                if not df_scatter.empty:
                    fig_scatter = px.scatter(
                        df_scatter,
                        x=ind_x,
                        y=ind_y,
                        text='COUNTRY_NAME',
                        color='STATUS_LABEL',
                        color_discrete_map={'Projeção': BLUE_PRIMARY, 'Dado Efetivo': BLUE_SECONDARY}
                    )
                    fig_scatter.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='#ffffff')))
                    fig_scatter.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_family="-apple-system, SF Pro Display",
                        xaxis=dict(showgrid=True, gridcolor="#e5e5ea"),
                        yaxis=dict(showgrid=True, gridcolor="#e5e5ea"),
                        height=480
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================================
# ABA 2: PERFIL DO PAÍS
# ==========================================
with tab2:
    selected_single_country = st.selectbox("Selecione um País para Perfil Detalhado:", options=all_countries)
    df_country = df[df['COUNTRY_NAME'] == selected_single_country]
    
    if not df_country.empty:
        st.markdown(f"### **{selected_single_country}** ({df_country['TIME_PERIOD'].iloc[0]})")
        
        pib_real = df_country[df_country['INDICATOR'] == 'NGDP_RPCH']
        inflacao = df_country[df_country['INDICATOR'] == 'PCPIPCH']
        desemprego = df_country[df_country['INDICATOR'] == 'LUR']
        populacao = df_country[df_country['INDICATOR'] == 'LP']
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            val = f"{pib_real['OBS_VALUE'].values[0]:.2f}%" if not pib_real.empty else "N/A"
            st.metric("PIB Real", val)
        with c2:
            val = f"{inflacao['OBS_VALUE'].values[0]:.2f}%" if not inflacao.empty else "N/A"
            st.metric("Inflação Média", val)
        with c3:
            val = f"{desemprego['OBS_VALUE'].values[0]:.2f}%" if not desemprego.empty else "N/A"
            st.metric("Desemprego", val)
        with c4:
            if not populacao.empty:
                pop_val = populacao['OBS_VALUE'].values[0]
                scale = populacao['SCALE'].values[0]
                pop_formatted = f"{pop_val * (10**int(scale if scale else 0)):,.0f}"
            else:
                pop_formatted = "N/A"
            st.metric("População", pop_formatted)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        df_gdp_pct = df_country[df_country['INDICATOR_NAME'].str.contains("Percent of GDP", case=False, na=False)]
        if not df_gdp_pct.empty:
            st.markdown("#### Indicadores em Percentual do PIB (%)")
            fig_gdp = px.bar(
                df_gdp_pct,
                y='INDICATOR_NAME',
                x='OBS_VALUE',
                orientation='h',
                color='IS_PROJECTION',
                color_discrete_map={True: BLUE_PRIMARY, False: BLUE_SECONDARY},
                labels={'OBS_VALUE': '% do PIB', 'INDICATOR_NAME': '', 'IS_PROJECTION': 'Projeção'}
            )
            fig_gdp.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_family="-apple-system, SF Pro Display",
                xaxis=dict(showgrid=True, gridcolor="#e5e5ea"),
                height=400
            )
            st.plotly_chart(fig_gdp, use_container_width=True)

# ==========================================
# ABA 3: INSIGHTS AUTOMÁTICOS
# ==========================================
with tab3:
    st.markdown("### Insights Automáticos")
    
    if df_filtered.empty:
        st.info("Selecione países e indicadores para gerar os insights.")
    else:
        df_pib = df_filtered[df_filtered['INDICATOR'] == 'NGDP_RPCH']
        if not df_pib.empty:
            max_pib = df_pib.loc[df_pib['OBS_VALUE'].idxmax()]
            min_pib = df_pib.loc[df_pib['OBS_VALUE'].idxmin()]
            
            st.info(
                f"🔵 **Maior Expansão:** **{max_pib['COUNTRY_NAME']}** destaca-se com crescimento do PIB Real projetado em **{max_pib['OBS_VALUE']:.2f}%**."
            )
            st.caption(
                f"Menor desempenho registrado: **{min_pib['COUNTRY_NAME']}** com **{min_pib['OBS_VALUE']:.2f}%**."
            )
            
        df_inf = df_filtered[df_filtered['INDICATOR'] == 'PCPIPCH']
        if not df_inf.empty:
            max_inf = df_inf.loc[df_inf['OBS_VALUE'].idxmax()]
            st.warning(
                f"⚠️ **Pressão Inflacionária:** A maior taxa de inflação identificada pertence a **{max_inf['COUNTRY_NAME']}** (**{max_inf['OBS_VALUE']:.2f}%**)."
            )

# ==========================================
# ABA 4: TABELA DETALHADA E DOWNLOAD
# ==========================================
with tab4:
    display_cols = [
        'COUNTRY', 'COUNTRY_NAME', 'INDICATOR', 'INDICATOR_NAME', 
        'TIME_PERIOD', 'OBS_VALUE', 'UNIT', 'IS_PROJECTION', 'LATEST_ACTUAL'
    ]
    df_display = df_filtered[display_cols].copy()
    
    st.dataframe(
        df_display.style.format({
            'OBS_VALUE': '{:,.2f}',
            'LATEST_ACTUAL': '{:.0f}'
        }),
        use_container_width=True,
        height=400
    )
    
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exportar Dados (CSV)",
        data=csv,
        file_name='weo_data_export.csv',
        mime='text/csv'
    )
