import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import joblib
import logging
from data.feature_engineering import add_technical_indicators

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:models:%(message)s')

def create_sequences(data, target_col, feature_cols, n_steps):
    """Creates sequences of data for time series forecasting."""
    X, y = [], []
    
    # Ensure target column exists
    if target_col not in data.columns:
        logging.warning(f"Target column '{target_col}' not found in data. Creating it...")
        data[target_col] = data['Close'].shift(-1)
    
    # Ensure all feature columns exist
    missing_features = [col for col in feature_cols if col not in data.columns]
    if missing_features:
        logging.warning(f"Missing features: {missing_features}. Removing from feature list.")
        feature_cols = [col for col in feature_cols if col in data.columns]
    
    # Drop rows with NaN values
    data_clean = data.dropna(subset=[target_col] + feature_cols)
    
    for i in range(len(data_clean) - n_steps):
        X.append(data_clean.iloc[i:(i + n_steps)][feature_cols].values)
        y.append(data_clean.iloc[i + n_steps][target_col])
    
    return np.array(X), np.array(y)

def generate_forecast_features(last_row, prediction, feature_cols):
    """
    Generate new technical indicators for a forecasted step.
    This creates realistic feature values for the next prediction.
    """
    # Create a new row with the predicted price
    new_row = last_row.copy()
    new_row['Close'] = prediction
    
    # Estimate other OHLC values based on typical patterns
    # Assume the predicted close is within the day's range
    price_change = prediction - last_row['Close']
    volatility_factor = 0.02  # 2% typical daily volatility
    
    # Generate realistic OHLC values
    if price_change > 0:  # Bullish day
        new_row['Open'] = prediction * (1 - volatility_factor * 0.3)
        new_row['High'] = prediction * (1 + volatility_factor * 0.2)
        new_row['Low'] = prediction * (1 - volatility_factor * 0.8)
    else:  # Bearish day
        new_row['Open'] = prediction * (1 + volatility_factor * 0.3)
        new_row['High'] = prediction * (1 + volatility_factor * 0.8)
        new_row['Low'] = prediction * (1 - volatility_factor * 0.2)
    
    # Estimate volume based on price movement
    volume_change = abs(price_change) / last_row['Close'] * 100
    new_row['Volume'] = last_row['Volume'] * (1 + volume_change * 0.1)
    
    # Create a single-row DataFrame for feature engineering
    new_df = pd.DataFrame([new_row])
    new_df.index = [last_row.name + pd.Timedelta(days=1)]
    
    # Add technical indicators to the new row
    try:
        # Combine with historical data for proper indicator calculation
        historical_data = pd.concat([last_row.to_frame().T, new_df])
        featured_data = add_technical_indicators(historical_data)
        new_features = featured_data.iloc[-1:][feature_cols]
        return new_features.iloc[0]
    except Exception as e:
        logging.warning(f"Could not generate features for forecast: {e}")
        # Fallback: use last known values with small random variation
        fallback_features = {}
        for col in feature_cols:
            if col in last_row:
                fallback_features[col] = last_row[col] * (1 + np.random.normal(0, 0.01))
            else:
                fallback_features[col] = 0
        return pd.Series(fallback_features)

def train_feature_forecasting_model(df, feature_cols, n_steps=10):
    """
    Train separate models for forecasting key technical indicators.
    This helps generate more realistic features for recursive forecasting.
    """
    logging.info("Training feature forecasting models...")
    feature_models = {}
    
    # Select key indicators that are most important for price prediction
    key_indicators = ['RSI', 'MACD', 'BB_Position', 'Volume_Ratio', 'Volatility']
    available_indicators = [col for col in key_indicators if col in feature_cols]
    
    for indicator in available_indicators:
        try:
            # Prepare data for this indicator
            indicator_data = df[['Close', 'Volume', indicator]].dropna()
            
            if len(indicator_data) < n_steps + 10:
                continue
                
            # Create sequences for indicator forecasting
            X_ind, y_ind = [], []
            for i in range(len(indicator_data) - n_steps):
                X_ind.append(indicator_data.iloc[i:(i + n_steps)][['Close', 'Volume']].values)
                y_ind.append(indicator_data.iloc[i + n_steps][indicator])
            
            X_ind = np.array(X_ind).reshape(len(X_ind), -1)
            y_ind = np.array(y_ind)
            
            # Train a simple model for this indicator
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X_ind, y_ind)
            feature_models[indicator] = model
            
            logging.info(f"Trained model for {indicator}")
            
        except Exception as e:
            logging.warning(f"Could not train model for {indicator}: {e}")
    
    return feature_models

