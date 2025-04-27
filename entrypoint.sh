#!/bin/bash
# entrypoint.sh

# Apply database migrations
echo "Waiting for database..."
python -c "
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import os

db_uri = os.environ.get('DATABASE_URL')
engine = create_engine(db_uri)

# Try to connect to the database
max_retries = 30
retries = 0
while retries < max_retries:
    try:
        connection = engine.connect()
        connection.close()
        print('Database is ready!')
        break
    except OperationalError:
        retries += 1
        print(f'Database connection attempt {retries}/{max_retries} failed. Retrying in 1 second...')
        time.sleep(1)

if retries == max_retries:
    print('Could not connect to database. Exiting...')
    exit(1)
"

# Check Redis connection
echo "Checking Redis connection..."
python -c "
import redis
import time
import os

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
print(f'Connecting to Redis at {redis_url}')

# Extract host and port from redis_url
if '://' in redis_url:
    redis_url = redis_url.split('://')[1]
if '@' in redis_url:
    redis_url = redis_url.split('@')[1]
host = redis_url.split(':')[0]
if '/' in redis_url.split(':')[1]:
    port = redis_url.split(':')[1].split('/')[0]
else:
    port = redis_url.split(':')[1]

print(f'Extracted Redis host: {host}, port: {port}')

# Try to connect to Redis
max_retries = 30
retries = 0
while retries < max_retries:
    try:
        r = redis.Redis(host=host, port=int(port), socket_connect_timeout=5)
        r.ping()
        print('Redis is ready!')
        break
    except redis.exceptions.ConnectionError:
        retries += 1
        print(f'Redis connection attempt {retries}/{max_retries} failed. Retrying in 1 second...')
        time.sleep(1)

if retries == max_retries:
    print('Could not connect to Redis. Services may not work correctly!')
"

# Initialize database
python -c "
from database import init_db
init_db()
print('Database initialized!')
"

# Execute the main command
exec "$@"
