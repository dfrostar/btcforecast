# BTCForecast

AI-powered Bitcoin price forecasting app using Streamlit, TensorFlow, and technical indicators.

## Features
- Deep learning (Bi-LSTM + Attention)
- Technical indicators: RSI, MACD, Bollinger Bands, OBV, Ichimoku Cloud
- Sentiment and on-chain data support
- Interactive charts and backtesting

## Quick Start

```bash
docker-compose up --build
```

Then visit [http://localhost:8501](http://localhost:8501)

## Development

- Python 3.11 recommended
- See `requirements.txt` for dependencies

## Conda Environment Setup (Recommended)

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).
2. Create the environment:
   ```sh
   conda env create -f environment.yml
   conda activate btcforecast
   ```
3. To update the environment:
   ```sh
   conda env update -f environment.yml --prune
   ```
4. Run the app or training scripts as usual.

> **Note:** The use of `requirements.txt` and pip is only for advanced users or non-Conda environments. The project is tested and supported with Conda as the primary method.

## License

MIT

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

## Code & Documentation Indexing
- See [CODE_INDEX.md](./CODE_INDEX.md) for a structured index of all code, scripts, and their purposes.
- See [DOCUMENT_INDEX.md](./DOCUMENT_INDEX.md) for all user and developer documentation.

**Best Practice:**
- Always update CODE_INDEX.md with every PR that adds, removes, or refactors files.
- Use the code index for navigation, onboarding, and as a checklist during code reviews.

---

**Contact:** For help, open an issue or contact the maintainer. 