def recursive_forecast(model, scaler, features, initial_data, days_to_predict=7, n_steps=30):
    """
    Implements true recursive forecasting where each prediction becomes input for the next step.
    Generates new technical indicators for each forecasted step.
    """
    logging.info(f"Starting recursive forecast for {days_to_predict} days...")
    
    # Train feature forecasting models
    feature_models = train_feature_forecasting_model(initial_data, features, n_steps)
    
    # Prepare initial sequence
    last_sequence = initial_data[features].tail(n_steps).values
    scaled_sequence = scaler.transform(last_sequence)
    
    predictions = []
    forecast_data = initial_data.copy()
    last_row = initial_data.iloc[-1]
    
    for day in range(days_to_predict):
        # Reshape for model prediction
        current_batch = scaled_sequence.reshape(1, -1)
        
        # Get price prediction
        price_prediction = model.predict(current_batch)[0]
        predictions.append(price_prediction)
        
        logging.info(f"Day {day + 1}: Predicted price = ${price_prediction:.2f}")
        
        # Generate new features for the next step
        try:
            new_features = generate_forecast_features(last_row, price_prediction, features)
            
            # Update last row with new data
            new_row = last_row.copy()
            new_row['Close'] = price_prediction
            new_row.name = last_row.name + pd.Timedelta(days=1)
            
            # Update features using our forecasting models where possible
            for indicator, indicator_model in feature_models.items():
                if indicator in features:
                    try:
                        # Use the feature forecasting model
                        indicator_input = np.array([[last_row['Close'], last_row['Volume']]])
                        predicted_indicator = indicator_model.predict(indicator_input)[0]
                        new_features[indicator] = predicted_indicator
                    except:
                        pass  # Keep the generated feature if model fails
            
            # Add the new row to forecast data
            forecast_data = pd.concat([forecast_data, pd.DataFrame([new_row])])
            
            # Update the sequence for next iteration
            new_scaled_features = scaler.transform([new_features[features].values])
            scaled_sequence = np.vstack([scaled_sequence[1:], new_scaled_features])
            
            last_row = new_row
            
        except Exception as e:
            logging.warning(f"Error generating features for day {day + 1}: {e}")
            # Fallback: use simple persistence
            scaled_sequence = np.roll(scaled_sequence, -1, axis=0)
            scaled_sequence[-1] = scaled_sequence[-2]  # Use last known values
    
    # Create future dates
    future_dates = pd.to_datetime(initial_data.index[-1]) + pd.to_timedelta(np.arange(1, days_to_predict + 1), 'D')
    
    return pd.DataFrame({
        'Date': future_dates,
        'Predicted_Close': predictions,
        'Confidence': [0.85 - i * 0.05 for i in range(days_to_predict)]  # Decreasing confidence
    })

