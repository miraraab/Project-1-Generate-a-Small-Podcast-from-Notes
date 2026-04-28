"""
src/llm_processor.py
--------------------
Stage 2 — Script Generation

Transforms a TranscriptData into a structured RecapScript using OpenAI.
Returns a RecapScript dataclass — the contract passed to tts_generator.py.

Prompt strategy: Feynman Method + Story Arc
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tone options — passed in from UI, injected into the prompt
# ---------------------------------------------------------------------------

ToneOption = Literal["standard", "humorous", "storytelling", "energetic"]

_TONE_INSTRUCTIONS: dict[str, str] = {
    "standard": "",
    "humorous": (
        "Occasionally add a light, well-placed joke or witty remark — never forced, "
        "always relevant to the concept being explained. Aim for one per major section. "
        "The humour should make the content more memorable, not distract from it."
    ),
    "storytelling": (
        "Weave in human moments throughout: a relatable struggle a student might have, "
        "a surprising real-world anecdote, or a brief story about how this concept once "
        "tripped someone up. Make the listener feel they are learning alongside a person, "
        "not just consuming information."
    ),
    "energetic": (
        "Keep the energy high throughout — like an enthusiastic coach who genuinely "
        "loves this subject and cannot believe how cool it is. Use punchy sentences, "
        "rhetorical questions, and moments of genuine excitement when a concept lands. "
        "Make the listener feel the forward momentum."
    ),
}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class RecapScript:
    class_name:     str
    date:           str
    intro:          str           = ""
    overview:       str           = ""
    key_points:     list[str]     = field(default_factory=list)
    deeper_dive:    str           = ""
    quiz_questions: list[str]     = field(default_factory=list)
    takeaway:       str           = ""
    outro:          str           = ""
    full_script:    str           = ""
    error:          Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return bool(self.full_script.strip()) and self.error is None

    def to_tts_text(self) -> str:
        return self.full_script

    def key_points_display(self) -> str:
        if not self.key_points:
            return "No key points extracted."
        return "\n".join(f"{i}. {pt}" for i, pt in enumerate(self.key_points, 1))

    def quiz_display(self) -> str:
        if not self.quiz_questions:
            return ""
        return "\n".join(f"Q{i}: {q}" for i, q in enumerate(self.quiz_questions, 1))


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the world's best educational podcast host — part brilliant professor,
part master storyteller, part Feynman-level explainer.

Your two superpowers:

1. THE FEYNMAN METHOD
You explain every concept in three layers:
- Layer 1: So simple a curious 16-year-old with no background could follow it
- Layer 2: The full university-level explanation with proper depth and nuance
- Layer 3: How an expert actually thinks about this in the real world
You never skip a layer. You never assume knowledge. You build understanding brick by brick.

2. THE STORY ARC
You treat every class as a story, not a list of topics.
- Every episode has a problem that needs solving
- Concepts are the tools the student picks up to solve that problem
- The episode builds toward a moment where everything clicks together
- The student ends knowing something they could not do before

Your voice is:
- Narrative and flowing — this is a story, not a lecture
- Warm and patient — no student is left behind
- Concrete — every abstraction gets a real-world example and a vivid analogy
- Spoken — every sentence sounds completely natural out loud
- Building — each concept connects to the next, nothing exists in isolation

You are producing a WORD-FOR-WORD SCRIPT for a long-form educational podcast.
There is no visual component. Every idea must land through sound alone.
Take your time. Make it unforgettable.\
"""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(transcript, tone: ToneOption = "standard") -> str:
    tone_text = _TONE_INSTRUCTIONS.get(tone, "")
    tone_block = (
        f"\nTONE GUIDANCE: {tone_text}\n"
        if tone_text
        else ""
    )

    return f"""\
Transform this class transcript into a long-form educational podcast episode
that combines the Feynman Method with a Story Arc structure.

CONTEXT:
- Course: {transcript.class_name}
- Date: {transcript.date}
- Instructor: {transcript.instructor}
- Transcript length: {transcript.word_count:,} words
{tone_block}
TRANSCRIPT:
{transcript.clean_text[:14000]}

---

OUTPUT FORMAT — produce each section with its label in square brackets.
Write ONLY the spoken words. No markdown, no bullet symbols, no headers.
This is a word-for-word narration script.

[INTRO]
4-5 sentences. Open by setting the scene — what problem or question does this
class exist to answer? Hook the listener with that problem before naming anything.
Then reveal the course, the date, and promise what the student will be able to
do by the end of this episode that they could not do before.
Make it feel like the opening of a great documentary.

[STORY SETUP]
3-4 sentences. Establish the narrative context for this class.
What is the world like WITHOUT the knowledge from today's class?
What goes wrong, what is confusing, what is impossible?
This is the before state — make the student feel the pain of not knowing.
Then introduce today's class as the solution to that pain.

[OVERVIEW]
2-3 sentences. Name every concept covered today as if introducing characters
in a story. Each concept is a tool the student will pick up along the way.
Build anticipation — make each one sound interesting and necessary.

[KEY POINTS]
Cover every single key concept from the transcript. Minimum 5, no maximum.
For EACH concept use the Feynman three-layer structure:

LAYER 1 — THE SIMPLE TRUTH
Explain it in 2-3 sentences that a curious 16-year-old with zero background
could understand perfectly. Use everyday language and a vivid analogy.
Start with: Here is the simplest way to think about this...

LAYER 2 — THE FULL PICTURE
Now explain it properly at university level. Add the nuance, the detail,
the technical accuracy. 3-4 sentences minimum. Connect it to how it actually
works in practice. Address what the simple explanation left out.

LAYER 3 — THE EXPERT LENS
How does a professional actually think about this concept on the job?
What do they watch out for? What do beginners always get wrong?
What mental model do experts use that makes this click at a deeper level?
2-3 sentences. Make the student feel like they are getting insider knowledge.

STORY CONNECTION
After each concept, one sentence connecting it to the narrative:
how does this concept help solve the problem you set up in the Story Setup?
How does picking up this tool move the student forward in the story?

Each concept should be at least 200 words. Separate each concept with a blank line.

[STORY CLIMAX]
This is the moment everything connects.
4-5 paragraphs where you show how ALL the concepts from today work together
to solve the problem you set up at the beginning.
Walk through a complete realistic scenario where a student or professional
uses every concept from this class in sequence.
Make the student feel the satisfaction of the pieces clicking into place.
This is the payoff for everything they just learned.

[DEEPER DIVE]
Pick the single most important or complex concept from the class.
Spend 6-8 paragraphs going deep using the full Feynman approach:
- Start from absolute first principles — assume nothing
- Build up the explanation one layer at a time
- Use a detailed real-world example with specific steps
- Address the 2-3 most common misconceptions head on
- Share the expert mental model that changes how you see this forever
- Connect it to the bigger story of the course — where does this lead?

[QUIZ]
5 self-test questions that range from conceptual to applied to analytical.
Mix easy and hard. One question per line.
The last question should require connecting multiple concepts together.

[TAKEAWAY]
2-3 sentences. What is the single insight that ties this whole story together?
Start with: If you remember only one thing from today...
End by connecting back to the opening problem — show that it is now solved.

[OUTRO]
3-4 sentences. Close the story loop — remind the student where they started
and how far they have come in just one episode.
Tease what comes next in the course as the next chapter of the story.
Leave the student feeling capable, curious, and ready for more.

---

TARGET LENGTH: 25 to 30 minutes of spoken audio (3,500 to 4,500 words total).
Write as one flowing narrative — concepts connect to each other, nothing exists
in isolation. Every section feeds into the next.
Plain spoken English only. No markdown. No bullet points.\
"""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_section(text: str, section: str) -> str:
    pattern = rf"\[{section}\](.*?)(?=\[[A-Z ]+\]|$)"
    match   = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_key_points(raw: str) -> list[str]:
    """
    Split KEY POINTS into individual concept blocks.
    Concepts are separated by blank lines — we keep each block intact
    so multi-paragraph Feynman explanations are not destroyed by line splitting.
    """
    if not raw.strip():
        return []
    blocks = [b.strip() for b in re.split(r"\n{2,}", raw) if len(b.strip()) > 50]
    return blocks if blocks else [raw.strip()]


