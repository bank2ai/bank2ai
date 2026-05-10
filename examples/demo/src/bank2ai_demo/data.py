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
        "bban": "1234-56-789012",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": 5420.50,
        "availableBalance": 5420.50,
        "overdraftLimit": 0.0,
        "ownerName": "Alex Demo",
        "product": "Demo Everyday Checking",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Current",
        "isWithdrawalAccount": True,
        "isDefaultAccount": True,
        "openedDate": "2018-04-12",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
    },
    {
        "id": "acc_savings_001",
        "name": "Emergency Fund",
        "accountNumber": "1234-56-789013",
        "bban": "1234-56-789013",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": 15000.00,
        "availableBalance": 15000.00,
        "overdraftLimit": 0.0,
        "ownerName": "Alex Demo",
        "product": "Demo High-Yield Savings",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Savings",
        "isWithdrawalAccount": True,
        "isDefaultAccount": False,
        "openedDate": "2020-09-03",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
    },
    {
        "id": "acc_credit_001",
        "name": "Visa Credit Card",
        "accountNumber": "1234-56-789014",
        "maskedPan": "411111xxxxxx4242",
        "bic": "DEMOUS33XXX",
        "currency": "USD",
        "balance": -850.25,
        "availableBalance": 4149.75,
        "overdraftLimit": 5000.0,
        "ownerName": "Alex Demo",
        "product": "Demo Visa Signature",
        "status": "Enabled",
        "usage": "Private",
        "accountType": "Credit",
        "isWithdrawalAccount": False,
        "isDefaultAccount": False,
        "openedDate": "2021-06-18",
        "balanceUpdatedAt": "2024-03-15T08:30:00Z",
        "statementBalance": 1240.75,
        "minimumPaymentDue": 35.00,
        "paymentDueDate": "2024-04-05",
        "statementClosingDate": "2024-04-12",
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
        "accountId": "acc_checking_001",
        "description": "Monthly Salary",
        "amount": 4500.00,
        "bookingDate": (today - timedelta(days=5)).isoformat(),
        "categoryId": "cat_income",
    })

    transactions.append({
        "id": "tx_002",
        "accountId": "acc_checking_001",
        "description": "Rent Payment",
        "amount": -1200.00,
        "bookingDate": (today - timedelta(days=3)).isoformat(),
        "categoryId": "cat_housing",
    })

    # Groceries
    grocery_stores = ["Whole Foods", "Trader Joe's", "Safeway", "Local Market"]
    for i, days_ago in enumerate([2, 7, 14, 21, 28, 35]):
        transactions.append({
            "id": f"tx_grocery_{i:03d}",
            "accountId": "acc_checking_001",
            "description": grocery_stores[i % len(grocery_stores)],
            "amount": -85.50 - (i * 5),
            "bookingDate": (today - timedelta(days=days_ago)).isoformat(),
            "categoryId": "cat_groceries",
        })

    # Transportation
    transactions.extend([
        {
            "id": "tx_gas_001",
            "accountId": "acc_checking_001",
            "description": "Shell Gas Station",
            "amount": -45.00,
            "bookingDate": (today - timedelta(days=4)).isoformat(),
            "categoryId": "cat_transportation",
        },
        {
            "id": "tx_transit_001",
            "accountId": "acc_checking_001",
            "description": "Monthly Metro Pass",
            "amount": -120.00,
            "bookingDate": (today - timedelta(days=1)).isoformat(),
            "categoryId": "cat_transportation",
        },
    ])

    # Entertainment (charged to credit card)
    transactions.extend([
        {
            "id": "tx_netflix_001",
            "accountId": "acc_credit_001",
            "description": "Netflix Subscription",
            "amount": -15.99,
            "bookingDate": (today - timedelta(days=10)).isoformat(),
            "categoryId": "cat_entertainment",
        },
        {
            "id": "tx_movie_001",
            "accountId": "acc_credit_001",
            "description": "Cinema Tickets",
            "amount": -32.00,
            "bookingDate": (today - timedelta(days=12)).isoformat(),
            "categoryId": "cat_entertainment",
        },
        {
            "id": "tx_spotify_001",
            "accountId": "acc_credit_001",
            "description": "Spotify Premium",
            "amount": -9.99,
            "bookingDate": (today - timedelta(days=8)).isoformat(),
            "categoryId": "cat_entertainment",
        },
    ])

    # Utilities
    transactions.extend([
        {
            "id": "tx_electric_001",
            "accountId": "acc_checking_001",
            "description": "Electric Company",
            "amount": -85.00,
            "bookingDate": (today - timedelta(days=15)).isoformat(),
            "categoryId": "cat_utilities",
        },
        {
            "id": "tx_internet_001",
            "accountId": "acc_checking_001",
            "description": "Internet Service Provider",
            "amount": -60.00,
            "bookingDate": (today - timedelta(days=18)).isoformat(),
            "categoryId": "cat_utilities",
        },
    ])

    # Dining (charged to credit card)
    restaurants = ["Pizza Place", "Sushi Bar", "Burger Joint", "Thai Restaurant", "Coffee Shop"]
    for i, days_ago in enumerate([1, 6, 9, 13, 20, 25, 30]):
        transactions.append({
            "id": f"tx_dining_{i:03d}",
            "accountId": "acc_credit_001",
            "description": restaurants[i % len(restaurants)],
            "amount": -25.00 - (i * 3),
            "bookingDate": (today - timedelta(days=days_ago)).isoformat(),
            "categoryId": "cat_dining",
        })

    # Healthcare
    transactions.append({
        "id": "tx_pharmacy_001",
        "accountId": "acc_checking_001",
        "description": "Pharmacy Co-pay",
        "amount": -20.00,
        "bookingDate": (today - timedelta(days=22)).isoformat(),
        "categoryId": "cat_healthcare",
    })

    # Shopping (charged to credit card)
    transactions.extend([
        {
            "id": "tx_amazon_001",
            "accountId": "acc_credit_001",
            "description": "Amazon.com",
            "amount": -78.50,
            "bookingDate": (today - timedelta(days=11)).isoformat(),
            "categoryId": "cat_shopping",
        },
        {
            "id": "tx_clothing_001",
            "accountId": "acc_credit_001",
            "description": "Clothing Store",
            "amount": -125.00,
            "bookingDate": (today - timedelta(days=16)).isoformat(),
            "categoryId": "cat_shopping",
        },
    ])

    # Foreign-currency transactions: amount is in the user's default currency
    # (USD here); originalCurrency / originalAmount carry the original.
    transactions.extend([
        {
            "id": "tx_paris_dining_001",
            "accountId": "acc_credit_001",
            "description": "Le Petit Bistro, Paris",
            "amount": -54.20,
            "originalCurrency": "EUR",
            "originalAmount": -49.80,
            "bookingDate": (today - timedelta(days=17)).isoformat(),
            "categoryId": "cat_dining",
        },
        {
            "id": "tx_london_shopping_001",
            "accountId": "acc_credit_001",
            "description": "Selfridges, London",
            "amount": -210.45,
            "originalCurrency": "GBP",
            "originalAmount": -165.00,
            "bookingDate": (today - timedelta(days=24)).isoformat(),
            "categoryId": "cat_shopping",
        },
    ])

    # Sort by date (newest first)
    transactions.sort(key=lambda x: x["bookingDate"], reverse=True)

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
