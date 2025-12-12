import streamlit as st
import pandas as pd
from ofxparse import OfxParser
import io
import json
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Organizador Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DADOS PADRÃO ---
DEFAULT_TERMOS_INTERNOS = [
    {'Termo': 'RESG', 'Tipo': 'Investimento'},
    {'Termo': 'RESGATE', 'Tipo': 'Investimento'},
    {'Termo': 'APLIC', 'Tipo': 'Investimento'},
    {'Termo': 'APLICACAO', 'Tipo': 'Investimento'},
    {'Termo': 'INVEST', 'Tipo': 'Investimento'},
    {'Termo': 'POUP', 'Tipo': 'Poupança'},
    {'Termo': 'CDB', 'Tipo': 'Investimento'},
    {'Termo': 'TESOURO', 'Tipo': 'Investimento'},
    {'Termo': 'TRANSF CONT', 'Tipo': 'Transferência'},
    {'Termo': 'ENTRE CONTAS', 'Tipo': 'Transferência'},
    {'Termo': 'AUTOMATICO', 'Tipo': 'Transferência'},
    {'Termo': 'NOME', 'Tipo': 'Pessoal'}
]

DEFAULT_REGRAS = [
    {'Palavra_Chave': 'UBER', 'Categoria': 'Transporte'},
    {'Palavra_Chave': '99POP', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'POSTO', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'IFOOD', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'RESTAURANTE', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'MERCADO', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'ATACADAO', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'NETFLIX', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'VIVO', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'LUZ', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'FARMACIA', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'PIX ENVIADO', 'Categoria': 'Transferências/PIX'},
    {'Palavra_Chave': 'SALARIO', 'Categoria': 'Renda'},
    {'Palavra_Chave': 'PIX RECEBIDO', 'Categoria': 'Entradas Diversas'}
]

# --- FUNÇÕES ---
def carregar_configuracoes(arquivo_json):
    """Carrega as regras salvas pelo usuário"""
    try:
        dados = json.load(arquivo_json)
        df_regras = pd.DataFrame(dados.get('regras', DEFAULT_REGRAS))
        df_internos = pd.DataFrame(dados.get('internos', DEFAULT_TERMOS_INTERNOS))
        return df_regras, df_internos
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de configuração: {e}")
        return None, None

def categorizar(descricao, valor, df_regras, df_internos):
    if not descricao: return 'Outros'
    descricao = str(descricao).upper()
    
    termos_internos = df_internos['Termo'].str.upper().tolist()
    regras_dict = dict(zip(df_regras['Palavra_Chave'].str.upper(), df_regras['Categoria']))

    # 1. Movimentação Interna
    for termo in termos_internos:
        if termo in descricao:
            for chave, categoria in regras_dict.items():
                if chave in descricao and categoria == 'Renda':
                    return 'Entradas/Renda'
            return 'Movimentação Interna'

    # 2. Renda
    if valor > 0: return 'Entradas/Renda'
    
    # 3. Regras de Gastos
    for chave, categoria in regras_dict.items():
        if chave in descricao: return categoria
            
    return 'Outros'

def processar_arquivos(uploaded_files, df_regras, df_internos):
    transacoes = []
    for uploaded_file in uploaded_files:
        try:
            content = uploaded_file.read().decode("ISO-8859-1")
            file_obj = io.StringIO(content)
            ofx = OfxParser.parse(file_obj)
            
            if ofx.account and ofx.account.statement:
                for t in ofx.account.statement.transactions:
                    valor = float(t.amount)
                    desc = t.memo if t.memo else "Sem Descrição"
                    cat = categorizar(desc, valor, df_regras, df_internos)
                    
                    if cat == 'Movimentação Interna': tipo = 'Neutro'
                    else: tipo = 'Entrada' if valor > 0 else 'Saída'

                    transacoes.append({
                        'Data': t.date.date(),
                        'Descrição': desc,
                        'Categoria': cat,
                        'Valor': valor,
                        'Tipo': tipo,
                        'ID_Transacao': t.id
                    })
        except Exception as e:
            st.error(f"Erro em {uploaded_file.name}: {e}")
    return pd.DataFrame(transacoes)