def train_ensemble_model(df, n_steps=30, test_size=0.2):
    """Trains a sophisticated ensemble model with feature selection and hyperparameter tuning."""
    logging.info("Preparing data...")
    
    # Ensure we have a copy of the dataframe
    df = df.copy()
    
    # Handle MultiIndex columns by flattening them
    if isinstance(df.columns, pd.MultiIndex):
        logging.info("Flattening MultiIndex columns...")
        df.columns = [col[0] if col[1] == '' else f"{col[0]}_{col[1]}" for col in df.columns]
    
    # Verify that 'Close' column exists
    if 'Close' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' column for target creation")
    
    # Create the target variable first - next day's close price
    df['target'] = df['Close'].shift(-1)
    
    # Define feature columns (exclude target and price columns)
    feature_cols = [col for col in df.columns if col not in ['target', 'Close', 'Open', 'High', 'Low']]
    
    # Log the available features for debugging
    logging.info(f"Available features: {feature_cols}")
    
    # Ensure we have features to work with
    if len(feature_cols) == 0:
        raise ValueError("No features available for training. Please ensure technical indicators are added.")
    
    # Impute NaNs in features with the mean of their respective columns
    for col in feature_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].mean())
            
    # Now drop rows where the target is NaN (the very last row)
    initial_rows = len(df)
    df = df.dropna(subset=['target'])
    final_rows = len(df)
    logging.info(f"Dropped {initial_rows - final_rows} rows with NaN targets. Remaining rows: {final_rows}")
    
    # Ensure we have enough data after cleaning
    if len(df) < n_steps + 10:
        raise ValueError(f"Insufficient data after cleaning. Need at least {n_steps + 10} rows, got {len(df)}")

    # --- Feature Selection ---
    logging.info(f"Original features: {len(feature_cols)}")
    X_fs = df[feature_cols]
    y_fs = df['target']
    
    # Select the top 30 features (or all if less than 30)
    k_features = min(30, len(feature_cols))
    selector = SelectKBest(f_regression, k=k_features)
    X_new = selector.fit_transform(X_fs, y_fs)
    selected_features = X_fs.columns[selector.get_support()].tolist()
    logging.info(f"Selected features: {len(selected_features)}")

    # --- Data Splitting and Scaling ---
    train_df, test_df = train_test_split(df, test_size=test_size, shuffle=False)
    
    scaler = MinMaxScaler()
    train_df_scaled = scaler.fit_transform(train_df[selected_features])
    test_df_scaled = scaler.transform(test_df[selected_features])
    
    X_train, y_train = create_sequences(pd.DataFrame(train_df_scaled, columns=selected_features).assign(target=train_df['target'].values), 'target', selected_features, n_steps)
    X_test, y_test = create_sequences(pd.DataFrame(test_df_scaled, columns=selected_features).assign(target=test_df['target'].values), 'target', selected_features, n_steps)

    # Reshape for sklearn models
    X_train = X_train.reshape(X_train.shape[0], -1)
    X_test = X_test.reshape(X_test.shape[0], -1)

    # --- Model Training ---
    logging.info("Training model with hyperparameter optimization...")
    estimators = [
        ('rf', RandomForestRegressor(n_estimators=50, random_state=42)),
        ('gb', GradientBoostingRegressor(n_estimators=50, random_state=42))
    ]
    stacking_regressor = StackingRegressor(estimators=estimators, final_estimator=Ridge())

    param_grid = {
        'rf__max_depth': [10, 20, None],
        'gb__learning_rate': [0.05, 0.1],
        'final_estimator__alpha': [0.5, 1.0]
    }
    
    tscv = TimeSeriesSplit(n_splits=5)
    grid_search = GridSearchCV(estimator=stacking_regressor, param_grid=param_grid, cv=tscv, n_jobs=-1, scoring='r2')
    grid_search.fit(X_train, y_train)
    
    best_model = grid_search.best_estimator_
    
    # --- Evaluation ---
    logging.info(f"Best model parameters: {grid_search.best_params_}")
    y_pred = best_model.predict(X_test)
    
    eval_results = {
        "r2_score": r2_score(y_test, y_pred),
        "mse": mean_squared_error(y_test, y_pred),
        "mae": mean_absolute_error(y_test, y_pred),
        "cv_scores": grid_search.cv_results_['mean_test_score'].tolist()
    }
    logging.info(f"Validation R² score: {eval_results['r2_score']:.4f}")
    
    # --- Save Model ---
    logging.info("Saving model...")
    joblib.dump(best_model, "btc_model.pkl")
    joblib.dump({"scaler": scaler, "features": selected_features}, "btc_scaler.pkl")
    
    return best_model, scaler, selected_features, eval_results

def predict_with_ensemble(model, scaler, features, data, days_to_predict=7, n_steps=30):
    """Makes future predictions using the trained ensemble model with recursive forecasting."""
    return recursive_forecast(model, scaler, features, data, days_to_predict, n_steps)

def evaluate_ensemble_model(model, scaler, features, df, n_steps=30):
    """Evaluates the model on a given dataset."""
    df = df.dropna(subset=features + ['target'])
    df_scaled = scaler.transform(df[features])
    
    X, y = create_sequences(pd.DataFrame(df_scaled, columns=features).assign(target=df['target'].values), 'target', features, n_steps)
    X = X.reshape(X.shape[0], -1)
    
    y_pred = model.predict(X)
    
    return {
        "r2_score": r2_score(y, y_pred),
        "mse": mean_squared_error(y, y_pred),
        "mae": mean_absolute_error(y, y_pred)
    } 