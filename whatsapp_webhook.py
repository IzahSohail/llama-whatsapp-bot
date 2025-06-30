import os
import json
import re
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import requests
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import asyncio
from dotenv import load_dotenv

# Import our Siraa agent
from siraa_agent import create_agent_for_user, get_session_data, reset_session, get_all_property_names

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Siraa WhatsApp Bot", version="1.0.0")

# Global session management
session_memory_map = {}

def extract_url_from_text(text: str) -> Optional[str]:
    """Finds the first HTTP or HTTPS URL in a string."""
    # This regex is simple and effective for this use case.
    match = re.search(r'https?://[^\s]+', text)
    if match:
        return match.group(0)
    return None

def split_message(text: str, limit: int = 1600) -> List[str]:
    """
    Splits a long message into multiple chunks under the character limit,
    preferring to split at newlines.
    """
    if len(text) <= limit:
        return [text]

    chunks = []
    current_chunk = ""
    lines = text.split('\n')

    for line in lines:
        # If adding the next line (plus a newline character) exceeds the limit
        if len(current_chunk) + len(line) + 1 > limit:
            # If the current chunk is not empty, add it to the list
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    
    # Add the last remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Final check: if any single line was over the limit, we need to split it by force
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > limit:
            for i in range(0, len(chunk), limit):
                final_chunks.append(chunk[i:i+limit])
        else:
            final_chunks.append(chunk)

    return final_chunks

def find_best_property_match(property_name: str, available_properties: List[str]) -> Optional[str]:
    """Find the best matching property name."""
    property_name_lower = property_name.lower().strip()
    
    # First try exact match
    for prop in available_properties:
        if prop.lower() == property_name_lower:
            return prop
    
    # Then try contains match
    for prop in available_properties:
        if property_name_lower in prop.lower() or prop.lower() in property_name_lower:
            return prop
    
    # Then try word-based matching
    property_words = set(property_name_lower.split())
    for prop in available_properties:
        prop_words = set(prop.lower().split())
        if property_words & prop_words:  # If there's any word overlap
            return prop
    
    return None

def get_session_id(phone_number: str) -> str:
    """Get or create session ID for a phone number."""
    return f"whatsapp_{phone_number}"

@app.post("/whatsapp_webhook")
async def webhook(request: Request):
    """Main webhook endpoint for Twilio WhatsApp messages."""
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        
        # Extract message details
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        message_body = form_data.get("Body", "").strip()
        
        print(f"Received message from {from_number}: {message_body}")
        
        # --- UNIFIED AGENT LOGIC ---
        # Get or create agent for this user
        session_id = get_session_id(from_number)
        if session_id not in session_memory_map:
            agent = create_agent_for_user(session_id)
            session_memory_map[session_id] = {"agent": agent}
        else:
            agent = session_memory_map[session_id]["agent"]
        
        # Get agent response for every message
        response = agent.chat(message_body)
        response_text = response.response.strip()
        
        # --- CREATE TWIML RESPONSE ---
        twiml = MessagingResponse()
        
        # Check if the agent's response contains a URL
        media_url = extract_url_from_text(response_text)
        
        if media_url:
            # Send a message with only the media, no body text.
            msg = twiml.message()
            msg.media(media_url)
            print(f"Response: Media URL - {media_url}")
        else:
            # It's a regular text response, split if necessary
            response_chunks = split_message(response_text)
            for chunk in response_chunks:
                twiml.message(chunk)
            print(f"Response: Text - {response_text}")
        
        return Response(content=str(twiml), media_type="application/xml")
            
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Return a simple error response
        twiml = MessagingResponse()
        twiml.message("Sorry, I'm having trouble processing your request. Please try again.")
        return Response(content=str(twiml), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
