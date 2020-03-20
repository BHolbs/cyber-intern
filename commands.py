import random
import requests

responses = ['It is certain.', 'It is decidedly so.', 'Without a doubt.', 'Yes - definitely.',
             'You can count on it.', 'As I see it, yes.', 'Most likely.', 'Outlook is good.', 'Yes.',
             'Signs point to yes.', 'Not sure, try again.', 'Ask me again later, I don\'t feel like answering.',
             'Better not tell you now and spoil the surprise.', 'Can\'t predict now.', 'Concentrate and ask again.',
             'Don\'t count on it.', 'Nope.', 'My sources say no.', 'Outlook ain\'t good.', 'Hell, no.']


# Function to handle eight ball question responses from a fixed pool
def eightball(msg):
    if len(msg.content) <= len('!eightball '):
        return '{0.author.mention}, please provide a question! It doesn\'t make sense for me to respond without a question.'.format(msg)

    val = random.randint(0, len(responses))
    shuff_responses = random.sample(responses, len(responses))
    response = shuff_responses[val]

    message = '{0.author.mention}, '.format(msg)
    message += ' ' + response
    return message


# Function to send GET request to gundam wiki API, returns the first page it finds in the json response,
# or a string indicating failure to find anything if search is badly formatted or returns nothing
def wikihandler(msg):
    query = msg.content[len('!gwiki '):]
    r = requests.get('https://gundam.fandom.com/api/v1/Search/List?query='+query)
    response = r.json()
    if r.status_code == 400 or r.status_code == 404:
        return '{0.author.mention}, I can\'t find anything with that search. Try again?'.format(msg)
    else:
        if len(response["items"]) == 0:
            return '{0.author.mention}, I can\'t find anything with that search. Try again?'.format(msg)
        url = response["items"][0]["url"]
        return '{0.author.mention}, looking for this?: '.format(msg) + url
