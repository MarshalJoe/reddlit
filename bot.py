#!/usr/bin/env python

import praw
import product
import boto3
import json

from config import *

def main():
    reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT,
                     username=REDDIT_USERNAME,
                     password=REDDIT_PASSWORD)
    subreddits_list = ["books", "literature", "BookDiscussion", "CurrentlyReading", "JustFinishedReading", "goodreads", "booksuggestions", "horrorlit", "Fantasy", "WeirdLit", "literature", "printSF", "bookclub"]
    subreddits = "+".join(subreddits_list)
    subreddit = reddit.subreddit(subreddits)
    for submission in subreddit.stream.submissions():
        try:
            process_submission(submission)
        except Exception, e:
            print(str(e))


def process_submission(submission):
    # Direct Product API integration
    product.process_submission(submission.title, submission.url, int(submission.created))

    # Lambda integration
    #book = product.extract_book_title(submission.title)

    # if book:
    #     lambda_call(book, submission.url)
    #     print("Lambda call successfully made")

def lambda_call(title, link, timestamp):
    client = boto3.client('lambda')
    
    payload = { 
        "title": title, 
        "link": link, 
        "timestamp": timestamp,
    }

    json_payload = json.dumps(payload)

    response = client.invoke(
        FunctionName='hello-world-python',
        Payload=json_payload,
    )

    return response

if __name__ == '__main__':
    main()