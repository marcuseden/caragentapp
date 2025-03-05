from typing import Dict, List
import pandas as pd
from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME

class PriceAnalyzer:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]

    def get_price_statistics(self) -> Dict:
        """Get price statistics by country"""
        pipeline = [
            {
                '$group': {
                    '_id': '$country',
                    'avg_price': {'$avg': '$price'},
                    'min_price': {'$min': '$price'},
                    'max_price': {'$max': '$price'},
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(self.collection.aggregate(pipeline))
        return pd.DataFrame(results)

    def compare_models(self, model: str) -> Dict:
        """Compare prices for specific car models across countries"""
        pipeline = [
            {
                '$match': {'model': model}
            },
            {
                '$group': {
                    '_id': '$country',
                    'avg_price': {'$avg': '$price'},
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(self.collection.aggregate(pipeline))
        return pd.DataFrame(results)

    def find_arbitrage_opportunities(self, min_price_diff: float = 0.2) -> List[Dict]:
        """Find cars with significant price differences between countries"""
        # Group by make/model and compare prices
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'make': '$make',
                        'model': '$model',
                        'year': '$year'
                    },
                    'prices': {
                        '$push': {
                            'country': '$country',
                            'price': '$price'
                        }
                    }
                }
            }
        ]
        
        results = list(self.collection.aggregate(pipeline))
        opportunities = []
        
        for result in results:
            prices = pd.DataFrame(result['prices'])
            if len(prices) >= 2:
                price_diff = (prices['price'].max() - prices['price'].min()) / prices['price'].min()
                if price_diff > min_price_diff:
                    opportunities.append({
                        'make': result['_id']['make'],
                        'model': result['_id']['model'],
                        'year': result['_id']['year'],
                        'price_difference': price_diff,
                        'prices': result['prices']
                    })
                    
        return opportunities 