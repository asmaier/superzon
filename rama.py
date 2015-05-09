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
	query = request.args.get("q","*")

	amazon = AmazonAPI(app.config["AMAZON_ACCESS_KEY"], app.config["AMAZON_SECRET_KEY"], app.config["AMAZON_ASSOC_TAG"], region=region.upper())
	products = amazon.search(Keywords=query, SearchIndex=category.capitalize())

	results = []
	response = """
	<!DOCTYPE html>
	<html lang="en">
 	<head>
		<meta charset="utf-8">
    	<title>RAMA</title>
  	</head>
  	<body>
	"""

	for i, product in enumerate(products):
		url = product.reviews[1]
		rp = requests.get(product.reviews[1], timeout=10)
		soup = BeautifulSoup(rp.content)
		try:
			# print url
			# print soup.find_all("img") 
			avg_rating = float(soup.find_all("img")[1]["title"].split()[0])

			# print soup.b.text
			reviews = int(soup.b.text.split()[0].replace(",","").replace(".",""))

			score = bayesian_average(avg_rating, reviews)
			
			results.append((score, reviews, avg_rating, product.title, product.price_and_currency, product.offer_url, product.small_image_url))
			# response += "<p>%d,%d,%f,%s</p>" % (i, reviews, avg_rating, product.title)
		except (IndexError, KeyError) as e:
			pass
			# response += "<p>%s</p>" % e
			# response += "<p>%d,%s</p>" % (i, product.title)

	for i, (score, reviews, rating, title, price, url, image_url) in enumerate(sorted(results, reverse=True)):
		response += '<p><a href="%s"><img src="%s" alt="%s" />%s</a>%s<meter max="5.0" min="0.0" value="%f">%f</meter></p>' % (url, image_url, title, title, price,score, score)  	

	response += "</body></html>"	
	return response	

if __name__ == "__main__":
    app.run()

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


