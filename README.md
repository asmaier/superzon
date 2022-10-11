#### ARCHIVED: This project used to be hosted at https://superzon.herokuapp.com/ . Since Amazon made crawling their website increasingly difficult and they also introduced new ranking algorithms, this project became obsolete. This repository here is just an archive of the code. 

# Superzon 

Superzon can be used to find the really best products on Amazon. It does that by reranking the Amazon search results using a bayesian average of the reviews taking the number of reviewers into account. It is implemented as a small webservice written with Flask in Python and deployed on Heroku.

## Developement 

After git checkout:

1. Install heroku toolbelt, see https://devcenter.heroku.com/articles/heroku-command-line
2. Install python requirements, see https://devcenter.heroku.com/articles/getting-started-with-python#declare-app-dependencies

    $ python3 -m venv env-superzon
    $ source env-superzon/bin/activate
    $ pip3 install -r requirements.txt

3. Install redis


    $ brew install redis
4. Start redis


    $ sh start_redis.sh
5. Start the app (see https://devcenter.heroku.com/articles/getting-started-with-python#run-the-app-locally)


    $ heroku local web  # using heroku configuration
    or
    $ python superzon.py
6. Open in browser


    $ open localhost:8080


To shutdown redis use `redis-cli shutdown`.
