import boto3
import time
from string import Template
from operator import itemgetter

# bootstrap
def handler(event, context):
    update_site()

def extract_subreddit(url):
	url_array = url.split("/")
	try:
		r_index = url_array.index("r")
		subreddit_index = r_index + 1
		subreddit = "r/" + url_array[subreddit_index]
	# if no /r/ uri, fall back on hostname
	except Exception:
		url_array = url.split("//")
		suffix = url_array [1]
		hostname = suffix.split(".")[-2]
		subreddit = hostname
	
	return subreddit


def update_site():
	client = boto3.client('dynamodb')
	s3 = boto3.resource('s3')

	data = client.scan(
	    TableName='books',
	    Limit=100,
	)

	books = sorted(data['Items'], key=lambda b: b['timestamp'], reverse=True)

	header = '''
		<!DOCTYPE html>
			<html>
			<style>
				.book-container {
					text-align:center;
					margin:100px;
				}

				.book-title, .book-author {
					margin-bottom:10px;
				}

				.book-title {
					font-size:1.5em;
				}

				.book-author {
					font-size:1em;
					font-style: italic;
				}

				.reddit-link, .twitter-bio {
					color:#1A0DAB;
				}

				* {
				  box-sizing: border-box;
				}

				html,
				body {
				  width: 100%;
				  height: 100%;
				  margin: 0;
				  padding: 0;
				}

				html {
				  color: #4C4C4C;
				  font-size: 18px;
				  font-family: 'Open Sans', sans-serif;
				  font-weight: 300;
				  line-height: 1.6;
				  background-color: #FFFFFF;
				}

				h1, h2, h3, h4, h5, h6 {
				  font-weight: 500;
				}

				p,
				dl,
				ol,
				ul,
				pre,
				img,
				table,
				blockquote {
				  margin: 0 0 1.5em;
				}

				ul {
				  padding: 0 0 0 1.5em;
				}

				a,
				.btn {
				  text-decoration: none;
				}

				a {
				  color: #36454f;
				}

				img,
				audio,
				embed,
				video,
				object {
				  height: auto;
				  max-width: 100%;
				}

				img,
				audio,
				video,
				canvas {
				  display: block;
				  margin-left: auto;
				  margin-right: auto;
				}

				footer {
					text-align:center;
					margin:2em;
				}

				.cf:before,
				.cf:after {
				  content: " ";
				  display: table;
				}

				.cf:after {
				  clear: both;
				}

				.pull-left {
				  float: left;
				}

				.pull-right {
				  float: right;
				}

				@media (max-width: 500px) {
					.book-title {
				    	font-size:1em;
				  	}

					.book-container {
						margin:50px;
						margin-top:0;
						margin-bottom:75px;
						line-height:1.25em;
				  	}
				}

			</style>

			<link rel="shortcut icon" href="favicon.ico" type="image/x-icon">
			<head>
				<script>
					function getAge(epoch) {
						let d = new Date();
						let current = Math.floor(d.getTime() / 1000);
						let delta = (current - epoch) + (8 * 60 * 60);
						let seconds = delta;
						let minutes = seconds / 60;
						let	hours = minutes / 60;
						let	days = hours / 24;
						let	msg = '';

						if (days > 1 && days < 2) {
							msg = `${Math.floor(days)} day ago on`;
						} else if (days > 2) {
							msg = `${Math.floor(days)} days ago on`;
						} else if (hours >= 1 && hours < 2) {
						    msg = `${Math.floor(hours)} hour ago on`;
						} else if (hours > 1 && hours < 24) {
						    msg = `${Math.floor(hours)} hours ago on`;
						} else if (minutes >= 1 && minutes < 2) {
						    msg = `${Math.floor(minutes)} minute ago on`;
						} else if (minutes > 1 && minutes < 60) {
						    msg = `${Math.floor(minutes)} minutes ago on`;
						} else if (seconds > 1 && seconds < 60) {
						    msg = `${seconds} seconds ago on`;
						} else {
						}
		  				return msg
					}
				</script>

				<title>reddlit: what reddit reads</title>
			</head>
			<body>
			<div class="book-container">
				<img src="reddlit_logo.png" />
			</div>

	'''

	row_template = Template(
		'''
		<div class="book-container">
			<a href="$amz_url">
				<img src="$image" />
			</a>
			<p class="book-title"><a href="$amz_url">$title</a></p>
			<p class="book-author">by $author</p>
			<p><span id="age-$age"></span>
			<script>
				(function () {
					let ageElem = document.getElementById("age-$age");
					ageElem.innerHTML= getAge($age);
				})();	
			</script> 
			<a class="reddit-link" href="$reddit_link"> $subreddit</a></p>
		</div>
		'''
	)

	footer = '''
		<footer>
			Copyright &copy; <span id="year"></span> <a class="twitter-bio" href="https://twitter.com/JoeCharMar">@joecharmar</a>
		</footer>

		<script>
		
			let date = new Date();
			let year = date.getFullYear();
			let tag = document.getElementById("year");
			tag.innerHTML= year;

			(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
			(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
			m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
			})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

			ga('create', 'UA-105838046-1', 'auto');
			ga('send', 'pageview');

		</script>

			</body>
		</html>
	'''

	html = ""

	html += header

	for book in books:
		subreddit = extract_subreddit(book['reddit_link']['S'])
		# Formatting requires using an extra key to retrieve the raw text that depends on the type
		row = row_template.substitute(
			title=book['title']['S'],
			author=book['author']['S'],
			reddit_link=book['reddit_link']['S'],
			amz_url=book['amz_url']['S'],
			image=book['image']['S'],
			subreddit=subreddit,
			age=book['timestamp']['N'],
		)
		html += row

	html += footer
	
	object = s3.Object('reddl.it', 'index.html')
	response = object.put(
		Body=html,
		ContentType="text/html",
	)

	return "Site Successfully Updated!"

if __name__ == '__main__':
	update_site()