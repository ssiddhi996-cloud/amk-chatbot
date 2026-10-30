import json
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Lead Database repository (Simulating CRM storage)
LEAD_DATABASE = []


def check_flexible_faq(message, step):
  """Context-aware intent matcher.

  If user is mid-flow (step > 0), it only triggers if they are explicitly
  asking a question (using question words or '?'). If they are just describing
  their requirements (even if they mention words like 'hotel' or 'location'),
  it treats it as data input!
  """
  msg = message.lower()
  is_explicit_question = "?" in msg or any(
      w in msg for w in ["what", "where", "how", "can you", "tell me", "do you"]
  )

  # If they are mid-flow and NOT asking an explicit question, skip FAQ and treat as data!
  if step > 0 and not is_explicit_question:
    return None

  # Flexible FAQ / Intent Matching
  if any(
      w in msg
      for w in [
          "cities",
          "city",
          "location",
          "where",
          "place",
          "areas",
          "office",
      ]
  ):
    return (
        "We provide our luxury hospitality, wedding, and event services"
        " across premier destinations including Jaipur, Udaipur, Jodhpur, and"
        " New Delhi."
    )

  elif any(
      w in msg for w in ["services", "service", "offer", "provide", "what do you"]
  ):
    return (
        "We offer an exclusive suite of luxury hospitality services, including"
        " royal destination wedding planning, corporate event management,"
        " bespoke multi-cuisine catering, and customized AMK Travels holiday"
        " packages."
    )

  elif any(w in msg for w in ["venue", "palace", "resort", "lawn", "hotel"]):
    return (
        "We partner with luxury heritage palaces, five-star resorts, and"
        " scenic lawns across all our operating locations."
    )

  elif any(w in msg for w in ["catering", "food", "menu", "dinner", "lunch"]):
    return (
        "Yes! Our culinary team offers bespoke multi-cuisine menus, featuring"
        " authentic royal Rajasthani thalis, pan-Asian, and continental"
        " cuisines."
    )

  elif any(w in msg for w in ["price", "cost", "budget", "charge", "rate"]):
    return (
        "Our packages are fully customized based on your guest count, venue"
        " selection, and specific requirements. Our senior concierge will"
        " provide a tailored quote!"
    )

  return None


