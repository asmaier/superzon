#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########
## RAMA 
## - Reranking amazon search results since 2015 -
##########

import argparse
import requests
from bs4 import BeautifulSoup
from amazon.api import AmazonAPI

from flask import Flask
from flask import request
app = Flask(__name__)
app.config.from_object("config")
app.debug = True

# We assume that if no votes are given, that
# the product is rated by prior_weight people with a 
# average rating of prior_avg_rating
prior_weight = 10
prior_avg_rating = 3

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/help")
def help():
	return """
	Finds the true bayesian ranking of items from Amazon.

	/<region>/<category>/q=<query>

	<query> : Search query for Amazon
	<region> : An amazon region from ['US', 'FR', 'CN', 'UK', 'IN', 'CA', 'DE', 'JP', 'IT', 'ES']
	<category> : An amazon category from ['All','Apparel','Appliances','ArtsAndCrafts','Automotive','Baby','Beauty','Blended','Books','Classical','Collectibles','DVD','DigitalMusic','Electronics','ForeignBooks','GiftCards','GourmetFood','Grocery','HealthPersonalCare','Hobbies','HomeGarden','HomeImprovement','Industrial','Jewelry','KindleStore','Kitchen','LawnAndGarden','Lighting','Luggage','Marketplace','MP3Downloads','Magazines','Miscellaneous','MobileApps','Music','MusicTracks','MusicalInstruments','OfficeProducts','OutdoorLiving','Outlet','PCHardware','PetSupplies','Photo','Shoes','Software','SoftwareVideoGames','SportingGoods','Tools','Toys','UnboxVideo','VHS','Video','VideoDownload','VideoGames','Watches','Wireless','WirelessAccessories']
	"""


@app.route("/<region>/<category>")
def rerank(region, category):
	query = request.args.get("q","*")

	print app.config["AMAZON_ACCESS_KEY"]
	print app.config["AMAZON_SECRET_KEY"]
	print app.config["AMAZON_ASSOC_TAG"] 

	amazon = AmazonAPI(app.config["AMAZON_ACCESS_KEY"], app.config["AMAZON_SECRET_KEY"], app.config["AMAZON_ASSOC_TAG"], region=region)

	products = amazon.search(Keywords=query, SearchIndex=category)

	print products
	results = []

	response = ""

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

			# see also http://en.wikipedia.org/wiki/Bayes_estimator#Practical_example_of_Bayes_estimators
			bayesian_average = (reviews * avg_rating + prior_weight * prior_avg_rating)/(reviews + prior_weight)
			
			results.append((bayesian_average, reviews, avg_rating, product.title))
			response += "%d,%d,%f,%s" % (i, reviews, avg_rating, product.title)
		except (IndexError, KeyError) as e:
			response += "%s" % e
			response += "%d,%s" % (i, product.title)

	for i, result in enumerate(sorted(results, reverse=True)):
		response += "%d,%s" % (i, result)  	

	return response	

if __name__ == "__main__":
    app.run()


