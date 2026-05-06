"""Hardcoded test data for bank2ai demo server.

This module provides realistic banking test data that can be used
to demonstrate the bank2ai specification without requiring a real bank.
"""

from datetime import date, timedelta

# Test accounts
ACCOUNTS = [
    {
        "id": "acc_checking_001",
        "name": "Main Checking",
        "accountNumber": "1234-56-789012",
        "currency": "USD",
        "balance": 5420.50,
        "availableBalance": 5420.50,
        "overdraftLimit": 0.0,
        "isWithdrawalAccount": True,
        "isDefaultAccount": True,
        "accountType": "Current",
    },
    {
        "id": "acc_savings_001",
        "name": "Emergency Fund",
        "accountNumber": "1234-56-789013",
        "currency": "USD",
        "balance": 15000.00,
        "availableBalance": 15000.00,
        "overdraftLimit": 0.0,
        "isWithdrawalAccount": True,
        "isDefaultAccount": False,
        "accountType": "Savings",
    },
    {
        "id": "acc_credit_001",
        "name": "Visa Credit Card",
        "accountNumber": "1234-56-789014",
        "currency": "USD",
        "balance": -850.25,
        "availableBalance": 4149.75,
        "overdraftLimit": 5000.0,
        "isWithdrawalAccount": False,
        "isDefaultAccount": False,
        "accountType": "Credit",
    },
]

# Generate transactions for the last 90 days
def generate_transactions():
    """Generate realistic transaction history."""
    transactions = []
    today = date.today()

    # Recurring monthly transactions
    transactions.append({
        "id": "tx_001",
        "account_id": "acc_checking_001",
        "description": "Monthly Salary",
        "amount": 4500.00,
        "transaction_date": (today - timedelta(days=5)).isoformat(),
        "category": "Income",
    })

    transactions.append({
        "id": "tx_002",
        "account_id": "acc_checking_001",
        "description": "Rent Payment",
        "amount": -1200.00,
        "transaction_date": (today - timedelta(days=3)).isoformat(),
        "category": "Housing",
    })

    # Groceries
    grocery_stores = ["Whole Foods", "Trader Joe's", "Safeway", "Local Market"]
    for i, days_ago in enumerate([2, 7, 14, 21, 28, 35]):
        transactions.append({
            "id": f"tx_grocery_{i:03d}",
            "account_id": "acc_checking_001",
            "description": grocery_stores[i % len(grocery_stores)],
            "amount": -85.50 - (i * 5),
            "transaction_date": (today - timedelta(days=days_ago)).isoformat(),
            "category": "Groceries",
        })

    # Transportation
    transactions.extend([
        {
            "id": "tx_gas_001",
            "account_id": "acc_checking_001",
            "description": "Shell Gas Station",
            "amount": -45.00,
            "transaction_date": (today - timedelta(days=4)).isoformat(),
            "category": "Transportation",
        },
        {
            "id": "tx_transit_001",
            "account_id": "acc_checking_001",
            "description": "Monthly Metro Pass",
            "amount": -120.00,
            "transaction_date": (today - timedelta(days=1)).isoformat(),
            "category": "Transportation",
        },
    ])

    # Entertainment (charged to credit card)
    transactions.extend([
        {
            "id": "tx_netflix_001",
            "account_id": "acc_credit_001",
            "description": "Netflix Subscription",
            "amount": -15.99,
            "transaction_date": (today - timedelta(days=10)).isoformat(),
            "category": "Entertainment",
        },
        {
            "id": "tx_movie_001",
            "account_id": "acc_credit_001",
            "description": "Cinema Tickets",
            "amount": -32.00,
            "transaction_date": (today - timedelta(days=12)).isoformat(),
            "category": "Entertainment",
        },
        {
            "id": "tx_spotify_001",
            "account_id": "acc_credit_001",
            "description": "Spotify Premium",
            "amount": -9.99,
            "transaction_date": (today - timedelta(days=8)).isoformat(),
            "category": "Entertainment",
        },
    ])

    # Utilities
    transactions.extend([
        {
            "id": "tx_electric_001",
            "account_id": "acc_checking_001",
            "description": "Electric Company",
            "amount": -85.00,
            "transaction_date": (today - timedelta(days=15)).isoformat(),
            "category": "Utilities",
        },
        {
            "id": "tx_internet_001",
            "account_id": "acc_checking_001",
            "description": "Internet Service Provider",
            "amount": -60.00,
            "transaction_date": (today - timedelta(days=18)).isoformat(),
            "category": "Utilities",
        },
    ])

    # Dining (charged to credit card)
    restaurants = ["Pizza Place", "Sushi Bar", "Burger Joint", "Thai Restaurant", "Coffee Shop"]
    for i, days_ago in enumerate([1, 6, 9, 13, 20, 25, 30]):
        transactions.append({
            "id": f"tx_dining_{i:03d}",
            "account_id": "acc_credit_001",
            "description": restaurants[i % len(restaurants)],
            "amount": -25.00 - (i * 3),
            "transaction_date": (today - timedelta(days=days_ago)).isoformat(),
            "category": "Dining",
        })

    # Healthcare
    transactions.append({
        "id": "tx_pharmacy_001",
        "account_id": "acc_checking_001",
        "description": "Pharmacy Co-pay",
        "amount": -20.00,
        "transaction_date": (today - timedelta(days=22)).isoformat(),
        "category": "Healthcare",
    })

    # Shopping (charged to credit card)
    transactions.extend([
        {
            "id": "tx_amazon_001",
            "account_id": "acc_credit_001",
            "description": "Amazon.com",
            "amount": -78.50,
            "transaction_date": (today - timedelta(days=11)).isoformat(),
            "category": "Shopping",
        },
        {
            "id": "tx_clothing_001",
            "account_id": "acc_credit_001",
            "description": "Clothing Store",
            "amount": -125.00,
            "transaction_date": (today - timedelta(days=16)).isoformat(),
            "category": "Shopping",
        },
    ])

    # Sort by date (newest first)
    transactions.sort(key=lambda x: x["transaction_date"], reverse=True)

    return transactions

