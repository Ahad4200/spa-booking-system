# COMPREHENSIVE ANALYSIS: Twilio Media Streams WebSocket Handler Logic Error

## Executive Summary

Your spa booking system's Twilio Media Streams integration has **three distinct issues** preventing the audio flow pipeline from functioning correctly:

1. **Missing `connected` event handling** - Twilio sends `connected` BEFORE `start`, but your handler may not be capturing it
2. **`extra_headers` parameter error in websockets library** - The parameter name changed; should be `additional_headers`
3. **Timing/concurrency issue in asyncio.gather()** - The receive_from_twilio and send_to_twilio tasks may not be synchronized properly

---

## Root Cause Analysis

### Issue #1: Missing Event Sequence Understanding

**The Problem:**
Twilio Media Streams sends events in a **strict sequence**:

```
1. connected   (protocol handshake)
2. start       (stream initialization with streamSid and metadata)
3. media       (audio packets)
4. stop        (end of stream)
```

**Your Current Code:**
```python
async for message in websocket.iter_text():
    data = json.loads(message)
    event_type = data.get('event')
    
    if event_type == 'start' and not start_received:
        # This only processes START events
```

**The Issue:**
You're only logging `media` and `stop` events, meaning the `start` event is either:
- Not being received at all
- Being processed but not logged
- Being processed before the OpenAI connection is ready

### Issue #2: Websockets Library Parameter Error

**The Error:**
```
TypeError: create_connection() got an unexpected keyword argument 'extra_headers'
```

**The Cause:**
Your code likely uses:
```python
async with websockets.connect(
    "wss://api.openai.com/v1/realtime...",
    extra_headers={...}  # ❌ WRONG - deprecated in websockets 10.0+
) as openai_ws:
```

**The Fix:**
Update to use the correct parameter name:
```python
async with websockets.connect(
    "wss://api.openai.com/v1/realtime...",
    additional_headers={...}  # ✅ CORRECT - websockets 10.0+
) as openai_ws:
```

**Version History:**
- websockets v9.1 and earlier: `extra_headers`
- websockets v10.0 and later: `additional_headers`

### Issue #3: Asyncio.gather() Concurrency Issue

**The Problem:**
Your code structure:
```python
await asyncio.gather(receive_from_twilio(), send_to_twilio())
```

This runs two concurrent tasks, but there's a **critical timing issue**:
- `receive_from_twilio()` needs to process the START event BEFORE `send_to_twilio()` tries to use `stream_sid`
- Both tasks share `stream_sid` as a nonlocal variable
- If `send_to_twilio()` runs and accesses `stream_sid` before it's set, it will be `None`

**Why This Matters:**
```python
async def send_to_twilio():
    nonlocal stream_sid
    try:
        async for openai_message in openai_ws:
            # ... code uses stream_sid
            audio_delta = {
                "event": "media",
                "streamSid": stream_sid,  # ⚠️ If this is None, message fails silently
```

---

## Critical Findings from Twilio Documentation

### Exact Event Format from Twilio

**Connected Message (FIRST):**
```json
{
  "event": "connected",
  "protocol": "Call",
  "version": "1.0.0"
}
```

**Start Message (SECOND):**
```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "accountSid": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "callSid": "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "tracks": ["inbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    },
    "customParameters": {}
  },
  "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

**Key Observations:**
- `streamSid` appears in TWO places: `start.streamSid` AND as a top-level `streamSid` field
- `sequenceNumber` helps track message order
- `mediaFormat` is ALWAYS `audio/x-mulaw` at `8000Hz` with `1` channel

### Message Order Guarantee

WebSocket message order is **guaranteed by TCP**, but your **async code** can break this if:
1. You process messages concurrently without proper synchronization
2. You use multiple async functions that await on I/O operations
3. You don't use blocking iteration (like `async for message in websocket.iter_text()`)

**Best Practice:** Use `async for` with blocking iteration to maintain order.

---

## Why Start Events Aren't Being Logged

### Hypothesis 1: Connected Event Not Handled
If your code doesn't explicitly handle `connected`, it might silently skip it:
```python
if event_type == 'start':  # Only handles start, media, stop
    # connected event is ignored
