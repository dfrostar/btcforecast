# Upgrade Components Guide

This guide provides code snippets and examples for implementing consistent upgrade prompts throughout the BTC Forecast application.

## 🎯 Overview

The upgrade components provide a consistent user experience for promoting premium features and encouraging subscription upgrades. There are two main components:

1. **`display_upgrade_banner()`** - Full-featured upgrade banner with feature list
2. **`display_feature_lock_banner()`** - Simple lock banner for basic features

## 🚀 Main Upgrade Banner Component

### Basic Usage

```python
def display_upgrade_banner(feature_name: str, premium_features: list = None, 
                          cta_text: str = "💳 Upgrade Now", price: str = "$29.99/month"):
    """Display a consistent upgrade banner for premium-locked features."""
```

### Example Implementations

#### 1. Live Prices Tab
```python
elif selected == "💰 Live Prices":
    st.title("💰 Live Cryptocurrency Prices")
    
    try:
        prices_data = get_api_data("realtime/prices")
        
        if prices_data and 'prices' in prices_data:
            # Show live prices
            st.success("✅ Real-time data connection: Active")
            # ... display prices ...
        else:
            st.error("❌ Real-time data connection: Failed")
            display_upgrade_banner("Real-time cryptocurrency prices", [
                "Live price updates every 30 seconds",
                "Real-time volume and market data",
                "Price alerts and notifications",
                "Advanced charting tools",
                "Portfolio tracking",
                "Risk analytics"
            ])
    except Exception as e:
        st.error(f"❌ Real-time data connection: Failed - {str(e)}")
        display_upgrade_banner("Real-time cryptocurrency prices", [
            "Live price updates every 30 seconds",
            "Real-time volume and market data", 
            "Price alerts and notifications",
            "Advanced charting tools",
            "Portfolio tracking",
            "Risk analytics"
        ])
```

#### 2. Community Features
```python
# For forums
display_upgrade_banner("Community forums", [
    "Create and participate in discussions",
    "Share trading strategies and insights",
    "Connect with other traders",
    "Access expert analysis",
    "Real-time notifications",
    "Moderated content quality"
])

# For shared predictions
display_upgrade_banner("Shared predictions", [
    "View community predictions",
    "Like and comment on predictions",
    "Share your own forecasts",
    "Track prediction accuracy",
    "Follow top predictors",
    "Real-time prediction feeds"
])

# For trending content
display_upgrade_banner("Trending content", [
    "Real-time trending predictions",
    "Popular forum discussions",
    "Trending hashtags and topics",
    "Community insights",
    "Market sentiment analysis",
    "Social trading signals"
])
```

#### 3. Portfolio Management
```python
elif selected == "💼 Portfolio":
    st.title("💼 Portfolio Management")
    
    if st.session_state.get('demo_mode', False):
        display_upgrade_banner("Portfolio management", [
            "Multi-asset portfolio tracking",
            "Real-time portfolio analytics",
            "Risk metrics (Sharpe ratio, VaR, drawdown)",
            "Portfolio optimization tools",
            "Performance benchmarking",
            "Automated rebalancing"
        ])
        return
```

#### 4. Advanced Forecast Features
```python
# For 7-day forecasts
display_upgrade_banner("7-day forecast", [
    "Advanced AI-powered predictions",
    "Multiple forecasting models",
    "Confidence intervals",
    "Risk assessment",
    "Technical analysis integration",
    "Market sentiment analysis"
])
```

### Customization Options

#### Custom CTA Text and Price
```python
display_upgrade_banner(
    feature_name="Advanced Analytics",
    premium_features=["Feature 1", "Feature 2", "Feature 3"],
    cta_text="🚀 Start Free Trial",
    price="$19.99/month"
)
```

#### Different Feature Lists
```python
# For API access
api_features = [
    "RESTful API access",
    "WebSocket connections",
    "Rate limiting (1000 req/hour)",
    "Real-time data feeds",
    "Custom webhooks",
    "API documentation"
]
display_upgrade_banner("API access", api_features)

# For enterprise features
enterprise_features = [
    "Custom integrations",
    "Dedicated support",
    "SLA guarantees",
    "Custom model training",
    "On-premise deployment",
    "White-label options"
]
display_upgrade_banner("Enterprise features", enterprise_features, 
                      cta_text="💼 Contact Sales", price="$299/month")
```

