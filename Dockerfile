FROM tensorflow/tensorflow:2.15.0-gpu
WORKDIR /app
COPY . /app
RUN pip uninstall -y keras keras-nightly keras-preprocessing keras-vis || true
RUN pip install --upgrade pip && pip install --ignore-installed -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"] 