def _parse_quiz(raw: str) -> list[str]:
    questions = []
    for line in raw.split("\n"):
        line = line.strip().lstrip("Q0123456789.: ").strip()
        if line.endswith("?") or len(line) > 20:
            questions.append(line)
    return questions[:5]


# ---------------------------------------------------------------------------
# Script assembly
# ---------------------------------------------------------------------------

def _assemble_script(
    intro:          str,
    story_setup:    str,
    overview:       str,
    key_points_raw: str,       # raw block — NOT the parsed list
    story_climax:   str,
    deeper_dive:    str,
    quiz_questions: list[str],
    takeaway:       str,
    outro:          str,
) -> str:
    parts = []

    if intro:
        parts.append(intro)
    if story_setup:
        parts.append(story_setup)
    if overview:
        parts.append(overview)
    if key_points_raw:
        parts.append("Let's walk through every key concept from today's class.")
        parts.append(key_points_raw)          # full text, nothing stripped
    if story_climax:
        parts.append("Now let's bring everything together.")
        parts.append(story_climax)
    if deeper_dive:
        parts.append("Let's go much deeper on the most important concept from today.")
        parts.append(deeper_dive)
    if quiz_questions:
        parts.append(
            "Before we wrap up, here are five questions to test your understanding. "
            "Pause after each one and think it through before moving on."
        )
        for q in quiz_questions:
            parts.append(q)
    if takeaway:
        parts.append(takeaway)
    if outro:
        parts.append(outro)

    return "\n\n".join(filter(None, parts))


