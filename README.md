After git checkout:

1. Install heroku toolbelt: 
https://devcenter.heroku.com/articles/heroku-command-line
2. Install python requirements
$ pip install -r requirements.txt
(see https://devcenter.heroku.com/articles/getting-started-with-python#declare-app-dependencies)
3. Install redis
$ brew install redis
4. Start redis
$ sh start_redis.sh
5. Start the app
$ python rama.py
6. Open in browser
$ open localhost:8080
