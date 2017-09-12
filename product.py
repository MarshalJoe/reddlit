import string
import time
import datetime
import bottlenose
import boto3
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
from ratelimit import rate_limited
from config import *

amazon = bottlenose.Amazon(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ASSOCIATE_TAG)
dynamodb = boto3.resource('dynamodb', region_name='us-east-2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def rate_limited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)
    def decorate(func):
        lastTimeCalled = [0.0]
        def rateLimitedFunction(*args,**kargs):
            elapsed = time.clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait>0:
                time.sleep(leftToWait)
            ret = func(*args,**kargs)
            lastTimeCalled[0] = time.clock()
            return ret
        return rateLimitedFunction
    return decorate

@rate_limited(1)
def search_product(product_keyword, search_index, author=False):
	if author:
		response = amazon.ItemSearch(Keywords=product_keyword, Author=author, SearchIndex=search_index)
	else:
		response = amazon.ItemSearch(Keywords=product_keyword, SearchIndex=search_index)
	parsed = BeautifulSoup(response, "html.parser")
	return parsed

@rate_limited(1)
def find_lowest_price(asin):
	response = amazon.ItemLookup(ItemId=asin,ResponseGroup="OfferSummary")
	parsed = BeautifulSoup(response, "html.parser")
	return parsed

@rate_limited(1)
def find_product_image(asin):
	response = amazon.ItemLookup(ItemId=asin,ResponseGroup="Images")
	parsed = BeautifulSoup(response, "html.parser")
	return parsed

def add_book_record(data):
	table = dynamodb.Table('books')
	try:
		response = table.put_item(Item=data, ConditionExpression="attribute_not_exists(title)")
		print('{:%Y-%m-%d %H:%M:%S} '.format(datetime.datetime.now()) +  'Adding ' + data['title'])
	except Exception, e:
		response = False
	return response

def strip_punctuation(text):
	result = text#.translate(None, string.punctuation)
	return result

def strip_beginning_lowercase_words(text):
	count = 0
	substr = ""
	while(count < len(text)):
		if (text[count].islower() or text[count] == " "):
			substr+=text[count]
		else:
			break
		count = count + 1

	result = text.replace(substr, "")
	return result

def extract_book_title(text):
	title_list = []
	tokens = word_tokenize(text)
	book = False
	# normalize
	tokens[0] = tokens[0].lower()

	for index, token in enumerate(tokens):
		# when you find "by"
		if token == "by":
			book = {}
			by_index = index
			title_string = tokens[:by_index]
			author_string = tokens[by_index:]
			book['author'] = author_string[1] + " " + author_string[2]

			try:
				beginning_index = title_string.index("The")
			except Exception:
				beginning_index = 0
					
			raw_title = title_string[beginning_index:]
			title = strip_punctuation(" ".join(raw_title))
			book['title'] = strip_beginning_lowercase_words(title)

	return book

def process_submission(title, link, timestamp):
	book = extract_book_title(title)


	if book:
		data = {}
		data['reddit_link'] = link
		data['timestamp'] = timestamp
		
		try:
			product_search = search_product(book['title'], "Books", book['author'])
		except Exception, e:
			print(str(e))
			return False

		items = product_search.find_all("items")

		try:
			data['author'] = items[0].author.text
		except Exception:
			return False
		
		try:
			data['title'] = items[0].title.text
		except Exception:
			return False

		try:
			data['asin'] = items[0].asin.text
		except Exception:
			return False

		try:
			data['amz_url'] = items[0].url.text
		except Exception:
			return False

		try:
			offer_search = find_lowest_price(data['asin'])
		except Exception, e:
			print(str(e))
			return False

		try:
			image_search = find_product_image(data['asin'])
		except Exception, e:
			print(str(e))
			return False
		
		offers = offer_search.find("lowestusedprice")
		large_image = image_search.find("largeimage")

		try:
			data['price'] = offers.formattedprice.text
		except Exception:
			data['price'] = "n/a"

		data['image'] = large_image.url.text

		add_book_record(data)
	else:
		return False

if __name__ == '__main__':
	print('main')

