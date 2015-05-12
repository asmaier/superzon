#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########
## RAMA 
## - Reranking Amazon search results since 2015 -
##########

import os
import time
import argparse
import json

import requests
import concurrent.futures as futures
import lxml.html as lh
from amazon.api import AmazonAPI
import redis

from flask import Flask
from flask import request
from flask import Response

app = Flask(__name__)

app.debug = False

# we are not at heroku
if not 'DYNO' in os.environ: 
	app.debug=True
	app.config.from_object("config")
	KEY = app.config["AMAZON_ACCESS_KEY"] 
	SECRET = app.config["AMAZON_SECRET_KEY"] 
	TAG = app.config["AMAZON_ASSOC_TAG"]
else:
	KEY = os.environ.get("AMAZON_ACCESS_KEY")
	SECRET = os.environ.get("AMAZON_SECRET_KEY")
	TAG = os.environ.get("AMAZON_ASSOC_TAG")	

print KEY, SECRET, TAG	

# We assume that if no votes are given, that
# the product is rated by prior_weight people with a 
# average rating of prior_avg_rating
prior_weight = 10
prior_avg_rating = 3

TTL = 86400  # 24 * 3600s = 1d
r_server = redis.Redis("localhost")

redis_on = False
try:
	r_server.ping()
	redis_on = True
except redis.ConnectionError:
	print "Redis is not available!"	

def bayesian_average(avg_rating, reviews):
	# see also http://en.wikipedia.org/wiki/Bayes_estimator#Practical_example_of_Bayes_estimators
	return (reviews * avg_rating + prior_weight * prior_avg_rating)/(reviews + prior_weight)

def convert_to_json(product):
	return json.dumps({
		"title" : product.title,
		"url" : product.offer_url,
		"image_url" : product.small_image_url,
		"reviews_url" : product.reviews[1]})

def extract_rating_data(url):
	try:
		# iframe_time = time.time()

		content = None
		if redis_on:
			content = r_server.get(url)
		if not content:
			# print "Cache miss!" 
			rp = requests.get(url, timeout=10)
			content = rp.content
			if redis_on:
				r_server.setex(url, content, TTL)

		# print "download iframe time:", time.time() - iframe_time	

		# parse_time = time.time()
		tree = lh.fromstring(content)
		# find the first image with title attribute
		avg_rating = float(tree.xpath(".//img/@title")[0].split()[0])
		# get text of first <b> tag
		# replace "," and "." to allow conversion to int
		reviews = int(tree.xpath(".//b")[0].text.split()[0].replace(",","").replace(".",""))
		# print "parse time:", time.time() - parse_time
		return (avg_rating, reviews)
	except (IndexError, KeyError, requests.exceptions.RequestException) as e:
		return (0.0, 0)

def write_query_to_db(cache_url, data):
	r_server.setex(cache_url, data, TTL)

def read_query_from_db(cache_url):
	return r_server.get(cache_url)	
			
@app.route("/")
def hello():
    return "RAMA - Reranking Amazon search results since 2015!"

@app.route("/help")
def help():
	return """
	Finds the true bayesian ranking of items from Amazon.

	/<region>/<category>/q=<query>

	<query> : Search query for Amazon
	<region> : An amazon region from ['US', 'FR', 'CN', 'UK', 'IN', 'CA', 'DE', 'JP', 'IT', 'ES']
	<category> : An amazon category from ['All','Apparel','Appliances','ArtsAndCrafts','Automotive','Baby','Beauty','Blended','Books','Classical','Collectibles','DVD','DigitalMusic','Electronics','ForeignBooks','GiftCards','GourmetFood','Grocery','HealthPersonalCare','Hobbies','HomeGarden','HomeImprovement','Industrial','Jewelry','KindleStore','Kitchen','LawnAndGarden','Lighting','Luggage','Marketplace','MP3Downloads','Magazines','Miscellaneous','MobileApps','Music','MusicTracks','MusicalInstruments','OfficeProducts','OutdoorLiving','Outlet','PCHardware','PetSupplies','Photo','Shoes','Software','SoftwareVideoGames','SportingGoods','Tools','Toys','UnboxVideo','VHS','Video','VideoDownload','VideoGames','Watches','Wireless','WirelessAccessories']
	"""

@app.route("/search/<region>/<category>")
def search(region, category):
	query = request.args.get("q","*")

	amazon = AmazonAPI(KEY, SECRET, TAG, Region=region.upper())
	products = amazon.search(Keywords=query, SearchIndex=category.capitalize())

	js = json.dumps([convert_to_json(product) for product in products])
	resp = Response(js, status=200, mimetype='application/json')

	return resp

@app.route("/<region>/<category>")
def rerank(region, category):
	starttime = time.time()
	print region, category
	query = request.args.get("q","*")

	cache_reader = None
	cache_writer = None
	if redis_on:
		cache_reader = read_query_from_db
		cache_writer = write_query_to_db

	search_start=time.time()
	amazon = AmazonAPI(KEY, SECRET, TAG, Region=region.upper(), CacheReader=cache_reader, CacheWriter=cache_writer)
	amazon_results_iterator = amazon.search(Keywords=query, SearchIndex=category)
	# convert the iterator to a list so we can loop through it multiple times
	# see http://stackoverflow.com/questions/3266180/can-iterators-be-reset-in-python
	products = list(amazon_results_iterator)
	print "search time: ", time.time() - search_start

	results = []
	html = """
	<!DOCTYPE html>
	<html lang="en">
 	<head>
		<meta charset="utf-8">
    	<title>RAMA</title>
  	</head>
  	<body>
	"""
	
	worker_start = time.time()
	with futures.ThreadPoolExecutor(max_workers=32) as executor:
		ratings = list(executor.map(extract_rating_data, [product.reviews[1] for product in products]))
	# ratings = list(map(extract_rating_data, [product.reviews[1] for product in products]))	
	print "process time:", time.time() - worker_start

	for i, product in enumerate(products):
		avg_rating, reviews = ratings[i]
		score = bayesian_average(avg_rating, reviews)
		
		results.append((score, reviews, avg_rating, product.title, product.price_and_currency, product.offer_url, product.small_image_url))

	for i, (score, reviews, rating, title, price, url, image_url) in enumerate(sorted(results, reverse=True)):
		# Aaargh!! This cost me hours to figure it out:
		# <img src="None"/> causes the browser to call http://127.0.0.1:8080/DE/None leading to weird errors
		# So better replace "None" with an empty string
		if not image_url:
			image_url = ""
		html += '<p><a href="%s"><img src="%s" alt="%s" />%s</a>%s<meter max="5.0" min="1.0" value="%f"></meter>%s, Reviews: %s</p>' % (url, image_url, title, title, price,score, score, reviews)  	

	html += "</body></html>"

	resp = Response(html, status=200, mimetype='text/html')

	print "response time: ", time.time() - starttime

	return resp

if __name__ == "__main__":
	# default flask port 5000 is used by Airplay on OS X
	# see http://stackoverflow.com/questions/26668294/airplay-messes-up-localhost
    app.run(port=8080)

# <div class="container">


#   <div class="meter-slim">
#     <span class="purple" style="width: 85%"></span>
#   </div>

# </div>

# .container {
#   width: 150px;
#   margin-left: auto;
#   margin-right: auto;
# }

# .meter-slim {
#   background-color: #ebebeb;
#   height: 15px;
#   border-color: #dedede;
#   border-style: solid;
#   border-width: 1px;
# }

# .meter-slim .purple {
#   display: block;
#   height: 100%;
#   background-color: #b300ff;
# }    


