#!/usr/local/bin/python3
import sys
import os
import preprocessor as p
import emoji
from get_user_tweets import write_to_file
from tweet_config import * 
import pandas as pd
import tweepy

class Retweet_Grabber(object):
	def __init__(self, screen_name, num_to_collect=74, *args, **kwargs):
	
		self.num_to_collect = num_to_collect
		self.screen_name = screen_name	
		retweet_df = self.get_old_retweets	
		self.tweet_ids = pd.read_csv("../data/{}_data.csv".format(screen_name)).head(num_to_collect)
		# TODO get old retweet df, get tweet df, remove tweet ids from tweet df if they've already
		#		been collected	

	def get_old_retweets(self):
		file_path = "../data/{}_retweets.csv".format(self.screen_name)
		exists = os.path.exists(file_path)
		if exists:
			return pd.read_csv(file_path)
		return None

	def put_tweets(self):
		screen_name = self.screen_name
		file_path = "../data/{}_retweets.csv".format(screen_name)
		try:
			os.remove(file_path)
		except:
			pass
		retweets_df = self.get_user_retweets()
		write_to_file(file_path,retweets_df)
		print("--- done for {} ---".format(screen_name))

	def get_user_retweets(self):
		screen_name = self.screen_name
		num_to_collect = self.num_to_collect
		retweet_df = pd.DataFrame(columns=RETWEET_COLS)
		for index, row in self.tweet_ids.iterrows():
			tweet_id = row['id']
			print("--- Getting retweet {} of {}, ID: {} ---".format(index, self.tweet_ids.shape[0],tweet_id))
			retweets = self.get_retweets(tweet_id)
			retweet_df = retweet_df.append(retweets)
		retweet_df.drop(retweet_df.loc[retweet_df['original_author']==screen_name].index, inplace=True)
		return retweet_df
	

	# TODO Find way to get more than 100 retweets
	def get_retweets(self,tweet_id):
		#Twitter only allows access to a users most recent 3240 tweets with this method
		#authorize twitter, initialize tweepy
		num_tweets	= 100
		tweets 		= api.retweets(id=tweet_id,count=num_tweets,tweet_mode='extended')
		retweet_df = pd.DataFrame(columns=RETWEET_COLS)
		for tweet in tweets:
			tweet_df 	= self.clean_retweet(tweet,tweet_id)
			retweet_df = retweet_df.append(tweet_df, ignore_index=True)
		return retweet_df

	def clean_retweet(self,tweet_obj,tweet_id):
		cleaned_tweet 	= []
		tweet			= tweet_obj._json
		cleaned_tweet 	+= [tweet_id,tweet['id'],'retweet', tweet['created_at'],tweet['source'],tweet['favorite_count'], tweet['retweet_count']]
		cleaned_tweet.append(tweet['user']['screen_name'])
		single_tweet_df = pd.DataFrame([cleaned_tweet], columns=RETWEET_COLS)
		return single_tweet_df

		

if __name__ == '__main__':
	usernames = sys.argv[1:]
	for username in usernames:
		print("--- starting data collection for {}".format(username))
		user = Retweet_Grabber(username,60)
		user.put_tweets()

