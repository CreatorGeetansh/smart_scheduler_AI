# Smart Scheduler AI Agent

This project is a sophisticated, voice-enabled AI agent built for the NextDimension take-home assignment. It functions as a perceptive personal assistant that can understand user needs, check a Google Calendar for availability, and manage events through a multi-turn, stateful conversation. The agent is deployed as an interactive web application using Streamlit.

---

## 🚀 Features

*   **🗣️ Hybrid Conversational UI:** Interact via both voice commands and text input. The agent responds with synthesized speech and text.
*   **🗓️ Full Calendar Management:**
    *   **Create Events:** Schedule new meetings and appointments.
    *   **Read Schedule:** Ask "What's my schedule for tomorrow?" to get a summary of your day.
    *   **Delete Events:** Directly ask to delete events (e.g., "delete my 5pm meeting").
*   **🧠 High Emotional Intelligence:** The agent detects the context of the event (e.g., a professional meeting vs. a personal date) and adapts its tone and suggestions accordingly.
*   **💡 Proactive Suggestions:** For personal events, the agent can suggest adding buffer time before the event or setting reminders.
*   **🔄 Multi-Turn Context:** The agent remembers the entire conversation, allowing users to change topics, correct themselves, and have a natural, flowing dialogue.
*   **🛠️ Transparent Tool Use:** The UI includes a "View Tool Details" expander to show exactly which functions the AI is calling and with what arguments, providing insight into its reasoning process.

---

## 🏗️ Architecture & Orchestration

The agent's architecture is designed to separate its "brain" from its "hands," allowing for a modular and robust system.

```mermaid
flowchart TD
    %% User Interface Layer
    subgraph UI["User Interface (Streamlit)"]
        A["User Input: Voice/Text"] --> B["app.py Orchestrator"]
        F["Agent Response: Text/Speech"] --> G["End Turn"]
    end

    %% Agent Core Layer
    subgraph CORE["Agent Core"]
        B --> C{"Reasoning Engine:\nGemini 1.5 Pro"}
        C -- "Wants to Talk" --> E["Generate Text Response"]
        C -- "Wants to Act" --> D["Generate Tool Call"]
        D --> H{"Tool Executor"}
        I["Tool Result"] --> C
        E --> F
    end

    %% Tools Layer
    subgraph TOOLS["Tools (calendar_tools.py)"]
        H -- "check_availability()" --> J{{"Google Calendar API"}}
        H -- "create_calendar_event()" --> J
        H -- "get_day_schedule()" --> J
        H -- "find_calendar_event()" --> J
        H -- "delete_calendar_event()" --> J
        J --> I
    end
