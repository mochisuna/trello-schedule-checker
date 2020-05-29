import datetime
import json
import os
import re
from trello import TrelloClient
import slackweb


def parseCard(card):
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


def schedule(event, context):
    client = TrelloClient(
        api_key=os.environ['TRELLO_API_KEY'],
        api_secret=os.environ['TRELLO_API_SECRET'],
        token=os.environ['TRELLO_TOKEN'],
    )
    slack = slackweb.Slack(url=os.environ['WEBHOOK_URL'])
    schedules = {}
    for list in client.get_board(os.environ['TRELLO_BOARD_ID']).all_lists():
        schedules[list.id] = {"name": list.name, "cards": []}
        for card in list.list_cards():
            target = parseCard(card)
            schedules[list.id]["cards"].append(target)

    text = "現在稼働中のキャンペーンは以下の通りです\n"
    for card in schedules[os.environ['RUNNING_CAMPAIGN']]['cards']:
        text += f"```キャンペーン名: {card['name']}\nラベル: {card['labels']}\nURL: {card['shortUrl']}```\n"
    slack.notify(text=text)

    text = "現在予定しているキャンペーンは以下の通りです\n"
    for card in schedules[os.environ['FUTURE_CAMPGAIGN']]['cards']:
        text += f"```{card['name']}: {card['shortUrl']}```\n"
    slack.notify(text=text)

    response = {
        "statusCode": 200,
        "body": json.dumps(schedules[os.environ['RUNNING_CAMPAIGN']]['cards'])
    }
    return response
