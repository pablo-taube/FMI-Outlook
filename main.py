# -*- coding: utf-8 -*-
"""
DESEMPENHO DA INDÚSTRIA NO MUNDO — COMTRADE + PROJEÇÕES DO FMI  (arquivo único)

Como executar
    pip install -r requirements.txt     (conteúdo logo abaixo)
    streamlit run app_desempenho_industria_mundo.py

requirements.txt  (copie estas linhas para um arquivo com esse nome)
    streamlit>=1.37
    pandas>=2.2
    numpy
    altair>=5
    pyarrow
    xmltodict
    xlsxwriter
    openpyxl

Estrutura deste arquivo
    1. Constantes, dicionário de países do FMI e formatos pt-BR
    2. Utilidades (antigo func.py / indmundo/utils.py)
    3. Leitura e validação dos arquivos (parquet COMTRADE e XML FMI)
    4. Estimativa dos países sem dados (metodologia TXG_RPCH)
    5. Gráficos (Altair)
    6. Páginas do Streamlit (Início e Desempenho da Indústria no Mundo)
"""

import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import xmltodict

# =============================================================================
# 1. CONSTANTES, DICIONÁRIO FMI E FORMATOS PT-BR
# =============================================================================

# Indicador do FMI usado na estimativa: variação % anual das exportações de bens
CONCEITO_FMI = "TXG_RPCH"

# A estimativa só pode começar neste ano ou depois (metodologia 2026).
# Para permitir estimar anos anteriores, reduza este valor.
ANO_MIN_ESTIMATIVA = 2022

# Colunas esperadas no parquet extraído do Databricks
COLUNAS_PARQUET = {
    "sum(VL_FOB)": "Valor",
    "NR_YEAR": "Ano",
    "CD_REPORTER_ISO_ALPHA3": "COU",
    "DS_REPORTER": "País",
}

# O FMI identifica Taiwan como TWN; o COMTRADE usa S19
ISO_FMI_PARA_COMTRADE = {"TWN": "S19"}

