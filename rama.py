#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########
## RAMA 
## - Reranking Amazon search results since 2015 -
##########

import argparse
import requests
from bs4 import BeautifulSoup
from amazon.api import AmazonAPI

from flask import Flask
from flask import request
from flask import Response
import json
import futures
app = Flask(__name__)
app.config.from_object("config")
app.debug = True

# We assume that if no votes are given, that
# the product is rated by prior_weight people with a 
# average rating of prior_avg_rating
prior_weight = 10
prior_avg_rating = 3

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
		print url
		rp = requests.get(url, timeout=10)
		soup = BeautifulSoup(rp.content) 
		avg_rating = float(soup.find_all("img")[1]["title"].split()[0])
		reviews = int(soup.b.text.split()[0].replace(",","").replace(".",""))
		return (avg_rating, reviews)
	except (IndexError, KeyError, requests.exceptions.RequestException) as e:
		return (0.0, 0)
			
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

	amazon = AmazonAPI(app.config["AMAZON_ACCESS_KEY"], app.config["AMAZON_SECRET_KEY"], app.config["AMAZON_ASSOC_TAG"], region=region.upper())
	products = amazon.search(Keywords=query, SearchIndex=category.capitalize())

	js = json.dumps([convert_to_json(product) for product in products])
	resp = Response(js, status=200, mimetype='application/json')

	return resp

@app.route("/<region>/<category>")
def rerank(region, category):
	print region, category
	query = request.args.get("q","*")

	amazon = AmazonAPI(app.config["AMAZON_ACCESS_KEY"], app.config["AMAZON_SECRET_KEY"], app.config["AMAZON_ASSOC_TAG"], region=region.upper())
	amazon_results_iterator = amazon.search(Keywords=query, SearchIndex=category.capitalize())

	# convert the iterator to a list so we can loop through it multiple times
	# see http://stackoverflow.com/questions/3266180/can-iterators-be-reset-in-python
	products = list(amazon_results_iterator)

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
	
	with futures.ProcessPoolExecutor(max_workers=10) as executor:
		ratings = list(executor.map(extract_rating_data, [product.reviews[1] for product in products]))

	# ratings = list(map(extract_rating_data, [product.reviews[1] for product in products]))	

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
		html += '<p><a href="%s"><img src="%s" alt="%s" />%s</a>%s<meter max="5.0" min="0.0" value="%f">%f</meter></p>' % (url, image_url, title, title, price,score, score)  	

	html += "</body></html>"

	resp = Response(html, status=200, mimetype='text/html')

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


