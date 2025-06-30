import os
import re
import json
from dotenv import load_dotenv
from typing import Dict
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.agent import ReActAgent
from llama_index.core.tools.function_tool import FunctionTool
from llama_index.core.tools import QueryEngineTool
from llama_index.core.memory import ChatMemoryBuffer
from build_vector_store import PropertyVectorStore
from build_faq_vector_store import FAQVectorStore

# Load environment variables
load_dotenv()

# Initialize Gemini LLM
llm = GoogleGenAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.4,
    verbose=True  # SHOW INTERNAL THOUGHTS
)

# Load vector stores
property_store = PropertyVectorStore(persist_directory="property_vector_store")
faq_store = FAQVectorStore(
    faq_document_paths=[
        "Siraa_overview.txt",
        "real_estate_101_content.txt"
    ],
    persist_directory="faq_vector_store"
)

def extract_budget(query: str) -> int | None:
    """
    Extract numeric budget from user query.
    Supports formats like '1 million', '1m', '1.5m', '500k', '750000', etc.
    """
    query = query.lower().replace(",", "")
    
    # Match formats like "1 million", "1m", "1.5m", "500k", "1000000"
    patterns = [
        (r"(\d+(\.\d+)?)\s*m(illion)?", 1_000_000),
        (r"(\d+(\.\d+)?)\s*k", 1_000),
        (r"\b(\d{6,})\b", 1)  # raw numbers like 750000
    ]
    
    for pattern, multiplier in patterns:
        match = re.search(pattern, query)
        if match:
            number = float(match.group(1))
            return int(number * multiplier)
    
    return None

def search_properties(query: str) -> str:
    """Search for properties based on the query."""
    try:
        budget = extract_budget(query)
        initial_results = property_store.search(query, n_results=50)
        
        if not initial_results:
            return "No properties found matching your criteria."
        
        if budget:
            filtered_results = []
            for result in initial_results:
                try:
                    price_str = result.get("metadata", {}).get("price", "0")
                    price_numeric = float(''.join(filter(str.isdigit, str(price_str))))
                    if price_numeric <= budget:
                        filtered_results.append(result)
                except (ValueError, TypeError):
                    # Still include unparseable ones
                    filtered_results.append(result)
            
            results = filtered_results[:5]
            if not results:
                return f"I couldn't find properties within your budget of {budget:,} AED. Here are some slightly higher-priced options:\n\n" + format_properties(initial_results[:3], query)
        else:
            results = initial_results[:5]
        
        return format_properties(results, query)

    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return "Something went wrong during the property search."


def format_properties(results, query: str = ""):
    """
    Helper function to format property results into a user-friendly list.
    """
    if not results:
        return "Unfortunately, I couldn't find any properties matching your exact criteria right now."

    response_lines = ["🏠 Here are some properties that match your search:\n"]
    query_lower = query.lower()
    
    show_brochures = "brochure" in query_lower or "pdf" in query_lower
    show_floor_plans = "floor" in query_lower or "plan" in query_lower or "layout" in query_lower
    
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        lines = []
        lines.append(f"{i}. **{metadata.get('property_name', 'N/A')}**")
        lines.append(f"   📍 Location: {metadata.get('location', 'N/A')}")
        lines.append(f"   🏘️ Type: {metadata.get('property_type', 'N/A')}")
        lines.append(f"   🛏️ Bedrooms: {metadata.get('bedrooms', 'N/A')}")
        lines.append(f"   💰 Price: {metadata.get('price', 'N/A')}")
        
        if metadata.get('amenities'):
            lines.append(f"   🎯 Amenities: {metadata.get('amenities', 'N/A')}")
        
        if show_brochures:
            lines.append(f"   📄 Brochure: {metadata.get('brochure', 'Not available')}")
            
        if show_floor_plans:
            lines.append(f"   🏗️ Floor Plans: {metadata.get('floor_plans', 'Not available')}")
        
        response_lines.append("\n".join(lines))

    response = "\n\n".join(response_lines)
    
    # Add a hint for the user if links weren't requested and there are results
    if not show_brochures and not show_floor_plans and results:
         response += "\n\nℹ️ You can ask for 'brochures' or 'floor plans' for details."

    return response

