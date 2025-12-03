# server/tools/builtin/onboarding_tools.py
"""
Onboarding workflow tools for Felix.

Guides new users through a conversational questionnaire to build
their initial memory profile with personal info, preferences, and context.
"""

import logging
from typing import Optional
from ..registry import tool_registry

logger = logging.getLogger(__name__)

# Onboarding questions organized by category
ONBOARDING_QUESTIONS = {
    "basic": [
        "What's your name?",
        "What do you prefer to be called?",
        "Where are you located? (city/timezone)",
    ],
    "work": [
        "What do you do for work or study?",
        "What programming languages or technologies do you work with?",
        "What are you currently working on or learning?",
    ],
    "preferences": [
        "What's your preferred communication style? (brief/detailed/conversational)",
        "Do you prefer dark mode or light mode?",
        "What time of day do you usually work/code?",
    ],
    "interests": [
        "What are your main interests or hobbies?",
        "What kind of projects are you passionate about?",
        "What music do you like? (for music player recommendations)",
    ],
    "goals": [
        "What are your current goals or what would you like help with?",
        "Is there anything specific you'd like Felix to remember or track?",
    ]
}

# Session state for tracking onboarding progress
_onboarding_state = {
    "active": False,
    "current_category": None,
    "current_question_index": 0,
    "responses": {},
    "categories_completed": []
}


def _get_total_questions(categories):
    """Calculate total number of questions for given categories."""
    return sum(len(ONBOARDING_QUESTIONS[cat]) for cat in categories)


def _get_current_question_number():
    """Get the current overall question number (1-indexed)."""
    state = _onboarding_state
    completed = 0
    for cat in state["categories_completed"]:
        completed += len(ONBOARDING_QUESTIONS[cat])
    
    current_cat = state["current_category"]
    if current_cat:
        completed += state["current_question_index"] + 1
    
    return completed


@tool_registry.register(
    description="Start the onboarding workflow to help Felix learn about the user. Use this for new users or when someone asks to set up their profile."
)
async def start_onboarding(quick_mode: Optional[bool] = False) -> str:
    """
    Begin the onboarding conversation.
    
    Args:
        quick_mode: If True, ask only essential questions (name, work, preferences)
    
    Returns:
        Welcome message with first question
    """
    global _onboarding_state
    
    _onboarding_state["active"] = True
    _onboarding_state["current_category"] = "basic"
    _onboarding_state["current_question_index"] = 0
    _onboarding_state["responses"] = {}
    _onboarding_state["categories_completed"] = []
    
    if quick_mode:
        _onboarding_state["categories"] = ["basic", "work", "preferences"]
    else:
        _onboarding_state["categories"] = ["basic", "work", "preferences", "interests", "goals"]
    
    logger.info("onboarding_started", quick_mode=quick_mode)
    
    # Get first question
    category = _onboarding_state["current_category"]
    question = ONBOARDING_QUESTIONS[category][0]
    total_questions = _get_total_questions(_onboarding_state["categories"])
    
    mode_text = "Quick " if quick_mode else ""
    intro = f"""👋 Welcome! I'm Felix, your AI voice assistant.

I'd like to get to know you better through a brief questionnaire. Your answers will be stored in my long-term memory system, allowing me to:
• Remember your preferences and context across sessions
• Personalize responses based on your work and interests  
• Provide more relevant suggestions and help
• Build on past conversations naturally

**{mode_text}Onboarding** - {total_questions} questions total

**Question 1/{total_questions}** - {category.title()}

{question}

_(Say "skip" to skip, or "stop onboarding" to finish early)_"""
    
    return intro


