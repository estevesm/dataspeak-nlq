# Como Fazer o Deploy de uma Aplicação Python com Streamlit em uma Máquina Virtual LINUX

Este guia descreve como implantar uma aplicação Python com **Streamlit** em uma máquina virtual (VM) com sistema operacional Linux, como Ubuntu 20.04 ou 22.04 LTS.

## 1. Configurar a Máquina Virtual
- **Escolha o provedor**: Utilize serviços como Google Cloud, AWS EC2, Azure, DigitalOcean, ou outro.
- **Sistema operacional**: Recomenda-se Ubuntu 20.04 ou 22.04 LTS.
- **Acesse a VM**: Conecte-se via SSH:
  ```bash
  ssh usuario@ip_da_vm
  ```

## 2. Atualizar o Sistema e Instalar Dependências Básicas
No terminal da VM, execute:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

## 3. Clonar o Repositório ou Transferir o Código
- **Clonar repositório** (se estiver no GitHub):
  ```bash
  git clone https://github.com/seu_usuario/seu_repositorio.git
  cd seu_repositorio
  ```
- **Transferir arquivos** (usando `scp`):
  ```bash
  scp -r /caminho/local/sua_app usuario@ip_da_vm:/caminho/destino
  ```

## 4. Configurar um Ambiente Virtual
Crie e ative um ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

## 5. Instalar o Streamlit e Dependências
- Instale o Streamlit e dependências listadas em `requirements.txt` (se houver):
  ```bash
  pip install streamlit
  pip install -r requirements.txt
  ```

## 6. Testar a Aplicação Localmente
- Execute a aplicação:
  ```bash
  streamlit run sua_app.py
  ```
- Acesse na porta 8501 (ex.: `http://localhost:8501`) ou use um túnel SSH (veja passo 8).

## 7. Configurar o Servidor para Deploy
Use **Gunicorn** com **Nginx** como proxy reverso.

### a) Instalar o Gunicorn
```bash
pip install gunicorn
```

### b) Configurar o Gunicorn
Teste o Gunicorn:
```bash
gunicorn --bind 0.0.0.0:8000 -w 4 streamlit_app:server
```
- Substitua `streamlit_app` pelo nome do arquivo Python (sem `.py`).

### c) Configurar um Serviço Systemd
Crie um serviço para rodar a aplicação em background:
```bash
sudo nano /etc/systemd/system/sua_app.service
```

Adicione:
```ini
[Unit]
Description=Sua Aplicação Streamlit
After=network.target

[Service]
User=seu_usuario
Group=www-data
WorkingDirectory=/caminho/para/sua_app
Environment="PATH=/caminho/para/sua_app/venv/bin"
ExecStart=/caminho/para/sua_app/venv/bin/gunicorn --bind 0.0.0.0:8000 -w 4 streamlit_app:server

[Install]
WantedBy=multi-user.target
```

Ative o serviço:
```bash
sudo systemctl start sua_app
sudo systemctl enable sua_app
```

## 8. Configurar o Nginx como Proxy Reverso
Instale o Nginx:
```bash
sudo apt install nginx -y
```

Crie a configuração:
```bash
sudo nano /etc/nginx/sites-available/sua_app
```

Adicione:
```nginx
server {
    listen 80;
    server_name seu_dominio_ou_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Habilite e reinicie:
```bash
sudo ln -s /etc/nginx/sites-available/sua_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 9. Configurar o Firewall
Permita o tráfego:
```bash
sudo ufw allow 80
sudo ufw allow ssh
sudo ufw enable
```

## 10. Acessar a Aplicação
- Acesse via `http://ip_da_vm` ou `http://seu_dominio`.
- Para testes locais, use um túnel SSH:
  ```bash
  ssh -L 8501:localhost:8501 usuario@ip_da_vm
  ```
  Acesse `http://localhost:8501` no navegador.

## 11. (Opcional) Configurar HTTPS com Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu_dominio
```

## 12. Monitoramento e Logs
- Logs do serviço:
  ```bash
  sudo journalctl -u sua_app.service
  ```
- Logs do Nginx:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  sudo tail -f /var/log/nginx/access.log
  ```

## Dicas Adicionais
- Use `requirements.txt` para gerenciar dependências.
- Garanta recursos suficientes na VM (mínimo 1GB RAM).
- Restrinja o acesso SSH e use chaves SSH.
- Faça backups regulares.
- Considere ferramentas como **Prometheus** ou **Grafana** para monitoramento.