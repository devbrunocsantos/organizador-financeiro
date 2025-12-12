import streamlit as st
import pandas as pd
from ofxparse import OfxParser
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Organizador Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (Opcional, para dar um toque mais 'App') ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DADOS INICIAIS (PADRÕES) ---
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

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO ---
def inicializar_session_state():
    """Gerencia o estado da sessão para persistir as regras editadas pelo usuário."""
    if 'df_regras' not in st.session_state:
        st.session_state['df_regras'] = pd.DataFrame(DEFAULT_REGRAS)
    if 'df_internos' not in st.session_state:
        st.session_state['df_internos'] = pd.DataFrame(DEFAULT_TERMOS_INTERNOS)

def categorizar(descricao, valor, df_regras, df_internos):
    """
    Função de categorização adaptada para ler dos DataFrames configuráveis.
    """
    if not descricao: return 'Outros'
    descricao = str(descricao).upper()
    
    # 1. Checa Movimentação Interna
    termos_internos = df_internos['Termo'].str.upper().tolist()
    
    # Cria dicionário de regras para busca rápida
    # Prioridade para regras de Renda dentro da checagem interna
    regras_dict = dict(zip(df_regras['Palavra_Chave'].str.upper(), df_regras['Categoria']))

    for termo in termos_internos:
        if termo in descricao:
            # Verifica exceção de Renda mesmo se parecer interno
            for chave, categoria in regras_dict.items():
                if chave in descricao and categoria == 'Renda':
                    return 'Entradas/Renda'
            return 'Movimentação Interna'

    # 2. Checa Renda
    if valor > 0: 
        return 'Entradas/Renda'
    
    # 3. Checa Regras de Gastos
    for chave, categoria in regras_dict.items():
        if chave in descricao: 
            return categoria
            
    return 'Outros'

def processar_arquivos(uploaded_files, df_regras, df_internos):
    """Processa a lista de arquivos OFX enviados via upload."""
    transacoes = []
    
    for uploaded_file in uploaded_files:
        try:
            # O OfxParser precisa de um arquivo em bytes ou string, o Streamlit fornece bytes
            # Decodificado para garantir leitura correta (ISO-8859-1 é padrão bancário BR)
            content = uploaded_file.read().decode("ISO-8859-1")
            file_obj = io.StringIO(content)
            
            ofx = OfxParser.parse(file_obj)
            
            if ofx.account and ofx.account.statement:
                for t in ofx.account.statement.transactions:
                    valor = float(t.amount)
                    desc = t.memo if t.memo else "Sem Descrição"
                    
                    cat = categorizar(desc, valor, df_regras, df_internos)
                    
                    if cat == 'Movimentação Interna':
                        tipo_transacao = 'Neutro'
                    else:
                        tipo_transacao = 'Entrada' if valor > 0 else 'Saída'

                    transacoes.append({
                        'Data': t.date.date(),
                        'Descrição': desc,
                        'Categoria': cat,
                        'Valor': valor,
                        'Tipo': tipo_transacao,
                        'ID_Transacao': t.id,
                        'Arquivo_Origem': uploaded_file.name
                    })
        except Exception as e:
            st.error(f"Erro ao ler {uploaded_file.name}: {e}")
            
    return pd.DataFrame(transacoes)

