from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import datetime
import logging
import sys
import json

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]
CREDENTIALS_FILE = "./secrets/credentials.json"
TOKEN_FILE = "./secrets/token.json"


with open("./secrets/birthday.json", "r") as fi:
    BIRTHDAY = json.loads(fi.read())


LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_creds():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
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


def get_birthday_id(service):
    LOGGER.info("Getting birthday calendar ID")
    all_calendars = service.calendarList().list(pageToken=None).execute()
    id = None
    for i in all_calendars["items"]:
        if i["summary"] == "Birthdays (Real)":
            id = i["id"]
    if id is None:
        LOGGER.error("Unable to find Birthday Calendar ID")
        sys.exit(2)
    else:
        LOGGER.info(f"Birthday Calendar ID is {id}")
    return id


def get_existing_events(service, id):
    LOGGER.info(f"Getting events for calendar: {id}")
    events_result = service.events().list(
        calendarId=id,
        maxResults=2500,
        singleEvents=False,
        timeMin="2019-01-03T10:00:00-00:00"
    ).execute()
    nextpagetoken = events_result.get("nextPageToken")
    if nextpagetoken:
        LOGGER.error("TODO - Implement page tokens")
        sys.exit(2)
    events = events_result.get('items', [])
    LOGGER.info(f"Found {len(events)} existing calender events")
    return events


def delete_existing_events(service, id, events):
    LOGGER.info(f"Attempting to delete {len(events)} events")
    batch = service.new_batch_http_request()
    for event in events:
        batch.add(
            service.events().delete(calendarId=id, eventId=event['id'])
        )
    batch.execute()
    LOGGER.info("All events deleted!")


def get_birthday_data(service):
    LOGGER.info("Getting Birthday Spreadsheet data")
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=BIRTHDAY["BIRTHDAY_SHEET_ID"],
        range=BIRTHDAY["BIRTHDAY_DATA_RANGE"]
    ).execute()
    values = result.get('values', [])
    LOGGER.info(f"Got {len(values)} birthdays from gsheets")
    return values


def create_calendar_events(service, birthday_data):
    LOGGER.info(f"Attempting to create {len(birthday_data)} new events")
    now = datetime.datetime.now().year
    event_template = {
        'summary': 'TESTING CALENDER',
        'start': {
            'date': '',
            'timeZone': 'Europe/London',
        },
        'end': {
            'date': '',
            'timeZone': 'Europe/London',
        },
        "recurrence": ["RRULE:FREQ=YEARLY"]
    }
    batch = service.new_batch_http_request()
    for person in birthday_data:
        date = f"{now}-{person[2]}-{person[1]}"
        event_template["summary"] = person[0]
        event_template["start"]["date"] = date
        event_template["end"]["date"] = date
        batch.add(
            service.events().insert(calendarId=id, body=event_template)
        )
    batch.execute()
    LOGGER.info("All events created!")


if __name__ == "__main__":
    
    creds = get_creds()
    service_cal = build('calendar', 'v3', credentials=creds)
    service_sheets = build('sheets', 'v4', credentials=creds)
    
    id = get_birthday_id(service_cal)
    events = get_existing_events(service_cal, id)
    delete_existing_events(service_cal, id, events)
    
    birthday_data = get_birthday_data(service_sheets)
    create_calendar_events(service_cal, birthday_data)
