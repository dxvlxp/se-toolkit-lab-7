import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request

from config import load_settings
from handlers import CommandContext, route_text


def telegram_call(token, method, payload):
    url = f'https://api.telegram.org/bot{token}/{method}'
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=45) as res:
        result = json.load(res)
    if not result.get('ok'):
        raise RuntimeError(f'Telegram API rejected {method}: {result}')
    return result['result']


def _keyboard():
    return {'inline_keyboard': [[
        {'text': 'Health', 'callback_data': '/health'},
        {'text': 'Labs', 'callback_data': '/labs'},
        {'text': 'Help', 'callback_data': '/help'},
    ]]}


def run_telegram(token, context):
    offset = 0
    logging.info('Bot polling started')
    while True:
        try:
            updates = telegram_call(token, 'getUpdates', {'timeout': 30, 'offset': offset})
            for update in updates:
                offset = update['update_id'] + 1
                callback = update.get('callback_query')
                if callback:
                    try:
                        telegram_call(token, 'answerCallbackQuery', {'callback_query_id': callback['id']})
                    except Exception:
                        logging.exception('Could not acknowledge callback')
                    message = callback.get('message') or {}
                    text = callback.get('data') or ''
                else:
                    message = update.get('message') or {}
                    text = message.get('text') or ''
                chat_id = (message.get('chat') or {}).get('id')
                if not chat_id or not text:
                    continue
                reply = route_text(text, context)
                telegram_call(token, 'sendMessage', {'chat_id': chat_id, 'text': reply[:4000],
                              'reply_markup': _keyboard()})
        except KeyboardInterrupt:
            return
        except Exception:
            logging.exception('Telegram polling error')
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', metavar='MESSAGE', help='Run handlers without Telegram')
    args = parser.parse_args()
    settings = load_settings()
    context = CommandContext()
    if args.test is not None:
        print(route_text(args.test, context))
        return 0
    if not settings.bot_token:
        print('BOT_TOKEN is required outside --test mode', file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    run_telegram(settings.bot_token, context)
    return 0


if __name__ == '__main__':
    sys.exit(main())