# Dicionário FMI (Code numérico do FMI ; descrição ; ISO alpha-3)
# Origem: "Dicionário países FMI.xlsx" (aba Dados)
DICIONARIO_FMI_TXT = """
111;United States;USA
112;United Kingdom;GBR
122;Austria;AUT
124;Belgium;BEL
128;Denmark;DNK
132;France;FRA
134;Germany;DEU
135;San Marino;SMR
136;Italy;ITA
137;Luxembourg;LUX
138;Netherlands;NLD
142;Norway;NOR
144;Sweden;SWE
146;Switzerland;CHE
156;Canada;CAN
158;Japan;JPN
171;Andorra;AND
172;Finland;FIN
174;Greece;GRC
176;Iceland;ISL
178;Ireland;IRL
181;Malta;MLT
182;Portugal;PRT
184;Spain;ESP
186;Türkiye;TUR
193;Australia;AUS
196;New Zealand;NZL
199;South Africa;ZAF
213;Argentina;ARG
218;Bolivia;BOL
223;Brazil;BRA
228;Chile;CHL
233;Colombia;COL
238;Costa Rica;CRI
243;Dominican Republic;DOM
248;Ecuador;ECU
253;El Salvador;SLV
258;Guatemala;GTM
263;Haiti;HTI
268;Honduras;HND
273;Mexico;MEX
278;Nicaragua;NIC
283;Panama;PAN
288;Paraguay;PRY
293;Peru;PER
298;Uruguay;URY
299;Venezuela;VEN
311;Antigua and Barbuda;ATG
314;Aruba;ABW
316;Barbados;BRB
321;Dominica;DMA
328;Grenada;GRD
336;Guyana;GUY
339;Belize;BLZ
343;Jamaica;JAM
359;Puerto Rico;PRI
361;St. Kitts and Nevis;KNA
362;St. Lucia;LCA
364;St. Vincent and the Grenadines;VCT
366;Suriname;SUR
369;Trinidad and Tobago;TTO
419;Bahrain;BHR
423;Cyprus;CYP
433;Iraq;IRQ
436;Israel;ISR
439;Jordan;JOR
443;Kuwait;KWT
446;Lebanon;LBN
449;Oman;OMN
453;Qatar;QAT
456;Saudi Arabia;SAU
463;Syria;SYR
466;United Arab Emirates;ARE
469;Egypt;EGY
474;Yemen;YEM
487;West Bank and Gaza;WBG
512;Afghanistan;AFG
513;Bangladesh;BGD
514;Bhutan;BTN
516;Brunei Darussalam;BRN
518;Myanmar;MMR
522;Cambodia;KHM
524;Sri Lanka;LKA
528;Taiwan Province of China;TWN
532;Hong Kong SAR;HKG
534;India;IND
536;Indonesia;IDN
537;Timor-Leste;TLS
542;Korea;KOR
544;Lao P.D.R.;LAO
546;Macao SAR;MAC
548;Malaysia;MYS
556;Maldives;MDV
558;Nepal;NPL
564;Pakistan;PAK
565;Palau;PLW
566;Philippines;PHL
576;Singapore;SGP
578;Thailand;THA
582;Vietnam;VNM
611;Djibouti;DJI
612;Algeria;DZA
614;Angola;AGO
616;Botswana;BWA
618;Burundi;BDI
622;Cameroon;CMR
624;Cabo Verde;CPV
626;Central African Republic;CAF
628;Chad;TCD
632;Comoros;COM
638;Benin;BEN
642;Equatorial Guinea;GNQ
643;Eritrea;ERI
644;Ethiopia;ETH
646;Gabon;GAB
652;Ghana;GHA
654;Guinea-Bissau;GNB
656;Guinea;GIN
662;Côte d'Ivoire;CIV
664;Kenya;KEN
666;Lesotho;LSO
668;Liberia;LBR
672;Libya;LBY
674;Madagascar;MDG
676;Malawi;MWI
678;Mali;MLI
682;Mauritania;MRT
684;Mauritius;MUS
686;Morocco;MAR
688;Mozambique;MOZ
692;Niger;NER
694;Nigeria;NGA
698;Zimbabwe;ZWE
714;Rwanda;RWA
716;São Tomé and Príncipe;STP
718;Seychelles;SYC
722;Senegal;SEN
724;Sierra Leone;SLE
726;Somalia;SOM
728;Namibia;NAM
732;Sudan;SDN
733;South Sudan;SSD
734;Eswatini;SWZ
738;Tanzania;TZA
742;Togo;TGO
744;Tunisia;TUN
746;Uganda;UGA
748;Burkina Faso;BFA
754;Zambia;ZMB
813;Solomon Islands;SLB
819;Fiji;FJI
826;Kiribati;KIR
836;Nauru;NRU
846;Vanuatu;VUT
853;Papua New Guinea;PNG
862;Samoa;WSM
866;Tonga;TON
867;Marshall Islands;MHL
868;Micronesia;FSM
869;Tuvalu;TUV
911;Armenia;ARM
912;Azerbaijan;AZE
913;Belarus;BLR
914;Albania;ALB
915;Georgia;GEO
916;Kazakhstan;KAZ
917;Kyrgyz Republic;KGZ
918;Bulgaria;BGR
921;Moldova;MDA
922;Russia;RUS
923;Tajikistan;TJK
924;China;CHN
925;Turkmenistan;TKM
926;Ukraine;UKR
927;Uzbekistan;UZB
935;Czech Republic;CZE
936;Slovak Republic;SVK
939;Estonia;EST
941;Latvia;LVA
942;Serbia;SRB
944;Hungary;HUN
946;Lithuania;LTU
948;Mongolia;MNG
960;Croatia;HRV
961;Slovenia;SVN
962;North Macedonia;MKD
963;Bosnia and Herzegovina;BIH
964;Poland;POL
967;Kosovo;UVK
968;Romania;ROU
"""

# Códigos presentes no XML do FMI, mas ausentes do dicionário acima.
# ATENÇÃO: atribuição feita a partir dos metadados do XML; CONFERIR com a lista
# oficial de códigos do FMI antes de usar. Ficam desligados por padrão.
DICIONARIO_FMI_EXTRA_TXT = """
313;Bahamas;BHS
429;Iran;IRN
634;Congo (conferir);COG
636;Dem. Rep. of the Congo (conferir);COD
648;Gambia;GMB
"""

