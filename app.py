# app.py
import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime
import speech_recognition as sr
import os
import io
import pytz

# Import our custom modules
from config import GEMINI_API_KEY
from calendar_tools import check_availability, create_calendar_event, get_day_schedule, manage_calendar_event, get_calendar_service
from logger_config import logger

# Import Streamlit UI components
from streamlit_mic_recorder import mic_recorder
from streamlit_js_eval import streamlit_js_eval

# --- Page & Model Configuration ---
st.set_page_config(
    page_title="Smart Scheduler AI",
    page_icon="🗓️",
    layout="centered"
)
st.title("🗓️ Smart Scheduler AI Agent")
st.caption("I'm a perceptive planner. I can schedule, manage, and tell you about your day!")

# --- Authentication & Initialization ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    if os.path.exists("token.json"):
        st.session_state.authenticated = True
    else:
        st.warning("You are not authenticated with Google Calendar.")
        if st.button("Authenticate with Google Calendar"):
            get_calendar_service() 
            st.session_state.authenticated = True
            st.success("Authentication successful! Please reload the page.")
            st.rerun()

with st.sidebar:
    st.header("Controls")
    if st.button("Start New Conversation"):
        # Clear all session state associated with the conversation
        for key in list(st.session_state.keys()):
            if key in ['messages', 'history']:
                del st.session_state[key]
        st.rerun()
    if st.button("Clear Google Credentials"):
        if os.path.exists("token.json"): os.remove("token.json")
        st.session_state.authenticated = False
        st.rerun()

# --- Model, Tools, and Prompt Configuration ---
genai.configure(api_key=GEMINI_API_KEY)

tools = [
    {"function_declarations": [
        {
            "name": "check_availability",
            "description": "Checks the user's calendar for available slots to schedule a new event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "Start of search range in ISO 8601 format."},
                    "end_time": {"type": "string", "description": "End of search range in ISO 8601 format."},
                    "duration_minutes": {"type": "integer", "description": "Meeting duration in minutes. This is a mandatory field."},
                    "timezone": {"type": "string", "description": "User's IANA timezone. Defaults to 'Asia/Kolkata' if not specified by the user."}
                }, "required": ["start_time", "end_time", "duration_minutes"]
            }
        },
        {
            "name": "get_day_schedule",
            "description": "Retrieves and lists all scheduled events for a specific day from the user's calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {"type": "string", "description": "The day to retrieve the schedule for. Can be 'today', 'tomorrow', or a specific date like '2025-06-10'."},
                    "timezone": {"type": "string", "description": "The user's IANA timezone. Defaults to 'Asia/Kolkata'."}
                }, "required": ["day"]
            }
        },
        {
            "name": "create_calendar_event",
            "description": "Creates a new calendar event. Only use this for brand new events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "The exact start time of the event in ISO 8601 format."},
                    "end_time": {"type": "string", "description": "The exact end time of the event in ISO 8601 format."},
                    "title": {"type": "string", "description": "The title of the meeting."},
                    "timezone": {"type": "string", "description": "The user's IANA timezone. Defaults to 'Asia/Kolkata'."}
                }, "required": ["start_time", "end_time", "title"]
            }
        },
        {
            "name": "manage_calendar_event",
            "description": "Finds, then deletes OR updates a single existing calendar event based on a search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search text to find the event, e.g., 'Meeting with HQ' or 'my 5pm meeting'."},
                    "action": {"type": "string", "description": "The operation to perform: 'delete' or 'update'."},
                    "new_start_time": {"type": "string", "description": "The new start time if updating (ISO 8601 format). Required for 'update' action."},
                    "new_end_time": {"type": "string", "description": "The new end time if updating (ISO 8601 format). Required for 'update' action."}
                }, "required": ["query", "action"]
            }
        }
    ]}
]

