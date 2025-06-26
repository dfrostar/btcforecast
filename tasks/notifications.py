"""
Notification Background Tasks
Automated alerts, system notifications, and reporting
"""

import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from celery import current_task
from celery.utils.log import get_task_logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from config import settings

logger = get_task_logger(__name__)

@current_task.task(bind=True, name="notifications.send_price_alert")
def send_price_alert(self, user_id: str, alert_type: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send price alert to user
    
    Args:
        user_id: User ID to send alert to
        alert_type: Type of alert (price_drop, price_spike, etc.)
        price_data: Current price data
        
    Returns:
        Dict containing notification results
    """
    try:
        logger.info(f"Starting price alert task {self.request.id} for user {user_id}")
        
        # Get user notification preferences
        user_prefs = get_user_notification_preferences(user_id)
        
        if not user_prefs.get("price_alerts_enabled", False):
            logger.info(f"Price alerts disabled for user {user_id}")
            return {
                "status": "skipped",
                "reason": "Price alerts disabled",
                "user_id": user_id,
                "task_id": self.request.id
            }
        
        # Format alert message
        alert_message = format_price_alert(alert_type, price_data)
        
        # Send notification through preferred channels
        notification_results = {}
        
        if user_prefs.get("email_enabled", False):
            email_result = send_email_notification(
                user_id, 
                "BTC Price Alert", 
                alert_message,
                user_prefs.get("email_address")
            )
            notification_results["email"] = email_result
        
        if user_prefs.get("sms_enabled", False):
            sms_result = send_sms_notification(
                user_id,
                alert_message,
                user_prefs.get("phone_number")
            )
            notification_results["sms"] = sms_result
        
        if user_prefs.get("webhook_enabled", False):
            webhook_result = send_webhook_notification(
                user_id,
                alert_type,
                price_data,
                user_prefs.get("webhook_url")
            )
            notification_results["webhook"] = webhook_result
        
        # Log notification
        log_notification(user_id, alert_type, notification_results)
        
        result = {
            "status": "success",
            "user_id": user_id,
            "alert_type": alert_type,
            "notification_results": notification_results,
            "task_id": self.request.id,
            "sent_time": datetime.now().isoformat()
        }
        
        logger.info(f"Price alert sent successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Price alert failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        if self.request.retries < 3:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(countdown=countdown, max_retries=3)
        
        return {
            "status": "failed",
            "error": str(e),
            "user_id": user_id,
            "task_id": self.request.id,
            "retries": self.request.retries
        }

@current_task.task(bind=True, name="notifications.send_system_alert")
def send_system_alert(self, alert_type: str, alert_data: Dict[str, Any], 
                     severity: str = "info") -> Dict[str, Any]:
    """
    Send system alert to administrators
    
    Args:
        alert_type: Type of system alert
        alert_data: Alert data and context
        severity: Alert severity (info, warning, error, critical)
        
    Returns:
        Dict containing alert results
    """
    try:
        logger.info(f"Starting system alert task {self.request.id}")
        
        # Get admin notification list
        admin_users = get_admin_users()
        
        if not admin_users:
            logger.warning("No admin users found for system alert")
            return {
                "status": "failed",
                "error": "No admin users found",
                "task_id": self.request.id
            }
        
        # Format system alert message
        alert_message = format_system_alert(alert_type, alert_data, severity)
        
        # Send to all admins
        notification_results = {}
        for admin_user in admin_users:
            try:
                if admin_user.get("email_enabled", False):
                    email_result = send_email_notification(
                        admin_user["id"],
                        f"System Alert: {alert_type}",
                        alert_message,
                        admin_user.get("email_address")
                    )
                    notification_results[admin_user["id"]] = {
                        "email": email_result
                    }
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_user['id']}: {e}")
                notification_results[admin_user["id"]] = {
                    "error": str(e)
                }
        
        # Log system alert
        log_system_alert(alert_type, alert_data, severity, notification_results)
        
        result = {
            "status": "success",
            "alert_type": alert_type,
            "severity": severity,
            "admin_count": len(admin_users),
            "notification_results": notification_results,
            "task_id": self.request.id,
            "sent_time": datetime.now().isoformat()
        }
        
        logger.info(f"System alert sent successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"System alert failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="notifications.send_daily_report")
def send_daily_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send daily report to users
    
    Args:
        user_id: Specific user ID (sends to all if None)
        
    Returns:
        Dict containing report results
    """
    try:
        logger.info(f"Starting daily report task {self.request.id}")
        
        # Generate daily report data
        report_data = generate_daily_report_data()
        
        # Get users to send reports to
        if user_id:
            users = [get_user_by_id(user_id)] if get_user_by_id(user_id) else []
        else:
            users = get_users_with_daily_reports()
        
        if not users:
            logger.info("No users found for daily reports")
            return {
                "status": "success",
                "message": "No users found for daily reports",
                "task_id": self.request.id
            }
        
        # Send reports
        notification_results = {}
        for user in users:
            try:
                # Generate personalized report
                personalized_report = personalize_report(report_data, user)
                
                # Send email report
                if user.get("email_enabled", False):
                    email_result = send_email_notification(
                        user["id"],
                        "BTC Forecast Daily Report",
                        personalized_report,
                        user.get("email_address"),
                        is_html=True
                    )
                    notification_results[user["id"]] = {
                        "email": email_result
                    }
            except Exception as e:
                logger.error(f"Failed to send daily report to user {user['id']}: {e}")
                notification_results[user["id"]] = {
                    "error": str(e)
                }
        
        # Log daily report
        log_daily_report(users, notification_results)
        
        result = {
            "status": "success",
            "user_count": len(users),
            "notification_results": notification_results,
            "task_id": self.request.id,
            "sent_time": datetime.now().isoformat()
        }
        
        logger.info(f"Daily reports sent successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily report failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="notifications.send_model_update_notification")
def send_model_update_notification(self, model_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send notification about model updates
    
    Args:
        model_metrics: New model performance metrics
        
    Returns:
        Dict containing notification results
    """
    try:
        logger.info(f"Starting model update notification task {self.request.id}")
        
        # Get users interested in model updates
        users = get_users_with_model_notifications()
        
        if not users:
            logger.info("No users found for model update notifications")
            return {
                "status": "success",
                "message": "No users found for model notifications",
                "task_id": self.request.id
            }
        
        # Format model update message
        update_message = format_model_update_message(model_metrics)
        
        # Send notifications
        notification_results = {}
        for user in users:
            try:
                if user.get("email_enabled", False):
                    email_result = send_email_notification(
                        user["id"],
                        "Model Update Notification",
                        update_message,
                        user.get("email_address")
                    )
                    notification_results[user["id"]] = {
                        "email": email_result
                    }
            except Exception as e:
                logger.error(f"Failed to send model update to user {user['id']}: {e}")
                notification_results[user["id"]] = {
                    "error": str(e)
                }
        
        result = {
            "status": "success",
            "user_count": len(users),
            "notification_results": notification_results,
            "task_id": self.request.id,
            "sent_time": datetime.now().isoformat()
        }
        
        logger.info(f"Model update notifications sent successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Model update notification failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

# Helper functions
def get_user_notification_preferences(user_id: str) -> Dict[str, Any]:
    """Get user notification preferences"""
    try:
        # Implementation to fetch from database
        # Placeholder implementation
        return {
            "price_alerts_enabled": True,
            "email_enabled": True,
            "sms_enabled": False,
            "webhook_enabled": False,
            "email_address": "user@example.com",
            "phone_number": None,
            "webhook_url": None
        }
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return {}

def format_price_alert(alert_type: str, price_data: Dict[str, Any]) -> str:
    """Format price alert message"""
    current_price = price_data.get("current_price", 0)
    change_percent = price_data.get("change_percent", 0)
    
    if alert_type == "price_drop":
        message = f"⚠️ BTC Price Alert: Price dropped to ${current_price:,.2f} ({change_percent:.2f}%)"
    elif alert_type == "price_spike":
        message = f"🚀 BTC Price Alert: Price spiked to ${current_price:,.2f} ({change_percent:.2f}%)"
    elif alert_type == "support_level":
        message = f"📉 BTC Price Alert: Approaching support level at ${current_price:,.2f}"
    elif alert_type == "resistance_level":
        message = f"📈 BTC Price Alert: Approaching resistance level at ${current_price:,.2f}"
    else:
        message = f"📊 BTC Price Alert: Current price ${current_price:,.2f} ({change_percent:.2f}%)"
    
    return message

def send_email_notification(user_id: str, subject: str, message: str, 
                          email_address: str, is_html: bool = False) -> Dict[str, Any]:
    """Send email notification"""
    try:
        if not settings.EMAIL_ENABLED:
            logger.warning("Email notifications disabled")
            return {"status": "disabled"}
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = email_address
        
        if is_html:
            msg.attach(MIMEText(message, 'html'))
        else:
            msg.attach(MIMEText(message, 'plain'))
        
        # Send email
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(msg)
        
        return {"status": "sent", "email": email_address}
        
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return {"status": "failed", "error": str(e)}

def send_sms_notification(user_id: str, message: str, phone_number: str) -> Dict[str, Any]:
    """Send SMS notification"""
    try:
        if not settings.SMS_ENABLED:
            logger.warning("SMS notifications disabled")
            return {"status": "disabled"}
        
        # Implementation would integrate with SMS service (Twilio, etc.)
        # Placeholder implementation
        logger.info(f"SMS notification to {phone_number}: {message}")
        
        return {"status": "sent", "phone": phone_number}
        
    except Exception as e:
        logger.error(f"SMS notification failed: {e}")
        return {"status": "failed", "error": str(e)}

def send_webhook_notification(user_id: str, alert_type: str, data: Dict[str, Any], 
                            webhook_url: str) -> Dict[str, Any]:
    """Send webhook notification"""
    try:
        if not webhook_url:
            return {"status": "no_webhook"}
        
        payload = {
            "user_id": user_id,
            "alert_type": alert_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {"status": "sent", "webhook_url": webhook_url}
        else:
            return {"status": "failed", "status_code": response.status_code}
        
    except Exception as e:
        logger.error(f"Webhook notification failed: {e}")
        return {"status": "failed", "error": str(e)}

def format_system_alert(alert_type: str, alert_data: Dict[str, Any], severity: str) -> str:
    """Format system alert message"""
    severity_icons = {
        "info": "ℹ️",
        "warning": "⚠️", 
        "error": "❌",
        "critical": "🚨"
    }
    
    icon = severity_icons.get(severity, "ℹ️")
    
    message = f"{icon} System Alert: {alert_type}\n\n"
    message += f"Severity: {severity.upper()}\n"
    message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    
    for key, value in alert_data.items():
        message += f"{key}: {value}\n"
    
    return message

def get_admin_users() -> List[Dict[str, Any]]:
    """Get list of admin users"""
    try:
        # Implementation to fetch from database
        # Placeholder implementation
        return [
            {
                "id": "admin1",
                "email_enabled": True,
                "email_address": "admin@example.com"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting admin users: {e}")
        return []

def generate_daily_report_data() -> Dict[str, Any]:
    """Generate daily report data"""
    try:
        # Implementation to generate report data
        # Placeholder implementation
        return {
            "current_price": 45000,
            "daily_change": 2.5,
            "prediction_accuracy": 0.75,
            "market_sentiment": "bullish",
            "top_indicators": ["RSI", "MACD", "Bollinger Bands"]
        }
    except Exception as e:
        logger.error(f"Error generating daily report data: {e}")
        return {}

def get_users_with_daily_reports() -> List[Dict[str, Any]]:
    """Get users who should receive daily reports"""
    try:
        # Implementation to fetch from database
        # Placeholder implementation
        return [
            {
                "id": "user1",
                "email_enabled": True,
                "email_address": "user@example.com"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting users for daily reports: {e}")
        return []

def personalize_report(report_data: Dict[str, Any], user: Dict[str, Any]) -> str:
    """Personalize report for specific user"""
    try:
        # Implementation to personalize report
        # Placeholder implementation
        return f"""
        <html>
        <body>
        <h2>BTC Forecast Daily Report</h2>
        <p>Current Price: ${report_data.get('current_price', 0):,.2f}</p>
        <p>Daily Change: {report_data.get('daily_change', 0):.2f}%</p>
        <p>Prediction Accuracy: {report_data.get('prediction_accuracy', 0):.1%}</p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error personalizing report: {e}")
        return "Daily report generation failed"

def format_model_update_message(model_metrics: Dict[str, Any]) -> str:
    """Format model update notification message"""
    r2_score = model_metrics.get("r2_score", 0)
    mae = model_metrics.get("mae", 0)
    
    message = f"🤖 Model Update Notification\n\n"
    message += f"New model performance metrics:\n"
    message += f"R² Score: {r2_score:.3f}\n"
    message += f"MAE: ${mae:,.2f}\n"
    message += f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    
    return message

def get_users_with_model_notifications() -> List[Dict[str, Any]]:
    """Get users who should receive model update notifications"""
    try:
        # Implementation to fetch from database
        # Placeholder implementation
        return [
            {
                "id": "user1",
                "email_enabled": True,
                "email_address": "user@example.com"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting users for model notifications: {e}")
        return []

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        # Implementation to fetch from database
        # Placeholder implementation
        return {
            "id": user_id,
            "email_enabled": True,
            "email_address": "user@example.com"
        }
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

# Logging functions
def log_notification(user_id: str, alert_type: str, results: Dict[str, Any]) -> None:
    """Log notification attempt"""
    try:
        # Implementation to log to database
        logger.info(f"Notification logged: user={user_id}, type={alert_type}, results={results}")
    except Exception as e:
        logger.error(f"Error logging notification: {e}")

def log_system_alert(alert_type: str, alert_data: Dict[str, Any], severity: str, 
                    results: Dict[str, Any]) -> None:
    """Log system alert"""
    try:
        # Implementation to log to database
        logger.info(f"System alert logged: type={alert_type}, severity={severity}, results={results}")
    except Exception as e:
        logger.error(f"Error logging system alert: {e}")

def log_daily_report(users: List[Dict[str, Any]], results: Dict[str, Any]) -> None:
    """Log daily report"""
    try:
        # Implementation to log to database
        logger.info(f"Daily report logged: users={len(users)}, results={results}")
    except Exception as e:
        logger.error(f"Error logging daily report: {e}") 