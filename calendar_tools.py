# calendar_tools.py
import datetime
import os
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger_config import logger

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            logger.error(f"Failed to load token.json: {e}. Forcing re-auth.")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}. Forcing re-auth.")
                if os.path.exists("token.json"): os.remove("token.json")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def check_availability(start_time: str, end_time: str, duration_minutes: int, timezone: str = "Asia/Kolkata") -> list[str]:
    logger.info(f"Tool 'check_availability' called with args: start={start_time}, end={end_time}")
    try:
        service = get_calendar_service()
        start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        body = {"timeMin": start_dt.isoformat(), "timeMax": end_dt.isoformat(), "timeZone": timezone, "items": [{"id": "primary"}]}
        events_result = service.freebusy().query(body=body).execute()
        busy_intervals = events_result.get('calendars', {}).get('primary', {}).get('busy', [])
        available_slots = []
        current_time = start_dt
        busy_intervals.sort(key=lambda x: x['start'])
        for busy in busy_intervals:
            busy_start = datetime.datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            if current_time + datetime.timedelta(minutes=duration_minutes) <= busy_start:
                available_slots.append(current_time.isoformat())
            busy_end = datetime.datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
            current_time = max(current_time, busy_end)
        if current_time + datetime.timedelta(minutes=duration_minutes) <= end_dt:
            available_slots.append(current_time.isoformat())
        return available_slots
    except Exception as e:
        logger.error(f"Error in check_availability: {e}", exc_info=True)
        return [f"An error occurred: {e}"]


def create_calendar_event(start_time: str, end_time: str, title: str, timezone: str = "Asia/Kolkata") -> str:
    logger.info(f"Tool 'create_calendar_event' called with args: start={start_time}, title={title}")
    try:
        service = get_calendar_service()
        event = {'summary': title, 'start': {'dateTime': start_time, 'timeZone': timezone}, 'end': {'dateTime': end_time, 'timeZone': timezone}}
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Success! The event '{title}' has been scheduled. Link: {created_event.get('htmlLink')}"
    except Exception as e:
        logger.error(f"Error in create_calendar_event: {e}", exc_info=True)
        return f"An error occurred: {e}"


def get_day_schedule(day: str, timezone: str = "Asia/Kolkata") -> list[str]:
    logger.info(f"Tool 'get_day_schedule' called for day: {day}")
    try:
        service = get_calendar_service()
        tz = pytz.timezone(timezone)
        if day.lower() == 'today':
            start_dt = datetime.datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        elif day.lower() == 'tomorrow':
            start_dt = (datetime.datetime.now(tz) + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_dt = tz.localize(datetime.datetime.strptime(day, "%Y-%m-%d"))
        end_dt = start_dt + datetime.timedelta(days=1, microseconds=-1)
        events_result = service.events().list(calendarId='primary', timeMin=start_dt.isoformat(), timeMax=end_dt.isoformat(), singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        if not events: return ["Your schedule for that day is completely free."]
        schedule = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            start_time_obj = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(tz)
            end_time_obj = datetime.datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(tz)
            schedule.append(f"{start_time_obj.strftime('%I:%M %p')} - {end_time_obj.strftime('%I:%M %p')}: {event['summary']}")
        return schedule
    except Exception as e:
        logger.error(f"Error in get_day_schedule: {e}", exc_info=True)
        return [f"An error occurred: {e}"]

# --- NEW, POWERFUL TOOL ---
def manage_calendar_event(query: str, action: str, new_start_time: str = None, new_end_time: str = None, timezone: str = "Asia/Kolkata") -> str:
    """
    Finds, deletes, or updates a single calendar event based on a search query.

    Args:
        query: The search text to find the event (e.g., 'Meeting with HQ').
        action: The operation to perform: 'delete' or 'update'.
        new_start_time: The new start time if updating (ISO 8601 format).
        new_end_time: The new end time if updating (ISO 8601 format).
        timezone: The user's IANA timezone.

    Returns:
        A confirmation message of the action performed.
    """
    logger.info(f"Tool 'manage_calendar_event' called with query: '{query}', action: '{action}'")
    try:
        service = get_calendar_service()
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now(tz)

        events_result = service.events().list(calendarId='primary', q=query, timeMin=now.isoformat(), maxResults=5, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return f"Error: No upcoming events found matching '{query}'."
        if len(events) > 1:
            return f"Error: Found multiple events matching '{query}'. Please be more specific."

        event = events[0]
        event_id = event['id']
        summary = event['summary']

        if action.lower() == 'delete':
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            logger.info(f"Event '{summary}' (ID: {event_id}) deleted successfully.")
            return f"Success: The event '{summary}' has been permanently deleted."
        
        elif action.lower() == 'update':
            if not new_start_time or not new_end_time:
                return "Error: To update an event, you must provide both a new start and end time."
            
            event['start']['dateTime'] = new_start_time
            event['end']['dateTime'] = new_end_time
            updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            logger.info(f"Event '{summary}' (ID: {event_id}) updated successfully.")
            return f"Success: The event '{summary}' has been updated. New time: {new_start_time}. Link: {updated_event.get('htmlLink')}"
        
        else:
            return f"Error: Invalid action '{action}'. Please use 'delete' or 'update'."

    except Exception as e:
        logger.error(f"Error in manage_calendar_event: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"