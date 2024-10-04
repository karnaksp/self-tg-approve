# self-tg-approve

Insatll Ollama

```bash
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz # скачивать не надо, потому что архив уже скачан в текущую директорию
sudo tar -C /usr -xzf ollama-linux-amd64.tgz
```

Create a service file in /etc/systemd/system/ollama.service:

```
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=$PATH"

[Install]
WantedBy=default.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
ollama run llama3 | exit
```