## 🔒 Simple Feature Lock Banner

### Basic Usage

```python
def display_feature_lock_banner(feature_name: str, message: str = None):
    """Display a simple feature lock banner for basic premium features."""
```

### Examples

#### 1. Basic Feature Lock
```python
display_feature_lock_banner("Advanced Charts")
```

#### 2. Custom Message
```python
display_feature_lock_banner(
    "Risk Analytics", 
    "Upgrade to Premium to access advanced risk metrics"
)
```

#### 3. In Context
```python
if not user_has_premium:
    display_feature_lock_banner("Portfolio Analytics")
    st.info("Please upgrade to access portfolio analytics features")
else:
    # Show portfolio analytics
    display_portfolio_analytics()
```

## 🎨 Styling and Customization

### CSS Classes Used

The upgrade banners use the following CSS classes that are defined in the mobile CSS:

```css
/* Mobile-first responsive design */
@media screen and (max-width: 768px) {
    .stButton > button {
        min-height: 44px;
        font-size: 16px;
        width: 100%;
        max-width: 300px;
    }
    
    .price-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        text-align: center;
    }
}
```

### Color Schemes

- **Primary Gradient**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Success Gradient**: `linear-gradient(135deg, #28a745 0%, #20c997 100%)`
- **Lock Banner**: `linear-gradient(135deg, #6c757d 0%, #495057 100%)`

## 📱 Mobile Responsiveness

The upgrade banners are fully responsive and include:

- Mobile-optimized button sizes (44px minimum height)
- Responsive text sizing
- Touch-friendly interactions
- Optimized spacing for mobile devices

## 🔧 Integration with Session State

### Demo Mode Detection
```python
if st.session_state.get('demo_mode', False):
    display_upgrade_banner("Feature Name", feature_list)
    return
```

### User Authentication Check
```python
if not st.session_state.get('authenticated', False):
    display_upgrade_banner("User Dashboard", [
        "Personalized predictions",
        "Save favorite analyses",
        "Custom alerts",
        "Portfolio tracking"
    ])
    return
```

## 📊 Analytics and Tracking

### Click Tracking
The upgrade banners include JavaScript for tracking clicks:

```javascript
onclick="window.location.href='#subscriptions'"
```

### Custom Event Tracking
You can add custom tracking by modifying the onclick handler:

```javascript
onclick="trackUpgradeClick('feature_name'); window.location.href='#subscriptions'"
```

## 🚀 Best Practices

1. **Consistent Messaging**: Use the same upgrade banner across similar features
2. **Feature-Specific Lists**: Customize feature lists to match the specific feature being promoted
3. **Clear Value Proposition**: Focus on benefits rather than just features
4. **Mobile-First**: Ensure banners work well on mobile devices
5. **A/B Testing**: Test different CTA texts and feature lists
6. **Contextual Placement**: Show upgrade banners when users try to access premium features

## 🔄 Maintenance

### Adding New Features
When adding new premium features:

1. Update the default feature list in `display_upgrade_banner()`
2. Add feature-specific banners where appropriate
3. Update this documentation with new examples

### Updating Pricing
To update pricing across all banners:

1. Modify the default `price` parameter in `display_upgrade_banner()`
2. Update any hardcoded price references
3. Test all upgrade banners to ensure consistency

## 📝 Code Snippet Template

Here's a template for implementing upgrade banners in new features:

```python
def new_premium_feature():
    """Example of implementing upgrade banner for new feature."""
    
    # Check if user has access
    if not user_has_premium_access():
        display_upgrade_banner("New Feature Name", [
            "Benefit 1",
            "Benefit 2", 
            "Benefit 3",
            "Benefit 4",
            "Benefit 5",
            "Benefit 6"
        ])
        return
    
    # Show premium feature
    st.write("### Premium Feature Content")
    # ... feature implementation ...
```

This guide ensures consistent implementation of upgrade prompts throughout the application while maintaining a professional and user-friendly experience. 