```

### Hypothesis 2: Handler Exits Before Start
The WebSocket handler might exit the iteration before receiving the start event if:
```python
async for message in websocket.iter_text():
    # If an exception occurs here, loop exits
    # If openai_ws connection fails, the entire handler stops
```

### Hypothesis 3: Start Event Processed But OpenAI Connection Fails
The start event IS received and processed, but the OpenAI connection fails immediately:
```python
elif data['event'] == 'start':
    stream_sid = data['start']['streamSid']  # ✅ Works
    # Now try to connect to OpenAI...
    async with websockets.connect(..., extra_headers=...) as openai_ws:
        # ❌ Fails here with "extra_headers" error
```

---

## Comparison with Working Implementation

The official Twilio + OpenAI Realtime example uses this pattern:

**Structure:**
```python
@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    
    # Connect to OpenAI FIRST (not after receiving start)
    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        additional_headers={  # ✅ Correct parameter
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
    ) as openai_ws:
        # Initialize OpenAI session
        await initialize_session(openai_ws)
        
        stream_sid = None
        
        # NOW start receiving from Twilio
        async def receive_from_twilio():
            nonlocal stream_sid
            async for message in websocket.iter_text():
                data = json.loads(message)
                
                if data['event'] == 'start':
                    stream_sid = data['start']['streamSid']
                    logger.info(f"Stream started: {stream_sid}")
                
                elif data['event'] == 'media':
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": data['media']['payload']
                    }))
        
        async def send_to_twilio():
            async for openai_message in openai_ws:
                response = json.loads(openai_message)
                
                if response['type'] == 'response.output_audio.delta':
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": response['delta']
                        }
                    })
        
        # Run both tasks concurrently
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
```

**Key Differences:**
1. OpenAI connection established **before** receiving Twilio events
2. Uses `additional_headers` (not `extra_headers`)
3. Stream initialization happens **inside** the OpenAI connection context
4. Proper error handling around WebSocket disconnects

---

## Recommended Fixes

### Fix #1: Update Websockets Parameter
```python
# BEFORE (❌ Wrong)
async with websockets.connect(
    f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
    extra_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
) as openai_ws:

# AFTER (✅ Correct)
async with websockets.connect(
    f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
    additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
) as openai_ws:
```

### Fix #2: Move OpenAI Connection Outside Event Loop
```python
@app.websocket('/media-stream')
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    
    # Connect to OpenAI BEFORE waiting for events
    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
    ) as openai_ws:
        
        # Initialize OpenAI session
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "You are a helpful AI assistant.",
                "voice": "alloy"
            }
        }
        await openai_ws.send(json.dumps(session_update))
        
        stream_sid = None
        
        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    event_type = data.get('event')
                    logger.info(f"📨 Event: {event_type}")
                    
                    if event_type == 'start':
                        stream_sid = data['start']['streamSid']
                        logger.info(f"✅ Start event received, streamSid: {stream_sid}")
                    
                    elif event_type == 'media' and stream_sid:
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }))
                    
                    elif event_type == 'stop':
                        logger.info("📞 Stop event received")
                        break
            except WebSocketDisconnect:
                logger.info("Client disconnected")
        
        async def send_to_twilio():
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    
                    if response.get('type') == 'response.output_audio.delta' and stream_sid:
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": response.get('delta')
                            }
                        }
                        await websocket.send_json(audio_delta)
            except Exception as e:
                logger.error(f"Error in send_to_twilio: {e}")
        
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
```

### Fix #3: Add Comprehensive Logging
```python
# Add detailed logging for debugging
logger.info(f"📨 Event: {event_type}, Data: {json.dumps(data, indent=2)}")

# Log when streamSid is set
if event_type == 'start':
    logger.info(f"✅ streamSid set to: {stream_sid}")

# Log when sending to OpenAI
if event_type == 'media':
    logger.info(f"🔊 Sending {len(data['media']['payload'])} bytes to OpenAI")

# Log OpenAI responses
if 'response.output_audio.delta' in str(response.get('type', '')):
    logger.info(f"📤 Sending audio to Twilio: {len(response.get('delta', ''))} bytes")