# Create FAQ search function tool
def search_faqs(query: str) -> str:
    """Search for FAQ answers based on the query."""
    try:
        results = faq_store.search(query, n_results=3)
        
        if not results:
            return "I couldn't find specific information about that. Please try rephrasing your question or ask about our properties."
        
        response = "📚 Here's what I found:\n\n"
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            response += f"{i}. {content}\n\n"
        
        return response
    except Exception as e:
        print(f"FAQ search error: {e}")
        return "I'm having trouble searching our knowledge base right now. Please try again in a moment."

# Create tool wrappers
property_tool = FunctionTool.from_defaults(
    fn=search_properties,
    name="PropertySearch",
    description="Search for real estate properties. Returns a formatted string of results. Your job is to output this string to the user exactly as it is given to you."
)

faq_tool = FunctionTool.from_defaults(
    fn=search_faqs,
    name="FAQSearch",
    description="Answer general questions about Siraa or the buying process."
)

def find_brochure_by_property_name(property_name: str):
    results = property_store.search("", n_results=1000)
    for result in results:
        meta = result.get("metadata", {})
        if meta.get("property_name", "").strip().lower() == property_name.strip().lower():
            return meta.get("brochure", "No brochure found.")
    return "Brochure not found."

def find_floor_plan_by_property_name(property_name: str):
    results = property_store.search("", n_results=1000)
    for result in results:
        meta = result.get("metadata", {})
        if meta.get("property_name", "").strip().lower() == property_name.strip().lower():
            return meta.get("floor_plans", "No floor plan found.")
    return "Floor plan not found."

brochure_tool = FunctionTool.from_defaults(
    fn=find_brochure_by_property_name,
    name="FindBrochure",
    description="Get brochure PDF URL for a specific property."
)

floorplan_tool = FunctionTool.from_defaults(
    fn=find_floor_plan_by_property_name,
    name="FindFloorPlan",
    description="Get property floor plan PDF URL for a specific property."
)

# Add these functions after the existing tool functions

def find_property_image_by_name(property_name: str):
    """Find property image URL by property name."""
    try:
        results = property_store.search("", n_results=1000)
        for result in results:
            meta = result.get("metadata", {})
            if meta.get("property_name", "").strip().lower() == property_name.strip().lower():
                image_url = meta.get("compressed_hero_image_link", "")
                if image_url and image_url != "Not available":
                    return image_url
        return "Image not found for this property."
    except Exception as e:
        print(f"Image search error: {e}")
        return "Unable to find image at the moment."

def find_property_brochure_by_name(property_name: str):
    """Find property brochure URL by property name."""
    try:
        results = property_store.search("", n_results=1000)
        for result in results:
            meta = result.get("metadata", {})
            if meta.get("property_name", "").strip().lower() == property_name.strip().lower():
                brochure_url = meta.get("brochure", "")
                if brochure_url and brochure_url != "Not available":
                    return brochure_url
        return "Brochure not found for this property."
    except Exception as e:
        print(f"Brochure search error: {e}")
        return "Unable to find brochure at the moment."

def find_property_floor_plan_by_name(property_name: str):
    """Find property floor plan URL by property name."""
    try:
        results = property_store.search("", n_results=1000)
        for result in results:
            meta = result.get("metadata", {})
            if meta.get("property_name", "").strip().lower() == property_name.strip().lower():
                floor_plan_url = meta.get("floor_plans", "")
                if floor_plan_url and floor_plan_url != "Not available":
                    return floor_plan_url
        return "Floor plan not found for this property."
    except Exception as e:
        print(f"Floor plan search error: {e}")
        return "Unable to find floor plan at the moment."

