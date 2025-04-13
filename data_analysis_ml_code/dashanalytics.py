# -*- coding: utf-8 -*-
"""dashanalytics.ipynb


Original file is located at
    https://colab.research.google.com/drive/1oKzGNdKpIaOMGZq4O8d4_iIWzxZk6fAm

# **Preprocess the Data**
"""

# Import library
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Connect with drive
from google.colab import drive

drive.mount('/content/drive',  force_remount=True)

# Import dataset from drive
df = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/swe/synthetic_online_retail_data.csv')

print(df.head())

print(df)

# Displaying DataFrame info
df.info()

# Displaying DataFrame column data types
df.dtypes

print(df.describe())

# Convert date columns
df['InvoiceDate'] = pd.to_datetime(df['order_date'])

# Drop nulls values
df.dropna(subset=['customer_id', 'product_id', 'order_date', 'category_name', 'product_name', 'quantity', 'price'], inplace=True)

# Remove duplicates
df.drop_duplicates(inplace=True)

# Create derived columns
df['TotalPrice'] = df['quantity'] * df['price']
df['Month'] = df['InvoiceDate'].dt.to_period('M')
df['Week'] = df['InvoiceDate'].dt.isocalendar().week
df['Year'] = df['InvoiceDate'].dt.year
df['Quarter'] = df['InvoiceDate'].dt.quarter

print(df)

"""#  **1. Sales Trend**"""

# Weekly Sales
weekly_sales = df.groupby('Week')['TotalPrice'].sum().reset_index()
print(weekly_sales)

plt.figure(figsize=(12, 5))
sns.lineplot(data=weekly_sales, x='Week', y='TotalPrice')
plt.title('Weekly Sales Trend')
plt.show()

# Monthly Sales
monthly_sales = df.groupby('Month')['TotalPrice'].sum().reset_index()
monthly_sales['Month'] = monthly_sales['Month'].astype(str)
print(monthly_sales)

plt.figure(figsize=(12, 5))
sns.lineplot(data=monthly_sales, x='Month', y='TotalPrice')
plt.xticks(rotation=45)
plt.title('Monthly Sales Trend')
plt.show()

# yearly sales
yearly_sales = df.groupby('Year')['TotalPrice'].sum().reset_index()
print(yearly_sales)

plt.figure(figsize=(12, 5))
sns.lineplot(data=yearly_sales, x='Year', y='TotalPrice')
plt.title('Yearly Sales Trend')
plt.show()

# yearly sales in percentage
total_sales = yearly_sales.sum()
yearly_sales_percentage = (yearly_sales / total_sales) * 100
print(yearly_sales_percentage)


plt.figure(figsize=(14, 8))
yearly_sales_percentage.plot(kind='bar', color='skyblue')

plt.title('Yearly Sales Percentage')
plt.xlabel('Year')
plt.ylabel('Sales Percentage (%)')
plt.xticks(rotation=45)
plt.grid(axis='y')
plt.tight_layout()
plt.show()

# Seasonal sales trend
seasonal_sales = df.groupby(['Year', 'Quarter'])['TotalPrice'].sum().reset_index()
print(seasonal_sales)

seasonal_sales.plot(x='Year', y='TotalPrice', kind='bar', stacked=True)
plt.title('Seasonal Sales Trend')
plt.xlabel('Year')
plt.ylabel('Total Sales')
plt.xticks(rotation=45)

# monthly sales growth rate
monthly_sales['GrowthRate'] = monthly_sales['TotalPrice'].pct_change() * 100
print(monthly_sales[['Month', 'GrowthRate']])

plt.figure(figsize=(14, 6))
plt.plot(monthly_sales['Month'], monthly_sales['GrowthRate'], marker='o', color='mediumseagreen')