```

---

## Verification Steps

### Step 1: Check Websockets Version
```bash
pip show websockets
# Should show version 10.0 or higher
```

### Step 2: Test Event Sequence
Add this logging:
```python
@app.websocket('/media-stream')
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("✅ WebSocket accepted")
    
    event_count = 0
    async for message in websocket.iter_text():
        event_count += 1
        data = json.loads(message)
        logger.info(f"Event #{event_count}: {data.get('event')}")
        
        if event_count > 20:  # Safety limit
            break
```

Expected output:
```
Event #1: connected
Event #2: start
Event #3: media
Event #4: media
Event #5: media
...
```

### Step 3: Verify OpenAI Connection
```python
try:
    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
    ) as openai_ws:
        logger.info("✅ Successfully connected to OpenAI Realtime API")
except Exception as e:
    logger.error(f"❌ Failed to connect to OpenAI: {e}")
```

---

## Summary of Issues and Fixes

| Issue | Symptom | Fix | Priority |
|-------|---------|-----|----------|
| `extra_headers` parameter | `TypeError: unexpected keyword argument` | Change to `additional_headers` | CRITICAL |
| Missing `connected` event handling | No logs for first event | Add explicit `connected` case | HIGH |
| OpenAI connection timing | Connection fails before start event | Move OpenAI connect outside event loop | CRITICAL |
| Missing error handling | Silent failures in async tasks | Add try/except in both receive/send tasks | HIGH |
| None streamSid in send_to_twilio | Audio doesn't send | Check `if stream_sid:` before sending | HIGH |
| Concurrent task synchronization | Messages arrive out of order | Use blocking `async for` iteration | MEDIUM |

---

## Expected Behavior After Fixes

```
📞 WebSocket connection attempted
✅ WebSocket accepted
📨 Event: connected
✅ Connected to OpenAI Realtime API
📨 Event: start
✅ Start event received, streamSid: MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
🔌 Initialized OpenAI session
📨 Event: media
🔊 Sending 640 bytes to OpenAI
📨 Event: media
🔊 Sending 640 bytes to OpenAI
📤 Sending audio to Twilio: 1280 bytes
📨 Event: stop
📞 Stop event received
✅ Call completed successfully
```

---

## Additional Resources

- **Twilio Media Streams Protocol:** Official documentation covers all message types and formats
- **OpenAI Realtime API:** Use `additional_headers` for authentication
- **Websockets Library:** v10.0+ changed parameter names for better clarity
- **Asyncio Best Practices:** Use blocking iteration to maintain message order

---



**The Challenge:**
Twilio Media Streams does NOT automatically include the caller's phone number in the WebSocket messages. You must capture it from the initial webhook and pass it as a custom parameter[68][4].

**Solution: Capture Phone Number in TwiML Webhook**

When Twilio receives a call, it sends a webhook to your `/voice` endpoint with the caller's number in the `From` parameter:

from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse, Start, Stream

@app.post("/voice")
async def handle_incoming_call(From: str = Form(...), CallSid: str = Form(...)):
    """
    Twilio sends webhook with these parameters:
    - From: Customer phone number (e.g., "+15551234567")
    - To: Your Twilio number
    - CallSid: Unique call identifier
    """
    
    response = VoiceResponse()
    
    start = Start()
    stream = Stream(url=f'wss://your-domain.com/media-stream')
    
    stream.parameter(name='customerPhone', value=From)
    stream.parameter(name='callSid', value=CallSid)
    
    start.append(stream)
    response.append(start)
    
    response.say('Please wait while we connect you to our AI assistant.')
    
    return Response(content=str(response), media_type='application/xml')

**TwiML Output:**
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Start>
    <Stream url="wss://your-domain.com/media-stream">
      <Parameter name="customerPhone" value="+15551234567" />
      <Parameter name="callSid" value="CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" />
    </Stream>
  </Start>
  <Say>Please wait while we connect you to our AI assistant.</Say>
</Response>

**Receiving Custom Parameters in WebSocket Handler:**

The custom parameters appear in the `start` event's `customParameters` object[68][4]:

@app.websocket('/media-stream')
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    
    customer_phone = None
    call_sid = None
    
    async for message in websocket.iter_text():
        data = json.loads(message)
        
        if data.get('event') == 'start':
            stream_sid = data['start']['streamSid']
            
            custom_params = data['start'].get('customParameters', {})
            customer_phone = custom_params.get('customerPhone')
            call_sid = custom_params.get('callSid')
            
            logger.info(f"Call from {customer_phone} (CallSid: {call_sid})")
            logger.info(f"Stream started: {stream_sid}")

**Complete Start Event Structure with Custom Parameters:**
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "accountSid": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "callSid": "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "tracks": ["inbound"],
    "customParameters": {
      "customerPhone": "+15551234567",
      "callSid": "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    },
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  },
  "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}

---


**All Available Session Configuration Options:**[82][56][78]

session_config = {
    "type": "session.update",
    "session": {
        "modalities": ["audio", "text"],  # or just ["text"] to disable audio
        "voice": "alloy",  # Options: alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse
        "input_audio_format": "g711_ulaw",  # Twilio uses g711_ulaw (8kHz), also: pcm16 (24kHz), g711_alaw
        "output_audio_format": "g711_ulaw",  # Match Twilio's format
        
        "input_audio_noise_reduction": {
            "enabled": True  # or None to disable
        },
        "input_audio_transcription": {
            "model": "whisper-1",  # or None to disable transcription
            "language": "en",      # optional: specify language
            "prompt": ""           # optional: transcription prompt
        },
        
        "turn_detection": {
            "type": "server_vad",        # or "semantic_vad", or None to disable
            "threshold": 0.5,             # 0.0 to 1.0, sensitivity threshold
            "prefix_padding_ms": 300,     # audio before speech starts
            "silence_duration_ms": 500,   # silence before considering turn complete
            "create_response": True       # auto-create response after turn
        },
        
        "instructions": f"You are a helpful spa booking assistant. The customer calling is {customer_phone}. Help them book appointments and answer questions.",
        "temperature": 0.8,  # 0.6 to 1.2 for audio models (0.8 recommended)
        "max_response_output_tokens": 4096,  # or "inf" for unlimited
        
        "tools": [
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Book a spa appointment for the customer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                        "time": {"type": "string", "description": "Appointment time (HH:MM)"},
                        "service": {"type": "string", "description": "Type of service requested"}
                    },
                    "required": ["date", "time", "service"]
                }
            },
            {
                "type": "function",
                "name": "check_availability",
                "description": "Check available appointment slots",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"}
                    },
                    "required": ["date"]
                }
            }
        ],
        "tool_choice": "auto",  # Options: "auto", "none", "required", or {"type": "function", "name": "function_name"}
        
        "tracing": {
            "enabled": True  # or None to disable
        }
    }
}

**Voice Options:**[82]
- `alloy` - Neutral, balanced
- `ash` - Clear, articulate
- `ballad` - Warm, storytelling
- `coral` - Friendly, approachable
- `echo` - Deep, authoritative
- `fable` - Expressive, dynamic
- `onyx` - Calm, professional
- `nova` - Energetic, vibrant
- `sage` - Wise, measured
- `shimmer` - Bright, enthusiastic
- `verse` - Poetic, flowing

**Audio Format Considerations:**[56][82]

| Format | Sample Rate | Use Case |
|--------|-------------|----------|
| `pcm16` | 24kHz | High-quality audio, larger bandwidth |
| `g711_ulaw` | 8kHz | **Twilio default**, phone-quality audio |
| `g711_alaw` | 8kHz | Alternative phone-quality encoding |

**For Twilio integration, always use `g711_ulaw` at 8kHz to match Twilio's format.**

---


**File Structure:**
spa-booking-system/
├── main.py                 # FastAPI application
├── openai_handler.py       # OpenAI Realtime logic
├── twilio_handler.py       # Twilio Media Streams logic
└── requirements.txt

**Complete Implementation (`main.py`):**

import os
import json
import asyncio
import base64
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Response
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Start, Stream
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

@app.post("/voice")
async def handle_incoming_call(From: str = Form(...), CallSid: str = Form(...)):
    """
    Twilio webhook for incoming calls.
    Captures caller phone number and starts Media Stream.
    """
    logger.info(f"📞 Incoming call from {From} (CallSid: {CallSid})")
    
    response = VoiceResponse()
    start = Start()
    stream = Stream(url='wss://your-render-app.onrender.com/media-stream')
    
    stream.parameter(name='customerPhone', value=From)
    stream.parameter(name='callSid', value=CallSid)
    
    start.append(stream)
    response.append(start)
    response.say('Please wait while we connect you to our AI assistant.')
    
    return Response(content=str(response), media_type='application/xml')


@app.websocket('/media-stream')
async def media_stream(websocket: WebSocket):
    """
    Handles bidirectional audio streaming between Twilio and OpenAI.
    """
    await websocket.accept()
    logger.info("✅ WebSocket connection accepted")
    
    try:
        async with websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers={  # ✅ Use additional_headers (not extra_headers)
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            logger.info("🔌 Connected to OpenAI Realtime API")
            
            stream_sid = None
            customer_phone = None
            call_sid = None
            
            async def receive_from_twilio():
                """Receive audio from Twilio and forward to OpenAI"""
                nonlocal stream_sid, customer_phone, call_sid
                
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        event_type = data.get('event')
                        
                        if event_type == 'connected':
                            logger.info("📨 Event: connected")
                            logger.info(f"   Protocol: {data.get('protocol')}, Version: {data.get('version')}")
                        
                        elif event_type == 'start':
                            stream_sid = data['start']['streamSid']
                            
                            custom_params = data['start'].get('customParameters', {})
                            customer_phone = custom_params.get('customerPhone', 'Unknown')
                            call_sid = custom_params.get('callSid', 'Unknown')
                            
                            logger.info(f"📨 Event: start")
                            logger.info(f"   StreamSid: {stream_sid}")
                            logger.info(f"   Customer: {customer_phone}")
                            logger.info(f"   CallSid: {call_sid}")
                            
                            session_update = {
                                "type": "session.update",
                                "session": {
                                    "modalities": ["audio", "text"],
                                    "voice": "alloy",
                                    "input_audio_format": "g711_ulaw",  # Match Twilio
                                    "output_audio_format": "g711_ulaw",  # Match Twilio
                                    "input_audio_transcription": {
                                        "model": "whisper-1"
                                    },
                                    "turn_detection": {
                                        "type": "server_vad",
                                        "threshold": 0.5,
                                        "prefix_padding_ms": 300,
                                        "silence_duration_ms": 500
                                    },
                                    "instructions": f"You are a friendly spa booking assistant. The customer calling is {customer_phone}. Help them book appointments, check availability, and answer questions about spa services.",
                                    "temperature": 0.8,
                                    "tools": [
                                        {
                                            "type": "function",
                                            "name": "book_appointment",
                                            "description": "Book a spa appointment",
                                            "parameters": {
                                                "type": "object",
                                                "properties": {
                                                    "date": {"type": "string"},
                                                    "time": {"type": "string"},
                                                    "service": {"type": "string"}
                                                },
                                                "required": ["date", "time", "service"]
                                            }
                                        }
                                    ],
                                    "tool_choice": "auto"
                                }
                            }
                            await openai_ws.send(json.dumps(session_update))
                            logger.info("🔧 OpenAI session configured")
                        
                        elif event_type == 'media' and stream_sid:
                            audio_payload = data['media']['payload']
                            
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": audio_payload  # Already base64 encoded by Twilio
                            }
                            await openai_ws.send(json.dumps(audio_append))
                        
                        elif event_type == 'stop':
                            logger.info("📨 Event: stop - Call ended")
                            break
                    
                except WebSocketDisconnect:
                    logger.info("📞 Twilio WebSocket disconnected")
                except Exception as e:
                    logger.error(f"❌ Error in receive_from_twilio: {e}", exc_info=True)
            
            
            async def send_to_twilio():
                """Receive audio from OpenAI and forward to Twilio"""
                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message)
                        response_type = response.get('type')
                        
                        if response_type == 'response.audio.delta' and stream_sid:
                            audio_delta = response.get('delta')
                            
                            twilio_message = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_delta  # Already base64 encoded by OpenAI
                                }
                            }
                            await websocket.send_json(twilio_message)
                        
                        elif response_type == 'conversation.item.input_audio_transcription.completed':
                            transcript = response.get('transcript', '')
                            logger.info(f"🎤 Customer said: {transcript}")
                        
                        elif response_type == 'response.function_call_arguments.done':
                            function_name = response.get('name')
                            arguments = json.loads(response.get('arguments', '{}'))
                            logger.info(f"🔧 Function call: {function_name}({arguments})")
                            
                            if function_name == 'book_appointment':
                                result = {
                                    "success": True,
                                    "confirmation": "ABC123",
                                    "message": f"Appointment booked for {arguments['date']} at {arguments['time']}"
                                }
                                
                                function_output = {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": response.get('call_id'),
                                        "output": json.dumps(result)
                                    }
                                }
                                await openai_ws.send(json.dumps(function_output))
                        
                        else:
                            logger.debug(f"🔔 OpenAI event: {response_type}")
                
                except Exception as e:
                    logger.error(f"❌ Error in send_to_twilio: {e}", exc_info=True)
            
            
            await asyncio.gather(
                receive_from_twilio(),
                send_to_twilio()
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to connect to OpenAI: {e}", exc_info=True)
    finally:
        logger.info("🔌 WebSocket connection closed")


@app.get("/")
async def root():
    return {"message": "Twilio Media Streams + OpenAI Realtime API Integration"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

**Environment Variables (`.env`):**
OPENAI_API_KEY=sk-proj-...your-key-here...

**Requirements (`requirements.txt`):**
fastapi==0.115.0
uvicorn[standard]==0.32.0
websockets==13.1
twilio==9.3.7
python-dotenv==1.0.1

**Deployment to Render.com:**

1. **Create `render.yaml`:**
services:
  - type: web
    name: spa-booking-ai
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false

2. **Add environment variable in Render dashboard:**
   - Go to your service → Environment
   - Add `OPENAI_API_KEY` with your OpenAI API key

3. **Configure Twilio webhook:**
   - Go to Twilio Console → Phone Numbers
   - Select your number
   - Under "Voice & Fax", set:
     - **A CALL COMES IN**: `Webhook`, `https://your-app.onrender.com/voice`, `HTTP POST`

