# Recursive Forecasting System Documentation

## Overview

The BTC Price Forecasting API v2.0 now implements a sophisticated **recursive forecasting system** that addresses the limitations of traditional time series forecasting methods. This system provides true multi-step forecasting where each prediction becomes input for the next step, with dynamic feature generation for each forecasted period.

## Key Features

### 1. True Recursive Forecasting
- **Each prediction feeds into the next**: Unlike traditional methods that use the same historical data for all future predictions, this system uses each predicted value as input for subsequent predictions.
- **Dynamic sequence updates**: The input sequence is updated after each prediction to include the newly forecasted values.
- **Realistic forecasting**: Predictions become more realistic as they account for the cumulative effects of previous forecasts.

### 2. Dynamic Feature Generation
- **Technical indicator regeneration**: For each forecasted step, new technical indicators are calculated based on the predicted price.
- **OHLC estimation**: Realistic Open, High, Low, Close values are generated for each forecasted day.
- **Volume prediction**: Volume is estimated based on price movement patterns.
- **Feature forecasting models**: Separate models are trained to predict key technical indicators.

### 3. Advanced Model Architecture
- **Ensemble approach**: Combines Random Forest, Gradient Boosting, and Ridge regression.
- **Feature selection**: Automatically selects the most relevant features using statistical tests.
- **Hyperparameter optimization**: Uses time series cross-validation for optimal model tuning.

## Implementation Details

### Core Functions

#### `recursive_forecast(model, scaler, features, initial_data, days_to_predict=7, n_steps=30)`
The main recursive forecasting function that:
1. Trains feature forecasting models for key indicators
2. Prepares the initial sequence from historical data
3. Iteratively predicts each day's price
4. Generates new features for each prediction
5. Updates the sequence for the next iteration

#### `generate_forecast_features(last_row, prediction, feature_cols)`
Generates realistic features for a forecasted step:
- Creates new OHLC values based on price movement direction
- Estimates volume based on price volatility
- Calculates technical indicators for the new data point
- Handles edge cases with fallback mechanisms

#### `train_feature_forecasting_model(df, feature_cols, n_steps=10)`
Trains separate models for forecasting key technical indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- BB_Position (Bollinger Band Position)
- Volume_Ratio
- Volatility

### API Endpoints

#### `/forecast/recursive` (POST)
Advanced recursive forecasting with feature generation:
```json
{
  "days": 7,
  "confidence_level": 0.8
}
```

#### `/forecast/features` (POST)
Forecast specific technical indicators:
```json
{
  "indicator": "RSI",
  "days": 5
}
```

#### `/predict` (POST)
Standard predictions using recursive forecasting:
```json
{
  "days": 7,
  "confidence_level": 0.8
}
```

## Technical Architecture

### Data Flow
1. **Historical Data Loading**: Fetches BTC price data with technical indicators
2. **Model Training**: Trains ensemble model with feature selection
3. **Recursive Prediction Loop**:
   - Predict next day's price
   - Generate new OHLC values
   - Calculate new technical indicators
   - Update input sequence
   - Repeat for specified number of days

### Feature Engineering Pipeline
1. **Price-based features**: Moving averages, EMAs, price momentum
2. **Volume indicators**: Volume ratios, volume moving averages
3. **Technical indicators**: RSI, MACD, Bollinger Bands, ROC, MOM
4. **Volatility measures**: Rolling standard deviations
5. **Momentum indicators**: Rate of change, momentum

### Model Ensemble
- **Random Forest**: Captures non-linear relationships
- **Gradient Boosting**: Handles complex feature interactions
- **Ridge Regression**: Provides regularization and stability
- **Stacking**: Combines predictions for optimal performance

## Advantages Over Traditional Methods

### 1. Realistic Predictions
- **No information leakage**: Each prediction uses only information available at that time
- **Cumulative effects**: Accounts for how previous predictions affect future ones
- **Market dynamics**: Reflects realistic price movement patterns

### 2. Feature Consistency
- **Dynamic indicators**: Technical indicators are recalculated for each step
- **Realistic values**: OHLC and volume estimates follow market patterns
- **No frozen features**: Features evolve with each prediction

### 3. Better Long-term Forecasting
- **Error propagation**: Naturally accounts for prediction uncertainty
- **Trend continuation**: Maintains realistic price momentum
- **Volatility modeling**: Reflects increasing uncertainty over time

## Usage Examples

### Basic Recursive Forecasting
```python
# Train the model first
response = requests.post("http://127.0.0.1:8000/train")

# Get recursive forecasts
forecast_response = requests.post("http://127.0.0.1:8000/forecast/recursive", 
                                json={"days": 7})
predictions = forecast_response.json()
```

### Technical Indicator Forecasting
```python
# Forecast RSI for next 5 days
rsi_forecast = requests.post("http://127.0.0.1:8000/forecast/features",
                           json={"indicator": "RSI", "days": 5})
rsi_predictions = rsi_forecast.json()
```

### Model Evaluation
```python
# Evaluate model performance
evaluation = requests.get("http://127.0.0.1:8000/evaluate")
metrics = evaluation.json()
```

## Performance Metrics

The system provides comprehensive evaluation metrics:
- **R² Score**: Measures prediction accuracy
- **Mean Squared Error (MSE)**: Quantifies prediction errors
- **Mean Absolute Error (MAE)**: Provides error magnitude
- **Cross-validation scores**: Ensures model robustness

## Future Enhancements

### Planned Improvements
1. **Monte Carlo Simulations**: Add uncertainty quantification
2. **Multiple Timeframes**: Support for hourly, weekly predictions
3. **Sentiment Integration**: Incorporate news and social media sentiment
4. **Market Regime Detection**: Adapt to different market conditions
5. **Real-time Updates**: Continuous model retraining with new data

### Advanced Features
1. **Confidence Intervals**: Provide prediction uncertainty ranges
2. **Scenario Analysis**: Multiple prediction scenarios
3. **Risk Metrics**: VaR, Sharpe ratio calculations
4. **Portfolio Integration**: Support for portfolio optimization

## Troubleshooting

### Common Issues
1. **Feature Generation Errors**: Check data quality and indicator calculations
2. **Model Convergence**: Ensure sufficient training data
3. **Memory Usage**: Large datasets may require optimization
4. **Prediction Stability**: Monitor for unrealistic predictions

### Best Practices
1. **Regular Retraining**: Update models with new data
2. **Feature Monitoring**: Track feature importance changes
3. **Performance Validation**: Validate predictions against actual data
4. **Error Handling**: Implement robust error handling for edge cases

## Conclusion

The recursive forecasting system represents a significant advancement in time series forecasting for cryptocurrency prices. By implementing true recursive prediction with dynamic feature generation, the system provides more realistic and accurate forecasts that better reflect market dynamics and prediction uncertainty.

This implementation addresses the fundamental limitations of traditional forecasting methods and provides a robust foundation for advanced financial modeling and risk management applications. 