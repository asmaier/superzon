After git checkout:

1. Install heroku toolbelt, see https://devcenter.heroku.com/articles/heroku-command-line
2. Install python requirements, see https://devcenter.heroku.com/articles/getting-started-with-python#declare-app-dependencies


    $ pip install -r requirements.txt

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
