import os
import sys
import configparser
import logging
import json
from datetime import datetime
import redis
import psycopg2
from psycopg2 import sql
from connection import connect_to_redis, connect_to_postgres

class upbit_dataloader:
    def __init__(self, dataloader_name: str):
        # log setting
        log_directory = "/CryptoStream/logs/dataloader"  
        log_filename = f"{dataloader_name}.log"  
        log_file_path = os.path.join(log_directory, log_filename)

        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        logging.basicConfig(
            level=logging.INFO,  
            format='%(asctime)s - %(levelname)s - %(message)s',  
            filename=log_file_path, 
            filemode='a' # a: append
        )

        # read conf
        config = configparser.ConfigParser()
        config.read('/CryptoStream/conf/dataloader.conf')

        # variables
        self.dataloader_name = dataloader_name
        self.q = config.get(dataloader_name,'queue')
        self.commit_count = config.get(dataloader_name,'commit_count')
        self.commit_count = int(self.commit_count)

        logging.info(f"{self.dataloader_name} queue: {self.q}")
        logging.info(f"{self.dataloader_name} commit count: {self.commit_count}")

    def transform_data(self, up_data: dict[str, any]) -> dict:
        return_dict = {'timestamp': up_data['tms'] / 1000,
                       'up_bid_price': up_data['obu'][0]['bp'],
                       'up_bid_vol': up_data['obu'][0]['bs'],
                       'up_ask_price': up_data['obu'][0]['ap'],
                       'up_ask_vol': up_data['obu'][0]['as']
                      }

        return return_dict

    def redis_to_postgres(self):
        pg_conn = connect_to_postgres()
        cursor = pg_conn.cursor()
        insert_count = 0
        
        redis_conn = connect_to_redis()
        
        while True:
            try:
                if redis_conn.llen(self.q) > 0:
                    # get data
                    up_data = redis_conn.rpop(self.q) 
                    up_data = json.loads(up_data)
                    ticker = up_data['cd'][4:]
                    up_data = self.transform_data(up_data)

                    # insert data
                    dt_object = datetime.fromtimestamp(up_data['timestamp'])
                    timestamp_date = dt_object.strftime('%Y%m%d')

                    insert_query = f"""
                        INSERT INTO {ticker}_upbit_{timestamp_date} (
                            timestamp, 
                            up_bid_price, 
                            up_bid_vol, 
                            up_ask_price, 
                            up_ask_vol) 
                        VALUES (%s, %s, %s, %s, %s)
                        """
                    insert_query = sql.SQL(insert_query)
                    cursor.execute(insert_query, (up_data['timestamp'], 
                                                up_data['up_bid_price'], 
                                                up_data['up_bid_vol'], 
                                                up_data['up_ask_price'], 
                                                up_data['up_ask_vol']
                                                ))
                    insert_count += 1

                    # commit
                    if insert_count % self.commit_count == 0:
                        pg_conn.commit()
                        insert_count = 0
                        #logging.info(f"Commit complete: {self.commit_count} records added")
                        
            except psycopg2.errors.UndefinedTable:
                # create table
                pg_conn.rollback()

                create_table_query = f"""
                CREATE TABLE IF NOT EXISTS {ticker}_upbit_{timestamp_date} (
                    timestamp NUMERIC(20, 5) PRIMARY KEY,
                    up_bid_price NUMERIC(20, 10),
                    up_bid_vol NUMERIC(20, 10),
                    up_ask_price NUMERIC(20, 10),
                    up_ask_vol NUMERIC(20, 10)
                );
                """
                create_table_query=sql.SQL(create_table_query)

                cursor.execute(create_table_query)
                pg_conn.commit()

                logging.info(f"Create {ticker} table")

                # insert data
                cursor.execute(insert_query, (up_data['timestamp'], 
                                                up_data['up_bid_price'], 
                                                up_data['up_bid_vol'], 
                                                up_data['up_ask_price'], 
                                                up_data['up_ask_vol']
                                                ))
                insert_count += 1

                # commit
                if insert_count % self.commit_count == 0:
                    pg_conn.commit()
                    insert_count = 0
                    #logging.info(f"Commit complete: {self.commit_count} records added")
            
            except (psycopg2.DatabaseError, psycopg2.OperationalError) as e:
                logging.error(f"Transaction error: {e}")
                pg_conn.rollback()
                insert_count = 0

            except (redis.ConnectionError, redis.TimeoutError) as e:
                logging.error(f"Redis Connection failed: {e}")
                redis_conn = connect_to_redis()

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logging.error(f"Postgres Connection failed: {e}")
                
                pg_conn = connect_to_postgres()
                cursor = pg_conn.cursor()
                insert_count = 0

            except Exception as e:                
                logging.error(f"upbit dataloader error: {e}")

    def run(self):
        self.redis_to_postgres()

if __name__ == '__main__':
    upbit_dataloader(sys.argv[1]).run()