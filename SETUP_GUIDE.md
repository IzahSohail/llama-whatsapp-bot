# Quick Setup Guide

## 1. Start ngrok
```bash
ngrok http 5000
```

## 2. Start the FastAPI server
```bash
source venv/bin/activate
python whatsapp_webhook.py
```

## 3. Configure Twilio Webhook
1. Go to Twilio Console → WhatsApp → Sandbox
2. Set webhook URL to: `https://your-ngrok-url.ngrok.io/webhook`
3. Set HTTP method to: `POST`

## 4. Test the bot
Send a message to your Twilio WhatsApp number:
- "Hi, I'm looking for properties under 1M AED"
- "Send me an image of Skyscape Avenue"
- "Can I get the brochure for Sobha One?"

## What the bot can do:
✅ **Property Search**: Find properties by budget, location, bedrooms
✅ **Media Support**: Send images, brochures, floor plans
✅ **Conversational**: Remembers your preferences
✅ **FAQ Answers**: Company and process questions

## Files:
- `siraa_agent.py` - The AI agent with all tools
- `whatsapp_webhook.py` - FastAPI webhook for Twilio
- `build_vector_store.py` - Builds property database
- `build_faq_vector_store.py` - Builds FAQ database

## Troubleshooting:
- If vector stores are corrupted: `rm -rf property_vector_store faq_vector_store` then rebuild
- Check console logs for incoming messages and responses
- Make sure ngrok URL is accessible and updated in Twilio 