def qualify_and_route(session_data):
  """Evaluates lead data and routes to correct internal department."""
  intent = session_data.get("intent", "").lower()
  details = session_data.get("details", {})

  has_budget = bool(details.get("budget"))
  has_timeline = bool(details.get("date") or details.get("travel_dates"))

  is_qualified = False
  department = "General Support"

  if "wedding" in intent or "event" in intent or "party" in intent:
    department = "Weddings & Events"
    if has_budget and has_timeline:
      is_qualified = True
  elif "travel" in intent or "trip" in intent or "package" in intent:
    department = "AMK Travels"
    if has_budget and has_timeline:
      is_qualified = True
  else:
    department = "Other Services"
    if has_budget:
      is_qualified = True

  return is_qualified, department


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
  data = request.json or {}
  message = data.get("message", "").strip()
  session = data.get(
      "session", {"step": 0, "intent": "", "details": {}, "contact": {}}
  )

  step = session.get("step", 0)
  intent = session.get("intent", "")
  details = session.get("details", {})
  contact = session.get("contact", {})

  response_text = ""
  next_step = step

  if step == -1:
    session = {"step": 0, "intent": "", "details": {}, "contact": {}}
    step = 0

  msg_lower = message.lower()

  # Reset / Start over handler
  if any(w in msg_lower for w in ["restart", "start over", "menu", "reset"]):
    return jsonify({
        "response": (
            "🔄 Let's start fresh! Are you looking to plan a majestic"
            " <b>Wedding/Event</b> or book an exclusive <b>Travel Package</b>?"
        ),
        "session": {"step": 0, "intent": "", "details": {}, "contact": {}},
    })

  # 1. Context-Aware FAQ Check
  faq_answer = check_flexible_faq(message, step)
  if faq_answer:
    reprompt = ""
    if step == 0:
      reprompt = "Would you like to plan a <b>Wedding/Event</b> or book a <b>Travel Package</b>?"
    elif step in [101, 102]:
      reprompt = (
          "To continue planning your event, please share your <b>estimated"
          " guest count and location/budget</b>:"
      )
    elif step in [201, 202, 301, 302]:
      reprompt = "To continue setting up your plan, please share your details:"
    elif step == 98:
      reprompt = "To finalize, could you please share your <b>name</b>?"
    elif step == 999:
      reprompt = "Lastly, please share your <b>phone number or email</b>:"

    return jsonify({
        "response": f"{faq_answer}<br><br><i>{reprompt}</i>",
        "session": {
            "step": step,
            "intent": intent,
            "details": details,
            "contact": contact,
        },
    })

  # --- CONVERSATIONAL STATE MACHINE FLOW ---
  if step == 0:
    if "wedding" in msg_lower or "marriage" in msg_lower or "shaadi" in msg_lower:
      intent = "Weddings & Events"
      next_step = 101
      response_text = (
          "✨ <b>Shubh Vivah!</b> Congratulations on your upcoming"
          " celebration. To help our team design your dream destination"
          " experience, could you please share your <b>estimated guest count and"
          " preferred city/location</b>?"
      )
    elif any(
        w in msg_lower for w in ["event", "party", "gathering", "celebration"]
    ):
      intent = "Weddings & Events"
      next_step = 101
      response_text = (
          "🎉 Excellent! To help our Events team plan your gathering"
          " seamlessly, could you please share your <b>estimated guest count and"
          " preferred location/venue type</b>?"
      )
    elif any(w in msg_lower for w in ["travel", "trip", "tour", "holiday"]):
      intent = "AMK Travels"
      next_step = 201
      response_text = (
          "✈️ Wonderful! AMK Travels would love to craft your journey. Are you"
          " looking for a domestic or international luxury package, and roughly"
          " <b>when are you planning to travel</b>?"
      )
    elif any(w in msg_lower for w in ["hi", "hello", "hey", "help"]):
      response_text = (
          "Namaste & welcome to <b>AMK Hospitality IPL</b>. 🙏 I'm your"
          " personal concierge. Are you looking to plan a majestic"
          " <b>Wedding/Event</b> or book an exclusive <b>Travel Package</b>?"
      )
      next_step = 0
    else:
      intent = "Other Services"
      next_step = 301
      response_text = (
          "Thank you for reaching out to AMK Hospitality. How may we assist you"
          " with our bespoke services today? Please share a brief overview."
      )

  elif step == 101:
    details["prefs"] = message
    next_step = 102
    response_text = (
        "Marvellous! What is your <b>estimated budget range</b> and expected"
        " <b>event date</b>? (e.g., 50 Lakhs, 3 December)"
    )
  elif step == 102:
    details["budget"] = message
    details["date"] = message
    next_step = 98
    response_text = (
        "Thank you so much! 🌟 Lastly, what is your <b>name</b> so our senior"
        " specialist can address you properly?"
    )

  elif step == 201:
    details["travel_prefs"] = message
    next_step = 202
    response_text = (
        "Splendid. What is your <b>total budget</b> and the <b>number of"
        " travelers</b>?"
    )
  elif step == 202:
    details["budget"] = message
    details["travel_dates"] = message
    next_step = 98
    response_text = (
        "Thank you so much! 🌟 Lastly, what is your <b>name</b> so our senior"
        " specialist can address you properly?"
    )

  elif step == 301:
    details["requirements"] = message
    next_step = 302
    response_text = (
        "What is your approximate <b>investment budget</b> for this service?"
    )
  elif step == 302:
    details["budget"] = message
    next_step = 98
    response_text = (
        "Thank you so much! 🌟 Lastly, what is your <b>name</b> so our senior"
        " specialist can address you properly?"
    )

  elif step == 98:
    contact["name"] = message
    next_step = 999
    response_text = (
        f"Thank you, <b>{contact['name']}</b>. 📞 Could you please share your"
        " <b>phone number or email</b> so our expert can connect with you?"
    )

  elif step == 999:
    contact["contact_info"] = message
    session["details"] = details
    session["intent"] = intent
    session["contact"] = contact

    is_qualified, department = qualify_and_route(session)
    lead_summary = {
        "department": department,
        "qualified": is_qualified,
        "client_name": contact.get("name"),
        "contact_info": contact.get("contact_info"),
        "intent": intent,
        "details": details,
    }
    LEAD_DATABASE.append(lead_summary)

    # Print structured JSON dossier to your terminal for review
    print("\n" + "=" * 50)
    print("🚀 [AMK HOSPITALITY IPL] NEW QUALIFIED LEAD DOSSIER:")
    print(json.dumps(lead_summary, indent=4))
    print("=" * 50 + "\n")

    if is_qualified:
      response_text = (
          f"✨ <b>Thank you, {contact.get('name')}! Your inquiry has been"
          f" successfully curated and routed directly to our expert"
          f" {department} team.</b><br><br>We have compiled your dossier, and a"
          f" senior concierge will reach out to you shortly at"
          f" <b>{contact.get('contact_info')}</b>."
      )
    else:
      response_text = (
          f"🙏 Thank you, {contact.get('name')}. We have logged your request"
          f" with our <b>Guest Relations</b> team, and someone will review your"
          f" query soon."
      )
    next_step = -1

  return jsonify({
      "response": response_text,
      "session": {
          "step": next_step,
          "intent": intent,
          "details": details,
          "contact": contact,
      },
  })


import os

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)