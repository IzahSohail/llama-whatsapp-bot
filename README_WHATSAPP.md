# Siraa WhatsApp Bot

A WhatsApp chatbot for real estate assistance using Twilio, FastAPI, and LlamaIndex.

## Features

- 🤖 **Intelligent Property Search**: Find properties based on budget, location, and preferences
- 📸 **Media Support**: Send property images, brochures, and floor plans
- 💬 **Conversational AI**: Natural language processing with memory
- 🏠 **Property Recommendations**: Smart filtering by price, bedrooms, and amenities
- 📱 **WhatsApp Integration**: Full WhatsApp Business API integration

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the root directory:

```bash
# Google Gemini API
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=your_twilio_whatsapp_number_here

# Optional: Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Build Vector Stores

```bash
# Build property vector store
python build_vector_store.py

# Build FAQ vector store
python build_faq_vector_store.py
```

### 4. Run the WhatsApp Bot

```bash
python whatsapp_webhook.py
```

The server will start on `http://localhost:8000`

### 5. Configure Twilio Webhook

1. Go to your Twilio Console
2. Navigate to WhatsApp > Sandbox or your WhatsApp Business API
3. Set the webhook URL to: `https://your-domain.com/webhook`
4. Set the HTTP method to POST

## API Endpoints

### Main Webhook
- **POST** `/webhook` - Twilio WhatsApp webhook endpoint

### Utility Endpoints
- **GET** `/health` - Health check
- **GET** `/properties` - Get all available property names
- **DELETE** `/session/{phone_number}` - Clear user session

## Usage Examples

### Property Search
```
User: "I'm looking for properties under 1M AED in Dubai"
Bot: [Sends property recommendations with details]
```

### Media Requests
```
User: "Send me an image of Skyscape Avenue"
Bot: [Sends property image]

User: "Can I get the brochure for Sobha One?"
Bot: [Sends PDF brochure]

User: "Show me the floor plan of Design Quarter"
Bot: [Sends floor plan PDF]
```

### FAQ Questions
```
User: "What is Siraa's value proposition?"
Bot: [Sends FAQ answer]
```

## Media Support

The bot can send the following media types:

- **Images**: Property photos from `compressed_hero_image_link`
- **Brochures**: PDF brochures from `brochure` field
- **Floor Plans**: PDF floor plans from `floor_plans` field

## Session Management

- Each WhatsApp number gets a unique session
- Conversations maintain context and preferences
- Sessions can be cleared via API endpoint

## Error Handling

- Graceful handling of missing media files
- Fallback responses for unavailable properties
- Error logging for debugging

## Development

### Testing Locally

1. Use ngrok to expose your local server:
```bash
ngrok http 8000
```

2. Use the ngrok URL as your Twilio webhook

### Logs

Check console output for:
- Incoming messages
- Agent responses
- Media requests
- Error messages

## Troubleshooting

### Common Issues

1. **Vector Store Errors**: Rebuild vector stores if corrupted
2. **Twilio Authentication**: Verify account SID and auth token
3. **Media Not Sending**: Check if URLs are publicly accessible
4. **Agent Not Responding**: Verify Google API key is valid

### Debug Mode

Enable verbose logging in `siraa_agent.py`:
```python
llm = Gemini(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.4,
    verbose=True  # Enable debug output
)
```

## Security Notes

- Keep your `.env` file secure and never commit it
- Use HTTPS in production
- Validate all incoming webhook data
- Rate limit if needed for production use

## Production Deployment

1. Deploy to cloud platform (AWS, GCP, Azure)
2. Set up SSL certificate
3. Configure environment variables
4. Set up monitoring and logging
5. Test thoroughly before going live 