from app.contracts.call_context import CallContext


CALL_SCRIPT_DRAFT = """
This is an editable example for voice testing, reflecting a warm, respectful
North Indian conversational tone suitable for parents.

Opening:
Hindi/Hinglish: "Namaste {parent_name} ji! Main college se baat kar rahi hoon.
Kya meri baat {parent_name} ji se ho rahi hai?"
English: "Hello {parent_name}, I am calling from the college attendance office.
Am I speaking with {parent_name}?"

After confirming guardian identity:
Hindi/Hinglish: "Ji namaste. College ke record mein {student_name} ki
attendance {attendance_period} ke liye {attendance_percentage}% dikh rahi hai.
Sab theek to hai ji? Kya koi khas wajah thi college na aane ki?"
English: "Thank you. The college record currently shows {student_name}'s
attendance for {attendance_period} as {attendance_percentage} percent. Is everything
all right? Was there a specific reason for the absence?"

If the parent reports illness, leave, or urgent family work:
Hindi/Hinglish: "Ji theek hai, main record karunga/karungi; college team confirm karegi. Umeed hai ab tabiyat theek hai. Kal se college zaroor bhejiyega."
English: "I understand. I will note this, and the college team will confirm. Please ensure they resume classes as soon as possible."

If this is the wrong person or number:
Hindi/Hinglish: "Maaf kijiyega, lagta hai galat number par call lag gaya.
Aapko pareshan karne ke liye kshama chahte hain. Namaste."
English: "I apologize, it seems I dialed the wrong number. Sorry for disturbing you. Have a good day."

If the parent is busy or in the fields / asks for callback:
Hindi/Hinglish: "Ji zaroor, hum samajh sakte hain. Aap kis waqt baat karna
chahenge? Hum college team ko note karwa denge."
English: "Certainly. When would be a convenient time for the college team to contact you?"

If the parent is upset or concerned:
Hindi/Hinglish: "Ji hum aapki baat samajh rahe hain. Aap chinta mat kijiye,
hum aapka sandesh college team tak pahuncha denge."
English: "I understand your concern. Please do not worry, I will share your note directly with the college faculty."

If the parent's words are unclear:
Hindi/Hinglish: "Maaf kijiye, aapki baat thodi clear nahi aayi. Kya aap ek baar
phir bolenge?"
English: "Sorry, your voice broke up a little. Could you please repeat that?"

Closing:
Hindi/Hinglish: "Bahut-bahut dhanyavaad {parent_name} ji apna samay dene ke liye.
Namaste, apna khayal rakhiyega."
English: "Thank you very much for your time. Have a wonderful day ahead."

The phrase "record karunga/karungi" means note the parent's concern for
college review. It does not mean recording call audio. Do not say that the
call is recorded.
"""


def build_draft_script(context: CallContext) -> str:
    attendance_period = (
        f"{context.attendance_period_start.strftime('%d %b %Y')} to "
        f"{context.attendance_period_end.strftime('%d %b %Y')}"
    )
    return CALL_SCRIPT_DRAFT.format(
        parent_name=context.parent_name,
        student_name=context.student_name,
        attendance_period=attendance_period,
        attendance_percentage=context.attendance_percentage,
    ).strip()