plt.title('Monthly Sales Growth Rate')
plt.xlabel('Month')
plt.ylabel('Growth Rate (%)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()

"""# **Product Performance**"""

# Best-selling products
best_products = df.groupby('product_name')['TotalPrice'].sum().sort_values(ascending=False).head(10)
print(best_products)

plt.figure(figsize=(14, 8))
best_products.plot(kind='barh', color='skyblue')

plt.title('Top 10 Best-Selling Products')
plt.xlabel('Total Sales')
plt.ylabel('Product Name')
# Highest sales at the top
plt.gca().invert_yaxis()
plt.grid(axis='x')
plt.tight_layout()
plt.show()

# Worst-selling products
worst_products = df.groupby('product_name')['TotalPrice'].sum().sort_values(ascending=True).head(10)
print(worst_products)

plt.figure(figsize=(14, 8))
worst_products.plot(kind='barh', color='salmon')

plt.title('Top 10 Worst-Selling Products')
plt.xlabel('Total Sales')
plt.ylabel('Product Name')
plt.grid(axis='x')
plt.tight_layout()
plt.show()

# Volume by brand/category
volume_by_category = df.groupby('category_name')['quantity'].sum().sort_values(ascending=False)
print(volume_by_category)

plt.figure(figsize=(14, 8))
volume_by_category.plot(kind='bar', color='teal')
plt.title('Total Volume Sold by Category')
plt.xlabel('Category')
plt.ylabel('Quantity Sold')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y')
plt.tight_layout()
plt.show()

volume_by_product = df.groupby('product_name')['quantity'].sum().sort_values(ascending=False).head(10)
print(volume_by_product)

plt.figure(figsize=(14, 8))
volume_by_product.plot(kind='barh', color='seagreen')
plt.title('Top 10 Products by Volume Sold')
plt.xlabel('Quantity Sold')
plt.ylabel('Product Name')
plt.gca().invert_yaxis()
plt.grid(axis='x')
plt.tight_layout()
plt.show()

# Avg revenue per product/category
avg_rev_product = df.groupby('product_name')['TotalPrice'].mean().sort_values(ascending=False).head(10)
print(avg_rev_product)

plt.figure(figsize=(14, 8))
avg_rev_product.plot(kind='barh', color='peru')
plt.title('Top 10 Products by Average Revenue')
plt.xlabel('Average Revenue (per sale)')
plt.ylabel('Product Name')
plt.gca().invert_yaxis()
plt.grid(axis='x')
plt.tight_layout()
plt.show()

avg_rev_category = df.groupby('category_name')['TotalPrice'].mean().sort_values(ascending=False)
print(avg_rev_category)


plt.figure(figsize=(14, 8))
avg_rev_category.plot(kind='bar', color='seagreen')
plt.title('Average Revenue per Category')
plt.xlabel('Category')
plt.ylabel('Average Revenue (per sale)')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y')
plt.tight_layout()
plt.show()

# Highest profit category
profit_category = df.groupby('category_name')['TotalPrice'].sum().sort_values(ascending=False).head()
print(profit_category)

plt.figure(figsize=(10, 6))
profit_category.plot(kind='bar', color='brown')
plt.title('Top 5 Highest Profit Categories')
plt.xlabel('Category')
plt.ylabel('Total Revenue')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y')
plt.tight_layout()
plt.show()

"""# **Customer Demographics**"""

# Distribution by age
df['Age Group'] = pd.cut(df['age'], bins=[0, 18, 30, 40, 50, 60, 100],
                         labels=['<18', '18-30', '30-40', '40-50', '50-60', '60+'])
age_distribution = df['Age Group'].value_counts().sort_index()
print("Age distribution:")
print(age_distribution)

plt.figure(figsize=(8, 6))
age_distribution.plot(kind='bar', title='Customer Distribution by Age Group')
plt.xlabel('Age Group')
plt.ylabel('Number of Customers')
plt.xticks(rotation=45, ha='right')
plt.grid(True)
plt.show()

# Gender distribution
gender_distribution = df['gender'].value_counts()
print("Gender distributio:")
print(gender_distribution)
gender_distribution_p = df['gender'].value_counts(normalize=True) * 100
print("Gender distribution in percentage:")
print(gender_distribution_p)
plt.figure(figsize=(8, 6))
gender_distribution.plot(kind='pie', autopct='%1.1f%%', title='Customer Distribution by Gender')
plt.ylabel('')
plt.show()

# Gender distribution by age
df['Age Group'] = pd.cut(df['age'], bins=[0, 18, 30, 40, 50, 60, 100],
                         labels=['<18', '18-30', '30-40', '40-50', '50-60', '60+'])

# Count the number of customers by Age Group and Gender
gender_age_distribution = df.groupby(['Age Group', 'gender']).size().unstack()

print("Gender distribution by Age Group:")
print(gender_age_distribution)

# Plot the gender distribution as grouped bars
gender_age_distribution.plot(kind='bar', figsize=(10, 6), color=['teal', 'coral'])
plt.title('Gender Distribution by Age Group')
plt.xlabel('Age Group')
plt.ylabel('Number of Customers')
plt.xticks(rotation=45, ha='right')
plt.legend(title='Gender')
plt.tight_layout()
plt.grid(axis='y')
plt.show()

df

age_amount_distribution = df.groupby('Age Group')['TotalPrice'].sum()
print("Total Amount by Age Group:")
print(age_amount_distribution)
plt.figure(figsize=(10, 6))
age_amount_distribution.plot(kind='bar', color='skyblue', title='Total Sales by Age Group')
plt.xlabel('Age Group')
plt.ylabel('Total Amount')
plt.xticks(rotation=45, ha='right')
plt.grid(True)
plt.tight_layout()
plt.show()

# Group by Gender and Age Group,
gender_age_sales = df.groupby(['gender', 'Age Group'])['TotalPrice'].sum().unstack()

print("Total Sales by Gender and Age Group:")
print(gender_age_sales)

# Plot total sales by gender and age group
gender_age_sales.plot(kind='bar', figsize=(12, 7), color=['skyblue', 'salmon', 'lightgreen', 'orange', 'purple', 'gray'])
plt.title('Total Sales by Gender and Age Group')
plt.xlabel('Gender')
plt.ylabel('Total Sales')
plt.xticks(rotation=0)  # Rotate x-axis labels for better readability
plt.legend(title='Age Group')
plt.grid(axis='y')
plt.tight_layout()
plt.show()

"""# **Geographical insights**"""

# City by highest customers
city_dist = df['city'].value_counts().head(10)
print(city_dist)

plt.figure(figsize=(10, 6))
city_dist.plot(kind='bar', color='skyblue', title='Top 10 Cities by Customer Count')
plt.xlabel('City')
plt.ylabel('Number of Customers')
plt.xticks(rotation=45, ha='right')

# City by lowest customer
city_dist = df['city'].value_counts().tail(10)
print(city_dist)

plt.figure(figsize=(10, 6))
city_dist.plot(kind='bar', color='skyblue', title='Bottom 10 Cities by Customer Count')
plt.xlabel('City')
plt.ylabel('Number of Customers')

# city by highest profit
city_profit = df.groupby('city')['TotalPrice'].sum().sort_values(ascending=False).head(10)
print(city_profit)

plt.figure(figsize=(10, 6))
city_profit.plot(kind='bar', color='skyblue', title='Top 10 Cities by Total Profit')
plt.xlabel('City')
plt.ylabel('Total Profit')

# city by loss amount
city_loss = df.groupby('city')['TotalPrice'].sum().sort_values(ascending=True).head(10)
print(city_loss)

plt.figure(figsize=(10, 6))
city_loss.plot(kind='bar', color='skyblue', title='Top 10 Cities by Loss Amount')
plt.xlabel('City')
plt.ylabel('Loss Amount')

"""# **Customer Behavior**"""

# Items bought together
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

basket = df.groupby('customer_id')['product_name'].apply(list).values.tolist()
te = TransactionEncoder()
te_array = te.fit_transform(basket)
df_tf = pd.DataFrame(te_array, columns=te.columns_)
frequent_items = apriori(df_tf, min_support=0.02, use_colnames=True)
rules = association_rules(frequent_items, metric="lift", min_threshold=1.0)

print(frequent_items.head(10))

# Average review score
avg_score = df.groupby("category_name")["review_score"].mean().sort_values(ascending=False)
print(avg_score)

# review score by gender
review_score_gender = df.groupby(['gender', 'review_score']).size().unstack()
print(review_score_gender)

# review score by product
review_score_product = df.groupby("product_name")["review_score"].mean().sort_values(ascending=False)
print(review_score_product)

# review score by category
review_score_category = df.groupby("category_name")["review_score"].mean().sort_values(ascending=False)
print(review_score_category)

# customer sentiment analysis
from textblob import TextBlob

df['Sentiment'] = df['review_score'].apply(lambda x: 'Positive' if x >= 4 else 'Negative' if x <= 2 else 'Neutral')
print(df[['review_score', 'Sentiment']])

plt.figure(figsize=(8, 5))
sns.countplot(data=df, x='Sentiment', order=['Positive', 'Neutral', 'Negative'], palette='viridis')
plt.title('Customer Sentiment Distribution')
plt.xlabel('Sentiment')
plt.ylabel('Number of Reviews')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

"""# **Prediction and Correlation**"""

# predict future sales trend
from prophet import Prophet

# Prepare data for Prophet
sales_df = monthly_sales.rename(columns={'Month': 'ds', 'TotalPrice': 'y'})

model = Prophet()
model.fit(sales_df)

# Predict next 6 months
future = model.make_future_dataframe(periods=6, freq='M')
forecast = model.predict(future)

# Plot forecast
model.plot(forecast);

# predict future top product
# Group by product and calculate total sales
product_sales = df.groupby('product_name')['TotalPrice'].sum().reset_index()

# Sort top products
top_products = product_sales.sort_values('TotalPrice', ascending=False).head(10)

# Plot
import seaborn as sns
import matplotlib.pyplot as plt

plt.figure(figsize=(10,5))
sns.barplot(data=top_products, x='TotalPrice', y='product_name', palette='viridis')
plt.title('Top 10 Products by Total Sales')
plt.xlabel('Total Sales')
plt.ylabel('Product Name')
plt.show()

# Compute correlation on all numeric columns automatically
corr_matrix = df.corr(numeric_only=True)

# Plot heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f")
plt.title('Correlation Heatmap of All Numeric Columns')
plt.show()

