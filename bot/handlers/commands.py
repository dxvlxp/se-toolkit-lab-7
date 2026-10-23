"""Task 1: Telegram-independent CLI handler scaffold."""
from dataclasses import dataclass

@dataclass
class CommandContext:
    lms: object = None
    llm: object = None

def route_text(message: str, context: CommandContext) -> str:
    text = (message or '').strip()
    if not text:
        return 'Send /help for commands.'
    words = text.split()
    command = words[0].split('@')[0].lower()
    if command == '/start':
        return 'Welcome to LMS Telegram bot! Use /help.'
    if command == '/help':
        return ('Commands: /start, /help, /health, /labs, /scores lab-04. '
                'Backend integration is planned in Task 2.')
    if command == '/health':
        return 'Backend status: pending integration (Task 2).'
    if command == '/labs':
        return 'Lab listing: pending backend integration (Task 2).'
    if command == '/scores':
        if len(words) < 2:
            return 'Usage: /scores lab-04'
        return f'Scores for {words[1]}: pending backend integration (Task 2).'
    if command.startswith('/'):
        return f'Unknown command: {command}. Use /help.'
    return 'Natural-language routing will be implemented in Task 3.'
