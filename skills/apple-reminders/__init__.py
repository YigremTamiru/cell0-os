"""
Apple Reminders Skill for Cell 0 OS

Integration with Apple Reminders via remindctl CLI.

Usage:
    from skills.apple_reminders.apple_reminders import AppleRemindersSkill
    from skills.apple_reminders.tools import AppleRemindersTools

    skill = AppleRemindersSkill()
    tools = AppleRemindersTools()
"""

__version__ = "1.0.0"
__author__ = "Cell 0 OS"

from .apple_reminders import AppleRemindersSkill
from .tools import AppleRemindersTools

__all__ = ['AppleRemindersSkill', 'AppleRemindersTools']
