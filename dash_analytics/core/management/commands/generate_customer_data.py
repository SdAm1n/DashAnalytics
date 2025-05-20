from django.core.management.base import BaseCommand
from core.customer_data_generator import generate_customer_behavior_data, generate_sample_sales


class Command(BaseCommand):
    help = 'Generate sample customer behavior data for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument('--sales', type=int, default=1000, help='Number of sales records to generate')
        parser.add_argument('--customers', type=int, default=100, help='Number of customer behavior records to generate')

    def handle(self, *args, **options):
        sales_count = options['sales']
        customers_count = options['customers']
        
        self.stdout.write(self.style.SUCCESS('Starting sample data generation...'))
        
        # Generate sales data first (needed for behavior analysis)
        generated_sales = generate_sample_sales(sales_count)
        self.stdout.write(self.style.SUCCESS(f'Sales data: {generated_sales} records'))
        
        # Then generate customer behavior data
        generated_customers = generate_customer_behavior_data(customers_count)
        self.stdout.write(self.style.SUCCESS(f'Customer behavior data: {generated_customers} records'))
        
        self.stdout.write(self.style.SUCCESS('Sample data generation completed!'))
