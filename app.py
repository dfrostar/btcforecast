import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import yfinance as yf

# --- App Configuration ---
st.set_page_config(
    page_title="Bitcoin Price Forecaster",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"

# --- Helper Functions ---
def get_api_data(endpoint):
    """Fetches data from the backend API."""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the API: {e}")
        return None

def post_api_data(endpoint):
    """Posts data to the backend API."""
    try:
        response = requests.post(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the API: {e}")
        return None

def plot_forecast(forecast_data):
    """Plots historical and forecasted Bitcoin prices."""
    if not forecast_data:
        return

    try:
        hist_df = pd.DataFrame(forecast_data.get("history", []))
        forecast_df = pd.DataFrame(forecast_data.get("forecast", []))

        if "Date" not in hist_df.columns or "Date" not in forecast_df.columns:
             st.error("Dataframes must contain 'Date' column.")
             st.write("History Dataframe:", hist_df.head())
             st.write("Forecast Dataframe:", forecast_df.head())
             return

        hist_df['Date'] = pd.to_datetime(hist_df['Date'])
        forecast_df['Date'] = pd.to_datetime(forecast_df['Date'])
        
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=hist_df['Date'],
            y=hist_df['Close'],
            mode='lines',
            name='Historical Price'
        ))

        fig.add_trace(go.Scatter(
            x=forecast_df['Date'],
            y=forecast_df['Predicted_Close'],
            mode='lines',
            name='Forecasted Price',
            line=dict(color='orange', dash='dash')
        ))

        fig.update_layout(
            title="Bitcoin Price: Historical vs. Forecast",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            legend_title="Legend",
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while plotting the data: {e}")
        st.write("Received data:", forecast_data)


# --- Main Application ---
def main():
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Home", "Forecast", "Model Evaluation"],
            icons=['house', 'graph-up-arrow', 'wrench'],
            menu_icon="cast",
            default_index=0,
        )

    st.title("Bitcoin Price Forecasting Dashboard")

    if selected == "Home":
        st.subheader("Welcome to the BTC Forecaster!")
        st.markdown("""
            This application provides tools to forecast Bitcoin prices using a machine learning model.
            
            **Navigate through the menu on the left to explore different features:**
            - **Forecast:** Get the latest price predictions.
            - **Model Evaluation:** View the performance metrics of the underlying prediction model and retrain it if needed.
            
            The backend is powered by a FastAPI server and an ensemble machine learning model.
        """)

    elif selected == "Forecast":
        st.subheader("Bitcoin Price Forecast")
        if st.button("Generate New Forecast"):
            with st.spinner("Fetching forecast from the model..."):
                forecast_data = get_api_data("forecast")
                if forecast_data and "history" in forecast_data and "forecast" in forecast_data:
                    st.success("Forecast generated successfully!")
                    st.session_state['forecast_data'] = forecast_data
                elif forecast_data:
                    st.error(f"Failed to get forecast: {forecast_data.get('detail', 'Unknown error')}")
        
        if 'forecast_data' in st.session_state:
            plot_forecast(st.session_state['forecast_data'])
            st.write("### Forecasted Prices")
            forecast_df = pd.DataFrame(st.session_state['forecast_data']['forecast'])
            st.dataframe(forecast_df)

    elif selected == "Model Evaluation":
        st.subheader("Model Performance and Training")
        st.info("Evaluate the model's performance or retrain it with the latest data.")
        
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Evaluate Model"):
                with st.spinner("Fetching model evaluation metrics..."):
                    eval_data = get_api_data("evaluate")
                    if eval_data:
                        st.session_state['eval_data'] = eval_data
                        st.success("Evaluation data loaded.")
                    else:
                        st.error("Could not fetch evaluation data.")

        with col2:
            if st.button("Train New Model"):
                with st.spinner("Model training in progress... This can take several minutes."):
                    train_data = post_api_data("train")
                    if train_data:
                         st.session_state['eval_data'] = train_data # Training endpoint also returns evaluation
                         st.success("Model training completed!")
                    else:
                        st.error("Model training failed.")
        
        if 'eval_data' in st.session_state:
            st.write("### Model Performance Metrics")
            metrics = st.session_state['eval_data']
            st.metric(label="R² Score", value=f"{metrics.get('r2_score', 0):.4f}")
            st.metric(label="Mean Squared Error (MSE)", value=f"{metrics.get('mse', 0):.4f}")
            st.metric(label="Mean Absolute Error (MAE)", value=f"{metrics.get('mae', 0):.4f}")
            
            if 'cv_scores' in metrics:
                st.write("#### Cross-Validation R² Scores")
                cv_df = pd.DataFrame(metrics['cv_scores'], columns=['CV R² Score'])
                st.bar_chart(cv_df)


if __name__ == "__main__":
    main() 