def gerar_excel(df):
    output = io.BytesIO()
    df_resumo = df.groupby('Categoria')['Valor'].sum().reset_index().sort_values('Valor')
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Extrato', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        wb = writer.book
        ws = writer.sheets['Extrato']
        fmt_moeda = wb.add_format({'num_format': 'R$ #,##0.00'})
        fmt_verd = wb.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': 'R$ #,##0.00'})
        fmt_verm = wb.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': 'R$ #,##0.00'})
        
        ws.set_column('D:D', 18, fmt_moeda) # Coluna Valor
        
        ws.conditional_format('D2:D1000', {'type': 'cell', 'criteria': '<', 'value': 0, 'format': fmt_verm})
        ws.conditional_format('D2:D1000', {'type': 'cell', 'criteria': '>', 'value': 0, 'format': fmt_verd})
        
    output.seek(0)
    return output

# --- APP PRINCIPAL ---
def main():
    st.sidebar.title("⚙️ Configurações")

    # 1. CARREGAR CONFIGURAÇÃO EXISTENTE
    config_file = st.sidebar.file_uploader("📂 Carregar Minhas Regras (Opcional)", type=['json'])
    
    # Inicializa ou atualiza o estado
    if 'df_regras' not in st.session_state:
        st.session_state['df_regras'] = pd.DataFrame(DEFAULT_REGRAS)
        st.session_state['df_internos'] = pd.DataFrame(DEFAULT_TERMOS_INTERNOS)
    
    if config_file is not None:
        # Se o usuário subiu um arquivo JSON, atualiza os dados
        regras, internos = carregar_configuracoes(config_file)
        if regras is not None:
            st.session_state['df_regras'] = regras
            st.session_state['df_internos'] = internos
            st.sidebar.success("Regras carregadas!")

    # 2. EDITORES
    with st.sidebar.expander("📝 Editar Regras de Categoria", expanded=False):
        st.session_state['df_regras'] = st.data_editor(st.session_state['df_regras'], num_rows="dynamic")

    with st.sidebar.expander("🔄 Editar Termos Internos", expanded=False):
        st.session_state['df_internos'] = st.data_editor(st.session_state['df_internos'], num_rows="dynamic")

    # 3. BOTÃO DE SALVAR (EXPORTAR)
    st.sidebar.markdown("---")
    st.sidebar.write("Gostou das regras? Salve para usar depois:")
    
    # Prepara o JSON para download
    dados_para_salvar = {
        'regras': st.session_state['df_regras'].to_dict(orient='records'),
        'internos': st.session_state['df_internos'].to_dict(orient='records')
    }
    json_bytes = json.dumps(dados_para_salvar, indent=4).encode('utf-8')
    
    st.sidebar.download_button(
        label="💾 Salvar Minhas Regras",
        data=json_bytes,
        file_name="minhas_regras_financas.json",
        mime="application/json"
    )

    # --- ÁREA PRINCIPAL ---
    st.title("💰 Organizador Financeiro")
    st.info("Arraste seus extratos bancários (OFX) e, opcionalmente, seu arquivo de regras salvo na barra lateral.")

    uploaded_files = st.file_uploader("Arquivos OFX do Banco", type=['ofx'], accept_multiple_files=True)

    if uploaded_files:
        df = processar_arquivos(uploaded_files, st.session_state['df_regras'], st.session_state['df_internos'])
        
        if not df.empty:
            # Métricas
            ent = df[df['Tipo']=='Entrada']['Valor'].sum()
            sai = df[df['Tipo']=='Saída']['Valor'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Entradas", f"R$ {ent:,.2f}")
            col2.metric("Saídas", f"R$ {sai:,.2f}")
            col3.metric("Saldo", f"R$ {ent+sai:,.2f}")

            # Visualização
            st.dataframe(df, use_container_width=True)

            # Download Excel
            st.download_button(
                "📥 Baixar Planilha Excel",
                data=gerar_excel(df),
                file_name=f"Financas_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

if __name__ == "__main__":
    main()