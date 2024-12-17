import os
import sys
import configparser
import logging
import json
from datetime import datetime, timedelta
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

        # connection DB
        self.pg_conn = connect_to_postgres()
        self.cursor = self.pg_conn.cursor()
        self.redis_conn = connect_to_redis()

    def transform_data(self, up_data: dict[str, any]) -> dict:
        timestamp = up_data['tms'] / 1000

        dt_object = datetime.fromtimestamp(timestamp)
        timestamp_date = dt_object.strftime('%Y%m%d')

        next_dt_object = dt_object + timedelta(days=1)
        timestamp_next_date = next_dt_object.strftime('%Y%m%d')
    
        return_dict = {'ticker': up_data['cd'][4:],
                       'timestamp': timestamp,
                       'timestamp_date': timestamp_date,
                       'timestamp_next_date': timestamp_next_date,
                       'orderbook': up_data['obu']
                      }

        return return_dict

    def create_table(self, ticker: str):
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {ticker}_upbit_orderbook (
            timestamp NUMERIC(20, 5),
            event_date DATE,
            up_bid_price1 NUMERIC(20, 10),
            up_bid_vol1 NUMERIC(20, 10),
            up_ask_price1 NUMERIC(20, 10),
            up_ask_vol1 NUMERIC(20, 10),
            up_bid_price2 NUMERIC(20, 10),
            up_bid_vol2 NUMERIC(20, 10),
            up_ask_price2 NUMERIC(20, 10),
            up_ask_vol2 NUMERIC(20, 10),
            up_bid_price3 NUMERIC(20, 10),
            up_bid_vol3 NUMERIC(20, 10),
            up_ask_price3 NUMERIC(20, 10),
            up_ask_vol3 NUMERIC(20, 10),
            up_bid_price4 NUMERIC(20, 10),
            up_bid_vol4 NUMERIC(20, 10),
            up_ask_price4 NUMERIC(20, 10),
            up_ask_vol4 NUMERIC(20, 10),
            up_bid_price5 NUMERIC(20, 10),
            up_bid_vol5 NUMERIC(20, 10),
            up_ask_price5 NUMERIC(20, 10),
            up_ask_vol5 NUMERIC(20, 10),
            PRIMARY KEY (timestamp, event_date) 
        ) PARTITION BY RANGE (event_date);
        """
        create_table_query=sql.SQL(create_table_query)

        self.cursor.execute(create_table_query)
        self.pg_conn.commit()

        logging.info(f"Create table: {ticker}_upbit_orderbook")

    def create_partition(self, up_data: dict):
        ticker = up_data['ticker']
        timestamp_date = up_data['timestamp_date']
        timestamp_next_date = up_data['timestamp_next_date']

        create_partition_query = f"""
        CREATE TABLE IF NOT EXISTS {ticker}_upbit_orderbook_{timestamp_date}
        PARTITION OF {ticker}_upbit_orderbook 
        FOR VALUES FROM (%s) TO (%s);
        """
        create_partition_query=sql.SQL(create_partition_query)

        self.cursor.execute(create_partition_query, (timestamp_date, timestamp_next_date))
        self.pg_conn.commit()

        logging.info(f"Create partition: {ticker}_upbit_orderbook_{timestamp_date}")

    def insert_data(self, up_data: dict, insert_count: int) -> int:        
        insert_query = f"""
        INSERT INTO {up_data['ticker']}_upbit_orderbook (
            timestamp, 
            event_date,
            up_bid_price1, up_bid_vol1, up_ask_price1, up_ask_vol1,
            up_bid_price2, up_bid_vol2, up_ask_price2, up_ask_vol2,
            up_bid_price3, up_bid_vol3, up_ask_price3, up_ask_vol3,
            up_bid_price4, up_bid_vol4, up_ask_price4, up_ask_vol4,
            up_bid_price5, up_bid_vol5, up_ask_price5, up_ask_vol5
            ) 
        VALUES (%s, 
                %s, 
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s)
        """
        insert_query = sql.SQL(insert_query)
        self.cursor.execute(insert_query, (up_data['timestamp'],
                                            up_data['timestamp_date'],
                                            up_data['orderbook'][0]['bp'], up_data['orderbook'][0]['bs'], up_data['orderbook'][0]['ap'], up_data['orderbook'][0]['as'],
                                            up_data['orderbook'][1]['bp'], up_data['orderbook'][1]['bs'], up_data['orderbook'][1]['ap'], up_data['orderbook'][1]['as'],
                                            up_data['orderbook'][2]['bp'], up_data['orderbook'][2]['bs'], up_data['orderbook'][2]['ap'], up_data['orderbook'][2]['as'],
                                            up_data['orderbook'][3]['bp'], up_data['orderbook'][3]['bs'], up_data['orderbook'][3]['ap'], up_data['orderbook'][3]['as'],
                                            up_data['orderbook'][4]['bp'], up_data['orderbook'][4]['bs'], up_data['orderbook'][4]['ap'], up_data['orderbook'][4]['as']
                                            ))
        insert_count += 1

        # commit
        if insert_count % self.commit_count == 0:
            self.pg_conn.commit()
            insert_count = 0
            #logging.info(f"Commit complete: {self.commit_count} records added")

        return insert_count

    def main(self):
        insert_count = 0
                
        while True:
            try:
                if self.redis_conn.llen(self.q) > 0:
                    # get data
                    up_data = self.redis_conn.rpop(self.q) 
                    up_data = json.loads(up_data)
                    up_data = self.transform_data(up_data)

                    # insert data
                    insert_count = self.insert_data(up_data, insert_count)
                        
            except psycopg2.errors.UndefinedTable:
                self.pg_conn.rollback()

                # create table
                self.create_table(up_data['ticker'])

                # create partition
                self.create_partition(up_data)

                # insert data
                insert_count = self.insert_data(up_data, insert_count)
            
            except psycopg2.IntegrityError as e:
                if "no partition of relation" in str(e):
                    self.pg_conn.rollback()  
                    
                    # create partition
                    self.create_partition(up_data)
 
                    # insert data
                    insert_count = self.insert_data(up_data, insert_count)

                else:
                    logging.error(f"upbit dataloader error: {e}")

            except (psycopg2.DatabaseError, psycopg2.OperationalError) as e:
                logging.error(f"Transaction error: {e}")
                self.pg_conn.rollback()
                insert_count = 0

            except (redis.ConnectionError, redis.TimeoutError) as e:
                logging.error(f"Redis Connection failed: {e}")
                self.redis_conn = connect_to_redis()

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logging.error(f"Postgres Connection failed: {e}")
                self.pg_conn = connect_to_postgres()
                self.cursor = self.pg_conn.cursor()
                insert_count = 0

            except Exception as e:                
                logging.error(f"upbit dataloader error: {e}")

    def run(self):
        self.main()

if __name__ == '__main__':
    upbit_dataloader(sys.argv[1]).run()