def _parse_response(raw: str, transcript) -> RecapScript:
    intro          = _extract_section(raw, "INTRO")
    story_setup    = _extract_section(raw, "STORY SETUP")
    overview       = _extract_section(raw, "OVERVIEW")
    key_points_raw = _extract_section(raw, "KEY POINTS")   # kept intact for assembly
    key_points     = _parse_key_points(key_points_raw)     # split for dataclass display
    story_climax   = _extract_section(raw, "STORY CLIMAX")
    deeper_dive    = _extract_section(raw, "DEEPER DIVE")
    quiz_questions = _parse_quiz(_extract_section(raw, "QUIZ"))
    takeaway       = _extract_section(raw, "TAKEAWAY")
    outro          = _extract_section(raw, "OUTRO")

    full_script = _assemble_script(
        intro, story_setup, overview, key_points_raw,
        story_climax, deeper_dive, quiz_questions,
        takeaway, outro,
    )

    if not full_script.strip():
        full_script = raw

    return RecapScript(
        class_name     = transcript.class_name,
        date           = transcript.date,
        intro          = intro,
        overview       = overview,
        key_points     = key_points,
        deeper_dive    = deeper_dive,
        quiz_questions = quiz_questions,
        takeaway       = takeaway,
        outro          = outro,
        full_script    = full_script,
    )


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Add it to your .env file.")
    client   = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model                 = "gpt-4o",          # verify your model string
        max_completion_tokens = 8192,
        messages              = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_recap(transcript, tone: ToneOption = "standard") -> RecapScript:
    """
    Transform a TranscriptData into a RecapScript using OpenAI.

    Parameters
    ----------
    transcript : TranscriptData
    tone       : one of "standard" | "humorous" | "storytelling" | "energetic"
                 Controls the personality injected into the prompt.
    """
    if not transcript.is_valid:
        return RecapScript(
            class_name = transcript.class_name,
            date       = transcript.date,
            error      = transcript.error or "Invalid transcript.",
        )

    logger.info("Generating recap for: %s (tone=%s)", transcript.class_name, tone)

    try:
        prompt = _build_prompt(transcript, tone=tone)
        raw    = _call_openai(prompt)
        script = _parse_response(raw, transcript)
        logger.info(
            "Recap ready — %d key points, %d quiz questions, %d words",
            len(script.key_points),
            len(script.quiz_questions),
            len(script.full_script.split()),
        )
        return script

    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return RecapScript(
            class_name = transcript.class_name,
            date       = transcript.date,
            error      = str(exc),
        )