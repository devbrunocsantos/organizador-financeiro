# 💰 Organizador Financeiro

Uma aplicação web desenvolvida em **Python** utilizando o framework **Streamlit**. O objetivo desta ferramenta é simplificar a gestão financeira, principalmente pessoal, permitindo a importação de extratos bancários no formato **OFX** e a conversão automática para planilhas Excel organizadas e categorizadas.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://organizador-financeiro.streamlit.app)

## ✨ Funcionalidades

- **Importação de OFX:** Suporte para leitura de múltiplos arquivos de extrato bancário simultaneamente.
- **Categorização Inteligente:**
  - Categorização baseada em palavras-chave configuráveis (ex: "Uber" -> "Transporte").
  - Identificação de termos internos para ignorar transferências entre contas do mesmo titular.
- **Exportação para Excel:**
  - Geração de planilha `.xlsx` formatada.
  - Aba de "Extrato Detalhado" com formatação condicional (Verde/Vermelho).
  - Aba de "Resumo Gerencial" com tabela dinâmica e Gráfico de Pizza.
- **Configurações Persistentes:** Salve e carregue suas regras de categorização em arquivos JSON.
- **Interface Amigável:** Manual de instruções integrado e feedback visual de erros/sucessos.

## 🚀 Como Executar

### Pré-requisitos
- Python 3.8 ou superior
- Pip (Gerenciador de pacotes)

### Instalação Local

1. Clone o repositório:
   ```bash
   git clone https://github.com/devbrunocsantos/organizador-financeiro.git
   ```

2. Entre na pasta:
   ```bash
   cd organizador-financeiro
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
  
4. Execute a aplicação:
   ```bash
   streamlit run app.py
   ```

## 🐳 Usando Docker / DevContainers (Recomendado)
Este projeto já está configurado para VS Code DevContainers.

1. Abra a pasta do projeto no VS Code.

2. Quando solicitado, clique em "Reopen in Container".

3. O ambiente será montado automaticamente com todas as dependências e o servidor iniciará na porta 8501.

## 🛠️ Tecnologias Utilizadas
- Streamlit: Interface web interativa.

- Pandas: Manipulação e análise de dados.

- Ofxparse: Leitura de arquivos bancários.

- XlsxWriter: Criação de arquivos Excel avançados com gráficos e formatação.

## 📂 Estrutura do Projeto
- `app.py`: Código fonte principal da aplicação.

- `config_financeiro.json`: (Gerado pelo usuário) Armazena as regras de categorias personalizadas.

- `.devcontainer/`: Configurações para ambiente de desenvolvimento Docker.

## 📝 Licença
Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
