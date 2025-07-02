import os
import requests
import logging
import smtplib

from dotenv import load_dotenv
from livekit import api
from livekit.agents import function_tool, RunContext
from textwrap import dedent
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

@function_tool
async def validate_address(
    context: RunContext,
    street_address: str,
    city: str,
    zip_code: str,
    state: str,
):
    """
    Check whether the address is valid
    """
    try:
        body = {
            'address': {
                'locality': city,
                'administrativeArea': state,
                'postalCode': zip_code,
                'addressLines': [street_address],
            }
        }

        logging.info(f'validating address for {body}')

        response = requests.post(
            f'https://addressvalidation.googleapis.com/v1:validateAddress?key={GOOGLE_MAPS_API_KEY}', 
            json=body
        )

        response_body = response.json()
        logging.info(f'address validation response: {response.json()}')

        if response.status_code == 200:
            if 'hasUnconfirmedComponents' in response_body and response_body['hasUnconfirmedComponents']:
                logging.info(f"unconfirmed address components: {response_body['unconfirmedComponentTypes']}")
                return f"the following components could not be validated: {response_body['unconfirmedComponentTypes']}"
            return response_body
        else:
            logging.error('failed to validate address')
            return 'failed to validate address'
    except Exception as e:
        logging.error(f'error occured while validating address: {e}')
        return 'error occured while validating address'

@function_tool
async def send_confirmation_email(
    context: RunContext,
    to_email: str,
    appointment_date: str,
    appointment_time: str,
    doctor_name: str,
):
    """
    Send an email through Gmail SMTP

    Args:
        to_email: Recipient email address
        appointment_date: Date of scheduled appointment (Ex. Tuesday, July 1st) 
        appointment_time: Time of scheduled appointment
        doctor_name: Name of the doctor for scheduled appointment
    """

    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not gmail_user or not gmail_password:
            logging.error('The Gmail credentials could not be retrieved from environment variables')
            return 'Error sending email: Gmail credentials not configured'

        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = 'Assort Health Appointment Confirmation'
        
        recipients = [to_email]

        message_body = dedent(
            f"""
            Your appointment at Assort Health with {doctor_name} has been confirmed for {appointment_date} at {appointment_time}.

            We look forward to seeing you soon!
            """
        )

        msg.attach(MIMEText(message_body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(gmail_user, gmail_password)

        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()

        logging.info(f'Email sent successfully to {to_email}')
        return f'Email sent successfully to {to_email}'
    
    except smtplib.SMTPAuthenticationError:
        logging.error('Gmail authentication failed')
        return 'Email sending failed: Authentication error. Please check your Gmail credentials'
    except smtplib.SMTPException as e:
        logging.error(f'SMTP error occurred: {e}')
        return f'Email sending failed: SMTP error - {str(e)}'
    except Exception as e:
        logging.error(f'Error sending email: {e}')
        return f'An error occurred while sending email: {str(e)}'
    
@function_tool
def get_current_date(context: RunContext):
    now = datetime.now()
    day = now.day
    return now.strftime(f"%A, %B {day}, %Y")

@function_tool
async def end_call(context: RunContext):
    """
    End the call with the user
    """
    # let the agent finish speaking
    current_speech = context.session.current_speech
    if current_speech:
        logging.info('Awaiting current speech to complete')
        await current_speech.wait_for_playout()

    logging.info('Ending the call')
    await hangup_call(context)


async def hangup_call(context: RunContext):
    if context is None:
        logging.error('Failed to end the call: No context found')
        return

    try:
        await context.api.room.delete_room(
            api.DeleteRoomRequest(
                room=context.room.name,
            )
        )
        logging.info(f'Successfully ended room: {context.room.name}')
    except Exception as e:
        logging.error(f'Failed to end the call: {e}')    
        
