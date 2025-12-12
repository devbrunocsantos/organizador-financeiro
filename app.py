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

# --- ESTILOS CSS PERSONALIZADOS ---
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
    /* Estilo específico para o botão de salvar configurações */
    div[data-testid="stSidebar"] .stButton>button {
        background-color: #007bff; 
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
ARQUIVO_CONFIG = "config_financeiro.json"

# --- DADOS INICIAIS ---
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

    for termo in termos_internos:
        if termo in descricao:
            for chave, categoria in regras_dict.items():
                if chave in descricao and categoria == 'Renda':
                    return 'Entradas/Renda'
            return 'Movimentação Interna'

    if valor > 0: 
        return 'Entradas/Renda'
    
    for chave, categoria in regras_dict.items():
        if chave in descricao: 
            return categoria
            
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
                    
                    tipo_transacao = 'Neutro' if cat == 'Movimentação Interna' else ('Entrada' if valor > 0 else 'Saída')

                    transacoes.append({
                        'Data': t.date.date(),
                        'Descrição': desc,
                        'Categoria': cat,
                        'Valor': valor,
                        'Tipo': tipo_transacao,
                        'Arquivo_Origem': uploaded_file.name
                    })
        except Exception as e:
            st.error(f"Erro ao ler {uploaded_file.name}: {e}")
            
    return pd.DataFrame(transacoes)

def gerar_excel_bytes(df_final):
    output = io.BytesIO()
    df_resumo = df_final.groupby('Categoria')['Valor'].sum().reset_index().sort_values(by='Valor', ascending=True)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Extrato Detalhado', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo Gerencial', index=False)

        workbook = writer.book
        ws_extrato = writer.sheets['Extrato Detalhado']
        ws_resumo = writer.sheets['Resumo Gerencial']

        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
        fmt_verm = workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': 'R$ #,##0.00'})
        fmt_verd = workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': 'R$ #,##0.00'})
        fmt_neutro = workbook.add_format({'font_color': '#333333', 'bg_color': '#E0E0E0', 'num_format': 'R$ #,##0.00'})
        
        ws_extrato.set_column('A:Z', 20)
        ws_resumo.set_column('A:Z', 20)
        
        idx_v_ext = df_final.columns.get_loc('Valor')
        ws_extrato.set_column(idx_v_ext, idx_v_ext, 18, fmt_moeda)
        idx_v_res = df_resumo.columns.get_loc('Valor')
        ws_resumo.set_column(idx_v_res, idx_v_res, 18, fmt_moeda)

        (max_row, max_col) = df_final.shape
        if max_row > 0:
            ws_extrato.add_table(0, 0, max_row, max_col - 1, {
                'columns': [{'header': col} for col in df_final.columns],
                'style': 'TableStyleMedium9',
                'name': 'TabelaExtrato'
            })
            idx_cat = df_final.columns.get_loc('Categoria')
            letra_cat = chr(65 + idx_cat)
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'formula', 'criteria': f'=${letra_cat}2="Movimentação Interna"', 'format': fmt_neutro})
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': fmt_verm})
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'cell', 'criteria': '>', 'value': 0, 'format': fmt_verd})

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
    st.sidebar.title("⚙️ Configurações")

    config_file = st.sidebar.file_uploader("📂 Carregar Minhas Regras (Opcional)", type=['json'])
    
    if 'df_regras' not in st.session_state:
        st.session_state['df_regras'] = pd.DataFrame(DEFAULT_REGRAS)
        st.session_state['df_internos'] = pd.DataFrame(DEFAULT_TERMOS_INTERNOS)
    
    if config_file is not None:
        regras, internos = carregar_configuracoes(config_file)
        if regras is not None:
            st.session_state['df_regras'] = regras
            st.session_state['df_internos'] = internos
            st.sidebar.success("Regras carregadas!")

    with st.sidebar.expander("📝 Editar Regras de Categoria", expanded=False):
        st.session_state['df_regras'] = st.data_editor(st.session_state['df_regras'], num_rows="dynamic")

    with st.sidebar.expander("🔄 Editar Termos Internos", expanded=False):
        st.session_state['df_internos'] = st.data_editor(st.session_state['df_internos'], num_rows="dynamic")

    st.sidebar.markdown("---")
    st.sidebar.write("Gostou das regras? Salve para usar depois:")
    
    dados_para_salvar = {
        'regras': st.session_state['df_regras'].to_dict(orient='records'),
        'internos': st.session_state['df_internos'].to_dict(orient='records')
    }
    json_bytes = json.dumps(dados_para_salvar, indent=4).encode('utf-8')
    
    st.sidebar.download_button(
        label="💾 Salvar Minhas Regras",
        data=json_bytes,
        file_name=ARQUIVO_CONFIG,
        mime="application/json"
    )

    # --- TÍTULO E MANUAL (NOVO) ---
    st.title("💰 Organizador Financeiro")
    
    # AQUI INSERIMOS O MANUAL DENTRO DE UM EXPANDER
    with st.expander("📘 Como usar este sistema (Clique para ler o Manual)", expanded=False):
        st.markdown("""
                    ### 📘 **Manual do Usuário: Organizador Financeiro**
                    ​Bem-vindo ao Organizador Financeiro! Esta ferramenta foi criada para transformar extratos bancários confusos em relatórios Excel organizados, categorizados e coloridos automaticamente.
                    
                    ### 🚀 **O que você precisa antes de começar**
                    - ​Para utilizar o sistema, você precisará apenas de:
                    - ​Arquivos OFX: Entre no site/app do seu banco e baixe o extrato no formato .ofx (Money/Quicken). O sistema aceita múltiplos arquivos de diferentes bancos ao mesmo tempo.
                    - ​Navegador Web: O sistema roda diretamente no seu navegador.

                    ### 🛠️ **Passo 1: Configurando suas Regras (Barra Lateral)**
                    ​Ao abrir o aplicativo, você verá uma barra lateral à esquerda chamada ⚙️ Configurações. O sistema já vem com regras padrão, mas a mágica acontece quando você personaliza para a sua realidade.
                    
                    - ​1. **Editar Regras de Categoria**
                        Nesta tabela, você ensina ao robô como classificar seus gastos.
                        - **​Palavra_Chave:** O termo que aparece no extrato (ex: UBER, IFOOD, POSTO).
                        - **​Categoria:** Como você quer agrupar isso (ex: Transporte, Alimentação).
                        - **​Dica:** Não precisa escrever a descrição inteira. Se o extrato mostra "UBER DO BRASIL TECNOLOGIA", basta cadastrar UBER.
                    
                    - ​2. **Editar Termos Internos**
                        ​Use esta tabela para transações que não são gastos nem ganhos reais, mas apenas movimentações entre suas contas. Exemplos: RESGATE, APLICACAO, TRANSF PARA MIM MESMO. 
                        ​O sistema irá marcar essas linhas em Cinza no Excel e não irá somá-las como despesa ou receita.
                    
                    - ​3. **Salvar/Carregar Configurações (Importante!)** 💾
                        ​Como o sistema roda na web, se você atualizar a página, as regras voltam ao padrão. 
                        ​Para não perder seu trabalho: Após editar as tabelas, clique em "💾 Salvar Minhas Regras". Um arquivo .json será baixado no seu computador. 
                        ​Na próxima vez: Basta arrastar esse arquivo .json para o campo "📂 Carregar Minhas Regras" no topo da barra lateral e todas as suas configurações personalizadas serão restauradas.
                    
                    ### 📂 **Passo 2: Processando os Extratos**
                    ​Na área principal (central) da tela:
                    - ​Localize o campo "Arquivos OFX do Banco".
                    - ​Arraste seus arquivos .ofx para lá (ou clique para buscar nas pastas).
                    - ​O sistema processará tudo instantaneamente.

                    ### ​**O que aparece na tela?**
                    - **​Métricas:** Resumo rápido de quanto entrou (Entradas), quanto saiu (Saídas) e o saldo final do período importado.
                    - **​Tabela de Pré-visualização:** Uma lista com todas as transações já categorizadas para você conferir se está tudo certo.
                    
                    ### 📊 **Passo 3: O Resultado Final (Excel)**
                    ​Se os dados na tela estiverem corretos, clique no botão azul:
                    
                    ### 👉 **"📥 Baixar Planilha Excel"**
                    ​O arquivo gerado conterá duas abas:
                    - **​Aba 1: Extrato Detalhado**
                        - ​Todas as transações unificadas.
                        - ​Cores Automáticas:
                            - 🟢 Verde: Entradas de dinheiro.
                            - 🔴 Vermelho: Saídas/Gastos.
                            - ​⚪ Cinza: Movimentações internas (neutras).
                
                    - ​Aba 2: Resumo Gerencial
                        - Uma tabela dinâmica somando os gastos por Categoria.
                        - ​Um Gráfico de Pizza pronto para visualização da distribuição dos seus gastos.

                    ### 💡 Dicas
                    - **​Prioridade das Regras:** O sistema verifica primeiro se é uma "Movimentação Interna". Se não for, ele verifica se é "Entrada" (dinheiro positivo). Por fim, ele tenta achar as palavras-chave de gastos. Se não achar nada, classifica como "Outros".
                    - **​Comece simples:** Não tente cadastrar todos os estabelecimentos do mundo. Cadastre os recorrentes (Netflix, Vivo, Academia, Supermercado habitual). O que sobrar como "Outros" no Excel você pode ajustar manualmente depois.
                    - **​Arquivos duplicados:** O sistema lê o que está no arquivo. Se você subir o mesmo extrato duas vezes, ele aparecerá duplicado. Certifique-se de selecionar os arquivos corretos.
                """)

    st.info("Arraste seus extratos bancários (OFX) abaixo.")

    uploaded_files = st.file_uploader("Arquivos OFX do Banco", type=['ofx'], accept_multiple_files=True)

    if uploaded_files:
        df = processar_arquivos(uploaded_files, st.session_state['df_regras'], st.session_state['df_internos'])
        
        if not df.empty:
            ent = df[df['Tipo']=='Entrada']['Valor'].sum()
            sai = df[df['Tipo']=='Saída']['Valor'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Entradas", f"R$ {ent:,.2f}")
            col2.metric("Saídas", f"R$ {sai:,.2f}")
            col3.metric("Saldo", f"R$ {ent+sai:,.2f}")

            st.dataframe(df, use_container_width=True)
            st.download_button(
                "📥 Baixar Planilha Excel",
                data=gerar_excel_bytes(df),
                file_name=f"Financas_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

if __name__ == "__main__":
    main()