# --- RESTORED "BETTER" EMPATHETIC PROMPT ---
system_prompt = f"""
You are a world-class AI assistant, not just a scheduler, but a thoughtful and perceptive planner with high emotional intelligence. Your primary goal is to make scheduling a seamless and pleasant experience by adapting your tone and suggestions to the nature of the event.

**Current Context:**
- The current date and time is: {datetime.now(pytz.timezone('Asia/Kolkata')).isoformat()}
- Your default timezone is 'Asia/Kolkata' (India Standard Time). You MUST assume this is the user's timezone unless they explicitly state a different one.

**Your Core Logic: Two Modes of Operation**
1.  **Personal/Social Mode (High EQ):** Triggers: "date," "hangout," "dinner," etc. Tone: Warm, friendly, use emojis. Proactive Suggestions: Offer buffer time, reminders, encouraging notes.
2.  **Professional/Formal Mode (High IQ):** Triggers: "meeting," "interview," "sync-up," etc. Tone: Efficient, clear, professional.

**General Rules:**
- Remember the entire conversation. Follow the user's lead.
- To delete an event, you must follow a two-step process: First, use `find_calendar_event` to get the event's unique ID. Then, after confirming with the user, use `delete_calendar_event` with that ID.
- You can also retrieve the user's schedule for a given day using `get_day_schedule`.
- CRITICAL RULE: When a tool returns a success message (especially with a link), present that exact message to the user. Do not claim you cannot access information the tool just gave you.
"""

# Initialize the model and history management
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=system_prompt,
    tools=tools
)

if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Chat Interface & Logic ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "details" in message:
            with st.expander("View Tool Details"):
                st.code(message["details"], language="json")

def speak(text):
    text = text.replace("'", "\\'").replace("\n", " ")
    js_code = f"""
        const utterance = new SpeechSynthesisUtterance('{text}');
        utterance.lang = 'en-US';
        window.speechSynthesis.speak(utterance);
    """
    streamlit_js_eval(js_code=js_code)

def process_and_respond(prompt):
    # Add user message to display history and API history
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.history.append({"role": "user", "parts": [{"text": prompt}]})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Use the low-level API for robust history management
                response = model.generate_content(
                    st.session_state.history,
                    generation_config=genai.types.GenerationConfig(candidate_count=1)
                )

                while response.candidates[0].content.parts and any(part.function_call for part in response.candidates[0].content.parts):
                    # This is a tool-use turn
                    st.session_state.history.append(response.candidates[0].content)
                    function_responses = []
                    
                    for part in response.candidates[0].content.parts:
                        if not part.function_call: continue # Skip non-function call parts

                        function_call = part.function_call
                        function_name = function_call.name
                        args = {key: value for key, value in function_call.args.items()}
                        
                        tool_details = json.dumps({"tool_name": function_name, "arguments": args}, indent=2)
                        st.info(f"⚙️ Using tool: `{function_name}`")
                        with st.expander("View Tool Details"):
                            st.code(tool_details, language="json")

                        # Execute the correct tool
                        if function_name == "check_availability":
                            tool_result = check_availability(**args)
                        elif function_name == "get_day_schedule":
                            tool_result = get_day_schedule(**args)
                        elif function_name == "create_calendar_event":
                            tool_result = create_calendar_event(**args)
                        elif function_name == "manage_calendar_event":
                            tool_result = manage_calendar_event(**args)
                        else:
                            tool_result = f"Unknown tool requested: {function_name}"
                        
                        function_responses.append({
                            "function_response": {
                                "name": function_name,
                                "response": {"result": json.dumps(tool_result)}
                            }
                        })
                    
                    # Append all tool results and call the model again
                    st.session_state.history.append({"role": "model", "parts": function_responses})
                    response = model.generate_content(st.session_state.history)

                final_response = response.text
                st.markdown(final_response)
                speak(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response, "details": "Tool sequence complete."})
                st.session_state.history.append({"role": "model", "parts": [{"text": final_response}]})

            except Exception as e:
                logger.error(f"An error occurred: {e}", exc_info=True)
                error_message = f"An error occurred: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                st.session_state.history.append({"role": "model", "parts": [{"text": f"Error: {e}"}]})

# --- User Input Handling ---
if st.session_state.authenticated:
    audio_bytes = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key='recorder', use_container_width=True, format="wav")

    if audio_bytes:
        r = sr.Recognizer()
        audio_io = io.BytesIO(audio_bytes['bytes'])
        with sr.AudioFile(audio_io) as source:
            audio_data = r.record(source)
        try:
            prompt = r.recognize_google(audio_data)
            process_and_respond(prompt)
        except (sr.UnknownValueError, sr.RequestError) as e:
            st.error(f"Could not understand audio or there was a service error: {e}")

    if prompt := st.chat_input("Or type your message here..."):
        process_and_respond(prompt)