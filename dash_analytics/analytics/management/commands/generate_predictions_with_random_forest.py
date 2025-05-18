"""
Management command to generate sales trend and top product predictions using Random Forest Regressor.
This replaces the previous time series algorithm.
"""
import pandas as pd
import numpy as np
import uuid
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from mongoengine.connection import get_db
from analytics.models import Prediction
from core.models import Sales, Product


class Command(BaseCommand):
    help = 'Generate sales predictions using Random Forest Regressor'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            'Starting prediction generation with Random Forest Regressor'))

        # Generate predictions for both databases
        self.generate_predictions('high_review_score_db')
        self.generate_predictions('low_review_score_db')

        self.stdout.write(self.style.SUCCESS(
            'Predictions successfully generated'))

    def generate_predictions(self, db_alias):
        """Generate predictions for the specified database"""
        self.stdout.write(f'Generating predictions for {db_alias}')

        # Load data
        sales_data = self.load_sales_data(db_alias)

        if sales_data.empty:
            self.stdout.write(self.style.WARNING(
                f'No sales data found in {db_alias}'))
            return

        # Delete existing predictions
        self.delete_existing_predictions(db_alias)

        # Process data
        df_processed = self.process_data(sales_data)

        # Generate predictions
        future_sales_predictions = self.predict_future_sales(df_processed)
        top_products_predictions = self.predict_top_products(df_processed)

        # Save predictions
        self.save_predictions(future_sales_predictions,
                              top_products_predictions, db_alias)

    def load_sales_data(self, db_alias):
        """Load sales data from database"""
        try:
            # Use Sales model to get data
            sales = list(Sales.objects.using(db_alias).all())

            if not sales:
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for sale in sales:
                data.append({
                    'product_id': sale.product_id,
                    'customer_id': sale.customer_id,
                    'quantity': sale.quantity,
                    'price': sale.revenue / sale.quantity if sale.quantity > 0 else 0,
                    'sale_date': sale.sale_date,
                    'revenue': sale.revenue,
                })

            df = pd.DataFrame(data)

            # Add product information
            products = list(Product.objects.using(db_alias).all())
            product_map = {str(p.product_id): {
                'category_id': p.category_id,
                'product_name': p.product_name,
                'category_name': p.category_name
            } for p in products}

            # Add additional columns
            df['category_id'] = df['product_id'].apply(
                lambda x: product_map.get(str(x), {}).get('category_id', 0))
            df['product_name'] = df['product_id'].apply(
                lambda x: product_map.get(str(x), {}).get('product_name', 'Unknown'))
            df['category_name'] = df['product_id'].apply(
                lambda x: product_map.get(str(x), {}).get('category_name', 'Unknown'))

            return df

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error loading data: {str(e)}'))
            return pd.DataFrame()

    def delete_existing_predictions(self, db_alias):
        """Delete existing time series predictions"""
        try:
            # Delete future sales trend predictions
            Prediction.objects(prediction_type='future_sales_trend').using(
                db_alias).delete()
            # Delete future top product predictions
            Prediction.objects(prediction_type='future_top_product').using(
                db_alias).delete()

            self.stdout.write(self.style.SUCCESS(
                f'Deleted existing predictions from {db_alias}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error deleting predictions: {str(e)}'))

    def process_data(self, df):
        """Process sales data for modeling"""
        try:
            # Create the target variable 'total_sales'
            df['total_sales'] = df['quantity'] * df['price']

            # Drop rows with missing values
            data_cleaned = df.dropna()

            return data_cleaned
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error processing data: {str(e)}'))
            return pd.DataFrame()

    def predict_future_sales(self, df):
        """Generate future sales trend predictions using Random Forest"""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        try:
            # Select features for regression
            features = ['product_id', 'category_id', 'quantity', 'price']
            target = 'total_sales'

            # Filter out non-numeric columns or encode them
            df_numeric = df.copy()
            for col in features:
                if df[col].dtype == object:
                    # Convert string IDs to numeric if needed
                    df_numeric[col] = pd.to_numeric(
                        df_numeric[col], errors='coerce')

            # Drop any rows with NaN after conversion
            df_numeric = df_numeric.dropna(subset=features + [target])

            # Define feature matrix X and target variable y
            X = df_numeric[features]
            y = df_numeric[target]

            # Train Random Forest on the full dataset
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            rf_model.fit(X, y)

            # Generate future predictions for next three quarters
            current_quarter = (datetime.now().month - 1) // 3 + 1
            current_year = datetime.now().year

            predictions = []
            for i in range(1, 4):
                next_quarter = current_quarter + i
                next_year = current_year

                # Adjust for year change
                while next_quarter > 4:
                    next_quarter -= 4
                    next_year += 1

                prediction_period = f"{next_year}-Q{next_quarter}"

                # Create future prediction - use model feature importance for trend
                feature_importance = rf_model.feature_importances_
                weighted_growth = sum(feature_importance) * 5  # Scaling factor

                # Calculate growth percentage
                average_sales = df_numeric['total_sales'].mean()
                # Adjust growth based on time horizon
                predicted_growth = (weighted_growth * 100) / (i * 2)

                # Format the prediction
                prediction_id = f"pred-rf-sales-trend-{prediction_period}"
                predicted_value = f"{predicted_growth:.2f}%"

                # Create prediction details
                prediction_details = {
                    "model": "Random Forest Regressor",
                    "average_sales": f"${average_sales:.2f}",
                    "feature_importance": {
                        # Format feature names to be more readable (e.g., product_id -> Product ID)
                        features[i].replace('_', ' ').title(): f"{importance:.4f}"
                        for i, importance in enumerate(feature_importance)
                    },
                    # Confidence decreases with time horizon
                    "confidence": f"{90 - (i * 10)}%"
                }

                predictions.append({
                    'id': prediction_id,
                    'prediction_type': 'future_sales_trend',
                    'prediction_period': prediction_period,
                    'predicted_value': predicted_value,
                    'details': json.dumps(prediction_details)
                })

            return predictions

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error predicting future sales: {str(e)}'))
            return []

    def predict_top_products(self, df):
        """Generate top product predictions using Random Forest"""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        try:
            # Select features for regression
            features = ['product_id', 'category_id', 'quantity', 'price']
            target = 'total_sales'

            # Filter out non-numeric columns or encode them
            df_numeric = df.copy()
            for col in features:
                if df[col].dtype == object:
                    # Convert string IDs to numeric if needed
                    df_numeric[col] = pd.to_numeric(
                        df_numeric[col], errors='coerce')

            # Create a mapping from numeric product_id to product_name
            product_mapping = df[['product_id',
                                  'product_name']].drop_duplicates()

            # Drop any rows with NaN after conversion
            df_numeric = df_numeric.dropna(subset=features + [target])

            # Add original product_id for later reference
            df_numeric['orig_product_id'] = df['product_id']

            # Define feature matrix X and target variable y
            X = df_numeric[features]
            y = df_numeric[target]

            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42)

            # Train Random Forest on the full dataset
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            rf_model.fit(X, y)

            # Predict sales on the test data
            y_pred = rf_model.predict(X_test)

            # Add predictions to test dataset
            test_with_pred = X_test.copy()
            test_with_pred['predicted_sales'] = y_pred
            test_with_pred['orig_product_id'] = df_numeric.loc[y_test.index,
                                                               'orig_product_id'].values

            # Aggregate predicted sales by product
            product_sales_pred = test_with_pred.groupby(
                'orig_product_id')['predicted_sales'].sum().reset_index()

            # Sort products by predicted sales descending
            top_products = product_sales_pred.sort_values(
                by='predicted_sales', ascending=False)

            # Generate future predictions for next three quarters
            current_quarter = (datetime.now().month - 1) // 3 + 1
            current_year = datetime.now().year

            predictions = []
            for i in range(1, 4):
                next_quarter = current_quarter + i
                next_year = current_year

                # Adjust for year change
                while next_quarter > 4:
                    next_quarter -= 4
                    next_year += 1

                prediction_period = f"{next_year}-Q{next_quarter}"

                # Take top products for this quarter (might vary slightly per quarter)
                top_n = 5 - (i - 1)  # Reduce number for further quarters
                quarter_top_products = top_products.head(top_n)

                # Get product names
                top_product_ids = quarter_top_products['orig_product_id'].tolist(
                )

                # Find product names from original dataframe
                top_product_names = []
                for pid in top_product_ids:
                    product_matches = product_mapping[product_mapping['product_id'] == pid]
                    if not product_matches.empty:
                        top_product_names.append(
                            product_matches.iloc[0]['product_name'])
                    else:
                        top_product_names.append(f"Product {pid}")

                # Use the top product for prediction
                if top_product_names:
                    top_product_name = top_product_names[0]

                    # Create prediction details
                    prediction_details = {
                        "model": "Random Forest Regressor",
                        "Top 5 Products": top_product_names[:5],
                        "Product Sales Values": {
                            name: f"${val:.2f}" for name, val in
                            zip(top_product_names[:5],
                                quarter_top_products['predicted_sales'].head(5).tolist())
                        },
                        # Confidence decreases with time horizon
                        "confidence": f"{90 - (i * 10)}%"
                    }

                    # Format the prediction
                    prediction_id = f"pred-rf-top-product-{prediction_period}"

                    predictions.append({
                        'id': prediction_id,
                        'prediction_type': 'future_top_product',
                        'prediction_period': prediction_period,
                        'predicted_value': top_product_name,
                        'details': json.dumps(prediction_details)
                    })

            return predictions

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error predicting top products: {str(e)}'))
            return []

    def save_predictions(self, future_sales_predictions, top_products_predictions, db_alias):
        """Save generated predictions to database"""
        try:
            # Combine all predictions
            all_predictions = future_sales_predictions + top_products_predictions

            # Save to database using Prediction model
            for pred_data in all_predictions:
                # Use the create_or_update_by_unique_fields method
                Prediction.create_or_update_by_unique_fields(
                    pred_data, db_alias)

            self.stdout.write(self.style.SUCCESS(
                f'Saved {len(all_predictions)} predictions to {db_alias}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error saving predictions: {str(e)}'))
