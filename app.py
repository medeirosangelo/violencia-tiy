import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Monitoramento TI Yanomami",
    page_icon="🛡️",
    layout="wide"
)

# --- FUNÇÃO DE CARREGAMENTO E CACHE ---
@st.cache_data
def load_data():
    # Caminho fixo conforme solicitado
    caminho = r"C:\Users\angelo.medeiros\Documents\Violencia TIY\HGR-violencia-tiy.xlsx"
    
    try:
        df = pd.read_excel(caminho)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None

    # --- TRATAMENTO DE DADOS (Igual ao Jupyter) ---
    # 1. Filtro Sexo Feminino
    if 'CS_SEXO' in df.columns:
        df = df[df['CS_SEXO'].isin(['F', '2', 2])].copy()
    
    # 2. Datas
    cols_data = ['DT_NOTIFIC', 'DT_NASC', 'DT_OCOR']
    for col in cols_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    df['ANO_NOTIFICACAO'] = df['DT_NOTIFIC'].dt.year

    # 3. Idade e Faixa Etária
    df['IDADE_CALCULADA'] = (df['DT_NOTIFIC'] - df['DT_NASC']).dt.days // 365.25
    bins = [0, 9, 19, 24, 59, 120]
    labels = ['Criança (0-9)', 'Adolescente (10-19)', 'Jovem (20-24)', 'Adulta (25-59)', 'Idosa (60+)']
    df['FAIXA_ETARIA'] = pd.cut(df['IDADE_CALCULADA'], bins=bins, labels=labels, right=True)

    # 4. Mapeamentos
    map_sinan = {1: 'Sim', 2: 'Não', 9: 'Ignorado', 3: 'Não se aplica', 8: 'Não se aplica'}
    
    if 'AUTOR_ALCO' in df.columns:
        df['ALCOOL_DESC'] = df['AUTOR_ALCO'].map(map_sinan).fillna('Ignorado')
    
    # Mapeamento Conjugal
    map_conjugal = {1: 'Solteira', 2: 'Casada/União', 3: 'Viúva', 4: 'Separada', 8: 'N/A', 9: 'Ignorado'}
    if 'SIT_CONJUG' in df.columns:
        df['SIT_CONJUG_DESC'] = df['SIT_CONJUG'].map(map_conjugal).fillna('Ignorado')

    return df

# Carrega os dados
df = load_data()

