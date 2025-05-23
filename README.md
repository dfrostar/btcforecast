# BTC4Cast: Bitcoin Forecasting Web App

## Quick Start (Local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Production Deployment (Docker)

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```
   The app will be available at `http://localhost:8501`.

2. **Set up your subdomain:**
   - Point `btc4cast.cheval-volant.com` to your server's IP in your DNS provider.

3. **Nginx Reverse Proxy (with HTTPS):**
   - Install Nginx and Certbot:
     ```bash
     sudo apt update && sudo apt install nginx certbot python3-certbot-nginx
     ```
   - Configure Nginx to proxy requests to the Streamlit app:
     ```nginx
     server {
         listen 80;
         server_name btc4cast.cheval-volant.com;

         location / {
             proxy_pass http://localhost:8501;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
             proxy_set_header X-Forwarded-Proto $scheme;
         }
     }
     ```
   - Enable the config and restart Nginx:
     ```bash
     sudo ln -s /etc/nginx/sites-available/yourconfig /etc/nginx/sites-enabled/
     sudo nginx -t
     sudo systemctl restart nginx
     ```
   - Get a free SSL certificate:
     ```bash
     sudo certbot --nginx -d btc4cast.cheval-volant.com
     ```

4. **Troubleshooting:**
   - Check logs: `docker logs <container_id>` or `streamlit logs`.
   - Make sure port 8501 is open on your firewall.
   - For Streamlit errors, check `~/.streamlit/logs/`.

## Customization
- Edit `app.py` for UI or model changes.
- Edit `train_agent.py` for automated retraining.

---

**Contact:** For help, open an issue or contact the maintainer. 