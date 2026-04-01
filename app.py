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
    # Investimentos / Poupança
    {'Termo': 'RESG', 'Tipo': 'Investimento'},
    {'Termo': 'RESGATE', 'Tipo': 'Investimento'},
    {'Termo': 'APLIC', 'Tipo': 'Investimento'},
    {'Termo': 'APLICACAO', 'Tipo': 'Investimento'},
    {'Termo': 'INVEST', 'Tipo': 'Investimento'},
    {'Termo': 'POUP', 'Tipo': 'Poupança'},
    {'Termo': 'CDB', 'Tipo': 'Investimento'},
    {'Termo': 'LCI', 'Tipo': 'Investimento'},
    {'Termo': 'LCA', 'Tipo': 'Investimento'},
    {'Termo': 'TESOURO', 'Tipo': 'Investimento'},
    {'Termo': 'FUNDO', 'Tipo': 'Investimento'},
    
    # Transferências entre contas do mesmo titular
    {'Termo': 'TRANSF CONT', 'Tipo': 'Transferência'},
    {'Termo': 'ENTRE CONTAS', 'Tipo': 'Transferência'},
    {'Termo': 'MESMA TITUL', 'Tipo': 'Transferência'},
    {'Termo': 'AUTOMATICO', 'Tipo': 'Transferência'},
    
    # Pagamento de Fatura (Geralmente neutro na conta corrente)
    {'Termo': 'PAG FATURA', 'Tipo': 'Pagamento Cartão'},
    {'Termo': 'PGTO FAT', 'Tipo': 'Pagamento Cartão'},
    {'Termo': 'PAG CARTAO', 'Tipo': 'Pagamento Cartão'},
    {'Termo': 'DEBITO AUT', 'Tipo': 'Débito Automático'}
]

