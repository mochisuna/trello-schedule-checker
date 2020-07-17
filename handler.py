import datetime
import json
import os
import re
import slackweb
import requests
import urllib
from threading import Thread
from trello import TrelloClient


def parse_card(card):
    labels = []
    if card.labels:
        for label in card.labels:
            labels.append(label.name)

    return {
        "id": card.id,
        "name": card.name,
        "labels": labels,
        "shortUrl": card.shortUrl,
    }


def within_period(name):
    match = re.search(r'【.+】', name)
    if (match):
        period = match.group().strip().replace('【', '').replace('】', '').split('-')
        try:
            today = datetime.datetime.today()
            begin = datetime.datetime.strptime(
                f'{today.year}/{period[0]}', "%Y/%m/%d")
            end = datetime.datetime.strptime(
                f'{today.year}/{period[1]}', "%Y/%m/%d")
            return begin <= today and today <= end
        except ValueError:
            return False
    return False

# callback処理


def slack_callback(response_url, post_data):
    post_headers = {
        'Content-type': 'application/json; charset=utf-8'
    }

    requests.post(
        response_url,
        headers=post_headers,
        data=post_data
    )


def schedule(event, context):
    # slash-commandのtimeout対策として速攻でレスポンスを返す
    response_urls = urllib.parse.parse_qs(event.get('body'))['response_url']
    if response_urls:
        post_data = {'text': 'running slash command...'}
        Thread(
            target=slack_callback,
            args=[
                response_urls[0],
                json.dumps(post_data).encode("utf-8")
            ]
        ).start()

    # レスポンスとは別に本来の目的の処理を走らせる
    client = TrelloClient(
        api_key=os.environ.get('TRELLO_API_KEY'),
        api_secret=os.environ.get('TRELLO_API_SECRET'),
        token=os.environ.get('TRELLO_TOKEN'),
    )
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        slack = slackweb.Slack(url=webhook_url)
    else:
        slack = None
    schedules = {}
    for list in client.get_board(os.environ.get('TRELLO_BOARD_ID')).all_lists():
        schedules[list.id] = {"name": list.name, "cards": []}
        for card in list.list_cards():
            target = parse_card(card)
            schedules[list.id]["cards"].append(target)
    current_schedule = schedules[os.environ.get('RUNNING_CAMPAIGN')]['cards']
    if current_schedule:
        text = "現在稼働中のキャンペーンは以下の通りです\n"
        for card in current_schedule:
            text += f"```キャンペーン名: {card['name']}\nラベル: {card['labels']}\nURL: {card['shortUrl']}```\n"
        if slack:
            slack.notify(text=text)
        else:
            print(text)

    future_schedule = schedules[os.environ.get('FUTURE_CAMPGAIGN')]['cards']
    if future_schedule:
        text = "現在予定しているキャンペーンは以下の通りです\n"
        for card in future_schedule:
            text += f"```{card['name']}: {card['shortUrl']}```\n"
        if slack:
            slack.notify(text=text)
        else:
            print(text)

    return {
        "statusCode": 200,
        "body": json.dumps(current_schedule)
    }
