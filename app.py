from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import datetime
from datetime import date
import logging
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apiclient import errors


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/contacts.readonly"
]
CREDENTIALS_FILE = "./secrets/credentials.json"
TOKEN_FILE = "./secrets/token.json"
TODAY = date.today()
TODAY_YEAR = date.today().year

with open("./secrets/config.json", "r") as fi:
    CONFIG = json.loads(fi.read())


LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_creds():
    LOGGER.info("Reading Token file f{TOKEN_FILE}")
    creds = None
    if os.path.exists(TOKEN_FILE):
        LOGGER.info("Token Found")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            LOGGER.info("Refreshing Token")
            creds.refresh(Request())
        else:
            LOGGER.info("Getting new token, using secrets: f{CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            LOGGER.info(f"Writing token to file: {TOKEN_FILE}")
            token.write(creds.to_json())
    return creds


def get_rtm_string(contact):
    STRING = "{name} #Birthdays *every year ^{day}/{month}/{year}"
    birthdays = contact.get("birthdays", [])
    if not birthdays:
        return None
    d = birthdays[0]["date"]
    if datetime.date(TODAY_YEAR, d["month"], d["day"]) < TODAY:
        year = TODAY_YEAR + 1
    else:
        year = TODAY_YEAR
    return STRING.format(
        name=contact["names"][0]["displayName"],
        day=d["day"],
        month=d["month"],
        year=year
    )


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_contacts(service):
    LOGGER.info("Getting contacts")
    results = service.people().connections().list(
        resourceName="people/me",
        pageSize=1000,
        personFields='names,birthdays'
    ).execute()
    connections = results.get('connections', [])
    LOGGER.info(f"Got {len(connections)} contacts")
    return connections


def get_chunked_strings(connections, chunk_size=30):
    strings_with_null = [get_rtm_string(i) for i in connections]
    strings = [i for i in strings_with_null if i]
    strings_chunked = list(chunks(strings, chunk_size))
    LOGGER.info(f"Reduced to {len(strings)} contacts with birthdays")
    return strings_chunked


def SendMessageInternal(service, message):
    LOGGER.info("Sending Email")
    try:
        message = service.users().messages().send(
            userId="me",
            body=message
        ).execute()
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def CreateMessage(content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Import Me"
    msg['From'] = CONFIG["email_me"]
    msg['To'] = CONFIG["email_rtm"]
    msg.attach(MIMEText(content, 'plain'))
    raw = base64.urlsafe_b64encode(msg.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}
    return body


if __name__ == "__main__":
    creds = get_creds()
    service_cal = build('people', 'v1', credentials=creds)
    service_mail = build('gmail', 'v1', credentials=creds)
    connections = get_contacts(service_cal)
    strings = get_chunked_strings(connections)
    messages = [CreateMessage("\n".join(i)) for i in strings]
    for message in messages:
        SendMessageInternal(service_mail, message)