DEFAULT_REGRAS = [
    # Transporte
    {'Palavra_Chave': 'UBER', 'Categoria': 'Transporte'},
    {'Palavra_Chave': '99POP', 'Categoria': 'Transporte'},
    {'Palavra_Chave': '99APP', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'POSTO', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'IPIRANGA', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'SHELL', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'PETROBRAS', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'SEM PARAR', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'VELOE', 'Categoria': 'Transporte'},
    {'Palavra_Chave': 'ESTACIONAMENTO', 'Categoria': 'Transporte'},

    # Alimentação
    {'Palavra_Chave': 'IFOOD', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'RAPPI', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'ZE DELIVERY', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'RESTAURANTE', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'PADARIA', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'BURGER', 'Categoria': 'Alimentação'},
    {'Palavra_Chave': 'MC DONALDS', 'Categoria': 'Alimentação'},
    
    # Mercado
    {'Palavra_Chave': 'MERCADO', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'SUPERMERCADO', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'ATACADAO', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'ASSAI', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'CARREFOUR', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'PAO DE ACUCAR', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'EXTRA', 'Categoria': 'Mercado'},
    {'Palavra_Chave': 'DIA%', 'Categoria': 'Mercado'},

    # Assinaturas e Serviços Digitais
    {'Palavra_Chave': 'NETFLIX', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'SPOTIFY', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'AMAZONPRIME', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'PRIME VIDEO', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'YOUTUBE', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'APPLE', 'Categoria': 'Assinaturas'},
    {'Palavra_Chave': 'GOOGLE', 'Categoria': 'Serviços Digitais'},

    # Compras Online
    {'Palavra_Chave': 'MERCADOLIVRE', 'Categoria': 'Compras'},
    {'Palavra_Chave': 'MELI', 'Categoria': 'Compras'},
    {'Palavra_Chave': 'AMAZON', 'Categoria': 'Compras'},
    {'Palavra_Chave': 'MAGALU', 'Categoria': 'Compras'},
    {'Palavra_Chave': 'SHOPEE', 'Categoria': 'Compras'},
    {'Palavra_Chave': 'SHEIN', 'Categoria': 'Compras'},

    # Contas Fixas
    {'Palavra_Chave': 'VIVO', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'CLARO', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'TIM', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'OI', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'ENERGIA', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'LUZ', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'SANEAMENTO', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'AGUA', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'INTERNET', 'Categoria': 'Contas Fixas'},
    {'Palavra_Chave': 'CONDOMINIO', 'Categoria': 'Moradia'},
    {'Palavra_Chave': 'ALUGUEL', 'Categoria': 'Moradia'},

    # Saúde
    {'Palavra_Chave': 'FARMACIA', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'DROGARIA', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'DROGASIL', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'RAIA', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'PAGUE MENOS', 'Categoria': 'Saúde'},
    {'Palavra_Chave': 'ULTRAFARMA', 'Categoria': 'Saúde'},

    # Bancário e Taxas
    {'Palavra_Chave': 'TAR', 'Categoria': 'Taxas Bancárias'},
    {'Palavra_Chave': 'TARIFA', 'Categoria': 'Taxas Bancárias'},
    {'Palavra_Chave': 'ANUIDADE', 'Categoria': 'Taxas Bancárias'},
    {'Palavra_Chave': 'IOF', 'Categoria': 'Impostos'},

    # Receitas e Transferências
    {'Palavra_Chave': 'PIX ENVIADO', 'Categoria': 'Transferências/PIX'},
    {'Palavra_Chave': 'SALARIO', 'Categoria': 'Renda'},
    {'Palavra_Chave': 'PROVENTOS', 'Categoria': 'Renda'},
    {'Palavra_Chave': 'PAGTO ELETRON COBRANCA', 'Categoria': 'Renda'},
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
    
    # Prepara o resumo
    df_resumo = df_final.groupby('Categoria')['Valor'].sum().reset_index().sort_values(by='Valor', ascending=True)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Extrato Detalhado', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo Gerencial', index=False)

        workbook = writer.book
        ws_extrato = writer.sheets['Extrato Detalhado']
        ws_resumo = writer.sheets['Resumo Gerencial']

        # --- FORMATOS ---
        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
        fmt_verm = workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': 'R$ #,##0.00'})
        fmt_verd = workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': 'R$ #,##0.00'})
        fmt_neutro = workbook.add_format({'font_color': '#333333', 'bg_color': '#E0E0E0', 'num_format': 'R$ #,##0.00'})
        
        # --- AUTO-AJUSTE DAS COLUNAS (ABA EXTRATO) ---
        for idx, col in enumerate(df_final.columns):
            # Tamanho máximo do texto na coluna
            max_len = df_final[col].astype(str).map(len).max()
            # Tamanho do cabeçalho
            max_len = max(max_len, len(col)) + 2
            # Se for coluna de Valor, garante um tamanho mínimo para caber R$
            if 'Valor' in col:
                max_len = max(max_len, 18)
                ws_extrato.set_column(idx, idx, max_len, fmt_moeda)
            else:
                ws_extrato.set_column(idx, idx, max_len)

        # --- AUTO-AJUSTE DAS COLUNAS (ABA RESUMO) ---
        for idx, col in enumerate(df_resumo.columns):
            max_len = df_resumo[col].astype(str).map(len).max()
            max_len = max(max_len, len(col)) + 2
            if 'Valor' in col:
                max_len = max(max_len, 18)
                ws_resumo.set_column(idx, idx, max_len, fmt_moeda)
            else:
                ws_resumo.set_column(idx, idx, max_len)

        # --- TABELAS E FORMATAÇÃO CONDICIONAL ---
        (max_row, max_col) = df_final.shape
        if max_row > 0:
            ws_extrato.add_table(0, 0, max_row, max_col - 1, {
                'columns': [{'header': col} for col in df_final.columns],
                'style': 'TableStyleMedium9',
                'name': 'TabelaExtrato'
            })
            idx_v_ext = df_final.columns.get_loc('Valor')
            idx_cat = df_final.columns.get_loc('Categoria')
            letra_cat = chr(65 + idx_cat)
            
            # Cores Condicionais
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'formula', 'criteria': f'=${letra_cat}2="Movimentação Interna"', 'format': fmt_neutro})
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': fmt_verm})
            ws_extrato.conditional_format(1, idx_v_ext, max_row, idx_v_ext, {'type': 'cell', 'criteria': '>', 'value': 0, 'format': fmt_verd})

        # --- GRÁFICO ---
        (mr_res, mc_res) = df_resumo.shape
        if mr_res > 0:
            # Cria a tabela no resumo
            ws_resumo.add_table(0, 0, mr_res, mc_res - 1, {'columns': [{'header': col} for col in df_resumo.columns], 'style': 'TableStyleMedium2'})
            
            chart = workbook.add_chart({'type': 'pie'})
            chart.add_series({
                'name': 'Distribuição de Gastos',
                'categories': ['Resumo Gerencial', 1, 0, mr_res, 0],
                'values':     ['Resumo Gerencial', 1, 1, mr_res, 1],
                'data_labels': {'value': True, 'num_format': 'R$ #,##0', 'position': 'outside'},
            })
            
            # Aumenta o tamanho do gráfico e define título
            chart.set_title({'name': 'Resumo Financeiro'})
            chart.set_style(10) # Estilo visual moderno
            chart.set_size({'width': 600, 'height': 400}) # Tamanho maior em pixels
            
            # Insere ao lado da tabela (D2)
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

    # --- TÍTULO E MANUAL ---
    st.title("💰 Organizador Financeiro")
    
    # MANUAL
    with st.expander("📘 Manual de Instruções: Clique aqui para começar", expanded=False):
    
        st.markdown("### 🎯 Objetivo do Sistema")
        st.markdown("Esta ferramenta converte o extrato do seu banco em uma planilha Excel organizada. Ela separa seus gastos por categorias (como Transporte, Mercado, Lazer) e colore as linhas automaticamente.")
        
        st.markdown("---")

        st.info("""
        ### 1️⃣ Passo Principal: Como baixar o Extrato (Arquivo OFX)
        Para o sistema funcionar, você precisa do extrato no formato **OFX** (dependendo do banco pode aparecer como Money ou Quicken).
        ⚠️ **Atenção:** Arquivos em **PDF** ou **Prints de tela** não funcionam.
        
        **Como conseguir o arquivo:**
        
        **📱 Pelo Aplicativo do Celular:**
        1. Abra o app do seu banco e vá em **Extrato**.
        2. Procure por botões como **"Exportar"**, **"Salvar"** ou o ícone de **Compartilhar**.
        3. Escolha o formato **OFX**.
        4. Salve o arquivo ou envie para seu próprio e-mail/computador.
        *(Nota: Se o seu app só oferecer PDF, será necessário acessar sua conta pelo site no computador).*
        
        **💻 Pelo Site (Internet Banking):**
        1. Acesse sua conta e vá em **Extrato**.
        2. Selecione o período e procure o botão **"Salvar em Arquivo"** ou **"Exportar"**.
        3. Escolha a opção **OFX**.
        """)

        st.markdown("### 2️⃣ Configuração (Menu Lateral)")
        st.markdown("""
        Antes de processar o extrato, defina as regras no menu à esquerda para o sistema saber como organizar seus gastos.
        
        **A. Tabela de Categorias**
        * **Coluna Palavra_Chave:** Digite uma parte do nome que aparece no extrato (Ex: `UBER`, `NETFLIX`, `CARREFOUR`).
        * **Coluna Categoria:** Digite o tipo desse gasto (Ex: `Transporte`, `Assinaturas`, `Mercado`).
        
        **B. Termos Internos (Ignorar)**
        * Use esta lista para transações que não são gastos reais (ex: pagamento de fatura de cartão, transferências para poupança, investimentos). O sistema não somará esses valores como entrada ou saída.
        """)

        st.warning("""
        💾 **IMPORTANTE: Salvar suas Regras**
        
        Se você atualizar a página, as regras definidas serão perdidas.
        1.  Após configurar, clique no botão **"💾 Salvar Minhas Regras"** (menu lateral).
        2.  Um arquivo de segurança será baixado.
        3.  Sempre que voltar a usar o sistema, arraste esse arquivo para a área **"📂 Carregar Minhas Regras"** para restaurar tudo.
        """)

        st.markdown("---")

        st.markdown("### 3️⃣ Gerando o Relatório")
        st.markdown("""
        1.  Localize a área **"Arquivos OFX do Banco"** no centro da tela.
        2.  Clique no botão **"Browse files"** e selecione os arquivos OFX que você baixou.
        3.  Confira a pré-visualização e, se estiver tudo certo, clique no botão azul **"📥 Baixar Planilha Excel"**.
        """)
        
        st.markdown("### 4️⃣ Legenda do Excel")
        st.markdown("""
        * 🟢 **Verde:** Entradas de dinheiro.
        * 🔴 **Vermelho:** Saídas e Gastos.
        * ⚪ **Cinza:** Transações ignoradas (Termos Internos).
        """)

        # Bloco Verde: Dicas Finais
        st.success("""
        💡 **Dicas:**
        * **Prioridade:** O robô busca primeiro por **Termos Internos**, depois **Entradas**, e por fim **Regras de Categoria**.
        * **Comece Simples:** Cadastre apenas os gastos recorrentes (Netflix, Escola, Mercado). O que sobrar como "Outros" no Excel você ajusta manualmente depois.
        * **Seu Nome:** Para não contabilizar transferências entre contas, cadastre seu nome em **Termos Internos**.
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
                file_name=f"Relatorio_Financas_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

if __name__ == "__main__":
    main()
