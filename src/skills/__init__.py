"""
Skills Package - Claude Code agent skills.

Skills are reusable, documented command patterns for Claude Code.
They define how Claude should process specific types of tasks.

Available Skills:
- LinkedInPostingSkill: Draft, schedule, and publish LinkedIn posts with HITL approval
- ProcessInboxSkill: Process action items from Needs_Action using Ralph Wiggum Loop

Skills are defined as markdown files in .claude/commands/ directory.
"""

# Optional imports - graceful fallback if dependencies not installed
try:
    from .linkedin_posting import LinkedInPostingSkill, PostDraft, PostResult
except ImportError:
    LinkedInPostingSkill = None
    PostDraft = None
    PostResult = None

try:
    from .process_inbox import ProcessInboxSkill, ProcessingResult, ActionItem
except ImportError:
    ProcessInboxSkill = None
    ProcessingResult = None
    ActionItem = None

try:
    from .ceo_briefing import CEOBriefingSkill
except ImportError:
    CEOBriefingSkill = None

try:
    from .social_posting import SocialPostingSkill
except ImportError:
    SocialPostingSkill = None

__all__ = [
    'LinkedInPostingSkill', 'PostDraft', 'PostResult',
    'ProcessInboxSkill', 'ProcessingResult', 'ActionItem',
    'CEOBriefingSkill',
    'SocialPostingSkill',
]