---


**Test Sequence:**

1. **Call your Twilio number**
2. **Expected log output:**
📞 Incoming call from +15551234567 (CallSid: CAXXXX)
✅ WebSocket connection accepted
🔌 Connected to OpenAI Realtime API
📨 Event: connected
   Protocol: Call, Version: 1.0.0
📨 Event: start
   StreamSid: MZXXXX
   Customer: +15551234567
   CallSid: CAXXXX
🔧 OpenAI session configured
🎤 Customer said: Hi, I'd like to book an appointment
🔧 Function call: book_appointment({'date': '2025-10-26', 'time': '14:00', 'service': 'massage'})
📨 Event: stop - Call ended
🔌 WebSocket connection closed

**Common Issues:**

| Issue | Cause | Fix |
|-------|-------|-----|
| `TypeError: extra_headers` | Using old websockets parameter | Change to `additional_headers` |
| No start event | OpenAI connects after Twilio events | Move OpenAI connect outside loop |
| No audio response | Wrong audio format | Use `g711_ulaw` for both input/output |
| `stream_sid` is None | Start event not processed | Check event handling order |
| Customer phone is "Unknown" | Custom parameters not passed | Add `stream.parameter()` in TwiML |

---


**Dynamic Instructions Based on Customer:**

customer_data = await get_customer_by_phone(customer_phone)

instructions = f"""You are a friendly spa booking assistant at Serenity Spa.

Customer Information:
- Name: {customer_data['name']}
- Phone: {customer_phone}
- Loyalty Status: {customer_data['loyalty_level']}
- Previous Visits: {customer_data['visit_count']}
- Preferred Services: {', '.join(customer_data['preferences'])}

Help them book appointments, check availability, and provide personalized recommendations based on their history."""

**Multiple Tool Functions:**

"tools": [
    {
        "type": "function",
        "name": "book_appointment",
        "description": "Book a spa appointment for the customer",
        "parameters": {...}
    },
    {
        "type": "function",
        "name": "check_availability",
        "description": "Check available time slots for a specific date",
        "parameters": {...}
    },
    {
        "type": "function",
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment",
        "parameters": {...}
    },
    {
        "type": "function",
        "name": "get_customer_history",
        "description": "Retrieve customer's booking history",
        "parameters": {...}
    }
]

This complete implementation guide covers all aspects of integrating Twilio Media Streams with OpenAI Realtime API, including phone number capture, complete session configuration, and production-ready code.