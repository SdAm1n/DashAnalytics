"""
Generate sample customer behavior data for testing purposes.
This script will create sample customer behavior records if none exist.
"""
from core.models import Customer, Sales, Order, Product
from analytics.models import CustomerBehavior
import random
from datetime import datetime, timedelta
import uuid

def generate_customer_behavior_data(num_records=100):
    """Generate sample customer behavior data for testing"""
    print("Checking existing customer behavior data...")
    
    # Check if we already have data
    existing_count = CustomerBehavior.objects.count()
    if existing_count > 0:
        print(f"Found {existing_count} existing customer behavior records. Skipping generation.")
        return existing_count
        
    print(f"Generating {num_records} customer behavior records...")
    
    # Get existing customers, or create some if needed
    customers = list(Customer.objects)
    if len(customers) < num_records:
        print("Not enough customers found. Creating sample customers...")
        for i in range(len(customers), num_records):
            customer_id = i + 1000  # Start from 1000 to avoid conflicts
            customer = Customer(
                customer_id=customer_id,
                gender=random.choice(['Male', 'Female', 'Non-binary']),
                age=random.randint(18, 80),
                city=f"City{random.randint(1, 20)}"
            )
            customer.save()
        customers = list(Customer.objects)
    
    segments = ['VIP', 'Regular', 'Occasional', 'New', 'At Risk']
    
    # Create customer behavior records
    for i in range(num_records):
        if i < len(customers):
            customer = customers[i]
            
            # Random but realistic data
            total_purchases = random.randint(1, 50)
            avg_purchase = random.uniform(20, 500)
            total_spent = total_purchases * avg_purchase
            purchase_frequency = random.uniform(0.1, 2.0)  # Average purchases per month
            
            # Assign segment based on spending and frequency
            if total_spent > 5000 and purchase_frequency > 1.5:
                segment = 'VIP'
            elif total_spent > 2000 or purchase_frequency > 1.0:
                segment = 'Regular'
            elif total_spent < 500 and purchase_frequency < 0.5:
                segment = 'Occasional'
            elif total_purchases < 3:
                segment = 'New'
            else:
                segment = random.choice(segments)  # Randomize rest
            
            # Create the customer behavior record
            behavior = CustomerBehavior(
                id=str(uuid.uuid4()),
                customer_id=str(customer.customer_id),
                total_purchases=total_purchases,
                total_spent=total_spent,
                purchase_frequency=purchase_frequency,
                customer_segment=segment
            )
            behavior.save()
    
    print(f"Generated {num_records} customer behavior records.")
    return num_records


def generate_sample_sales(num_sales=1000):
    """Generate sample sales data for testing"""
    print("Checking existing sales data...")
    
    # Check if we already have data
    existing_count = Sales.objects.count()
    if existing_count > 0:
        print(f"Found {existing_count} existing sales records. Skipping generation.")
        return existing_count
    
    print(f"Generating {num_sales} sample sales records...")
    
    # Get or create customers
    customers = list(Customer.objects)
    if not customers:
        print("No customers found. Creating sample customers...")
        for i in range(100):
            customer_id = i + 1000  # Start from 1000 to avoid conflicts
            customer = Customer(
                customer_id=customer_id,
                gender=random.choice(['Male', 'Female', 'Non-binary']),
                age=random.randint(18, 80),
                city=f"City{random.randint(1, 20)}"
            )
            customer.save()
        customers = list(Customer.objects)
    
    # Get or create products
    products = list(Product.objects)
    if not products:
        print("No products found. Creating sample products...")
        categories = ['Electronics', 'Clothing', 'Home', 'Books', 'Beauty']
        for i in range(50):
            product_id = i + 2000  # Start from 2000 to avoid conflicts
            category_id = random.randint(1, 5)
            product = Product(
                product_id=product_id,
                category_id=category_id,
                category_name=categories[category_id-1],
                product_name=f"Product {product_id}",
                price=random.uniform(10, 1000)
            )
            product.save()
        products = list(Product.objects)
    
    # Generate sales spanning the last year
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    
    cities = [customer.city for customer in customers]
    
    for i in range(num_sales):
        # Random date within the range
        days_to_add = random.randint(0, 365)
        sale_date = start_date + timedelta(days=days_to_add)
        
        # Random customer and product
        customer = random.choice(customers)
        product = random.choice(products)
        
        # Random quantity between 1 and 5
        quantity = random.randint(1, 5)
        
        # Calculate revenue and profit
        revenue = quantity * float(product.price)
        profit = revenue * random.uniform(0.1, 0.4)  # 10-40% profit margin
        
        # Create the sales record
        sale = Sales(
            id=str(uuid.uuid4()),
            customer_id=str(customer.customer_id),
            product_id=str(product.product_id),
            quantity=quantity,
            sale_date=sale_date,
            revenue=revenue,
            profit=profit,
            city=random.choice(cities)
        )
        sale.save()
    
    print(f"Generated {num_sales} sample sales records.")
    return num_sales


if __name__ == "__main__":
    # This can be run as a standalone script
    generate_sample_sales(1000)
    generate_customer_behavior_data(100)
