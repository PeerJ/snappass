import os
import uuid
import yaml
import redis

from flask import abort, Flask, render_template, request

config = dict()
config['NO_SSL'] = os.environ.get('NO_SSL', False)
config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Secret Key')
config['STATIC_URL'] = os.environ.get('STATIC_URL', 'static')
config['REDIS_HOST'] = os.environ.get('REDIS_HOST', 'localhost')
config['REDIS_PORT'] = os.environ.get('REDIS_PORT', 6379)
config['REDIS_DB'] = os.environ.get('REDIS_DB', 0)
config['REDIS_PASSWORD'] = os.environ.get('REDIS_PASSWORD', None)

CONFIG_FILE = os.environ.get('SNAPPASS_CONFIG', None)
if CONFIG_FILE and os.path.isfile(CONFIG_FILE):
    config_data = open(CONFIG_FILE)
    # merge dictionaries - prefer config file settings if present
    config = dict(config.items() + yaml.load(config_data).items())
    config_data.close()

app = Flask(__name__)
app.secret_key = config['SECRET_KEY']
app.config.update(dict(STATIC_URL=config['STATIC_URL']))

id_ = lambda: uuid.uuid4().hex
redis_client = redis.StrictRedis(host=config['REDIS_HOST'],
                                 port=config['REDIS_PORT'],
                                 db=config['REDIS_DB'],
                                 password=config['REDIS_PASSWORD'])

time_conversion = {
    'week': 604800,
    'day': 86400,
    'hour': 3600
}


def set_password(password, ttl):
    key = id_()
    redis_client.set(key, password)
    redis_client.expire(key, ttl)
    return key


def get_password(key):
    password = redis_client.get(key)
    redis_client.delete(key)
    return password


def clean_input():
    """
    Make sure we're not getting bad data from the front end,
    format data to be machine readable
    """
    if not 'password' in request.form:
        abort(400)

    if not 'ttl' in request.form:
        abort(400)

    time_period = request.form['ttl'].lower()
    if not time_period in time_conversion:
        abort(400)

    return time_conversion[time_period], request.form['password']


@app.route('/', methods=['GET'])
def index():
    return render_template('set_password.html')


@app.route('/', methods=['POST'])
def handle_password():
    ttl, password = clean_input()
    key = set_password(password, ttl)

    if config['NO_SSL']:
        base_url = request.url_root
    else:
        base_url = request.url_root.replace("http://", "https://")
    link = base_url + key
    return render_template('confirm.html', password_link=link)


@app.route('/<password_key>', methods=['GET'])
def show_password(password_key):
    password = get_password(password_key)
    if not password:
        abort(404)

    return render_template('password.html', password=password)


def main():
    app.run(host='0.0.0.0', debug=True)


if __name__ == '__main__':
    main()
