import os
import logging
import time
import redis
import psycopg2

def connect_to_redis():
    while True:
        try:
            redis_conn = redis.Redis(host=os.getenv('REDIS_HOST'), 
                                     port=os.getenv('REDIS_PORT'), 
                                     password=os.getenv('REDIS_PASSWORD'), 
                                     db=0)
            redis_conn.ping()
            logging.info("Connected to Redis")
            return redis_conn
        
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logging.error(f"Redis Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def connect_to_postgres():
    while True:
        try:
            conn = psycopg2.connect(
                                host=os.getenv('POSTGRES_HOST'),  
                                port=os.getenv('POSTGRES_PORT'),
                                user=os.getenv('POSTGRES_USER'),   
                                password=os.getenv('POSTGRES_PASSWORD'),
                                database=os.getenv('POSTGRES_DB')
                            )
            logging.info("Connected to Postgres")
            return conn

        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logging.error(f"Postgres Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)