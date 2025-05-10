import redis

# Default Redis connection parameters
# These should ideally match how your FastAPI app connects to Redis (db 0 for login_number)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

def get_redis_client():
    """
    Establishes a synchronous connection to Redis and returns a client instance.

    Returns:
        redis.Redis: A Redis client instance if connection is successful.
        None: If the connection fails.
    """
    try:
        # decode_responses=True will ensure that get() returns strings instead of bytes
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()  # Check if the connection is successful
        print("Successfully connected to Redis.")
        return r
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred with Redis: {e}")
        return None