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

# We assume that if no votes are given, that
# the product is rated by prior_weight people with a 
# average rating of prior_avg_rating
prior_weight = 10
prior_avg_rating = 3


parser = argparse.ArgumentParser(description="Finds the true bayesian ranking of items from Amazon.")
parser.add_argument("search_query", action="store", help="Search query for Amazon")
parser.add_argument("--region", action="store", default="DE", help="An amazon region from ['US', 'FR', 'CN', 'UK', 'IN', 'CA', 'DE', 'JP', 'IT', 'ES']")
parser.add_argument("--category", action="store", default="All", help="An amazon category from ['All','Apparel','Appliances','ArtsAndCrafts','Automotive','Baby','Beauty','Blended','Books','Classical','Collectibles','DVD','DigitalMusic','Electronics','ForeignBooks','GiftCards','GourmetFood','Grocery','HealthPersonalCare','Hobbies','HomeGarden','HomeImprovement','Industrial','Jewelry','KindleStore','Kitchen','LawnAndGarden','Lighting','Luggage','Marketplace','MP3Downloads','Magazines','Miscellaneous','MobileApps','Music','MusicTracks','MusicalInstruments','OfficeProducts','OutdoorLiving','Outlet','PCHardware','PetSupplies','Photo','Shoes','Software','SoftwareVideoGames','SportingGoods','Tools','Toys','UnboxVideo','VHS','Video','VideoDownload','VideoGames','Watches','Wireless','WirelessAccessories']")
args=parser.parse_args()

amazon = AmazonAPI("","", "", region=args.region)

products = amazon.search(Keywords=args.search_query, SearchIndex=args.category)

results = []

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
		print i, reviews, avg_rating, product.title
	except (IndexError, KeyError) as e:
		print e
		print i, product.title

		
	

for i, result in enumerate(sorted(results, reverse=True)):
	print i, result  	