def get_all_property_names():
    """Get all available property names for reference."""
    try:
        results = property_store.search("", n_results=1000)
        property_names = []
        for result in results:
            meta = result.get("metadata", {})
            property_name = meta.get("property_name", "")
            if property_name:
                property_names.append(property_name)
        return property_names
    except Exception as e:
        print(f"Property names search error: {e}")
        return []

# Create media tool wrappers
image_tool = FunctionTool.from_defaults(
    fn=find_property_image_by_name,
    name="FindPropertyImage",
    description="Get property image URL for a specific property by name."
)

brochure_tool = FunctionTool.from_defaults(
    fn=find_property_brochure_by_name,
    name="FindPropertyBrochure",
    description="Get property brochure PDF URL for a specific property by name."
)

floorplan_tool = FunctionTool.from_defaults(
    fn=find_property_floor_plan_by_name,
    name="FindPropertyFloorPlan",
    description="Get property floor plan PDF URL for a specific property by name."
)

# System prompt
SYSTEM_PROMPT = """You are Siraa, a helpful real estate assistant.

RULES:
- For any questions about properties, you MUST use the `PropertySearch` tool. Output the result from this tool directly to the user without any modification or summary.
- For questions about images, brochures, or floor plans, you MUST use the correct tool (`FindPropertyImage`, `FindPropertyBrochure`, `FindPropertyFloorPlan`).
- If one of those tools returns a URL, your final answer MUST be only the URL.
- For all other general questions, use the `FAQSearch` tool.
"""

# Global: hold reference to memory/agent
session_memory_map = {}

def create_agent_for_user(session_id: str) -> ReActAgent:
    memory = ChatMemoryBuffer.from_defaults()

    agent = ReActAgent.from_tools(
        tools=[property_tool, faq_tool, image_tool, brochure_tool, floorplan_tool],
        llm=llm,
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
        verbose=True
    )

    session_memory_map[session_id] = {
        "agent": agent,
        "preferences": {},
        "memory": memory
    }

    return agent

def extract_preferences_with_llm(message: str, current_preferences: Dict) -> Dict:
    prompt = f"""Analyze this message and extract real estate preferences.

Current preferences: {current_preferences}
Message: {message}

Return a JSON with these fields ONLY if they are mentioned:
{{
  "location": "e.g. Dubai Marina",
  "property_type": "apartment/villa/etc.",
  "bedrooms": "number or range",
  "budget": "number or range",
  "amenities": ["list", "of", "amenities"]
}}
If no new info, return {{}}.
"""
    try:
        response = llm.complete(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"[PREFERENCE EXTRACTION ERROR] {e}")
        return {}

def determine_query_context(message: str) -> str:
    prompt = f"""Classify this message:
- "property" if it's about finding/recommending properties
- "general" if it's about the company or buying process

Message: {message}
Answer with only: property or general."""
    try:
        response = llm.complete(prompt)
        return response.text.strip().lower()
    except:
        return "property"

def get_session_data(session_id: str):
    return session_memory_map.get(session_id)

def reset_session(session_id: str):
    if session_id in session_memory_map:
        del session_memory_map[session_id]

def main():
    """
    Terminal mode: test Siraa agent in your console.
    """
    print("👋 Welcome to Siraa! Your Real Estate Assistant.")
    print("Type 'exit' to quit the chat.")
    print("-" * 50)

    session_id = "test_user"
    agent = create_agent_for_user(session_id)
    session = get_session_data(session_id)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "exit":
                print("Siraa: 👋 Goodbye!")
                break

            # Extract preferences from the message
            new_prefs = extract_preferences_with_llm(user_input, session["preferences"])
            session["preferences"].update(new_prefs)

            # Determine context (property vs general)
            context = determine_query_context(user_input)
            if context == "property":
                user_prompt = f"Current preferences: {session['preferences']}\n\nUser message: {user_input}"
            else:
                user_prompt = user_input

            # Run agent using chat method
            response = agent.chat(user_prompt)
            print(f"Siraa: {response.response}")

        except KeyboardInterrupt:
            print("\nSiraa: 👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


if __name__ == "__main__":
    main()
