# Como Fazer o Deploy de uma Aplicação Python com Streamlit em uma Máquina Virtual Windows

Este guia detalha como implantar uma aplicação Python com **Streamlit** em uma máquina virtual (VM) com Windows Server (2019 ou 2022).

## 1. Configurar a Máquina Virtual
- **Escolha o provedor**: Utilize serviços como AWS EC2, Azure, Google Cloud, ou outro.
- **Sistema operacional**: Recomenda-se Windows Server 2019 ou 2022.
- **Acesse a VM**: Conecte-se via Remote Desktop Protocol (RDP) usando as credenciais fornecidas pelo provedor (ex.: `mstsc` no Windows ou outro cliente RDP).

## 2. Instalar Dependências Básicas
1. **Baixar e Instalar o Python**:
   - Acesse [python.org](https://www.python.org/downloads/windows/) e baixe a versão mais recente do Python (ex.: Python 3.9 ou superior).
   - Execute o instalador:
     - Marque a opção **"Add Python to PATH"**.
     - Escolha **"Install Now"** ou personalize o local de instalação.
   - Verifique a instalação no PowerShell ou Prompt de Comando:
     ```powershell
     python --version
     pip --version
     ```

2. **Instalar o Git**:
   - Baixe o instalador do [Git for Windows](https://git-scm.com/download/win).
   - Execute o instalador com configurações padrão.
   - Verifique a instalação:
     ```powershell
     git --version
     ```

## 3. Clonar o Repositório ou Transferir o Código
- **Clonar repositório** (se estiver no GitHub):
  - Abra o PowerShell e navegue até o diretório desejado:
    ```powershell
    cd C:\Caminho\Para\Sua\Pasta
    git clone https://github.com/seu_usuario/seu_repositorio.git
    cd seu_repositorio
    ```
- **Transferir arquivos**:
  - Use o RDP para copiar e colar os arquivos da sua máquina local para a VM ou use ferramentas como WinSCP para transferência.

## 4. Configurar um Ambiente Virtual
1. Crie um ambiente virtual:
   ```powershell
   python -m venv venv
   ```
2. Ative o ambiente virtual:
   ```powershell
   .\venv\Scripts\Activate
   ```

## 5. Instalar o Streamlit e Dependências
- Instale o Streamlit e dependências listadas em `requirements.txt` (se houver):
  ```powershell
  pip install streamlit
  pip install -r requirements.txt
  ```
- Se não houver `requirements.txt`, instale apenas as bibliotecas necessárias para sua aplicação.

## 6. Testar a Aplicação Localmente
- Execute a aplicação:
  ```powershell
  streamlit run sua_app.py
  ```
- O Streamlit iniciará um servidor na porta 8501. Acesse via `http://localhost:8501` na VM (se tiver um navegador) ou configure um túnel RDP (veja passo 8).

## 7. Configurar o Servidor para Deploy
Para rodar a aplicação de forma persistente e acessível, use o **Gunicorn** com **IIS (Internet Information Services)** como proxy reverso.

### a) Instalar o Gunicorn
```powershell
pip install gunicorn
```

### b) Configurar o Gunicorn
Teste o Gunicorn:
```powershell
gunicorn --bind 0.0.0.0:8000 -w 4 streamlit_app:server
```
- Substitua `streamlit_app` pelo nome do arquivo Python (sem `.py`).
- O parâmetro `-w 4` define 4 workers (ajuste conforme os recursos da VM).

### c) Configurar o Gunicorn como Serviço
No Windows, você pode usar o **NSSM (Non-Sucking Service Manager)** para rodar o Gunicorn como serviço:
1. Baixe o NSSM de [nssm.cc](https://nssm.cc/download).
2. Extraia e adicione o NSSM ao PATH ou copie para `C:\Windows`.
3. Configure o serviço:
   ```powershell
   nssm install SuaApp
   ```
   - No instalador gráfico do NSSM:
     - **Path**: `C:\Caminho\Para\SuaApp\venv\Scripts\gunicorn.exe`
     - **Startup directory**: `C:\Caminho\Para\SuaApp`
     - **Arguments**: `--bind 0.0.0.0:8000 -w 4 streamlit_app:server`
     - **Service name**: `SuaApp`
   - Salve e inicie o serviço:
     ```powershell
     nssm start SuaApp
     ```

## 8. Configurar o IIS como Proxy Reverso
1. **Habilitar o IIS**:
   - Abra o **Server Manager** > **Add Roles and Features**.
   - Selecione **Web Server (IIS)** e instale com os recursos padrão.
2. **Instalar o ARR (Application Request Routing)**:
   - Baixe e instale o [ARR](https://www.iis.net/downloads/microsoft/application-request-routing).
3. **Configurar o Proxy Reverso**:
   - Abra o **IIS Manager**.
   - Crie um novo site ou use o site padrão.
   - Configure o **URL Rewrite**:
     - Adicione uma regra de proxy reverso para redirecionar requisições de `http://localhost` (ou seu domínio) para `http://localhost:8000`.
     - Exemplo de configuração no `web.config`:
       ```xml
       <?xml version="1.0" encoding="UTF-8"?>
       <configuration>
           <system.webServer>
               <rewrite>
                   <rules>
                       <rule name="ReverseProxy" stopProcessing="true">
                           <match url="(.*)" />
                           <action type="Rewrite" url="http://localhost:8000/{R:1}" />
                       </rule>
                   </rules>
               </rewrite>
           </system.webServer>
       </configuration>
       ```
4. Reinicie o IIS:
   ```powershell
   iisreset
   ```

## 9. Configurar o Firewall
Permita o tráfego na porta 80 (HTTP) ou 443 (HTTPS, se configurado):
```powershell
netsh advfirewall firewall add rule name="Allow HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="Allow RDP" dir=in action=allow protocol=TCP localport=3389
```

## 10. Acessar a Aplicação
- Acesse via `http://ip_da_vm` ou `http://seu_dominio` no navegador.
- Para testes locais, use o RDP para acessar a VM e abrir `http://localhost:8501` no navegador da VM.

## 11. (Opcional) Configurar HTTPS com Certbot
- O Certbot não é nativo para Windows, mas você pode usar o **Let's Encrypt** com ferramentas como **Certify The Web**:
  1. Baixe e instale o [Certify The Web](https://certifytheweb.com/).
  2. Configure um certificado para seu domínio no IIS.
  3. Siga as instruções para vincular o certificado ao site.

## 12. Monitoramento e Logs
- **Logs do Gunicorn**:
  - Verifique os logs do serviço via NSSM:
    ```powershell
    nssm status SuaApp
    ```
  - Ou configure o Gunicorn para gerar logs em arquivo:
    ```powershell
    gunicorn --bind 0.0.0.0:8000 -w 4 --access-logfile gunicorn.log streamlit_app:server
    ```
- **Logs do IIS**:
  - Acesse em `C:\inetpub\logs\LogFiles`.

## Dicas Adicionais
- **Gerenciamento de dependências**: Use um `requirements.txt` para consistência.
- **Recursos da VM**: Mínimo de 2GB de RAM para aplicações simples.
- **Segurança**: Restrinja o acesso RDP, use senhas fortes e mantenha o sistema atualizado.
- **Backup**: Faça backups regulares do código e da VM.
- **Monitoramento**: Considere ferramentas como **Zabbix** ou **Nagios** para monitoramento.