@tool_registry.register(
    description="Process the user's response during onboarding and move to the next question. Use this after the user answers an onboarding question."
)
async def onboarding_next(user_response: str) -> str:
    """
    Process current response and get next question.
    
    Args:
        user_response: The user's answer to the current question
    
    Returns:
        Next question or completion message
    """
    global _onboarding_state
    
    if not _onboarding_state["active"]:
        return "No onboarding in progress. Use start_onboarding() to begin."
    
    # Handle special commands
    if user_response.lower().strip() in ["stop onboarding", "quit", "exit", "done"]:
        return await complete_onboarding()
    
    skip = user_response.lower().strip() in ["skip", "pass", "next"]
    
    # Store response if not skipping
    if not skip:
        category = _onboarding_state["current_category"]
        q_index = _onboarding_state["current_question_index"]
        question = ONBOARDING_QUESTIONS[category][q_index]
        
        if category not in _onboarding_state["responses"]:
            _onboarding_state["responses"][category] = []
        
        _onboarding_state["responses"][category].append({
            "question": question,
            "answer": user_response
        })
    
    # Move to next question
    _onboarding_state["current_question_index"] += 1
    
    # Check if current category is complete
    category = _onboarding_state["current_category"]
    if _onboarding_state["current_question_index"] >= len(ONBOARDING_QUESTIONS[category]):
        _onboarding_state["categories_completed"].append(category)
        
        # Move to next category
        current_cat_idx = _onboarding_state["categories"].index(category)
        if current_cat_idx + 1 < len(_onboarding_state["categories"]):
            _onboarding_state["current_category"] = _onboarding_state["categories"][current_cat_idx + 1]
            _onboarding_state["current_question_index"] = 0
        else:
            # All categories complete
            return await complete_onboarding()
    
    # Get next question
    category = _onboarding_state["current_category"]
    q_index = _onboarding_state["current_question_index"]
    question = ONBOARDING_QUESTIONS[category][q_index]
    
    current_q = _get_current_question_number()
    total_q = _get_total_questions(_onboarding_state["categories"])
    
    return f"""**Question {current_q}/{total_q}** - {category.title()}

{question}"""


@tool_registry.register(
    description="Complete the onboarding workflow and store all collected information in memory."
)
async def complete_onboarding() -> str:
    """
    Finish onboarding and save all responses to memory.
    
    Returns:
        Summary of stored memories
    """
    global _onboarding_state
    
    if not _onboarding_state["active"]:
        return "No onboarding in progress."
    
    _onboarding_state["active"] = False
    
    # Format responses for storage
    responses = _onboarding_state["responses"]
    total_qa = sum(len(qa_list) for qa_list in responses.values())
    
    if total_qa == 0:
        logger.info("onboarding_completed_empty")
        return "Onboarding completed, but no information was provided. You can start over with start_onboarding() if you'd like."
    
    # Build summary
    summary_lines = ["🎉 **Onboarding Complete!**\n", f"Collected {total_qa} pieces of information:\n"]
    
    memories_to_store = []
    
    for category, qa_list in responses.items():
        summary_lines.append(f"**{category.title()}:**")
        for qa in qa_list:
            summary_lines.append(f"  • {qa['question']}")
            summary_lines.append(f"    → {qa['answer']}")
            
            # Prepare memory entry
            memories_to_store.append({
                "content": f"[{qa['question']}] {qa['answer']}",
                "tags": [category, "onboarding", "profile"],
                "importance": "high"  # Onboarding info is high priority
            })
    
    summary_lines.append(f"\n📝 All information will be stored in my memory using {len(memories_to_store)} memory entries.")
    summary_lines.append("\nI'll now remember these details across all our conversations!")
    
    logger.info("onboarding_completed", 
                categories=len(responses), 
                total_responses=total_qa,
                memories=len(memories_to_store))
    
    # Return summary with instruction to use remember() for each entry
    summary = "\n".join(summary_lines)
    
    # Add metadata about what to do next
    summary += "\n\n_Note: Use the remember() tool to store each of these memories now._"
    
    # Store the list of memories to be saved
    _onboarding_state["pending_memories"] = memories_to_store
    
    return summary


@tool_registry.register(
    description="Get the list of pending memories from completed onboarding that need to be stored."
)
async def get_onboarding_memories() -> list:
    """
    Retrieve memories collected during onboarding.
    
    Returns:
        List of memory objects ready to be stored
    """
    global _onboarding_state
    
    if "pending_memories" not in _onboarding_state or not _onboarding_state["pending_memories"]:
        return []
    
    memories = _onboarding_state["pending_memories"]
    _onboarding_state["pending_memories"] = []  # Clear after retrieval
    
    logger.info("onboarding_memories_retrieved", count=len(memories))
    return memories


@tool_registry.register(
    description="Check if onboarding is currently active or get the current onboarding status."
)
async def onboarding_status() -> str:
    """
    Get current onboarding workflow status.
    
    Returns:
        Status information
    """
    if not _onboarding_state["active"]:
        return "No onboarding in progress. Use start_onboarding() to begin."
    
    category = _onboarding_state["current_category"]
    q_index = _onboarding_state["current_question_index"]
    completed = len(_onboarding_state["categories_completed"])
    total = len(_onboarding_state["categories"])
    
    status = f"""📋 **Onboarding Status**

**Progress:** {completed}/{total} categories completed
**Current Category:** {category.title()}
**Question:** {q_index + 1}/{len(ONBOARDING_QUESTIONS[category])}
**Responses Collected:** {sum(len(qa) for qa in _onboarding_state['responses'].values())}

Use onboarding_next() to continue, or complete_onboarding() to finish."""
    
    return status
