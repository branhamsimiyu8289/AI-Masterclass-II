import html
import logging
import os
import smtplib
import time
from pathlib import Path
from email.mime.text import MIMEText


def _send_message(msg):
    address = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not address or not app_password:
        raise RuntimeError(
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in the environment."
        )

    msg["From"] = address
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.send_message(msg)


def send_email(to, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["To"] = to
    _send_message(msg)
    logging.info("Sent email")


from email.mime.multipart import MIMEMultipart

def send_html_report(to, data):
    html_body = (
        '<html><body style="font-family: Arial, sans-serif;">'
        '<h2 style="color: #1F4E79;">Weekly Sales Report</h2>'
        '<table border="1" cellpadding="8" style="border-collapse:collapse;">'
        '<tr style="background:#1F4E79; color:white;"><th>County</th><th>Orders</th><th>Revenue (KES)</th></tr>'
        f'<tr><td>Nairobi</td><td>{html.escape(str(data["nairobi_orders"]))}</td><td>{data["nairobi_revenue"]:,}</td></tr>'
        f'<tr><td>Mombasa</td><td>{html.escape(str(data["mombasa_orders"]))}</td><td>{data["mombasa_revenue"]:,}</td></tr>'
        '</table></body></html>'
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Weekly Sales Report"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    _send_message(msg)
    logging.info("Sent HTML report")


def fetch_todays_data():
    raise NotImplementedError(
        "Connect fetch_todays_data() to your report data source before scheduling."
    )


def daily_report_job():
    try:
        data = fetch_todays_data()
        send_html_report("manager@company.co.ke", data)
        logging.info("OK - daily report sent")
    except Exception as exc:
        logging.error("FAILED - daily report (%s)", type(exc).__name__)


def main():
    from dotenv import load_dotenv
    import schedule

    load_dotenv(Path(__file__).with_name(".env"))
    logging.basicConfig(
        filename="email_log.txt",
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
    )
    schedule.every().day.at("08:00").do(daily_report_job)
    logging.info("Daily report scheduler started")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()