def gerar_excel_bytes(df_final):
    """
    Gera o arquivo Excel em memória (buffer) para download,
    mantendo toda a sua lógica visual original.
    """
    output = io.BytesIO()
    
    # Prepara resumo
    df_resumo = df_final.groupby('Categoria')['Valor'].sum().reset_index()
    df_resumo = df_resumo.sort_values(by='Valor', ascending=True)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Extrato Detalhado', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo Gerencial', index=False)

        workbook = writer.book
        ws_extrato = writer.sheets['Extrato Detalhado']
        ws_resumo = writer.sheets['Resumo Gerencial']

        # --- ESTILOS ORIGINAIS ---
        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
        fmt_verm = workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': 'R$ #,##0.00'})
        fmt_verd = workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': 'R$ #,##0.00'})
        fmt_neutro = workbook.add_format({'font_color': '#333333', 'bg_color': '#E0E0E0', 'num_format': 'R$ #,##0.00'})
        
        # Ajuste de Colunas (Lógica simplificada para App)
        ws_extrato.set_column('A:Z', 20)
        ws_resumo.set_column('A:Z', 20)
        
        # Formatação Moeda
        idx_v_ext = df_final.columns.get_loc('Valor')
        ws_extrato.set_column(idx_v_ext, idx_v_ext, 18, fmt_moeda)
        
        idx_v_res = df_resumo.columns.get_loc('Valor')
        ws_resumo.set_column(idx_v_res, idx_v_res, 18, fmt_moeda)

        # Tabelas
        (max_row, max_col) = df_final.shape
        if max_row > 0:
            ws_extrato.add_table(0, 0, max_row, max_col - 1, {
                'columns': [{'header': col} for col in df_final.columns],
                'style': 'TableStyleMedium9',
                'name': 'TabelaExtrato'
            })
        
        # Formatação Condicional
        idx_cat = df_final.columns.get_loc('Categoria')
        letra_cat = chr(65 + idx_cat)
        
        ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {
            'type': 'formula', 'criteria': f'=${letra_cat}2="Movimentação Interna"', 'format': fmt_neutro
        })
        ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {
            'type': 'cell', 'criteria': '<', 'value': 0, 'format': fmt_verm
        })
        ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {
            'type': 'cell', 'criteria': '>', 'value': 0, 'format': fmt_verd
        })

        # Gráfico
        (mr_res, mc_res) = df_resumo.shape
        if mr_res > 0:
            ws_resumo.add_table(0, 0, mr_res, mc_res - 1, {'columns': [{'header': col} for col in df_resumo.columns], 'style': 'TableStyleMedium2'})
            chart = workbook.add_chart({'type': 'pie'})
            chart.add_series({
                'name': 'Balanço Financeiro',
                'categories': ['Resumo Gerencial', 1, 0, mr_res, 0],
                'values':     ['Resumo Gerencial', 1, 1, mr_res, 1],
                'data_labels': {'value': True, 'num_format': 'R$ #,##0'},
            })
            ws_resumo.insert_chart('D2', chart)

    output.seek(0)
    return output

# --- INTERFACE PRINCIPAL ---
def main():
    inicializar_session_state()

    # --- SIDEBAR: CONFIGURAÇÕES ---
    with st.sidebar:
        st.header("⚙️ Configurações")
        st.info("Edite as tabelas abaixo para personalizar a categorização.")
        
        with st.expander("📝 Regras de Categoria", expanded=False):
            st.caption("Associe palavras-chave a categorias.")
            st.session_state['df_regras'] = st.data_editor(
                st.session_state['df_regras'], 
                num_rows="dynamic",
                key="editor_regras"
            )

        with st.expander("🔄 Termos Internos (Ignorar)", expanded=False):
            st.caption("Termos que indicam transferências entre suas próprias contas.")
            st.session_state['df_internos'] = st.data_editor(
                st.session_state['df_internos'], 
                num_rows="dynamic",
                key="editor_internos"
            )

    # --- ÁREA PRINCIPAL ---
    st.title("📊 Organizador Financeiro Pessoal")
    st.write("Transforme seus extratos bancários (OFX) em uma planilha organizada e visual.")

    # 1. Upload
    uploaded_files = st.file_uploader(
        "Arraste seus arquivos OFX aqui", 
        type=['ofx'], 
        accept_multiple_files=True,
        help="Você pode selecionar múltiplos arquivos de bancos diferentes."
    )

    if uploaded_files:
        with st.spinner('Processando extratos...'):
            # Processamento
            df = processar_arquivos(
                uploaded_files, 
                st.session_state['df_regras'], 
                st.session_state['df_internos']
            )

        if not df.empty:
            # 2. Prévia dos Dados
            st.success(f"{len(df)} transações processadas com sucesso!")
            
            # Cards de Resumo Rápido na Tela
            col1, col2, col3 = st.columns(3)
            entrada = df[df['Tipo'] == 'Entrada']['Valor'].sum()
            saida = df[df['Tipo'] == 'Saída']['Valor'].sum()
            
            col1.metric("Total Entradas", f"R$ {entrada:,.2f}")
            col2.metric("Total Saídas", f"R$ {saida:,.2f}", delta_color="inverse")
            col3.metric("Saldo do Período", f"R$ {entrada + saida:,.2f}")

            # Aba de visualização simples
            tab1, tab2 = st.tabs(["📋 Tabela Detalhada", "📈 Gráfico Rápido"])
            
            with tab1:
                st.dataframe(df.style.format(subset=['Valor'], formatter="R$ {:.2f}"), use_container_width=True)
            
            with tab2:
                df_chart = df[df['Tipo'] == 'Saída'].groupby('Categoria')['Valor'].sum().abs().reset_index()
                st.bar_chart(df_chart, x='Categoria', y='Valor')

            # 3. Botão de Download
            st.markdown("---")
            st.subheader("📥 Baixar Relatório Completo")
            
            excel_data = gerar_excel_bytes(df)
            file_name = f"Controle_Financeiro_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            
            st.download_button(
                label="Baixar Excel Formatado",
                data=excel_data,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else:
            st.warning("Nenhuma transação válida encontrada nos arquivos.")

if __name__ == "__main__":

    main()