# Locale pt-BR do Vega/d3 (separador decimal vírgula, milhar ponto)
PT_FORMAT = {
    "decimal": ",",
    "thousands": ".",
    "grouping": [3],
    "currency": ["R$", ""],
}
PT_TIME_FORMAT = {
    "dateTime": "%A, %e de %B de %Y. %X",
    "date": "%d/%m/%Y",
    "time": "%H:%M:%S",
    "periods": ["AM", "PM"],
    "days": ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"],
    "shortDays": ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"],
    "months": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "shortMonths": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}
EMBED_OPTIONS = {"embedOptions": {"formatLocale": PT_FORMAT, "timeFormatLocale": PT_TIME_FORMAT}}

OPCOES_MEDIDA = ["Valor (bilhões US$)", "Participação (%)"]
COL_PART = "Participação no mundo (%)"

METODOLOGIA_MD = """
**Método para países sem dados no COMTRADE — Desempenho da Indústria no Mundo 2026**

1. Usa-se o indicador **TXG_RPCH** das projeções do FMI (World Economic Outlook), que mede a
   **taxa de crescimento das exportações apenas de bens**. A taxa é aplicada sobre o valor do
   **ano anterior** para obter o valor das exportações do ano sem dados.
2. Descrição do indicador na base do FMI (tradução): a variação percentual mede a mudança
   relativa de um valor ao longo do tempo, calculada pela diferença entre o valor atual e o
   anterior, dividida pelo valor anterior e multiplicada por 100.
3. Para países com dados faltantes de vários anos, a estimativa começa, **no mínimo, em {ano_min}**.
   A falta de dados em anos seguidos faz com que o valor das exportações do país seja uma
   **estimativa sobre outra estimativa**.
4. Depois de estimados os valores que faltavam, somam-se os valores de **todos os países**
   (estimados ou não) e calculam-se os **novos percentuais de participação** no mundo.
"""

# =============================================================================
# 2. UTILIDADES
# =============================================================================


def medida_desempenho(medida: str) -> str:
    """Traduz o rótulo do rádio para o nome da coluna."""
    return "Valor" if medida == OPCOES_MEDIDA[0] else COL_PART


def set_y_min(x):
    if pd.isna(x):
        return None
    return x * 1.05 if x < 0 else x * 0.95


def set_y_max(x):
    if pd.isna(x):
        return None
    return x * 0.95 if x < 0 else x * 1.05


def largura_total(funcao, *args, **kwargs):
    """Chama um elemento do Streamlit ocupando toda a largura, em qualquer versão.

    Versões novas usam width="stretch"; versões antigas usam use_container_width=True.
    """
    try:
        return funcao(*args, width="stretch", **kwargs)
    except TypeError:
        return funcao(*args, use_container_width=True, **kwargs)


def carregar_dicionario(usar_extras: bool = False) -> pd.DataFrame:
    """Dicionário FMI → ISO COMTRADE (já com TWN→S19)."""
    texto = DICIONARIO_FMI_TXT + (DICIONARIO_FMI_EXTRA_TXT if usar_extras else "")
    linhas = [l.split(";") for l in texto.strip().splitlines() if l.strip()]
    dic = pd.DataFrame(linhas, columns=["Code", "Descrição", "ISO"])
    dic["ISO"] = dic["ISO"].replace(ISO_FMI_PARA_COMTRADE)
    return dic


def para_excel(abas: dict) -> bytes:
    """Gera um .xlsx. `abas` = {nome: (DataFrame, incluir_indice)}."""
    saida = io.BytesIO()
    with pd.ExcelWriter(saida, engine="xlsxwriter") as escritor:
        for nome, (tabela, indice) in abas.items():
            tabela.to_excel(escritor, index=indice, sheet_name=nome[:31])
    return saida.getvalue()


# =============================================================================
# 3. LEITURA E VALIDAÇÃO DOS ARQUIVOS
# =============================================================================


@st.cache_data(show_spinner="Lendo o parquet do COMTRADE...")
def ler_parquet(conteudo: bytes) -> pd.DataFrame:
    df = pd.read_parquet(io.BytesIO(conteudo))
    faltando = [c for c in COLUNAS_PARQUET if c not in df.columns]
    if faltando:
        raise ValueError(
            f"colunas ausentes no parquet: {faltando}. Colunas encontradas: {list(df.columns)}"
        )
    df = df.rename(columns=COLUNAS_PARQUET)[list(COLUNAS_PARQUET.values())]
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce")
    df = df.dropna(subset=["Ano", "COU"])
    df["Ano"] = df["Ano"].astype(int)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce") / 1e9  # bilhões US$
    return df