TRANSACTIONS = generate_transactions()

# Categories
CATEGORIES = [
    {"id": "cat_income", "name": "Income"},
    {"id": "cat_housing", "name": "Housing"},
    {"id": "cat_groceries", "name": "Groceries"},
    {"id": "cat_transportation", "name": "Transportation"},
    {"id": "cat_entertainment", "name": "Entertainment"},
    {"id": "cat_utilities", "name": "Utilities"},
    {"id": "cat_dining", "name": "Dining"},
    {"id": "cat_healthcare", "name": "Healthcare"},
    {"id": "cat_shopping", "name": "Shopping"},
]

# Recipients
RECIPIENTS = [
    {
        "id": "rcpt_001",
        "name": "Jane Smith",
        "accountNumber": "5678-90-123456",
        "accountNumberType": "Domestic",
        "bankInfo": "Demo Bank",
        "paymentType": "Domestic",
        "socialSecurityNumber": "123-45-6789",
        "address": "456 Oak Ave, City, State 12345",
        "isFavorite": True,
        "description": "Friend",
    },
    {
        "id": "rcpt_002",
        "name": "John Doe",
        "accountNumber": "5678-90-123457",
        "accountNumberType": "Domestic",
        "bankInfo": "Demo Bank",
        "paymentType": "Domestic",
        "socialSecurityNumber": "234-56-7890",
        "address": "789 Elm St, City, State 12345",
        "isFavorite": False,
        "description": "Contractor",
    },
    {
        "id": "rcpt_003",
        "name": "Alice Johnson",
        "accountNumber": "5678-90-123458",
        "accountNumberType": "Domestic",
        "bankInfo": "Demo Bank",
        "paymentType": "Domestic",
        "socialSecurityNumber": "345-67-8901",
        "address": "321 Pine Rd, City, State 12345",
        "isFavorite": True,
        "description": "Family",
    },
    {
        "id": "rcpt_004",
        "name": "Bob Williams",
        "accountNumber": "5678-90-123459",
        "accountNumberType": "Domestic",
        "bankInfo": "Demo Bank",
        "paymentType": "Domestic",
        "socialSecurityNumber": "456-78-9012",
        "address": "654 Maple Dr, City, State 12345",
        "isFavorite": False,
        "description": "Landlord",
    },
]