if df is not None:
    # --- SIDEBAR (FILTROS) ---
    st.sidebar.header("Filtros")
    
    anos_disponiveis = sorted(df['ANO_NOTIFICACAO'].dropna().unique().astype(int))
    anos_sel = st.sidebar.multiselect("Selecione o Ano", anos_disponiveis, default=anos_disponiveis)
    
    # Filtrar DataFrame
    df_filtered = df[df['ANO_NOTIFICACAO'].isin(anos_sel)]

    # --- TÍTULO E KPIs ---
    st.title("🛡️ Painel de Monitoramento: Violência na TI Yanomami")
    st.markdown("**Fonte:** HGR / SINAN | **Recorte:** Mulheres e Meninas (2019-2024)")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Casos Notificados", len(df_filtered))
    with col2:
        # Contagem de Violência Física
        viol_fisica = len(df_filtered[df_filtered['VIOL_FISIC'] == 1])
        st.metric("Casos c/ Violência Física", viol_fisica)
    with col3:
        # Uso de Álcool
        alcool_sim = len(df_filtered[df_filtered.get('AUTOR_ALCO') == 1])
        pct_alcool = (alcool_sim / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
        st.metric("Suspeita de Álcool (Autor)", f"{pct_alcool:.1f}%", help="Porcentagem de casos onde houve uso de álcool pelo autor")
    with col4:
        # Faixa Etária Principal
        top_faixa = df_filtered['FAIXA_ETARIA'].value_counts().idxmax() if not df_filtered.empty else "-"
        st.metric("Faixa Etária + Atingida", top_faixa)

    # --- LINHA 1: PERFIL DA VÍTIMA ---
    st.markdown("### 1. Perfil da Vítima")
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        # Gráfico de Faixa Etária
        contagem_etaria = df_filtered['FAIXA_ETARIA'].value_counts().sort_index().reset_index()
        contagem_etaria.columns = ['Faixa Etária', 'Qtd']
        
        fig_etaria = px.bar(
            contagem_etaria, x='Faixa Etária', y='Qtd', 
            text='Qtd', title="Distribuição por Faixa Etária",
            color_discrete_sequence=['#FF6B6B']
        )
        st.plotly_chart(fig_etaria, use_container_width=True)

    with row1_col2:
        # Gráfico Situação Conjugal
        if 'SIT_CONJUG_DESC' in df_filtered.columns:
            contagem_conjugal = df_filtered['SIT_CONJUG_DESC'].value_counts().reset_index()
            contagem_conjugal.columns = ['Situação', 'Qtd']
            
            fig_conjugal = px.pie(
                contagem_conjugal, names='Situação', values='Qtd', 
                title="Situação Conjugal", hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_conjugal, use_container_width=True)

    # --- LINHA 2: CARACTERÍSTICAS DA VIOLÊNCIA ---
    st.markdown("### 2. Características da Violência")
    row2_col1, row2_col2 = st.columns([2, 1])

    with row2_col1:
        # Tipos de Violência (Multiplas escolhas)
        cols_violencia = {
            'VIOL_FISIC': 'Física', 'VIOL_PSICO': 'Psicológica', 'VIOL_SEXU': 'Sexual', 
            'VIOL_TORT': 'Tortura', 'VIOL_FINAN': 'Patrimonial', 'VIOL_NEGLI': 'Negligência'
        }
        dados_violencia = {}
        for col, nome in cols_violencia.items():
            if col in df_filtered.columns:
                dados_violencia[nome] = len(df_filtered[df_filtered[col] == 1])
        
        df_viol_tipo = pd.DataFrame(list(dados_violencia.items()), columns=['Tipo', 'Qtd']).sort_values('Qtd', ascending=True)
        
        fig_viol = px.bar(
            df_viol_tipo, x='Qtd', y='Tipo', orientation='h', text='Qtd',
            title="Tipos de Violência (Múltipla escolha)",
            color='Qtd', color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_viol, use_container_width=True)

    with row2_col2:
        # Meio Utilizado (Top 5)
        cols_meio = [c for c in df_filtered.columns if c.startswith('AG_') and c != 'AG_OUTROS']
        dados_meio = {}
        for col in cols_meio:
            qtd = len(df_filtered[df_filtered[col] == 1])
            if qtd > 0:
                nome_limpo = col.replace('AG_', '').title()
                dados_meio[nome_limpo] = qtd
        
        df_meio = pd.DataFrame(list(dados_meio.items()), columns=['Meio', 'Qtd']).sort_values('Qtd', ascending=False).head(5)
        
        fig_meio = px.bar(
            df_meio, x='Meio', y='Qtd', title="Meios + Utilizados (Top 5)",
            color_discrete_sequence=['#FFA07A']
        )
        st.plotly_chart(fig_meio, use_container_width=True)

    # --- LINHA 3: O AGRESSOR ---
    st.markdown("### 3. Perfil do Provável Autor")
    row3_col1, row3_col2, row3_col3 = st.columns(3)

    with row3_col1:
        # Vínculo
        cols_vinculo = [c for c in df_filtered.columns if c.startswith('REL_') and c != 'REL_TRAB']
        dados_vinculo = {}
        for col in cols_vinculo:
            qtd = len(df_filtered[df_filtered[col] == 1])
            if qtd > 0:
                nome_limpo = col.replace('REL_', '').title()
                dados_vinculo[nome_limpo] = qtd
        
        df_vinculo = pd.DataFrame(list(dados_vinculo.items()), columns=['Vínculo', 'Qtd']).sort_values('Qtd', ascending=False).head(7)
        
        fig_vinculo = px.bar(
            df_vinculo, x='Vínculo', y='Qtd', title="Vínculo com a Vítima",
            color_discrete_sequence=['#4682B4']
        )
        st.plotly_chart(fig_vinculo, use_container_width=True)

    with row3_col2:
        # Uso de Álcool
        if 'ALCOOL_DESC' in df_filtered.columns:
            alcool_counts = df_filtered['ALCOOL_DESC'].value_counts().reset_index()
            alcool_counts.columns = ['Uso Álcool', 'Qtd']
            
            fig_alcool = px.pie(
                alcool_counts, names='Uso Álcool', values='Qtd', 
                title="Suspeita de Uso de Álcool",
                color_discrete_map={'Sim': '#FF4B4B', 'Não': '#87CEEB', 'Ignorado': '#D3D3D3'}
            )
            st.plotly_chart(fig_alcool, use_container_width=True)

    with row3_col3:
        # Sexo do Autor
        if 'AUTOR_SEXO' in df_filtered.columns:
            map_sexo = {1: 'Masculino', 2: 'Feminino', 3: 'Ambos', 9: 'Ignorado'}
            df_filtered['SEXO_AUTOR_DESC'] = df_filtered['AUTOR_SEXO'].map(map_sexo).fillna('Ignorado')
            sexo_counts = df_filtered['SEXO_AUTOR_DESC'].value_counts().reset_index()
            sexo_counts.columns = ['Sexo', 'Qtd']
            
            fig_sexo = px.pie(sexo_counts, names='Sexo', values='Qtd', title="Sexo do Autor", hole=0.4)
            st.plotly_chart(fig_sexo, use_container_width=True)

    # --- RODAPÉ ---
    st.markdown("---")
    st.info("Painel Desenvolvido para o Projeto Enfrentamento à violência contra mulheres e crianças Yanomami e Ye'kwana (CoMulheres/CGAJ/DHPS).")

else:
    st.warning("Aguardando carregamento dos dados.")