def _achar_chave(dicionario: dict, sufixo: str):
    for chave, valor in dicionario.items():
        if chave.endswith(sufixo):
            return valor
    raise KeyError(f"elemento '*{sufixo}' não encontrado no XML")


def _como_lista(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


@st.cache_data(show_spinner="Lendo o XML do FMI...")
def ler_fmi(conteudo: bytes) -> pd.DataFrame:
    """Devolve DataFrame (Code, Ano, Taxa) apenas com o indicador TXG_RPCH."""
    dados = xmltodict.parse(conteudo)
    raiz = next(iter(dados.values()))
    dataset = _achar_chave(raiz, "DataSet")
    linhas = []
    for serie in _como_lista(dataset.get("Series")):
        if serie.get("@CONCEPT") != CONCEITO_FMI:
            continue
        for obs in _como_lista(serie.get("Obs")):
            linhas.append((serie.get("@REF_AREA"), obs.get("@TIME_PERIOD"), obs.get("@OBS_VALUE")))
    taxas = pd.DataFrame(linhas, columns=["Code", "Ano", "Taxa"])
    taxas["Ano"] = pd.to_numeric(taxas["Ano"], errors="coerce")
    taxas["Taxa"] = pd.to_numeric(taxas["Taxa"], errors="coerce")  # 'n/a' vira NaN
    taxas = taxas.dropna(subset=["Code", "Ano", "Taxa"])
    if taxas.empty:
        raise ValueError(f"nenhuma observação do indicador {CONCEITO_FMI} com valor numérico")
    taxas["Ano"] = taxas["Ano"].astype(int)
    return taxas


def montar_base(df: pd.DataFrame):
    """Tabela larga (país × ano) com NaN onde o país não reportou, e nomes dos países."""
    nomes = df.drop_duplicates("COU").set_index("COU")["País"]
    larga = df.groupby(["COU", "Ano"])["Valor"].sum(min_count=1).unstack("Ano")
    larga = larga.reindex(columns=range(int(larga.columns.min()), int(larga.columns.max()) + 1))
    return larga.rename_axis("COU"), nomes


# =============================================================================
# 4. ESTIMATIVA DOS PAÍSES SEM DADOS
# =============================================================================


def estimar(larga: pd.DataFrame, taxas_iso: pd.DataFrame, ano_inicio: int):
    """Preenche lacunas: V(t) = V(t-1) × (1 + TXG_RPCH(t)/100), de ano_inicio até o último ano.

    - Só preenche células vazias (NaN); dados reais nunca são alterados.
    - Anos seguidos sem dados são encadeados (estimativa sobre estimativa).
    - Sem valor no ano anterior ou sem taxa do FMI no ano, a célula continua vazia.
    Retorna (valores, flag_estimado, taxa_aplicada).
    """
    valores = larga.copy()
    estimado = pd.DataFrame(False, index=larga.index, columns=larga.columns)
    taxa_aplicada = pd.DataFrame(np.nan, index=larga.index, columns=larga.columns)
    taxas = taxas_iso.reindex(larga.index)
    ultimo = int(larga.columns.max())
    for ano in range(int(ano_inicio), ultimo + 1):
        if ano not in valores.columns or (ano - 1) not in valores.columns or ano not in taxas.columns:
            continue
        novo = valores[ano - 1] * (1 + taxas[ano] / 100)
        mascara = valores[ano].isna() & novo.notna()
        valores.loc[mascara, ano] = novo[mascara]
        estimado.loc[mascara, ano] = True
        taxa_aplicada.loc[mascara, ano] = taxas.loc[mascara, ano]
    return valores, estimado, taxa_aplicada


def diagnosticar(obs, valores, nomes, taxas_iso, isos_dicionario, ano_inicio, tem_fmi):
    """Lista os países que seguem sem valor no último ano e o motivo."""
    ano_fim = int(valores.columns.max())
    linhas = []
    for cou in valores.index[valores[ano_fim].isna()]:
        ultimo = obs.loc[cou].last_valid_index()
        if not tem_fmi:
            motivo = "XML do FMI não carregado"
        elif cou not in isos_dicionario:
            motivo = "ISO ausente no dicionário do FMI"
        elif cou not in taxas_iso.index or taxas_iso.loc[cou].dropna().empty:
            motivo = f"FMI sem série {CONCEITO_FMI} com valores"
        elif ultimo is None or ultimo < ano_inicio - 1:
            motivo = f"Último dado real anterior a {ano_inicio - 1}: sem base para a estimativa"
        else:
            motivo = "Taxa do FMI ausente em algum ano do intervalo"
        linhas.append({"COU": cou, "País": nomes.get(cou, cou), "Último ano com dado real": ultimo, "Motivo": motivo})
    return pd.DataFrame(linhas, columns=["COU", "País", "Último ano com dado real", "Motivo"])


def tabela_estimados(valores, estimado, taxa_aplicada, nomes) -> pd.DataFrame:
    linhas = []
    for i, j in np.argwhere(estimado.values):
        cou, ano = estimado.index[i], estimado.columns[j]
        linhas.append(
            {
                "COU": cou,
                "País": nomes.get(cou, cou),
                "Ano": int(ano),
                "Taxa FMI aplicada (%)": taxa_aplicada.iloc[i, j],
                "Valor estimado (bilhões US$)": valores.iloc[i, j],
            }
        )
    tabela = pd.DataFrame(
        linhas, columns=["COU", "País", "Ano", "Taxa FMI aplicada (%)", "Valor estimado (bilhões US$)"]
    )
    return tabela.sort_values(["País", "Ano"]).reset_index(drop=True)


def montar_longo(valores, estimado, nomes) -> pd.DataFrame:
    """Formato longo com a participação recalculada sobre a soma de TODOS os países."""
    v = valores.rename_axis("COU").reset_index().melt(id_vars="COU", var_name="Ano", value_name="Valor")
    e = estimado.rename_axis("COU").reset_index().melt(id_vars="COU", var_name="Ano", value_name="Estimado")
    longo = v.merge(e, on=["COU", "Ano"])
    longo["Ano"] = longo["Ano"].astype(int)
    longo["País"] = longo["COU"].map(nomes)
    longo[COL_PART] = longo["Valor"] / longo.groupby("Ano")["Valor"].transform("sum") * 100
    return longo.sort_values(["País", "Ano"]).reset_index(drop=True)


# =============================================================================
# 5. GRÁFICOS
# =============================================================================


def eixo_ano(titulo="Ano"):
    return alt.X("Ano:Q", axis=alt.Axis(format="d", tickMinStep=1, labelAngle=-90), title=titulo)


def grafico_linha(g1: pd.DataFrame, medida: str):
    col = medida_desempenho(medida)
    y_min, y_max = set_y_min(g1[col].min()), set_y_max(g1[col].max())
    escala = alt.Scale(domain=[y_min, y_max]) if y_min is not None else alt.Scale(zero=False)

    base = (
        alt.Chart(g1)
        .mark_line(strokeWidth=3)
        .encode(x=eixo_ano(), y=alt.Y(f"{col}:Q", scale=escala, title=medida), color="País:N")
    )

    # Tooltip: ponto, valor e régua no ano mais próximo do mouse
    proximo = alt.selection_point(nearest=True, on="mouseover", fields=["Ano"], empty=False, clear="click")
    seletores = alt.Chart(g1).mark_point().encode(x="Ano:Q", opacity=alt.value(0)).add_params(proximo)
    pontos = base.mark_point().encode(opacity=alt.condition(proximo, alt.value(1), alt.value(0)))
    textos = base.mark_text(align="left", dx=5, dy=-5).encode(
        text=alt.condition(proximo, alt.Text(f"{col}:Q", format=".2f"), alt.value(" "))
    )
    regua = alt.Chart(g1).mark_rule(color="gray").encode(x="Ano:Q").transform_filter(proximo)
    camadas = base + seletores + pontos + regua + textos

    # Losangos marcam valores estimados
    est = g1[g1["Estimado"] & g1[col].notna()]
    if not est.empty:
        marcas = (
            alt.Chart(est)
            .mark_point(shape="diamond", size=110, filled=True)
            .encode(x="Ano:Q", y=alt.Y(f"{col}:Q", scale=escala), color="País:N")
        )
        camadas = camadas + marcas
    camadas["usermeta"] = EMBED_OPTIONS
    return camadas


def grafico_variacao(g4: pd.DataFrame):
    barras = (
        alt.Chart(g4)
        .mark_bar()
        .encode(
            x=alt.X("Variação anual:Q", title="Variação anual"),
            y=alt.Y("País:N", sort="-x", title=None),
            color=alt.condition(alt.datum["Variação anual"] > 0, alt.value("#376092"), alt.value("#b90e0c")),
            tooltip=["País:N", alt.Tooltip("Variação anual:Q", format=".3f"), "Estimado:N"],
        )
    )
    texto = (
        alt.Chart(g4)
        .mark_text(align="left", dx=4, color="#000000")
        .encode(
            x="Variação anual:Q",
            y=alt.Y("País:N", sort="-x"),
            text=alt.Text("Variação anual:Q", format=".3f"),
        )
    )
    grafico = (barras + texto).properties(height=800)
    grafico["usermeta"] = EMBED_OPTIONS
    return grafico


def grafico_ranking(df: pd.DataFrame, medida: str, top_n: int):
    """Ranking por ano com controle deslizante (substitui o antigo bar_chart_race)."""
    col = medida_desempenho(medida)
    base = df.dropna(subset=[col]).sort_values(["Ano", col], ascending=[True, False])
    base = base.groupby("Ano").head(top_n).copy()
    base[col] = base[col].round(2)

    seletor_ano = alt.binding_range(min=int(base["Ano"].min()), max=int(base["Ano"].max()), step=1, name="Ano ")
    ano_sel = alt.selection_point(name="Year", fields=["Ano"], bind=seletor_ano, value=int(base["Ano"].max()))

    barras = (
        alt.Chart(base)
        .mark_bar()
        .encode(
            x=alt.X(f"{col}:Q", title=medida, scale=alt.Scale(domain=[0, set_y_max(base[col].max())])),
            y=alt.Y("País:N", sort="-x", axis=alt.Axis(minExtent=180)),
            color=alt.condition(alt.datum.País == "Brazil", alt.value("orange"), alt.value("grey")),
        )
        .add_params(ano_sel)
        .transform_filter(ano_sel)
    )
    texto = barras.mark_text(align="left", baseline="middle", dx=3).encode(
        text=alt.Text(f"{col}:Q", format=".2f")
    )
    grafico = barras + texto
    grafico["usermeta"] = EMBED_OPTIONS
    return grafico


# =============================================================================
# 6. PÁGINAS
# =============================================================================


def pagina_inicial():
    st.title("🌍 Desempenho da Indústria no Mundo")
    st.markdown(
        "Análise das exportações de manufaturados por país a partir do **COMTRADE**, "
        "com **estimativa dos países sem dados** usando as projeções do **FMI**."
    )

    st.subheader("Como usar")
    st.markdown(
        """
1. No menu lateral, abra **Desempenho da Indústria no Mundo**.
2. Envie o arquivo **Parquet** do COMTRADE (extração do notebook *COMTRADE Desempenho Indústria no mundo*, Databricks).
3. Envie o arquivo **XML** das projeções do FMI (World Economic Outlook, indicador `TXG_RPCH`).
   Sem o XML, o app mostra apenas os dados observados, sem estimativas.
4. Escolha o ano em que a estimativa começa e explore os gráficos. **◆ losangos** e células em **amarelo**
   indicam valores estimados.
5. Baixe os dados em Excel (inclui as abas de valores estimados, países sem projeção e metodologia).
        """
    )

    st.subheader("Metodologia")
    st.markdown(METODOLOGIA_MD.format(ano_min=ANO_MIN_ESTIMATIVA))
    st.markdown("Fórmula aplicada a cada país *i* e ano *t* sem dado:")
    st.latex(r"V_{i,t} = V_{i,t-1} \times \left(1 + \frac{TXG\_RPCH_{i,t}}{100}\right)")

    with st.expander("Dependências (requirements.txt)"):
        st.code(
            "streamlit>=1.37\npandas>=2.2\nnumpy\naltair>=5\npyarrow\nxmltodict\nxlsxwriter\nopenpyxl",
            language="text",
        )
    with st.expander("Dicionário de países do FMI embutido no código"):
        largura_total(st.dataframe, carregar_dicionario(False), hide_index=True)


@st.fragment
def painel(longo: pd.DataFrame, estimados: pd.DataFrame, diagnostico: pd.DataFrame, metodologia: str):
    """Parte interativa: só ela é reexecutada ao mexer nos filtros."""
    medida = st.radio("Medida", OPCOES_MEDIDA, index=1, horizontal=True, key="medida")
    col = medida_desempenho(medida)
    anos = sorted(longo["Ano"].unique())

    # ---- Evolução por país
    st.markdown("#### Evolução país")
    paises = sorted(longo["País"].dropna().unique())
    sel = st.multiselect("País", paises, default=[p for p in ["Brazil"] if p in paises], key="paises")
    if len(anos) > 1:
        ini, fim = st.select_slider("Intervalo", options=anos, value=(anos[0], anos[-1]), key="intervalo")
    else:
        ini, fim = anos[0], anos[0]
    g1 = longo[longo["País"].isin(sel) & longo["Ano"].between(ini, fim)]
    if g1[col].notna().any():
        largura_total(st.altair_chart, grafico_linha(g1, medida), theme=None)
        if g1["Estimado"].any():
            st.caption("◆ = valor estimado com a taxa TXG_RPCH do FMI.")
    else:
        st.info("Selecione ao menos um país com dados no intervalo.")

    # ---- Variação anual
    st.markdown("#### Variação anual: 15 maiores e 15 menores")
    g4 = longo.sort_values(["País", "Ano"]).copy()
    g4["Variação anual"] = g4.groupby("País")[col].diff()
    ano_var = st.select_slider("Ano variações", options=anos, value=anos[-1], key="ano_var")
    g4 = g4[(g4["Ano"] == ano_var)].dropna(subset=["Variação anual"]).sort_values("Variação anual", ascending=False)
    g4 = pd.concat([g4.head(15), g4.tail(15)]).drop_duplicates("COU")
    if g4.empty:
        st.info("Sem variações calculáveis para o ano escolhido.")
    else:
        g4["Estimado"] = g4["Estimado"].map({True: "estimado", False: "observado"})
        largura_total(st.altair_chart, grafico_variacao(g4), theme=None)

    # ---- Ranking
    st.markdown("#### Evolução ranking países")
    if len(anos) > 1:
        largura_total(st.altair_chart, grafico_ranking(longo, medida, 40), theme=None)

    # ---- Dados detalhados
    st.markdown("#### Dados detalhados")
    g3 = longo.pivot(columns="Ano", index="País", values=col)
    g3 = g3.sort_values(g3.columns.max(), ascending=False)
    marca = longo.pivot(columns="Ano", index="País", values="Estimado").reindex(index=g3.index, columns=g3.columns)
    marca = marca.fillna(False).astype(bool)
    g3.columns = g3.columns.astype(str)
    marca.columns = g3.columns
    estilo = g3.style.apply(
        lambda d: np.where(marca.values, "background-color: #FFF2CC", ""), axis=None
    ).format("{:.2f}", na_rep="")
    largura_total(st.dataframe, estilo)
    st.caption("Células em amarelo = valores estimados.")

    # ---- Tabelas de apoio
    with st.expander(f"Valores estimados ({len(estimados)})"):
        largura_total(st.dataframe, estimados, hide_index=True)
    with st.expander(f"Países sem valor no último ano ({len(diagnostico)})"):
        largura_total(st.dataframe, diagnostico, hide_index=True)

    # ---- Download
    g1x = g1.drop(columns=["COU"]).copy()
    g4x = g4.drop(columns=["COU"]).copy()
    arquivo = para_excel(
        {
            "Evolução país": (g1x, False),
            "Variação anual": (g4x, False),
            "Dados detalhados": (g3, True),
            "Valores estimados": (estimados, False),
            "Países sem projeção": (diagnostico, False),
            "Metodologia": (pd.DataFrame({"Metodologia": metodologia.strip().splitlines()}), False),
        }
    )
    largura_total(
        st.download_button,
        label="📥 Baixar dados",
        data=arquivo,
        file_name="Dados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download",
    )


def pagina_comtrade():
    st.title("📉 Desempenho da Indústria no Mundo")

    col1, col2 = st.columns(2)
    with col1:
        arq_parquet = st.file_uploader(
            "Arquivo Parquet (COMTRADE)",
            type="parquet",
            key="bd",
            help='Parquet com a extração da Comtrade do notebook "COMTRADE Desempenho Indústria no mundo" (Databricks).',
        )
    with col2:
        arq_xml = st.file_uploader(
            "Arquivo XML de projeções do FMI",
            type="xml",
            key="fmi",
            help="XML do World Economic Outlook do FMI detalhado por país (indicador TXG_RPCH).",
        )

    if arq_parquet is None:
        st.info(
            "Envie o arquivo **Parquet** do COMTRADE para continuar. "
            "O XML do FMI é opcional, mas sem ele não há estimativa para os países sem dados.",
            icon="ℹ️",
        )
        return

    # --- Leitura do parquet
    try:
        base = ler_parquet(arq_parquet.getvalue())
    except Exception as e:
        st.error(f"Erro ao ler o parquet: {e}. Verifique se é o arquivo correto e tente novamente.", icon="🚨")
        return
    obs, nomes = montar_base(base)
    ano_fim = int(obs.columns.max())

    # --- Estimativa
    estimado = pd.DataFrame(False, index=obs.index, columns=obs.columns)
    taxa_aplicada = pd.DataFrame(np.nan, index=obs.index, columns=obs.columns)
    valores = obs.copy()
    taxas_iso = pd.DataFrame()
    isos_dic = set()
    ano_ini = ANO_MIN_ESTIMATIVA
    tem_fmi = arq_xml is not None

    if tem_fmi:
        try:
            taxas = ler_fmi(arq_xml.getvalue())
        except Exception as e:
            st.error(f"Erro ao ler o XML do FMI: {e}. Verifique o arquivo enviado e tente novamente.", icon="🚨")
            return

        c1, c2 = st.columns([1, 2])
        with c1:
            opcoes = list(range(ANO_MIN_ESTIMATIVA, ano_fim + 1)) or [ano_fim]
            ano_ini = st.selectbox(
                "Iniciar estimativa FMI em",
                options=opcoes,
                index=0,
                help=f"Pela metodologia, a estimativa começa no mínimo em {ANO_MIN_ESTIMATIVA}.",
            )
        with c2:
            usar_extras = st.checkbox(
                "Incluir códigos FMI adicionais (Bahamas, Irã, Congo, RD Congo, Gâmbia)",
                value=False,
                help="Códigos que estão no XML mas não no dicionário original. Conferir com a lista oficial do FMI.",
            )

        dic = carregar_dicionario(usar_extras)
        isos_dic = set(dic["ISO"])
        taxas["ISO"] = taxas["Code"].map(dict(zip(dic["Code"], dic["ISO"])))
        sem_iso = taxas.loc[taxas["ISO"].isna(), "Code"].nunique()
        taxas_iso = taxas.dropna(subset=["ISO"]).pivot_table(
            index="ISO", columns="Ano", values="Taxa", aggfunc="mean"
        )
        valores, estimado, taxa_aplicada = estimar(obs, taxas_iso, int(ano_ini))
        st.caption(
            f"{sem_iso} códigos do XML não constam no dicionário (inclui agregados regionais, como zona do euro e mundo)."
        )
    else:
        st.info("XML do FMI não enviado: exibindo apenas os dados observados, sem estimativas.", icon="ℹ️")

    # --- Resumo
    diag = diagnosticar(obs, valores, nomes, taxas_iso, isos_dic, int(ano_ini), tem_fmi)
    estimados = tabela_estimados(valores, estimado, taxa_aplicada, nomes)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Países com dado real em {ano_fim}", int(obs[ano_fim].notna().sum()))
    m2.metric(f"Estimados em {ano_fim}", int(estimado[ano_fim].sum()))
    m3.metric(f"Sem valor em {ano_fim}", int(valores[ano_fim].isna().sum()))
    m4.metric("Total de valores estimados", int(estimado.values.sum()))

    longo = montar_longo(valores, estimado, nomes)
    painel(longo, estimados, diag, METODOLOGIA_MD.format(ano_min=ANO_MIN_ESTIMATIVA))


def main():
    st.set_page_config(
        page_title="Desempenho da Indústria no Mundo",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    pg = st.navigation(
        [
            st.Page(pagina_inicial, title="Início", icon="🏠", default=True),
            st.Page(pagina_comtrade, title="Desempenho da Indústria no Mundo", icon="📉"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
