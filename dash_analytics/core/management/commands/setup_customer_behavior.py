from django.core.management.base import BaseCommand
from core.customer_data_generator import generate_customer_behavior_data, generate_sample_sales
from core.models import Sales, Product, Customer
from analytics.models import CustomerBehavior
import random
import uuid
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Generate sample data for customer behavior analysis'

    def add_arguments(self, parser):
        parser.add_argument('--sales', type=int, default=200, 
                            help='Number of sales records to generate')
        parser.add_argument('--customers', type=int, default=50, 
                            help='Number of customer behavior records to generate')
        parser.add_argument('--clear', action='store_true', 
                            help='Clear existing customer behavior data before generating new data')

    def handle(self, *args, **options):
        sales_count = options['sales']
        customers_count = options['customers']
        clear_existing = options['clear']
        
        self.stdout.write(self.style.SUCCESS('Starting customer behavior data generation...'))
        
        # Clear existing data if requested
        if clear_existing:
            self.stdout.write("Clearing existing customer behavior data...")
            CustomerBehavior.objects.delete()
            self.stdout.write(self.style.SUCCESS("Existing customer behavior data cleared."))
        
        # Generate sales data first (needed for behavior analysis)
        generated_sales = self.ensure_sales_data(sales_count)
        self.stdout.write(self.style.SUCCESS(f'Sales data: {generated_sales} records available'))
        
        # Then generate customer behavior data
        generated_customers = generate_customer_behavior_data(customers_count)
        self.stdout.write(self.style.SUCCESS(f'Customer behavior data: {generated_customers} records generated/available'))
        
        # Generate additional metrics for purchase time analysis
        self.generate_purchase_time_distribution()
        
        self.stdout.write(self.style.SUCCESS('Customer behavior data generation completed!'))
    
    def ensure_sales_data(self, min_count):
        """Ensure we have enough sales data for analysis"""
        existing_count = Sales.objects.count()
        
        if existing_count >= min_count:
            return existing_count
        
        # We need to generate more sales data
        to_generate = min_count - existing_count
        self.stdout.write(f"Generating {to_generate} additional sales records...")
        
        # Use the existing function or generate our own data
        generated = generate_sample_sales(to_generate)
        
        # Verify data was generated
        new_count = Sales.objects.count()
        return new_count
    
    def generate_purchase_time_distribution(self):
        """Generate purchase time distribution data for the time analysis chart"""
        sales = Sales.objects.all()
        
        if not sales:
            self.stdout.write(self.style.WARNING("No sales data available for time analysis."))
            return
        
        # Update sales data to have a more realistic time distribution
        # This makes the time analysis charts more meaningful
        
        # Preferred hours: morning (8-10), lunch (12-13), evening (17-20)
        peak_hours = [8, 9, 10, 12, 13, 17, 18, 19, 20]
        
        # Preferred days: Friday, Saturday, Sunday
        peak_days = [4, 5, 6]  # 0=Monday, 6=Sunday
        
        self.stdout.write("Updating sales timestamps for realistic time distribution...")
        count = 0
        
        # We'll only update a subset of all sales to maintain some randomness
        sales_to_update = min(500, len(sales))
        for sale in list(sales)[:sales_to_update]:
            original_date = sale.sale_date
            
            # 70% of sales happen during peak hours
            if random.random() < 0.7:
                hour = random.choice(peak_hours)
            else:
                hour = random.randint(8, 22)  # Normal store hours
            
            # 60% of sales happen during peak days
            if random.random() < 0.6:
                # Keep the same week but change the day to a peak day
                days_to_add = random.choice(peak_days) - original_date.weekday()
                if days_to_add < 0:
                    days_to_add += 7  # Move to next week
                
                new_date = original_date + timedelta(days=days_to_add)
            else:
                new_date = original_date  # Keep original day
            
            # Set the new date with preferred hour
            new_datetime = datetime(
                year=new_date.year,
                month=new_date.month,
                day=new_date.day,
                hour=hour,
                minute=random.randint(0, 59)
            )
            
            # Update the sale date
            sale.sale_date = new_datetime
            sale.save()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Updated {count} sales records with realistic time distribution."))
